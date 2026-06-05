"""Transcripcion de audio -> texto via Groq Whisper API (cloud, ligero).

Antes este modulo usaba `faster-whisper` localmente (~3-4 GB de modelo y
torch). Migrado a Groq para reducir el tamano de la imagen y no depender de
torch/CTranslate2. Si no hay `GROQ_API_KEY` configurada, devuelve un fallback
explicito en lugar de romper el arranque del backend (mismo contrato que la
version anterior).

Interfaz publica intacta:
    - dataclass TranscriptionResult
    - funcion transcribir_audio(audio_path, language=...)
    - funcion warm_whisper()  (no-op en la version cloud)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.services.groq_client import groq_audio_transcribe


WHISPER_DEFAULT_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "es")


@dataclass
class TranscriptionResult:
    text: str
    language: Optional[str]
    duration_seconds: Optional[float]
    source: str  # "groq-whisper" | "fallback" | "error"
    error: Optional[str] = None


def transcribir_audio(
    audio_path: str,
    *,
    language: Optional[str] = None,
) -> TranscriptionResult:
    path = Path(audio_path)
    if not path.exists():
        return TranscriptionResult(
            text="",
            language=None,
            duration_seconds=None,
            source="error",
            error=f"Archivo no encontrado: {audio_path}",
        )

    result = groq_audio_transcribe(
        audio_path=str(path),
        language=language or WHISPER_DEFAULT_LANGUAGE,
    )
    if not result:
        return TranscriptionResult(
            text="",
            language=None,
            duration_seconds=None,
            source="fallback",
            error="GROQ_API_KEY ausente o llamada fallida.",
        )

    text = (result.get("text") or "").strip()
    return TranscriptionResult(
        text=text,
        language=result.get("language") or language or WHISPER_DEFAULT_LANGUAGE,
        duration_seconds=result.get("duration"),
        source="groq-whisper",
    )


def warm_whisper() -> None:
    """No-op: el modelo vive en la nube, no hay carga local que precalentar."""
    return None
