from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytesseract
from PIL import Image, ImageEnhance, ImageOps, ImageStat

from app.services.storage import guess_mime_type


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


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
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return fallback_incident_analysis(descripcion=descripcion, incident_type=incident_type)


def analyze_vehicle_photos(*, image_paths: list[str]) -> VehiclePhotoAnalysis:
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
        return _analyze_vehicle_locally(image_paths=image_paths)

    try:
        return _analyze_vehicle_with_gemini(image_paths=image_paths)
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return _analyze_vehicle_locally(image_paths=image_paths)


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

    request = Request(
        url=(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        ),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=45) as response:
        raw = response.read().decode("utf-8")

    parsed = json.loads(raw)
    text = _extract_text(parsed)
    data = json.loads(text)

    return IncidentAnalysis(
        clasificacion=_sanitize_text(data.get("clasificacion"), "Incidente general"),
        prioridad=_sanitize_priority(data.get("prioridad")),
        resumen=_sanitize_text(
            data.get("resumen"),
            "Se genero un resumen automatico del incidente.",
        ),
        especialidad_requerida=_sanitize_specialty(data.get("especialidad_requerida")),
    )


def _analyze_vehicle_with_gemini(*, image_paths: list[str]) -> VehiclePhotoAnalysis:
    prompt = (
        "Analiza las fotos de un vehiculo y devuelve solo JSON valido con estas claves exactas: "
        "placa, marca, modelo, anio, color, resumen. "
        "Si no estas seguro de una clave textual devuelve cadena vacia. "
        "Si no puedes inferir el anio devuelve null. "
        "Debes leer la placa visible en las fotos si aparece. "
        "No inventes datos que no se vean razonablemente en las imagenes."
    )

    parts: list[dict[str, object]] = [{"text": prompt}]
    for path in image_paths[:4]:
        parts.append(_file_part(path))

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }

    request = Request(
        url=(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        ),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=45) as response:
        raw = response.read().decode("utf-8")

    parsed = json.loads(raw)
    text = _extract_text(parsed)
    data = json.loads(text)

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


def _analyze_vehicle_locally(*, image_paths: list[str]) -> VehiclePhotoAnalysis:
    raw_text_fragments: list[str] = []
    detected_color = ""

    for index, path in enumerate(image_paths):
        image = Image.open(path).convert("RGB")
        if not detected_color:
          detected_color = _detect_color(image)
        raw_text_fragments.extend(_extract_candidate_text(image))
        if index >= 2:
            break

    joined = " ".join(fragment for fragment in raw_text_fragments if fragment).upper()
    plate = _find_plate(joined)
    year = _find_year(joined)
    brand, model = _find_brand_and_model(joined)

    found_bits = [
        f"placa: {plate}" if plate else None,
        f"marca: {brand}" if brand else None,
        f"modelo: {model}" if model else None,
        f"año: {year}" if year else None,
        f"color: {detected_color}" if detected_color else None,
    ]
    summary = (
        "Se genero una sugerencia local a partir de OCR y color. "
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
        source="local-ocr",
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


def _extract_candidate_text(image: Image.Image) -> list[str]:
    variants = [
        image,
        ImageOps.grayscale(image),
        ImageEnhance.Contrast(ImageOps.grayscale(image)).enhance(2.4),
        ImageOps.autocontrast(ImageOps.grayscale(image)),
    ]

    texts: list[str] = []
    for variant in variants:
        text = pytesseract.image_to_string(variant, config="--psm 6")
        cleaned = " ".join(text.split())
        if cleaned:
            texts.append(cleaned)
    return texts


def _find_plate(text: str) -> str:
    candidates = re.findall(r"\b[A-Z0-9]{5,8}\b", text)
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
    }
    filtered = [item for item in candidates if item not in blacklist and not item.isdigit()]
    if not filtered:
        return ""
    filtered.sort(key=lambda item: (sum(char.isdigit() for char in item), len(item)), reverse=True)
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
    }

    normalized = text.upper()
    for brand, models in brands.items():
        if brand.upper() in normalized:
            for model in models:
                if model in normalized:
                    return brand, model.replace("-", " ")
            return brand, ""

    for brand, models in brands.items():
        for model in models:
            if model in normalized:
                return brand, model.replace("-", " ")
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
