FROM node:22-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ENV VITE_USE_MOCK=false VITE_API_URL=/api/v1
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
    FRONTEND_DIST_DIR=/app/frontend/dist OCR_MODEL_DIR=/app/ocr-models
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
COPY backend/app/ai/requirements-ai.txt backend/app/ai/requirements-ai.txt
RUN pip install --no-cache-dir -r backend/requirements.txt -r backend/app/ai/requirements-ai.txt 'psycopg[binary]>=3.2,<4' 'onnxruntime>=1.20,<2'
COPY backend/ backend/
RUN python -c 'from backend.app.ai.document_processor import warm_ocr_models; warm_ocr_models()'
COPY --from=frontend /build/frontend/dist/ frontend/dist/
COPY scripts/start.sh scripts/start.sh
RUN chmod +x scripts/start.sh
EXPOSE 10000
CMD ["./scripts/start.sh"]
