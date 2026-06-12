# syntax=docker/dockerfile:1

# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — build the React frontend into static assets
# ─────────────────────────────────────────────────────────────────────────────
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install
COPY frontend/ ./
RUN npm run build

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — Python runtime serving the API + the built UI
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    CAPTION_STATIC_DIR=/app/static \
    DATA_DIR=/data

# ffmpeg for audio extraction; libgomp1 is required by CTranslate2 (faster-whisper).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

# Optional GPU support: build with `--build-arg INSTALL_CUDA=true` to add the
# CUDA libraries CTranslate2 needs. Leave false for the lean CPU image.
ARG INSTALL_CUDA=false
RUN if [ "$INSTALL_CUDA" = "true" ]; then \
        pip install nvidia-cublas-cu12 nvidia-cudnn-cu12; \
    fi

# Optional bundled offline translator: build with `--build-arg BUNDLE_TRANSLATE=true`
# to embed LibreTranslate (the ":*-translate" image). Adds ~2 GB (it pulls PyTorch).
ARG BUNDLE_TRANSLATE=false
ENV BUNDLE_TRANSLATE=${BUNDLE_TRANSLATE}
RUN if [ "$BUNDLE_TRANSLATE" = "true" ]; then pip install libretranslate; fi

COPY backend/ ./
COPY --from=frontend /frontend/dist /app/static
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).status==200 else 1)"

ENTRYPOINT ["/entrypoint.sh"]
