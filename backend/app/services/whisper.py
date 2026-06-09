"""Transcripcion de audio -> texto con Faster-Whisper local.

Este modulo cumple el requerimiento academico de ejecutar Whisper en el backend
sin depender de una API externa para speech-to-text. El modelo se carga una sola
vez por proceso y luego se reutiliza en cada peticion.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional


WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
WHISPER_DEFAULT_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "es")
WHISPER_CPU_THREADS = int(os.getenv("WHISPER_CPU_THREADS", "0"))
WHISPER_NUM_WORKERS = int(os.getenv("WHISPER_NUM_WORKERS", "1"))
WHISPER_BEAM_SIZE = int(os.getenv("WHISPER_BEAM_SIZE", "5"))
WHISPER_VAD_FILTER = os.getenv("WHISPER_VAD_FILTER", "true").lower() in {
    "1",
    "true",
    "yes",
    "si",
}


@dataclass
class TranscriptionResult:
    text: str
    language: Optional[str]
    duration_seconds: Optional[float]
    source: str  # "faster-whisper" | "error"
    error: Optional[str] = None


@lru_cache(maxsize=1)
def get_whisper_model():
    from faster_whisper import WhisperModel

    return WhisperModel(
        WHISPER_MODEL,
        device=WHISPER_DEVICE,
        compute_type=WHISPER_COMPUTE_TYPE,
        cpu_threads=WHISPER_CPU_THREADS,
        num_workers=WHISPER_NUM_WORKERS,
    )


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

    try:
        model = get_whisper_model()
        segments, info = model.transcribe(
            str(path),
            language=language or WHISPER_DEFAULT_LANGUAGE,
            beam_size=WHISPER_BEAM_SIZE,
            vad_filter=WHISPER_VAD_FILTER,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return TranscriptionResult(
            text=text,
            language=getattr(info, "language", None) or language or WHISPER_DEFAULT_LANGUAGE,
            duration_seconds=getattr(info, "duration", None),
            source="faster-whisper",
        )
    except Exception as exc:
        return TranscriptionResult(
            text="",
            language=None,
            duration_seconds=None,
            source="error",
            error=f"Faster-Whisper no pudo transcribir el audio: {exc}",
        )


def warm_whisper() -> None:
    """Precarga el modelo local para evitar latencia en la primera peticion."""
    get_whisper_model()
