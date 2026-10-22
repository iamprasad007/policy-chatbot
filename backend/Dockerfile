# Build context is the repo root (see docker-compose.yml), so frontend/ and
# widget/ are visible alongside backend/ for the static-asset build stages.

FROM node:20-slim AS frontend-build
WORKDIR /src
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM node:20-slim AS widget-build
WORKDIR /src
COPY widget/package*.json ./
RUN npm ci
COPY widget/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download embedding model at build time
RUN python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY backend/ .
COPY --from=frontend-build /src/dist /app/frontend_dist
COPY --from=widget-build /src/dist /app/widget_dist

EXPOSE 5000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
