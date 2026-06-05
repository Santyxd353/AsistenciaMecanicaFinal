"""Cliente Groq ligero (solo HTTP, sin dependencias ML).

Provee:
- groq_vision_json(): manda imagen(es) + prompt -> JSON estructurado.
- groq_audio_transcribe(): manda audio -> texto.

Diseno: 100% via urllib (stdlib) para vision JSON, y `requests` (multipart)
para el upload de audio. Sin torch, sin transformers, sin Pillow obligatorio.

Modelos por defecto:
- vision: `meta-llama/llama-4-scout-17b-16e-instruct` (free tier Groq, multimodal).
- audio:  `whisper-large-v3` (free tier).
Ambos overrideables via env `GROQ_VISION_MODEL` y `GROQ_AUDIO_MODEL`.

Si `GROQ_API_KEY` no esta seteada, las funciones devuelven None y dejan que
el caller decida que hacer (fallback Gemini, mensaje al usuario, etc.).
"""

from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path
from typing import Any, Optional
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

from PIL import Image


GROQ_API_BASE = "https://api.groq.com/openai/v1"
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
GROQ_AUDIO_MODEL = os.getenv("GROQ_AUDIO_MODEL", "whisper-large-v3")
GROQ_TIMEOUT_SECONDS = float(os.getenv("GROQ_TIMEOUT_SECONDS", "30"))


def _api_key() -> Optional[str]:
    key = os.getenv("GROQ_API_KEY", "").strip()
    return key or None


def _image_to_jpeg_b64(path: Path) -> Optional[str]:
    """Lee la imagen, la convierte a JPEG en memoria y devuelve base64.

    Groq vision actualmente acepta data URLs jpeg/png de forma estable.
    Otros formatos (webp, gif, heic) llegan a producir 403/400. Estandarizar
    a JPEG via PIL evita ese problema y reduce el tamano del payload.
    """
    try:
        with Image.open(path) as img:
            rgb = img.convert("RGB")
            # Limitar la resolucion para mantener el payload chico: bajamos a
            # 1280px en el lado mayor (suficiente para placa/marca/modelo).
            rgb.thumbnail((1280, 1280))
            buf = io.BytesIO()
            rgb.save(buf, format="JPEG", quality=85, optimize=True)
            return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception as exc:  # noqa: BLE001
        print(f"[groq_vision] no se pudo convertir {path} a JPEG: {exc}")
        return None


def groq_vision_json(
    *,
    image_paths: list[str],
    prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 512,
) -> Optional[dict[str, Any]]:
    """Llama al endpoint chat/completions de Groq con imagenes inline.

    Devuelve el JSON parseado del primer choice (esperado JSON puro) o None
    si no hay key, hubo error de red, o la respuesta no es JSON parseable.
    """
    key = _api_key()
    if not key or not image_paths:
        return None

    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for raw_path in image_paths[:4]:
        path = Path(raw_path)
        if not path.exists():
            continue
        b64 = _image_to_jpeg_b64(path)
        if not b64:
            continue
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })

    if len(content) == 1:  # ninguna imagen valida
        return None

    payload = {
        "model": model or GROQ_VISION_MODEL,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    request = Request(
        url=f"{GROQ_API_BASE}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            # Cloudflare WAF de Groq devuelve 403 (error code 1010) si el
            # User-Agent es `Python-urllib/...`. Forzamos uno aceptado.
            "User-Agent": "asistencia-mecanica-backend/1.0 (+https://groq.com)",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=GROQ_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            body = "<no body>"
        print(f"[groq_vision] HTTPError {exc.code}: {body}")
        return None
    except (URLError, TimeoutError, ValueError) as exc:
        print(f"[groq_vision] error: {exc}")
        return None

    choices = data.get("choices") or []
    if not choices:
        return None
    raw_text = ((choices[0].get("message") or {}).get("content") or "").strip()
    # response_format=json_object debe garantizar JSON puro, pero quitamos
    # cercas de markdown por si el modelo las envuelve igual.
    cleaned = raw_text.strip("`")
    if cleaned.startswith("json"):
        cleaned = cleaned[4:].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        print(f"[groq_vision] JSON invalido: {exc} | raw={raw_text[:200]}")
        return None


def groq_audio_transcribe(
    *,
    audio_path: str,
    language: Optional[str] = None,
    model: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Sube un audio al endpoint audio/transcriptions de Groq (Whisper).

    Devuelve dict con `text`, `language`, `duration` (cuando viene) o None.
    Usa `requests` para multipart porque urllib hace muy engorroso multipart.
    """
    key = _api_key()
    path = Path(audio_path)
    if not key or not path.exists():
        return None

    try:
        import requests  # type: ignore
    except Exception as exc:  # noqa: BLE001
        print(f"[groq_audio] requests no disponible: {exc}")
        return None

    files = {"file": (path.name, path.read_bytes(), "application/octet-stream")}
    data = {
        "model": model or GROQ_AUDIO_MODEL,
        "response_format": "verbose_json",
        "temperature": "0",
    }
    if language:
        data["language"] = language

    try:
        resp = requests.post(
            f"{GROQ_API_BASE}/audio/transcriptions",
            headers={"Authorization": f"Bearer {key}"},
            files=files,
            data=data,
            timeout=GROQ_TIMEOUT_SECONDS,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[groq_audio] error red: {exc}")
        return None

    if resp.status_code >= 400:
        print(f"[groq_audio] HTTP {resp.status_code}: {resp.text[:200]}")
        return None
    try:
        return resp.json()
    except ValueError as exc:
        print(f"[groq_audio] JSON invalido: {exc}")
        return None
