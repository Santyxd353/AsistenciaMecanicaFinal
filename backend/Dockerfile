FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema (mucho mas ligeras que antes):
# * build-essential / libpq-dev -> compilacion de psycopg2-binary (suele
#   ser opcional con wheels precompiladas, pero las dejamos para alpine-like)
# * curl -> usado por el HEALTHCHECK
#
# Removidos respecto a la version anterior (>10 GB final):
#   - tesseract-ocr / tesseract-ocr-spa  (OCR ahora lo hace el LLM en la nube)
#   - ffmpeg                              (audio ahora via Groq Whisper API)
#   - libgl1 / libglib2.0-0               (no hay torch/transformers locales)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY . .

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:${PORT:-8000}/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
