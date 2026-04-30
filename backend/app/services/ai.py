from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytesseract
from PIL import Image, ImageEnhance, ImageOps, ImageStat

from app.services.storage import guess_mime_type


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
HF_VEHICLE_MODEL = os.getenv("HF_VEHICLE_MODEL", "therealcyberlord/stanford-car-vit-patch16").strip()


@dataclass
class IncidentAnalysis:
    clasificacion: str
    prioridad: str
    resumen: str
    especialidad_requerida: str


@dataclass
class VehiclePhotoAnalysis:
    placa: str
    marca: str
    modelo: str
    anio: Optional[int]
    color: str
    resumen: str
    source: str


def fallback_incident_analysis(
    *,
    descripcion: str,
    incident_type: Optional[str] = None,
) -> IncidentAnalysis:
    clasificacion = "Incidente general"
    prioridad = "Baja"
    resumen = "El cliente reporta una falla general pendiente de diagnostico manual."
    especialidad = "general"

    desc_eval = f"{incident_type or ''} {descripcion}".lower()

    if any(token in desc_eval for token in ["no enciende", "bateria", "batería", "click click", "arranca"]):
        clasificacion = "Problema de bateria o sistema electrico"
        prioridad = "Media"
        resumen = (
            "El vehiculo no responde al arranque. Se requiere revision de bateria, alternador o sistema electrico."
        )
        especialidad = "electrico"
    elif any(token in desc_eval for token in ["pinchada", "llanta", "neumatico", "neumático"]):
        clasificacion = "Problema de llanta o neumatico"
        prioridad = "Media"
        resumen = "El vehiculo presenta una falla en llanta o neumatico y requiere asistencia en ruta."
        especialidad = "llantas"
    elif any(token in desc_eval for token in ["humo", "recalentado", "temperatura", "motor"]):
        clasificacion = "Problema de motor o recalentamiento"
        prioridad = "Alta"
        resumen = "Hay indicios de falla de motor o recalentamiento. Requiere atencion prioritaria."
        especialidad = "motor"
    elif any(token in desc_eval for token in ["llaves", "cerrajer", "cerrado"]):
        clasificacion = "Problema de cerrajeria automotriz"
        prioridad = "Media"
        resumen = "El incidente sugiere apertura de vehiculo o asistencia de cerrajeria."
        especialidad = "cerrajeria"
    elif any(token in desc_eval for token in ["choque", "colision", "colisión", "accidente", "golpe"]):
        clasificacion = "Choque o colision"
        prioridad = "Alta"
        resumen = "El incidente parece involucrar colision o golpe. Conviene revisar danos y posible remolque."
        especialidad = "grua"

    return IncidentAnalysis(
        clasificacion=clasificacion,
        prioridad=prioridad,
        resumen=resumen,
        especialidad_requerida=especialidad,
    )


def analyze_incident(
    *,
    descripcion: str,
    incident_type: Optional[str] = None,
    image_paths: Optional[list[str]] = None,
    audio_paths: Optional[list[str]] = None,
    vehicle_photo_path: Optional[str] = None,
) -> IncidentAnalysis:
    if not GEMINI_API_KEY:
        return fallback_incident_analysis(descripcion=descripcion, incident_type=incident_type)

    try:
        return _analyze_with_gemini(
            descripcion=descripcion,
            incident_type=incident_type,
            image_paths=image_paths or [],
            audio_paths=audio_paths or [],
            vehicle_photo_path=vehicle_photo_path,
        )
    except Exception:
        return fallback_incident_analysis(descripcion=descripcion, incident_type=incident_type)


def analyze_vehicle_photos(*, image_paths: list[str], file_names: Optional[list[str]] = None) -> VehiclePhotoAnalysis:
    if not image_paths:
        return VehiclePhotoAnalysis(
            placa="",
            marca="",
            modelo="",
            anio=None,
            color="",
            resumen="No se enviaron fotos para analizar.",
            source="fallback",
        )
    if not GEMINI_API_KEY:
        try:
            return _analyze_vehicle_with_best_fallback(image_paths=image_paths, file_names=file_names or [])
        except Exception:
            return VehiclePhotoAnalysis(
                placa="",
                marca="",
                modelo="",
                anio=None,
                color="",
                resumen="No se pudo completar el analisis local del vehiculo. Completa los datos manualmente.",
                source="safe-fallback",
            )

    try:
        result = _analyze_vehicle_with_gemini(image_paths=image_paths, file_names=file_names or [])
        if not any([result.placa, result.marca, result.modelo, result.color, result.anio]):
            fallback = _analyze_vehicle_with_best_fallback(image_paths=image_paths, file_names=file_names or [])
            if any([fallback.placa, fallback.marca, fallback.modelo, fallback.color, fallback.anio]):
                return VehiclePhotoAnalysis(
                    placa=fallback.placa,
                    marca=fallback.marca,
                    modelo=fallback.modelo,
                    anio=fallback.anio,
                    color=fallback.color,
                    resumen=f"{result.resumen} Se completo con analisis local de respaldo.",
                    source="gemini+local",
                )
        return result
    except Exception:
        try:
            return _analyze_vehicle_with_best_fallback(image_paths=image_paths, file_names=file_names or [])
        except Exception:
            return VehiclePhotoAnalysis(
                placa="",
                marca="",
                modelo="",
                anio=None,
                color="",
                resumen="La IA no pudo identificar datos suficientes. Completa o corrige los campos manualmente.",
                source="safe-fallback",
            )


def summarize_audio_file(*, audio_path: str, descripcion: str = "") -> str:
    if not audio_path:
        return "No se adjunto audio descriptivo."

    if not GEMINI_API_KEY:
        return "Audio recibido. No se genero resumen automatico porque Gemini no esta configurado."

    prompt = (
        "Transcribe mentalmente este audio de una emergencia vehicular y devuelve un resumen breve en espanol. "
        "Incluye: falla principal, sintomas mencionados, urgencia percibida y cualquier referencia de ubicacion. "
        f"Descripcion escrita por el cliente: {descripcion or 'No registrada'}"
    )
    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}, _file_part(audio_path)]}],
            "generationConfig": {"temperature": 0.2},
        }
        return _sanitize_text(
            _extract_text(_call_gemini(payload)),
            "Audio recibido, pero no se pudo extraer un resumen claro.",
        )
    except Exception:
        return "Audio recibido. La IA no pudo resumirlo automaticamente, pero el taller puede escucharlo."


def warm_vehicle_ai() -> None:
    if GEMINI_API_KEY:
        return
    try:
        _load_hf_vehicle_bundle()
    except Exception:
        return


def _analyze_with_gemini(
    *,
    descripcion: str,
    incident_type: Optional[str],
    image_paths: list[str],
    audio_paths: list[str],
    vehicle_photo_path: Optional[str],
) -> IncidentAnalysis:
    prompt = (
        "Analiza un incidente vehicular para una plataforma de asistencia mecanica. "
        "Debes devolver solo JSON valido con estas claves exactas: "
        'clasificacion, prioridad, resumen, especialidad_requerida. '
        "La prioridad solo puede ser Alta, Media o Baja. "
        "La especialidad_requerida debe ser una de: general, electrico, llantas, motor, grua, cerrajeria, carroceria. "
        f"Tipo reportado: {incident_type or 'No especificado'}. "
        f"Descripcion del cliente: {descripcion}"
    )

    parts: list[dict[str, object]] = [{"text": prompt}]

    for path in image_paths[:4]:
        parts.append(_file_part(path))

    if vehicle_photo_path and vehicle_photo_path not in image_paths:
        parts.append(
            {
                "text": (
                    "La siguiente imagen corresponde a la foto general del vehiculo registrada previamente. "
                    "Usala solo como contexto complementario."
                )
            }
        )
        parts.append(_file_part(vehicle_photo_path))

    for path in audio_paths[:1]:
        parts.append(
            {
                "text": (
                    "El siguiente archivo es un audio descriptivo del cliente. "
                    "Transcribelo mentalmente, extrae la falla principal y usalo para la clasificacion."
                )
            }
        )
        parts.append(_file_part(path))

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }

    text = _extract_text(_call_gemini(payload))
    data = _parse_json_object(text)

    return IncidentAnalysis(
        clasificacion=_sanitize_text(data.get("clasificacion"), "Incidente general"),
        prioridad=_sanitize_priority(data.get("prioridad")),
        resumen=_sanitize_text(
            data.get("resumen"),
            "Se genero un resumen automatico del incidente.",
        ),
        especialidad_requerida=_sanitize_specialty(data.get("especialidad_requerida")),
    )


def _analyze_vehicle_with_gemini(*, image_paths: list[str], file_names: list[str]) -> VehiclePhotoAnalysis:
    prompt = (
        "Analiza las fotos de un vehiculo y devuelve solo JSON valido con estas claves exactas: "
        "placa, marca, modelo, anio, color, resumen. "
        "Si es una foto clara del exterior de un auto, identifica marca, modelo aproximado, anio aproximado y color. "
        "Si la placa es visible, transcribela. Si no hay placa visible devuelve cadena vacia en placa. "
        "Usa inferencias razonables cuando el modelo del auto sea reconocible, pero marca en resumen si el anio es aproximado. "
        "Si no puedes inferir el anio devuelve null. "
        "No devuelvas todos los campos vacios si el auto es visible."
    )

    parts: list[dict[str, object]] = [{"text": prompt}]
    for index, path in enumerate(image_paths[:4]):
        if index < len(file_names) and file_names[index].strip():
            parts.append(
                {
                    "text": (
                        "Nombre original del archivo: "
                        f"{file_names[index].strip()}. "
                        "Usalo solo como pista complementaria si coincide con la imagen."
                    )
                }
            )
        parts.append(_file_part(path))

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }

    text = _extract_text(_call_gemini(payload))
    data = _parse_json_object(text)

    anio_value = data.get("anio")
    anio: Optional[int] = None
    if isinstance(anio_value, int):
        anio = anio_value
    elif anio_value is not None and str(anio_value).strip():
        try:
            candidate = int(str(anio_value).strip())
            if 1950 <= candidate <= 2100:
                anio = candidate
        except ValueError:
            anio = None

    return VehiclePhotoAnalysis(
        placa=_sanitize_plate(data.get("placa")),
        marca=_sanitize_text(data.get("marca"), ""),
        modelo=_sanitize_text(data.get("modelo"), ""),
        anio=anio,
        color=_sanitize_text(data.get("color"), ""),
        resumen=_sanitize_text(
            data.get("resumen"),
            "La IA proceso las fotos del vehiculo y genero una sugerencia editable.",
        ),
        source="gemini",
    )


def _analyze_vehicle_with_best_fallback(*, image_paths: list[str], file_names: list[str]) -> VehiclePhotoAnalysis:
    hf_result = _analyze_vehicle_with_hf_model(image_paths=image_paths, file_names=file_names)
    local_result = _analyze_vehicle_locally(image_paths=image_paths, file_names=file_names)
    if hf_result is None:
        return local_result

    marca = local_result.marca or hf_result.marca
    modelo = local_result.modelo or hf_result.modelo
    anio = local_result.anio or hf_result.anio
    placa = local_result.placa or hf_result.placa
    color = local_result.color or hf_result.color

    summary_parts = [
        hf_result.resumen,
        f"marca: {marca}" if marca else None,
        f"modelo: {modelo}" if modelo else None,
        f"anio: {anio}" if anio else None,
        f"placa: {placa}" if placa else None,
        f"color: {color}" if color else None,
    ]
    return VehiclePhotoAnalysis(
        placa=placa,
        marca=marca,
        modelo=modelo,
        anio=anio,
        color=color,
        resumen=" | ".join(part for part in summary_parts if part),
        source="hybrid-local-hf",
    )


def _analyze_vehicle_with_hf_model(*, image_paths: list[str], file_names: list[str]) -> Optional[VehiclePhotoAnalysis]:
    try:
        bundle = _load_hf_vehicle_bundle()
    except Exception:
        return None

    try:
        image = Image.open(image_paths[0]).convert("RGB")
    except Exception:
        return None

    processor, model = bundle
    inputs = processor(images=image, return_tensors="pt")
    outputs = model(**inputs)
    logits = outputs.logits[0]
    probabilities = logits.softmax(dim=0)
    top_index = int(probabilities.argmax().item())
    confidence = float(probabilities[top_index].item())
    label = model.config.id2label.get(top_index, "")
    if not label:
        return None

    brand, model_name, year = _parse_vehicle_label(label)
    hint_text = _extract_filename_hints(file_names)
    hinted_brand, hinted_model = _find_brand_and_model(hint_text.upper())
    hinted_year = _find_year(hint_text.upper())

    if hinted_brand and not brand:
        brand = hinted_brand
    if hinted_model and not model_name:
        model_name = hinted_model
    if hinted_year and not year:
        year = hinted_year

    if not brand and not model_name:
        return None

    summary = (
        "Clasificacion visual local completada con modelo de Hugging Face. "
        f"Etiqueta: {label}. confianza: {confidence:.2f}"
    )
    return VehiclePhotoAnalysis(
        placa="",
        marca=brand,
        modelo=model_name,
        anio=year,
        color="",
        resumen=summary,
        source="hf-local-model",
    )


def _analyze_vehicle_locally(*, image_paths: list[str], file_names: list[str]) -> VehiclePhotoAnalysis:
    raw_text_fragments: list[str] = []
    detected_color = ""
    hint_text = _extract_filename_hints(file_names)
    hinted_brand, hinted_model = _find_brand_and_model(hint_text.upper())
    hinted_year = _find_year(hint_text.upper())

    for index, path in enumerate(image_paths):
        try:
            image = Image.open(path).convert("RGB")
        except Exception:
            continue
        if not detected_color:
            detected_color = _detect_color(image)
        if not (hinted_brand or hinted_model or hinted_year):
            raw_text_fragments.extend(_extract_candidate_text(image))
        raw_text_fragments.extend(_extract_plate_candidate_text(image))
        if hinted_brand or hinted_model or hinted_year or index >= 1:
            break

    joined = " ".join(fragment for fragment in raw_text_fragments if fragment).upper()
    combined = " ".join(part for part in [joined, hint_text] if part).upper()
    plate = _find_plate(combined)
    year = hinted_year or _find_year(combined)
    brand, model = _find_brand_and_model(combined)

    found_bits = [
        f"placa: {plate}" if plate else None,
        f"marca: {brand}" if brand else None,
        f"modelo: {model}" if model else None,
        f"anio: {year}" if year else None,
        f"color: {detected_color}" if detected_color else None,
        "se usaron pistas del nombre del archivo" if hint_text else None,
    ]
    summary = (
        "Se genero una sugerencia local a partir de OCR, recortes del vehiculo y color. "
        + ", ".join(bit for bit in found_bits if bit)
        if any(found_bits)
        else "No se detectaron datos suficientes en las fotos. Completa el formulario manualmente."
    )

    return VehiclePhotoAnalysis(
        placa=plate,
        marca=brand,
        modelo=model,
        anio=year,
        color=detected_color,
        resumen=summary,
        source="local-enhanced",
    )


def _file_part(path: str) -> dict[str, object]:
    file_path = Path(path)
    encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return {
        "inline_data": {
            "mime_type": guess_mime_type(str(file_path)),
            "data": encoded,
        }
    }


def _gemini_model_candidates() -> list[str]:
    configured = (GEMINI_MODEL or "").strip()
    candidates = [
        configured,
        "gemini-2.0-flash",
        "gemini-1.5-flash",
    ]
    unique: list[str] = []
    for model in candidates:
        if model and model not in unique:
            unique.append(model)
    return unique


def _call_gemini(payload: dict[str, object]) -> dict[str, object]:
    last_error: Exception | None = None
    for model in _gemini_model_candidates():
        request = Request(
            url=(
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent?key={GEMINI_API_KEY}"
            ),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            last_error = exc
            continue
    raise RuntimeError("Gemini no respondio correctamente.") from last_error


def _extract_text(payload: dict[str, object]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("Gemini no devolvio candidatos.")
    content = candidates[0].get("content")
    if not isinstance(content, dict):
        raise ValueError("Gemini no devolvio contenido.")
    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        raise ValueError("Gemini no devolvio partes.")
    text = parts[0].get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Gemini no devolvio texto.")
    return text


def _parse_json_object(text: str) -> dict[str, object]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        payload = json.loads(cleaned[start:end + 1])

    if not isinstance(payload, dict):
        raise ValueError("Gemini no devolvio un objeto JSON.")
    return payload


@lru_cache(maxsize=1)
def _load_hf_vehicle_bundle():
    from transformers import AutoImageProcessor, AutoModelForImageClassification

    processor = AutoImageProcessor.from_pretrained(HF_VEHICLE_MODEL)
    model = AutoModelForImageClassification.from_pretrained(HF_VEHICLE_MODEL)
    model.eval()
    return processor, model


def _sanitize_text(value: object, default: str) -> str:
    text = str(value).strip() if value is not None else ""
    return text or default


def _sanitize_priority(value: object) -> str:
    normalized = str(value).strip().capitalize() if value is not None else ""
    if normalized not in {"Alta", "Media", "Baja"}:
        return "Media"
    return normalized


def _sanitize_specialty(value: object) -> str:
    normalized = str(value).strip().lower() if value is not None else ""
    if normalized not in {
        "general",
        "electrico",
        "llantas",
        "motor",
        "grua",
        "cerrajeria",
        "carroceria",
    }:
        return "general"
    return normalized


def _sanitize_plate(value: object) -> str:
    raw = str(value).upper().strip() if value is not None else ""
    return "".join(char for char in raw if char.isalnum() or char == "-")


def _parse_vehicle_label(label: str) -> tuple[str, str, Optional[int]]:
    cleaned = " ".join(str(label).replace("_", " ").split())
    year = _find_year(cleaned.upper())
    without_year = re.sub(r"\b(19[6-9]\d|20[0-4]\d)\b", "", cleaned).strip()
    without_year = re.sub(r"\s+", " ", without_year)
    if not without_year:
        return "", "", year

    tokens = without_year.split()
    brand = tokens[0].title()
    remainder = " ".join(tokens[1:]).strip()
    remainder = _strip_body_style(remainder)
    return brand, remainder, year


def _extract_candidate_text(image: Image.Image) -> list[str]:
    variants = [_prepare_variant(variant) for variant in _generate_image_regions(image)]

    texts: list[str] = []
    for variant in variants:
        for config in ("--psm 6", "--psm 11"):
            try:
                text = pytesseract.image_to_string(variant, config=config)
            except Exception:
                continue
            cleaned = " ".join(text.split())
            if cleaned:
                texts.append(cleaned)
    return texts


def _find_plate(text: str) -> str:
    normalized = re.sub(r"[^A-Z0-9-]+", " ", text.upper())
    candidates = re.findall(r"\b[A-Z0-9-]{5,8}\b", normalized)
    blacklist = {
        "TOYOTA",
        "NISSAN",
        "SUZUKI",
        "HYUNDAI",
        "CHEVROLET",
        "VOLKSWAGEN",
        "MITSUBISHI",
        "MERCEDES",
        "RENAULT",
        "COROLLA",
        "FRONT",
        "SEDAN",
        "PHOTO",
        "IMAGE",
    }
    filtered = [item for item in candidates if item not in blacklist and not item.isdigit()]
    if not filtered:
        return ""
    filtered.sort(
        key=lambda item: (_score_plate_candidate(item), sum(char.isdigit() for char in item), len(item)),
        reverse=True,
    )
    return filtered[0]


def _find_year(text: str) -> Optional[int]:
    matches = re.findall(r"\b(19[6-9]\d|20[0-4]\d)\b", text)
    if not matches:
        return None
    try:
        return int(matches[0])
    except ValueError:
        return None


def _find_brand_and_model(text: str) -> tuple[str, str]:
    brands: dict[str, list[str]] = {
        "Toyota": ["COROLLA", "YARIS", "HILUX", "RAV4", "PRADO", "ETIOS"],
        "Nissan": ["SENTRA", "VERSA", "FRONTIER", "MARCH", "XTRAIL", "X-TRAIL"],
        "Suzuki": ["SWIFT", "VITARA", "JIMNY", "DZIRE", "ERTIGA"],
        "Hyundai": ["ACCENT", "TUCSON", "SANTA", "ELANTRA", "CRETA"],
        "Kia": ["RIO", "SPORTAGE", "PICANTO", "CERATO"],
        "Chevrolet": ["ONIX", "SAIL", "TRACKER", "SPARK", "CRUZE"],
        "Volkswagen": ["GOL", "VOYAGE", "POLO", "AMAROK", "SAVEIRO"],
        "Renault": ["LOGAN", "SANDERO", "DUSTER", "KWID"],
        "Mitsubishi": ["L200", "MONTERO", "ASX", "OUTLANDER"],
        "Mazda": ["CX5", "CX-5", "MAZDA3", "BT50", "BT-50"],
        "Honda": ["CIVIC", "CITY", "CRV", "CR-V", "HRV", "HR-V", "FIT"],
        "Ford": ["RANGER", "ECOSPORT", "ESCAPE", "FOCUS", "FIESTA"],
        "Jeep": ["WRANGLER", "CHEROKEE", "COMPASS", "RENEGADE"],
        "Subaru": ["IMPREZA", "FORESTER", "XV", "OUTBACK"],
    }

    normalized = text.upper()
    for brand, models in brands.items():
        if brand.upper() in normalized:
            for model in models:
                if model in normalized:
                    return brand, _humanize_model(model)
            return brand, ""

    for brand, models in brands.items():
        for model in models:
            if model in normalized:
                return brand, _humanize_model(model)
    return "", ""


def _detect_color(image: Image.Image) -> str:
    sample = image.resize((80, 80))
    stat = ImageStat.Stat(sample)
    r, g, b = stat.mean[:3]

    if max(r, g, b) < 55:
        return "Negro"
    if min(r, g, b) > 205:
        return "Blanco"
    if abs(r - g) < 12 and abs(g - b) < 12:
        return "Gris"
    if r > 150 and g > 110 and b < 90:
        return "Dorado"
    if r > 150 and g < 100 and b < 100:
        return "Rojo"
    if r > 130 and g > 90 and b < 80:
        return "Naranja"
    if b > r + 20 and b > g + 20:
        return "Azul"
    if g > r + 12 and g > b + 12:
        return "Verde"
    if r > 120 and b > 120 and g < 110:
        return "Morado"
    if r > 120 and g > 90 and b > 70:
        return "Beige"
    return "Plateado"


def _extract_filename_hints(file_names: list[str]) -> str:
    hints: list[str] = []
    for file_name in file_names[:4]:
        if not file_name:
            continue
        stem = Path(file_name).stem
        normalized = re.sub(r"[_\-]+", " ", stem)
        normalized = re.sub(r"[^A-Za-z0-9 ]+", " ", normalized)
        normalized = " ".join(normalized.split())
        if normalized:
            hints.append(normalized)
    return " ".join(hints)


def _generate_image_regions(image: Image.Image) -> list[Image.Image]:
    width, height = image.size
    regions = [image]
    regions.extend(
        [
            image.crop((0, int(height * 0.45), width, height)),
            image.crop((int(width * 0.2), int(height * 0.52), int(width * 0.8), int(height * 0.9))),
            image.crop((int(width * 0.25), int(height * 0.35), int(width * 0.75), int(height * 0.6))),
        ]
    )
    prepared: list[Image.Image] = []
    for region in regions:
        if region.width <= 0 or region.height <= 0:
            continue
        target_width = min(max(int(region.width * 1.15), 220), 900)
        target_height = min(max(int(region.height * 1.15), 160), 650)
        prepared.append(region.resize((target_width, target_height)))
    return prepared


def _prepare_variant(image: Image.Image) -> Image.Image:
    grayscale = ImageOps.grayscale(image)
    grayscale = ImageOps.autocontrast(grayscale)
    grayscale = ImageEnhance.Contrast(grayscale).enhance(2.8)
    grayscale = ImageEnhance.Sharpness(grayscale).enhance(2.0)
    return grayscale


def _extract_plate_candidate_text(image: Image.Image) -> list[str]:
    texts: list[str] = []
    for region in _generate_image_regions(image)[1:3]:
        grayscale = _prepare_variant(region)
        for threshold in (145,):
            binary = grayscale.point(lambda pixel, t=threshold: 255 if pixel > t else 0)
            for config in ("--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-",):
                try:
                    text = pytesseract.image_to_string(binary, config=config)
                except Exception:
                    continue
                cleaned = " ".join(text.split())
                if cleaned:
                    texts.append(cleaned)
    return texts


def _score_plate_candidate(candidate: str) -> int:
    score = 0
    digits = sum(char.isdigit() for char in candidate)
    letters = sum(char.isalpha() for char in candidate)
    if 5 <= len(candidate) <= 8:
        score += 2
    if digits >= 2:
        score += 2
    if letters >= 2:
        score += 2
    if "-" in candidate:
        score += 1
    if candidate and candidate[0].isalpha() and candidate[-1].isdigit():
        score += 1
    return score


def _humanize_model(model: str) -> str:
    normalized = model.replace("-", " ").strip()
    return normalized.title()


def _strip_body_style(model_name: str) -> str:
    suffixes = (
        " sedan",
        " coupe",
        " cab",
        " crew cab",
        " extended cab",
        " regular cab",
        " suv",
        " wagon",
        " convertible",
        " hatchback",
        " minivan",
        " van",
        " roadster",
        " supercab",
        " quad cab",
        " double cab",
    )
    normalized = f" {model_name.strip().lower()} "
    changed = True
    while changed:
        changed = False
        for suffix in suffixes:
            if normalized.endswith(f"{suffix} "):
                normalized = normalized[: -len(suffix) - 1].rstrip()
                normalized = f" {normalized.strip()} "
                changed = True
                break
    return normalized.strip().title()
