"""Endpoints stand-alone para los módulos de IA.

Los flujos principales (crear solicitud) siguen invocando a la IA internamente.
Estos endpoints permiten que el cliente/taller use la IA por sí solos:

* transcribir un audio ad-hoc para ver el texto antes de adjuntarlo.
* clasificar una foto para sugerir la categoría del incidente.
* generar el resumen estructurado de un incidente desde texto plano.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import get_current_user
from app.models.user import User
from app.services.ai import analyze_incident
from app.services.storage import save_upload_file, url_to_path
from app.services.vision_damage import analizar_dano
from app.services.whisper import transcribir_audio


router = APIRouter()


@router.post("/transcribir-audio")
async def transcribir_audio_endpoint(
    audio: UploadFile = File(...),
    language: Optional[str] = Form(default=None),
    _: User = Depends(get_current_user),
):
    """Sube un audio, lo transcribe con faster-whisper y devuelve texto + metadatos."""
    if not audio.filename:
        raise HTTPException(status_code=400, detail="Archivo de audio sin nombre.")

    relative_url = await save_upload_file(
        upload=audio, category="ia-audio", prefix="transcripcion"
    )
    local_path = url_to_path(relative_url)
    if not local_path:
        raise HTTPException(status_code=500, detail="No se pudo guardar el audio subido.")

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
):
    """Genera clasificación, prioridad, resumen y especialidad desde texto.

    Usa Gemini si está configurado; cae al clasificador heurístico si no.
    """
    if not descripcion.strip():
        raise HTTPException(status_code=400, detail="La descripción no puede estar vacía.")
    analysis = analyze_incident(descripcion=descripcion, incident_type=incident_type)
    return {
        "clasificacion": analysis.clasificacion,
        "prioridad": analysis.prioridad,
        "resumen": analysis.resumen,
        "especialidad_requerida": analysis.especialidad_requerida,
    }
