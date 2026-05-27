"""Clasificador básico de incidentes vehiculares por imagen.

El módulo `ai.py` ya cubría detección de marca/modelo. Este servicio se ocupa
del problema complementario: **¿qué tipo de daño se ve en la foto?**.

Estrategia híbrida (todo opcional, todo con fallback):

1. **Heurística por color/textura** — siempre disponible, ligero. Detecta
   patrones genéricos (predominio de negro = posible humo/quemado, mucho
   gris/textura irregular = posible abolladura, etc). Es muy imperfecta pero
   estable y rápida, ideal para que la UI siempre tenga algo que mostrar.
2. **Modelo HF** (opcional) — si `transformers` y un modelo pre-entrenado
   están disponibles, lo usamos. Default `microsoft/resnet-50` con el mapa
   de ImageNet, filtrado a clases que correlacionen con daño/llanta/coche.
3. **Gemini Vision** — si hay `GEMINI_API_KEY`, delegamos la clasificación
   con un prompt acotado a las 5 categorías del producto.

Categorías canónicas (las mismas que usa el motor de asignación):
    `bateria`, `llanta`, `choque`, `motor`, `otros`.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from PIL import Image, ImageStat

from app.services.storage import guess_mime_type


GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "20"))
HF_DAMAGE_MODEL = os.getenv("HF_DAMAGE_MODEL", "").strip()

CATEGORIAS_VALIDAS = {"bateria", "llanta", "choque", "motor", "otros"}


@dataclass
class DamageAnalysis:
    categoria: str
    confianza: float
    descripcion: str
    source: str  # "gemini" | "hf" | "heuristic"


def analizar_dano(image_path: str) -> DamageAnalysis:
    """Punto de entrada principal. Devuelve siempre un resultado utilizable."""
    if os.getenv("GEMINI_API_KEY", "").strip():
        result = _analizar_con_gemini(image_path)
        if result is not None:
            return result

    if HF_DAMAGE_MODEL:
        result = _analizar_con_hf(image_path)
        if result is not None:
            return result

    return _analizar_heuristico(image_path)


def _analizar_con_gemini(image_path: str) -> Optional[DamageAnalysis]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    path = Path(image_path)
    if not path.exists():
        return None

    prompt = (
        "Eres un perito de seguros automotriz. Mira la imagen y devuelve solo JSON "
        "con las claves exactas: categoria, confianza, descripcion. "
        "categoria debe ser UNA de: bateria, llanta, choque, motor, otros. "
        "confianza es un decimal entre 0 y 1. "
        "descripcion: una frase breve en español sobre el daño visible."
    )

    try:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    except Exception as exc:  # noqa: BLE001
        print(f"No se pudo leer la imagen para Gemini: {exc}")
        return None

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": guess_mime_type(str(path)),
                            "data": encoded,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={api_key}"
    )
    request = Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=GEMINI_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, ValueError) as exc:
        print(f"Gemini damage falló: {exc}")
        return None

    candidates = data.get("candidates") or []
    if not candidates:
        return None
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "\n".join(part.get("text", "") for part in parts if isinstance(part, dict))
    cleaned = text.strip().lstrip("`").strip()
    if cleaned.startswith("json"):
        cleaned = cleaned[4:].strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return None

    categoria = str(parsed.get("categoria", "")).strip().lower()
    if categoria not in CATEGORIAS_VALIDAS:
        categoria = "otros"
    confianza = parsed.get("confianza")
    try:
        confianza_value = float(confianza) if confianza is not None else 0.6
    except (TypeError, ValueError):
        confianza_value = 0.6
    descripcion = str(parsed.get("descripcion") or "").strip() or "Daño identificado por IA."

    return DamageAnalysis(
        categoria=categoria,
        confianza=max(0.0, min(1.0, confianza_value)),
        descripcion=descripcion,
        source="gemini",
    )


@lru_cache(maxsize=1)
def _load_hf_classifier():
    if not HF_DAMAGE_MODEL:
        return None
    try:
        from transformers import AutoImageProcessor, AutoModelForImageClassification  # type: ignore
    except Exception as exc:  # noqa: BLE001
        print(f"transformers no disponible: {exc}")
        return None
    try:
        processor = AutoImageProcessor.from_pretrained(HF_DAMAGE_MODEL)
        model = AutoModelForImageClassification.from_pretrained(HF_DAMAGE_MODEL)
        model.eval()
        return processor, model
    except Exception as exc:  # noqa: BLE001
        print(f"No se pudo cargar el modelo HF de daños '{HF_DAMAGE_MODEL}': {exc}")
        return None


def _analizar_con_hf(image_path: str) -> Optional[DamageAnalysis]:
    bundle = _load_hf_classifier()
    if bundle is None:
        return None

    try:
        image = Image.open(image_path).convert("RGB")
    except Exception:
        return None

    processor, model = bundle
    inputs = processor(images=image, return_tensors="pt")
    outputs = model(**inputs)
    logits = outputs.logits[0]
    probabilities = logits.softmax(dim=0)
    top_index = int(probabilities.argmax().item())
    label = (model.config.id2label.get(top_index, "") or "").lower()
    confidence = float(probabilities[top_index].item())
    return DamageAnalysis(
        categoria=_mapear_label_a_categoria(label),
        confianza=confidence,
        descripcion=f"Clasificación HF: {label}",
        source="hf",
    )


def _mapear_label_a_categoria(label: str) -> str:
    label_norm = label.lower()
    if any(k in label_norm for k in ("tire", "wheel", "rim", "neumat", "llant")):
        return "llanta"
    if any(k in label_norm for k in ("engine", "motor", "smoke", "humo", "fire")):
        return "motor"
    if any(k in label_norm for k in ("battery", "bateria")):
        return "bateria"
    if any(k in label_norm for k in ("crash", "wreck", "dented", "choque", "colision")):
        return "choque"
    return "otros"


def _analizar_heuristico(image_path: str) -> DamageAnalysis:
    """Fallback determinista basado en color medio y nombre de archivo.

    No pretende ser exacto: garantiza que el sistema **siempre** devuelva algo
    coherente para que la UI no muestre estado vacío.
    """
    path = Path(image_path)
    nombre = path.stem.lower()
    if any(k in nombre for k in ("bateria", "battery")):
        return DamageAnalysis(
            categoria="bateria",
            confianza=0.45,
            descripcion="Heurística por nombre de archivo: indicio de problema de batería.",
            source="heuristic",
        )
    if any(k in nombre for k in ("llanta", "rueda", "tire", "wheel")):
        return DamageAnalysis(
            categoria="llanta",
            confianza=0.45,
            descripcion="Heurística por nombre de archivo: indicio de problema de llanta.",
            source="heuristic",
        )
    if any(k in nombre for k in ("choque", "crash", "accident")):
        return DamageAnalysis(
            categoria="choque",
            confianza=0.5,
            descripcion="Heurística por nombre de archivo: posible colisión.",
            source="heuristic",
        )

    try:
        image = Image.open(image_path).convert("RGB")
    except Exception:
        return DamageAnalysis(
            categoria="otros",
            confianza=0.3,
            descripcion="No se pudo abrir la imagen para análisis heurístico.",
            source="heuristic",
        )

    sample = image.resize((64, 64))
    stat = ImageStat.Stat(sample)
    r, g, b = stat.mean[:3]
    brightness = (r + g + b) / 3.0

    if brightness < 55:
        return DamageAnalysis(
            categoria="motor",
            confianza=0.35,
            descripcion="Predominio de tonos oscuros: posible humo o vano de motor.",
            source="heuristic",
        )
    if max(r, g, b) - min(r, g, b) < 18 and brightness < 140:
        return DamageAnalysis(
            categoria="llanta",
            confianza=0.35,
            descripcion="Tonos grisáceos uniformes: probable detalle de neumático/rueda.",
            source="heuristic",
        )
    return DamageAnalysis(
        categoria="otros",
        confianza=0.4,
        descripcion="Imagen recibida; clasificación heurística no concluyente.",
        source="heuristic",
    )
