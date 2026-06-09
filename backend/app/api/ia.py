"""Endpoints stand-alone para los módulos de IA.

Los flujos principales (crear solicitud) siguen invocando a la IA internamente.
Estos endpoints permiten que el cliente/taller use la IA por sí solos:

* transcribir un audio ad-hoc para ver el texto antes de adjuntarlo.
* clasificar una foto para sugerir la categoría del incidente.
* generar el resumen estructurado de un incidente desde texto plano.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.domain import Taller
from app.models.user import User
from app.services.ai import analyze_incident
from app.services.piper_tts import synthesize_speech
from app.services.storage import delete_relative_url, save_upload_file, url_to_path
from app.services.vision_damage import analizar_dano
from app.services.whisper import transcribir_audio


router = APIRouter()
MAX_AUDIO_MB = int(os.getenv("MAX_AUDIO_MB", "25"))
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg", ".aac"}
ASSISTANT_MESSAGES = {
    "post_recording": "Enseguida su solicitud sera enviada a los talleres mas cercanos segun la especialidad requerida.",
    "request_sent": "Su solicitud fue enviada. En breve tendra una notificacion.",
    "search_results": "No se encontraron solicitudes con esos filtros.",
}
UNAVAILABLE_SPECIALTY_MESSAGE = (
    "No contamos con esa especialidad pero lo hemos derivado su solicitud "
    "con un taller de auxilio general."
)
SPECIALTY_TTS_LABELS = {
    "electrico": "electricos",
    "electricidad": "electricos",
    "alternador y arranque": "de alternador y arranque",
    "batería": "de bateria",
    "bateria": "de bateria",
    "llantas": "de llantas",
    "motor": "mecanicos",
    "frenos": "de frenos",
    "suspensión": "de suspension",
    "suspension": "de suspension",
    "transmisión / caja": "de transmision y caja",
    "transmision / caja": "de transmision y caja",
    "embrague": "de embrague",
    "dirección": "de direccion",
    "direccion": "de direccion",
    "aire acondicionado": "de aire acondicionado",
    "inyección y combustible": "de inyeccion y combustible",
    "inyeccion y combustible": "de inyeccion y combustible",
    "escape": "de escape",
    "grua": "de grua",
    "grúa / remolque": "de grua y remolque",
    "grua / remolque": "de grua y remolque",
    "cerrajeria": "cerrajeros automotrices",
    "cerrajería automotriz": "cerrajeros automotrices",
    "cerrajeria automotriz": "cerrajeros automotrices",
    "carroceria": "de carroceria",
    "carrocería y pintura": "de carroceria y pintura",
    "carroceria y pintura": "de carroceria y pintura",
    "choque": "de chapa y pintura",
    "chocó": "de chapa y pintura",
    "choco": "de chapa y pintura",
    "diagnóstico electrónico (obd)": "de diagnostico electronico",
    "diagnostico electronico (obd)": "de diagnostico electronico",
    "autos eléctricos - carga rápida": "de autos electricos y carga rapida",
    "autos electricos - carga rapida": "de autos electricos y carga rapida",
    "autos eléctricos - batería de tracción": "de bateria de traccion para autos electricos",
    "autos electricos - bateria de traccion": "de bateria de traccion para autos electricos",
    "autos híbridos": "de autos hibridos",
    "autos hibridos": "de autos hibridos",
    "general": "de auxilio general",
    "auxilio general": "de auxilio general",
}


def specialty_tts_label(value: str) -> str:
    normalized = " ".join((value or "").strip().lower().split())
    if not normalized:
        return SPECIALTY_TTS_LABELS["general"]
    if normalized in SPECIALTY_TTS_LABELS:
        return SPECIALTY_TTS_LABELS[normalized]
    return f"de {normalized}"


def is_general_specialty(value: str) -> bool:
    normalized = " ".join((value or "").strip().lower().split())
    return normalized in {"general", "auxilio general"}


def especialidades_taller_disponibles(session: Session) -> list[str]:
    nombres = {
        especialidad.nombre
        for taller in session.exec(select(Taller).where(Taller.activo == True)).all()
        for especialidad in taller.especialidades
        if especialidad.nombre
    }
    return sorted(nombres)


@router.post("/transcribir-audio")
async def transcribir_audio_endpoint(
    audio: UploadFile = File(...),
    language: Optional[str] = Form(default=None),
    _: User = Depends(get_current_user),
):
    """Sube un audio, lo transcribe con Faster-Whisper local y devuelve texto + metadatos."""
    if not audio.filename:
        raise HTTPException(status_code=400, detail="Archivo de audio sin nombre.")

    extension = Path(audio.filename).suffix.lower()
    if extension not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Formato de audio no permitido. Use mp3, mp4, mpeg, mpga, m4a, wav, webm, ogg o aac.",
        )

    relative_url = await save_upload_file(
        upload=audio, category="ia-audio", prefix="transcripcion"
    )
    local_path = url_to_path(relative_url)
    if not local_path:
        raise HTTPException(status_code=500, detail="No se pudo guardar el audio subido.")

    max_bytes = MAX_AUDIO_MB * 1024 * 1024
    if local_path.stat().st_size > max_bytes:
        delete_relative_url(relative_url)
        raise HTTPException(
            status_code=413,
            detail=f"El audio supera el limite de {MAX_AUDIO_MB} MB.",
        )

    result = transcribir_audio(str(local_path), language=language)
    return {
        "url": relative_url,
        "text": result.text,
        "language": result.language,
        "duration_seconds": result.duration_seconds,
        "source": result.source,
        "error": result.error,
    }


@router.post("/clasificar-imagen")
async def clasificar_imagen_endpoint(
    imagen: UploadFile = File(...),
    _: User = Depends(get_current_user),
):
    """Sube una imagen y devuelve la categoría del incidente sugerida."""
    if not imagen.filename:
        raise HTTPException(status_code=400, detail="Archivo de imagen sin nombre.")

    relative_url = await save_upload_file(
        upload=imagen, category="ia-imagen", prefix="dano"
    )
    local_path = url_to_path(relative_url)
    if not local_path:
        raise HTTPException(status_code=500, detail="No se pudo guardar la imagen subida.")

    analysis = analizar_dano(str(local_path))
    return {
        "url": relative_url,
        "categoria": analysis.categoria,
        "confianza": round(analysis.confianza, 3),
        "descripcion": analysis.descripcion,
        "source": analysis.source,
    }


@router.post("/resumir-incidente", status_code=status.HTTP_200_OK)
def resumir_incidente_endpoint(
    descripcion: str = Form(...),
    incident_type: Optional[str] = Form(default=None),
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Genera clasificación, prioridad, resumen y especialidad desde texto.

    Usa Gemini si está configurado; cae al clasificador heurístico si no.
    """
    if not descripcion.strip():
        raise HTTPException(status_code=400, detail="La descripción no puede estar vacía.")
    analysis = analyze_incident(
        descripcion=descripcion,
        incident_type=incident_type,
        available_specialties=especialidades_taller_disponibles(session),
    )
    return {
        "clasificacion": analysis.clasificacion,
        "prioridad": analysis.prioridad,
        "resumen": analysis.resumen,
        "especialidad_requerida": analysis.especialidad_requerida,
    }


@router.post("/asistente-voz", status_code=status.HTTP_200_OK)
def asistente_voz_endpoint(
    message_key: str = Form(...),
    especialidad: Optional[str] = Form(default=None),
    descripcion: Optional[str] = Form(default=None),
    incident_type: Optional[str] = Form(default=None),
    cantidad: Optional[int] = Form(default=None),
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    text = ASSISTANT_MESSAGES.get(message_key)
    if not text:
        raise HTTPException(status_code=400, detail="Mensaje de asistente no soportado.")

    analysis = None
    detected_specialty = (especialidad or "").strip().lower()
    if message_key == "post_recording" and (descripcion or incident_type):
        analysis = analyze_incident(
            descripcion=(descripcion or "").strip(),
            incident_type=(incident_type or "").strip() or None,
            available_specialties=especialidades_taller_disponibles(session),
        )
        detected_specialty = analysis.especialidad_requerida

    if message_key == "post_recording":
        if is_general_specialty(detected_specialty):
            text = UNAVAILABLE_SPECIALTY_MESSAGE
        else:
            specialty_label = specialty_tts_label(detected_specialty)
            text = (
                "Enseguida su solicitud sera enviada a los talleres "
                f"{specialty_label} mas cercanos."
            )

    if message_key == "search_results":
        total = max(0, cantidad or 0)
        detected_specialty = (especialidad or incident_type or "").strip()
        specialty = detected_specialty or "los filtros indicados"
        date_context = (descripcion or "").strip()
        date_suffix = f" registradas {date_context}" if date_context else ""
        if total == 1:
            text = f"Se encontro 1 solicitud con incidencia de {specialty}{date_suffix}."
        elif total > 1:
            text = f"Se encontraron {total} solicitudes con incidencias de {specialty}{date_suffix}."
        else:
            text = f"No se encontraron solicitudes con incidencias de {specialty}{date_suffix}."

    result = synthesize_speech(text, prefix=message_key)
    if result.error:
        raise HTTPException(status_code=500, detail=result.error)
    return {
        "text": result.text,
        "url": result.relative_url,
        "source": result.source,
        "especialidad_detectada": detected_specialty or None,
        "clasificacion": analysis.clasificacion if analysis else None,
    }
