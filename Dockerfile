# One stateless container: the phone app (static) + the API. Scales horizontally on Cloud Run.
FROM node:20-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
# ENVIRONMENT=prod refuses to start on demo settings; the judge demo runs with ENVIRONMENT=demo
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080 ENVIRONMENT=prod
# Tesseract with Indic models: shop licences arrive in regional scripts
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-hin tesseract-ocr-mar \
    tesseract-ocr-tam tesseract-ocr-tel tesseract-ocr-kan tesseract-ocr-guj tesseract-ocr-ben tesseract-ocr-mal tesseract-ocr-pan libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt
COPY api/ api/
COPY data/ data/
COPY --from=web /web/dist web/dist
# read the demo specimens once here, so no instance spends its first minutes on OCR
RUN cd api && ENVIRONMENT=demo python -c "from app.kyc.service import bake; bake()"
RUN useradd -m appuser && mkdir -p var && chown -R appuser /app
USER appuser
WORKDIR /app/api
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
