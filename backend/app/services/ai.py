from __future__ import annotations

import base64
import json
import os
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image, ImageEnhance, ImageOps, ImageStat

from app.services.groq_client import groq_vision_json
from app.services.storage import guess_mime_type


GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "25"))
HF_VEHICLE_MODEL = os.getenv("HF_VEHICLE_MODEL", "therealcyberlord/stanford-car-vit-patch16").strip()


SPECIALTY_RULES: tuple[dict[str, object], ...] = (
    {
        "especialidad": "electricidad",
        "clasificacion": "Problema electrico",
        "prioridad": "Media",
        "keywords": ("bateria", "batería", "no enciende", "click", "alternador", "arranque", "electrico", "eléctrico", "luces", "fusible"),
        "resumen": "El vehiculo presenta una falla electrica o de arranque.",
    },
    {
        "especialidad": "alternador y arranque",
        "clasificacion": "Problema de alternador o arranque",
        "prioridad": "Media",
        "keywords": ("alternador", "arranque", "motor de arranque", "burro", "no arranca", "descarga"),
        "resumen": "El incidente sugiere revision de alternador, bateria o sistema de arranque.",
    },
    {
        "especialidad": "batería",
        "clasificacion": "Problema de bateria",
        "prioridad": "Media",
        "keywords": ("bateria", "batería", "borne", "descargada", "sin bateria", "pasar corriente"),
        "resumen": "El vehiculo requiere asistencia por bateria descargada o falla relacionada.",
    },
    {
        "especialidad": "llantas",
        "clasificacion": "Problema de llanta o neumatico",
        "prioridad": "Media",
        "keywords": ("llanta", "neumatico", "neumático", "pinchada", "pinchazo", "rueda", "aire de la llanta"),
        "resumen": "El vehiculo presenta una falla en llanta o neumatico y requiere asistencia en ruta.",
    },
    {
        "especialidad": "motor",
        "clasificacion": "Problema de motor",
        "prioridad": "Alta",
        "keywords": ("motor", "humo", "pistonea", "se apaga", "perdio potencia", "perdió potencia", "ruido del motor"),
        "resumen": "Hay indicios de falla de motor. Requiere revision mecanica prioritaria.",
    },
    {
        "especialidad": "refrigeración / radiador",
        "clasificacion": "Problema de refrigeracion o radiador",
        "prioridad": "Alta",
        "keywords": ("recalentado", "recalento", "recalentó", "temperatura", "radiador", "agua", "coolant", "anticongelante", "ventilador"),
        "resumen": "El vehiculo presenta senales de recalentamiento o falla del sistema de refrigeracion.",
    },
    {
        "especialidad": "frenos",
        "clasificacion": "Problema de frenos",
        "prioridad": "Alta",
        "keywords": ("freno", "frenos", "no frena", "pedal", "pastilla", "disco", "abs", "liquido de frenos"),
        "resumen": "El incidente sugiere falla en el sistema de frenos y requiere atencion urgente.",
    },
    {
        "especialidad": "suspensión",
        "clasificacion": "Problema de suspension",
        "prioridad": "Media",
        "keywords": ("suspension", "suspensión", "amortiguador", "golpe abajo", "tren delantero", "bujes", "vibra mucho"),
        "resumen": "El vehiculo presenta sintomas de falla en suspension o tren delantero.",
    },
    {
        "especialidad": "transmisión / caja",
        "clasificacion": "Problema de transmision o caja",
        "prioridad": "Alta",
        "keywords": ("caja", "transmision", "transmisión", "cambio", "embrague", "no entra marcha", "patina"),
        "resumen": "El incidente apunta a una falla en transmision, caja o embrague.",
    },
    {
        "especialidad": "embrague",
        "clasificacion": "Problema de embrague",
        "prioridad": "Media",
        "keywords": ("embrague", "clutch", "pedal de embrague", "no entran los cambios"),
        "resumen": "El vehiculo requiere revision del sistema de embrague.",
    },
    {
        "especialidad": "dirección",
        "clasificacion": "Problema de direccion",
        "prioridad": "Alta",
        "keywords": ("direccion", "dirección", "volante duro", "hidraulica", "hidráulica", "no gira", "cremallera"),
        "resumen": "El incidente sugiere una falla en el sistema de direccion.",
    },
    {
        "especialidad": "aire acondicionado",
        "clasificacion": "Problema de aire acondicionado",
        "prioridad": "Baja",
        "keywords": ("aire acondicionado", "no enfria", "no enfría", "compresor", "climatizador", "gas del aire"),
        "resumen": "El vehiculo presenta una falla en aire acondicionado o climatizacion.",
    },
    {
        "especialidad": "inyección y combustible",
        "clasificacion": "Problema de inyeccion o combustible",
        "prioridad": "Media",
        "keywords": ("inyeccion", "inyección", "combustible", "gasolina", "diesel", "bomba de gasolina", "inyector", "filtro de combustible"),
        "resumen": "El incidente apunta a una falla de inyeccion o suministro de combustible.",
    },
    {
        "especialidad": "escape",
        "clasificacion": "Problema de escape",
        "prioridad": "Baja",
        "keywords": ("escape", "catalizador", "silenciador", "humo negro", "olor a gases"),
        "resumen": "El vehiculo requiere revision del sistema de escape.",
    },
    {
        "especialidad": "carrocería y pintura",
        "clasificacion": "Choque o dano de carroceria",
        "prioridad": "Alta",
        "keywords": ("choque", "colision", "colisión", "accidente", "golpe", "abollado", "parachoque", "carroceria", "carrocería"),
        "resumen": "El incidente involucra golpe, colision o dano de carroceria.",
    },
    {
        "especialidad": "grúa / remolque",
        "clasificacion": "Solicitud de grua o remolque",
        "prioridad": "Alta",
        "keywords": ("grua", "grúa", "remolque", "remolcar", "varado", "no se mueve", "no puede circular"),
        "resumen": "El vehiculo no puede circular y podria requerir grua o remolque.",
    },
    {
        "especialidad": "cerrajería automotriz",
        "clasificacion": "Problema de cerrajeria automotriz",
        "prioridad": "Media",
        "keywords": ("llave", "llaves", "cerradura", "cerrajeria", "cerrajería", "me quede afuera", "bloqueado"),
        "resumen": "El incidente sugiere apertura o asistencia de cerrajeria automotriz.",
    },
    {
        "especialidad": "diagnóstico electrónico (obd)",
        "clasificacion": "Diagnostico electronico requerido",
        "prioridad": "Media",
        "keywords": ("check engine", "scanner", "obd", "testigo", "sensor", "computadora", "codigo de error"),
        "resumen": "El vehiculo requiere diagnostico electronico con escaner OBD.",
    },
    {
        "especialidad": "autos eléctricos - carga rápida",
        "clasificacion": "Problema de carga en auto electrico",
        "prioridad": "Media",
        "keywords": ("carga rapida", "carga rápida", "cargador", "no carga", "electrico no carga", "eléctrico no carga"),
        "resumen": "El incidente sugiere un problema de carga en vehiculo electrico.",
    },
    {
        "especialidad": "autos eléctricos - batería de tracción",
        "clasificacion": "Problema de bateria de traccion",
        "prioridad": "Alta",
        "keywords": ("bateria de traccion", "batería de tracción", "alto voltaje", "autonomia", "autonomía", "vehiculo electrico", "vehículo eléctrico"),
        "resumen": "El vehiculo electrico podria tener falla de bateria de traccion.",
    },
    {
        "especialidad": "autos híbridos",
        "clasificacion": "Problema de sistema hibrido",
        "prioridad": "Media",
        "keywords": ("hibrido", "híbrido", "sistema hibrido", "sistema híbrido", "bateria hibrida", "batería híbrida"),
        "resumen": "El vehiculo hibrido requiere diagnostico especializado.",
    },
)


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


def _normalize_text(value: object) -> str:
    text = str(value or "")
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(normalized.casefold().split())


def _best_available_specialty_match(
    *,
    text: str,
    selected_specialty: Optional[str],
    available_specialties: Optional[list[str]],
) -> Optional[str]:
    if not available_specialties:
        return selected_specialty

    normalized_options = [
        (specialty, _normalize_text(specialty))
        for specialty in available_specialties
        if str(specialty or "").strip()
    ]
    if not normalized_options:
        return selected_specialty

    general_specialty = _available_general_specialty(normalized_options)

    selected_normalized = _normalize_text(selected_specialty)
    for specialty, normalized_specialty in normalized_options:
        if selected_normalized and (
            selected_normalized == normalized_specialty
            or selected_normalized in normalized_specialty
            or normalized_specialty in selected_normalized
        ):
            return specialty

    best_specialty: Optional[str] = None
    best_score = 0
    for specialty, normalized_specialty in normalized_options:
        score = 0
        if normalized_specialty and normalized_specialty in text:
            score += 5
        for token in normalized_specialty.split():
            if len(token) >= 4 and token in text:
                score += 2
        for rule in SPECIALTY_RULES:
            rule_specialty = _normalize_text(rule["especialidad"])
            if not (
                rule_specialty == normalized_specialty
                or rule_specialty in normalized_specialty
                or normalized_specialty in rule_specialty
            ):
                continue
            for keyword in rule["keywords"]:  # type: ignore[index]
                normalized_keyword = _normalize_text(keyword)
                if normalized_keyword and normalized_keyword in text:
                    score += 3 if " " in normalized_keyword else 2
        if score > best_score:
            best_score = score
            best_specialty = specialty

    return best_specialty if best_score > 0 else general_specialty


def _available_general_specialty(
    normalized_options: list[tuple[str, str]],
) -> Optional[str]:
    return next(
        (
            specialty
            for specialty, normalized_specialty in normalized_options
            if normalized_specialty in {"auxilio general", "general"}
        ),
        None,
    )


def fallback_incident_analysis(
    *,
    descripcion: str,
    incident_type: Optional[str] = None,
    available_specialties: Optional[list[str]] = None,
) -> IncidentAnalysis:
    text = _normalize_text(f"{incident_type or ''} {descripcion}")
    best_rule: dict[str, object] | None = None
    best_score = 0

    for rule in SPECIALTY_RULES:
        score = 0
        specialty = _normalize_text(rule["especialidad"])
        if specialty and specialty in text:
            score += 4
        for keyword in rule["keywords"]:  # type: ignore[index]
            normalized_keyword = _normalize_text(keyword)
            if normalized_keyword and normalized_keyword in text:
                score += 3 if " " in normalized_keyword else 2
        if score > best_score:
            best_score = score
            best_rule = rule

    matched_specialty = _best_available_specialty_match(
        text=text,
        selected_specialty=str(best_rule["especialidad"]) if best_rule else None,
        available_specialties=available_specialties,
    )
    if matched_specialty:
        if best_rule:
            return IncidentAnalysis(
                clasificacion=str(best_rule["clasificacion"]),
                prioridad=str(best_rule["prioridad"]),
                resumen=str(best_rule["resumen"]),
                especialidad_requerida=matched_specialty,
            )
        return IncidentAnalysis(
            clasificacion="Incidente general",
            prioridad="Baja",
            resumen="El cliente reporta una falla pendiente de diagnostico manual.",
            especialidad_requerida=matched_specialty,
        )

    if not best_rule:
        return IncidentAnalysis(
            clasificacion="Incidente general",
            prioridad="Baja",
            resumen="El cliente reporta una falla general pendiente de diagnostico manual.",
            especialidad_requerida="auxilio general",
        )

    return IncidentAnalysis(
        clasificacion=str(best_rule["clasificacion"]),
        prioridad=str(best_rule["prioridad"]),
        resumen=str(best_rule["resumen"]),
        especialidad_requerida=str(best_rule["especialidad"]),
    )

def analyze_incident(
    *,
    descripcion: str,
    incident_type: Optional[str] = None,
    image_paths: Optional[list[str]] = None,
    audio_paths: Optional[list[str]] = None,
    vehicle_photo_path: Optional[str] = None,
    available_specialties: Optional[list[str]] = None,
) -> IncidentAnalysis:
    if not _gemini_api_key():
        return fallback_incident_analysis(
            descripcion=descripcion,
            incident_type=incident_type,
            available_specialties=available_specialties,
        )

    try:
        return _analyze_with_gemini(
            descripcion=descripcion,
            incident_type=incident_type,
            image_paths=image_paths or [],
            audio_paths=audio_paths or [],
            vehicle_photo_path=vehicle_photo_path,
            available_specialties=available_specialties,
        )
    except Exception as exc:
        print(f"Gemini incidente fallo: {exc}")
        return fallback_incident_analysis(
            descripcion=descripcion,
            incident_type=incident_type,
            available_specialties=available_specialties,
        )


def analyze_vehicle_photos(*, image_paths: list[str], file_names: Optional[list[str]] = None) -> VehiclePhotoAnalysis:
    """Identifica marca/modelo/color/año/placa a partir de fotos.

    Cadena de proveedores (todo solo HTTP, sin ML local):
      1. Groq vision (Llama 4 multimodal) si GROQ_API_KEY esta seteada.
      2. Gemini vision como fallback si GEMINI_API_KEY esta seteada.
      3. Resultado vacio "safe-fallback" si nada respondio.

    Campos que el modelo no reconozca con confianza vienen como string vacio
    ("" para placa/marca/modelo/color) o None (anio). El cliente muestra
    "no identificado" para esos campos sin bloquear el registro manual.
    """
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

    # 1) Groq vision
    groq_result = _analyze_vehicle_with_groq(image_paths=image_paths)
    if groq_result is not None and _has_useful_fields(groq_result):
        return groq_result

    # 2) Gemini fallback
    if _gemini_api_key():
        try:
            gemini_result = _analyze_vehicle_with_gemini(image_paths=image_paths, file_names=file_names or [])
            if _has_useful_fields(gemini_result):
                # Si Groq habia detectado algo parcial, conservamos lo de Gemini
                # (mas confiable por tener prompt afinado). El resumen explica.
                return gemini_result
            # Gemini tampoco saco nada util. Devolvemos lo que tenga, marcado.
            return gemini_result
        except Exception as exc:  # noqa: BLE001
            print(f"[ai.analyze_vehicle_photos] Gemini fallo: {exc}")

    # Si Groq devolvio respuesta pero sin campos utiles, devolvemos eso.
    if groq_result is not None:
        return groq_result

    # 3) Sin nada configurado o todo fallo.
    return VehiclePhotoAnalysis(
        placa="",
        marca="",
        modelo="",
        anio=None,
        color="",
        resumen=(
            "La IA no esta configurada (faltan GROQ_API_KEY o GEMINI_API_KEY) o no "
            "pudo identificar el vehiculo. Completa los campos manualmente."
        ),
        source="safe-fallback",
    )


def _has_useful_fields(result: VehiclePhotoAnalysis) -> bool:
    return bool(result.placa or result.marca or result.modelo or result.color or result.anio)


def _analyze_vehicle_with_groq(*, image_paths: list[str]) -> Optional[VehiclePhotoAnalysis]:
    """Pide a Groq vision un JSON estructurado con los 5 campos."""
    prompt = (
        "Eres un perito automotriz. Mira las fotos del vehiculo y devuelve SOLO un "
        "JSON con estas claves EXACTAS y nada mas:\n"
        '{"placa": "...", "marca": "...", "modelo": "...", "anio": 0, "color": "...", "resumen": "..."}\n\n'
        "Reglas:\n"
        "- placa: el texto exacto de la matricula si es legible (mayusculas, sin "
        "espacios). Si no se ve, no se lee claro, o es ambigua, devuelve \"\".\n"
        "- marca: la marca del vehiculo (Toyota, Nissan, etc). Si no la sabes, \"\".\n"
        "- modelo: el modelo (Corolla, Hilux, Sentra, etc). Si no estas seguro, \"\".\n"
        "- anio: numero entero del año si lo puedes inferir; si no, 0.\n"
        "- color: color predominante en español (Blanco, Rojo, Gris, Negro, etc). "
        "Si no es claro, \"\".\n"
        "- resumen: una frase breve en español describiendo lo que ves.\n"
        "No inventes valores. Mejor \"\" o 0 que adivinar."
    )

    data = groq_vision_json(image_paths=image_paths, prompt=prompt, max_tokens=400)
    if data is None:
        return None

    placa = _sanitize_plate(data.get("placa"))
    marca = _sanitize_text(str(data.get("marca") or ""), "")
    modelo = _sanitize_text(str(data.get("modelo") or ""), "")
    color = _sanitize_text(str(data.get("color") or ""), "")
    anio = _coerce_anio(data.get("anio"))
    resumen = _sanitize_text(
        str(data.get("resumen") or ""),
        "Datos sugeridos por Groq vision. Revisa antes de guardar.",
    )

    return VehiclePhotoAnalysis(
        placa=placa,
        marca=marca,
        modelo=modelo,
        anio=anio,
        color=color,
        resumen=resumen,
        source="groq",
    )


def _coerce_anio(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        try:
            n = int(float(str(value)))
        except (TypeError, ValueError):
            return None
    if 1950 <= n <= 2100:
        return n
    return None


def summarize_audio_file(*, audio_path: str, descripcion: str = "") -> str:
    if not audio_path:
        return "No se adjunto audio descriptivo."

    if not _gemini_api_key():
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
    except Exception as exc:
        print(f"Gemini audio fallo: {exc}")
        return "Audio recibido. La IA no pudo resumirlo automaticamente, pero el taller puede escucharlo."


def warm_vehicle_ai() -> None:
    """No-op: la IA de vehiculos se hace 100% via HTTP (Groq/Gemini).

    Antes precargaba un modelo HF local (transformers/torch) para no pagar el
    coste de la primera request. Ya no aplica: no hay modelo local que cargar.
    """
    return None


def _analyze_with_gemini(
    *,
    descripcion: str,
    incident_type: Optional[str],
    image_paths: list[str],
    audio_paths: list[str],
    vehicle_photo_path: Optional[str],
    available_specialties: Optional[list[str]] = None,
) -> IncidentAnalysis:
    if available_specialties:
        specialty_names = {
            str(specialty).strip()
            for specialty in available_specialties
            if str(specialty or "").strip()
        } or {"auxilio general"}
    else:
        specialty_names = {
            str(rule["especialidad"]) for rule in SPECIALTY_RULES
        } | {"auxilio general"}
    specialty_options = ", ".join(
        sorted(specialty_names)
    )
    prompt = (
        "Analiza un incidente vehicular para una plataforma de asistencia mecanica. "
        "Debes devolver solo JSON valido con estas claves exactas: "
        'clasificacion, prioridad, resumen, especialidad_requerida. '
        "La prioridad solo puede ser Alta, Media o Baja. "
        f"La especialidad_requerida debe ser una de estas especialidades del sistema: {specialty_options}. "
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
        especialidad_requerida=_sanitize_specialty(
            data.get("especialidad_requerida"),
            available_specialties=available_specialties,
        ),
    )


def _analyze_vehicle_with_gemini(*, image_paths: list[str], file_names: list[str]) -> VehiclePhotoAnalysis:
    prompt = (
        "Eres un perito automotriz. Analiza las fotos de un vehiculo y devuelve solo JSON valido, sin markdown, "
        "con estas claves exactas: placa, marca, modelo, anio, color, resumen. "
        "Si es una foto clara del exterior de un auto, identifica marca, modelo aproximado, anio aproximado y color. "
        "Es obligatorio devolver tu mejor estimacion de marca, modelo y color si se ve un auto, aunque no estes 100% seguro. "
        "No uses palabras del nombre del archivo como placa. No inventes placa si no se ve claramente. "
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
                        "No lo uses para placa. Usalo solo como pista de marca/modelo si coincide visualmente."
                    )
                }
            )
        parts.append(_image_file_part_for_gemini(path))

    payload: dict[str, object] = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.1,
        },
    }

    try:
        text = _extract_text(_call_gemini({**payload, "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}}))
    except Exception:
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


def _image_file_part_for_gemini(path: str) -> dict[str, object]:
    file_path = Path(path)
    try:
        image = Image.open(file_path).convert("RGB")
        image.thumbnail((1280, 1280))
        from io import BytesIO

        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=82, optimize=True)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return {
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": encoded,
            }
        }
    except Exception:
        return _file_part(path)


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


def _gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip()


def _call_gemini(payload: dict[str, object]) -> dict[str, object]:
    last_error: Exception | None = None
    api_key = _gemini_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY no esta configurada.")

    for model in _gemini_model_candidates():
        model_name = model.replace("models/", "").strip()
        request = Request(
            url=(
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_name}:generateContent?key={api_key}"
            ),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=GEMINI_TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="ignore")[:600]
            except Exception:
                detail = str(exc)
            last_error = RuntimeError(f"{model_name}: HTTP {exc.code} {detail}")
            print(f"Gemini error con {model_name}: {last_error}")
            continue
        except (URLError, TimeoutError, ValueError) as exc:
            last_error = RuntimeError(f"{model_name}: {exc}")
            print(f"Gemini error con {model_name}: {exc}")
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
    text = "\n".join(
        part.get("text", "")
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    ).strip()
    if not text:
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
        candidate = cleaned[start:end + 1]
        candidate = re.sub(r",\s*}", "}", candidate)
        candidate = re.sub(r",\s*]", "]", candidate)
        payload = json.loads(candidate)

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


def _sanitize_specialty(
    value: object,
    *,
    available_specialties: Optional[list[str]] = None,
) -> str:
    normalized = _normalize_text(value)
    if not normalized:
        return "auxilio general"

    if available_specialties:
        normalized_options = [
            (str(specialty), _normalize_text(specialty))
            for specialty in available_specialties
            if str(specialty or "").strip()
        ]
        for specialty in available_specialties:
            normalized_specialty = _normalize_text(specialty)
            if normalized_specialty and (
                normalized == normalized_specialty
                or normalized in normalized_specialty
                or normalized_specialty in normalized
            ):
                return str(specialty)
        return _available_general_specialty(normalized_options) or "auxilio general"

    allowed = {_normalize_text(rule["especialidad"]): str(rule["especialidad"]) for rule in SPECIALTY_RULES}
    allowed["auxilio general"] = "auxilio general"
    legacy_aliases = {
        "general": "auxilio general",
        "electrico": "electricidad",
        "electricos": "electricidad",
        "mecanico": "motor",
        "mecanicos": "motor",
        "grua": "gr?a / remolque",
        "remolque": "gr?a / remolque",
        "cerrajeria": "cerrajer?a automotriz",
        "carroceria": "carrocer?a y pintura",
        "bateria": "bater?a",
        "radiador": "refrigeraci?n / radiador",
        "caja": "transmisi?n / caja",
        "transmision": "transmisi?n / caja",
    }
    if normalized in allowed:
        return allowed[normalized]
    if normalized in legacy_aliases:
        return legacy_aliases[normalized]
    for key, canonical in allowed.items():
        if key in normalized or normalized in key:
            return canonical
    return "auxilio general"

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
    """Stub: OCR local con tesseract retirado. La deteccion ahora es LLM."""
    _ = image
    return []


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
        "SCALED",
        "IMG",
        "JPEG",
        "JPG",
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
    """Stub: el OCR local con tesseract fue retirado para reducir el tamano de
    la imagen Docker. La deteccion de placa ahora la hace el LLM via Groq/Gemini.
    """
    return []


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
