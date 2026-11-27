FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SICKSHIFT_DATA_DIR=/data \
    SICKSHIFT_NO_AUTO_INSTALL=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-dashboard.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dashboard.txt orjson

COPY . /app

RUN mkdir -p /data /shows \
    && chmod +x /app/sickshift.py

VOLUME ["/data", "/shows"]
EXPOSE 8081

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8081/dashboard/health || exit 1

ENTRYPOINT ["python", "/app/sickshift.py", "--datadir", "/data", "--config", "/data/config.ini", "--nolaunch"]
