"""Transcripción de audio → texto con faster-whisper (CPU local).

Decisiones:
* Usamos `faster-whisper` en lugar de `openai-whisper` por menor consumo RAM
  y por estar optimizado con CTranslate2 (~4x más rápido en CPU).
* El modelo se carga perezosamente y se cachea con `@lru_cache` para no pagar
  el coste de carga en cada request.
* Tamaño del modelo controlado por env `WHISPER_MODEL_SIZE` (default `small`).
  Para producción podríamos saltar a `medium`/`large-v3` si hay GPU.
* Idioma fijado a español por defecto pero permitimos override por request.

Si la dependencia `faster-whisper` no está instalada, el módulo igual carga
y `transcribir_audio` devuelve un fallback explícito en lugar de romper el
arranque del backend. Esto facilita ejecutar el resto del sistema sin la IA
pesada durante desarrollo.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional


WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
WHISPER_DEFAULT_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "es")


@dataclass
class TranscriptionResult:
    text: str
    language: Optional[str]
    duration_seconds: Optional[float]
    source: str  # "faster-whisper" | "fallback" | "error"
    error: Optional[str] = None


@lru_cache(maxsize=1)
def _load_model():
    """Carga perezosa del modelo. Devuelve None si la dependencia no está."""
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception as exc:  # noqa: BLE001
        print(f"faster-whisper no disponible: {exc}")
        return None
    try:
        return WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"No se pudo cargar el modelo whisper '{WHISPER_MODEL_SIZE}': {exc}")
        return None


def transcribir_audio(
    audio_path: str,
    *,
    language: Optional[str] = None,
) -> TranscriptionResult:
    """Transcribe el archivo de audio indicado.

    El audio puede venir en cualquier formato soportado por ffmpeg (mp3, wav,
    m4a, ogg, webm). faster-whisper lo decodifica internamente.
    """
    path = Path(audio_path)
    if not path.exists():
        return TranscriptionResult(
            text="",
            language=None,
            duration_seconds=None,
            source="error",
            error=f"Archivo no encontrado: {audio_path}",
        )

    model = _load_model()
    if model is None:
        return TranscriptionResult(
            text="",
            language=None,
            duration_seconds=None,
            source="fallback",
            error="faster-whisper no instalado o modelo no disponible.",
        )

    try:
        segments_iter, info = model.transcribe(
            str(path),
            language=language or WHISPER_DEFAULT_LANGUAGE,
            beam_size=1,
            vad_filter=True,
        )
        # segments es un generator; lo materializamos para devolver el texto
        # completo en una sola pasada.
        segments = list(segments_iter)
        text = " ".join(segment.text.strip() for segment in segments if segment.text).strip()
        return TranscriptionResult(
            text=text,
            language=info.language,
            duration_seconds=getattr(info, "duration", None),
            source="faster-whisper",
        )
    except Exception as exc:  # noqa: BLE001
        return TranscriptionResult(
            text="",
            language=None,
            duration_seconds=None,
            source="error",
            error=str(exc),
        )


def warm_whisper() -> None:
    """Pre-carga el modelo. Útil en background si se quiere precalentar."""
    _load_model()
