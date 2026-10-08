# Một ảnh cho cả sản phẩm (spec 07, mục 1.1): bước đầu dựng giao diện, bước sau là máy chủ Python phục vụ cả API lẫn giao diện.
FROM node:22-slim AS web
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web ./
# Khóa bản đồ của Goong nằm trong mã giao diện (trình duyệt cần nó để tải ô bản đồ), nên phải có lúc dựng.
ARG VITE_GOONG_MAP_KEY
ENV VITE_GOONG_MAP_KEY=$VITE_GOONG_MAP_KEY VITE_API_BASE=
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements-run.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements-run.txt
COPY src src
RUN pip install --no-cache-dir --no-deps .
COPY --from=web /app/web/dist web/dist
ENV FLOODRISK_DATA=/data FLOODRISK_WEB_DIST=/app/web/dist REFRESH_MINUTES=60 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "floodrisk.api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
