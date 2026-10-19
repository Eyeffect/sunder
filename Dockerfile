# SUNDER — web server image
# multi-stage: build the SPA with node, run FastAPI+uvicorn from source.
FROM node:22-alpine AS web
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/index.html web/tsconfig.json web/vite.config.ts ./
COPY web/src ./src
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
# deps first so this layer survives code changes
COPY pyproject.toml ./
RUN pip install --no-cache-dir fastapi 'uvicorn[standard]' httpx
COPY sunder ./sunder
COPY --from=web /build/web/dist ./web/dist
EXPOSE 8000
CMD ["uvicorn", "sunder.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
