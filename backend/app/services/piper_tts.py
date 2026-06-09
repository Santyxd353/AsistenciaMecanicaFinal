"""Sintesis de voz local con Piper TTS.

Piper ejecuta inferencia local en CPU. La voz se descarga una vez si no existe
en el volumen de uploads y luego queda cacheada para ejecuciones offline.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlretrieve
from uuid import uuid4

from app.services.storage import UPLOAD_ROOT


PIPER_BINARY = os.getenv("PIPER_BINARY", "piper")
PIPER_VOICE_NAME = os.getenv("PIPER_VOICE_NAME", "es_ES-carlfm-x_low")
PIPER_VOICE_DIR = Path(os.getenv("PIPER_VOICE_DIR", str(UPLOAD_ROOT / "piper-voices"))).resolve()
PIPER_OUTPUT_DIR = Path(os.getenv("PIPER_OUTPUT_DIR", str(UPLOAD_ROOT / "tts"))).resolve()
PIPER_TIMEOUT_SECONDS = int(os.getenv("PIPER_TIMEOUT_SECONDS", "30"))
PIPER_AUTO_DOWNLOAD = os.getenv("PIPER_AUTO_DOWNLOAD", "true").lower() in {
    "1",
    "true",
    "yes",
    "si",
}
PIPER_VOICE_BASE_URL = os.getenv(
    "PIPER_VOICE_BASE_URL",
    "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/carlfm/x_low",
)


@dataclass
class TtsResult:
    text: str
    relative_url: str | None
    source: str
    error: str | None = None


def _voice_model_path() -> Path:
    return PIPER_VOICE_DIR / f"{PIPER_VOICE_NAME}.onnx"


def _voice_config_path() -> Path:
    return PIPER_VOICE_DIR / f"{PIPER_VOICE_NAME}.onnx.json"


def ensure_piper_voice() -> tuple[Path | None, str | None]:
    PIPER_VOICE_DIR.mkdir(parents=True, exist_ok=True)
    model_path = _voice_model_path()
    config_path = _voice_config_path()
    if model_path.exists() and config_path.exists():
        return model_path, None

    if not PIPER_AUTO_DOWNLOAD:
        return None, (
            f"Modelo Piper no encontrado en {model_path}. "
            "Descargue el .onnx y .onnx.json o active PIPER_AUTO_DOWNLOAD."
        )

    try:
        urlretrieve(f"{PIPER_VOICE_BASE_URL}/{model_path.name}?download=true", model_path)
        urlretrieve(f"{PIPER_VOICE_BASE_URL}/{config_path.name}?download=true", config_path)
    except Exception as exc:
        model_path.unlink(missing_ok=True)
        config_path.unlink(missing_ok=True)
        return None, f"No se pudo descargar la voz Piper {PIPER_VOICE_NAME}: {exc}"

    return model_path, None


def synthesize_speech(text: str, *, prefix: str = "asistente") -> TtsResult:
    clean_text = " ".join(text.strip().split())
    if not clean_text:
        return TtsResult(text="", relative_url=None, source="error", error="Texto vacio.")

    model_path, error = ensure_piper_voice()
    if error or not model_path:
        return TtsResult(text=clean_text, relative_url=None, source="error", error=error)

    PIPER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PIPER_OUTPUT_DIR / f"{prefix}-{uuid4().hex}.wav"
    try:
        subprocess.run(
            [
                PIPER_BINARY,
                "--model",
                str(model_path),
                "--output_file",
                str(output_path),
            ],
            input=clean_text,
            text=True,
            capture_output=True,
            check=True,
            timeout=PIPER_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        output_path.unlink(missing_ok=True)
        return TtsResult(
            text=clean_text,
            relative_url=None,
            source="error",
            error=f"Piper no pudo sintetizar el audio: {exc}",
        )

    relative_url = f"/uploads/tts/{output_path.name}"
    return TtsResult(text=clean_text, relative_url=relative_url, source="piper-tts")
