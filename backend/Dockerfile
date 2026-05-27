FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema:
# * build-essential / libpq-dev → compilación de psycopg2
# * tesseract-ocr / tesseract-ocr-spa → OCR para placas y texto vehicular
# * ffmpeg → decodificación de audios para faster-whisper
# * libgl1 / libglib2.0-0 → runtime de OpenCV/Pillow para modelos HF
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    tesseract-ocr \
    tesseract-ocr-spa \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY . .

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:${PORT:-8000}/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
