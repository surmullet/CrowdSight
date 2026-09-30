# ==========================================
# CrowdSight Multi-Stage Production Dockerfile
# ==========================================

# Stage 1: Build Frontend UI
FROM node:22-alpine AS web-builder
WORKDIR /app/web

# Install pnpm 9 LTS for stable container builds
RUN corepack enable && corepack prepare pnpm@9.15.4 --activate

# Copy package manifests and install dependencies
COPY web/package.json web/pnpm-lock.yaml* web/pnpm-workspace.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install

# Copy web source and build production bundle
COPY web/ ./
COPY contracts/app-v1/ ../contracts/app-v1/
RUN pnpm run build

# Stage 2: Python Application Runtime
FROM python:3.10-slim AS runtime
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    CROWDSIGHT_ENVIRONMENT=production \
    CROWDSIGHT_DATABASE_URL=sqlite:////app/data/db/crowdsight.db \
    CROWDSIGHT_MEDIA_ROOT=/app/data/media \
    CROWDSIGHT_ARTIFACT_ROOT=/app/data/artifacts \
    CROWDSIGHT_RETENTION_DAYS=30

# Install system dependencies: ffmpeg for video decoding/transcoding, libgl for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    fastapi uvicorn pydantic pydantic-settings sqlalchemy \
    opencv-python-headless numpy shapely jsonschema \
    structlog pyyaml httpx

# Copy backend source code and contracts
COPY src/ ./src/
COPY configs/ ./configs/
COPY contracts/ ./contracts/
COPY scripts/ ./scripts/

# Install the application package
RUN pip install -e .

# Copy built frontend assets from Stage 1
COPY --from=web-builder /app/web/dist ./web/dist

# Create storage directories
RUN mkdir -p /app/data/media /app/data/artifacts /app/data/db

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "crowdsight.service.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
