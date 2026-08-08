FROM python:3.11-slim

LABEL maintainer="Sanji_fr"
LABEL description="Reze - Telegram Group Management Bot"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# System dependencies:
# - build-essential: compiles TgCrypto
# - libjpeg/zlib/libwebp: Pillow image + WEBP sticker support
# - ffmpeg: video/gif -> VP9 webm video sticker encoding, downloader module
# - Noto fonts: Unicode, italic/bold text and emoji rendering

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libwebp-dev \
    ffmpeg \
    fonts-dejavu-core \
    fonts-noto-core \
    fonts-noto-math \
    fonts-noto-color-emoji \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway injects $PORT for web services.
# Reze is a polling bot, so no EXPOSE/health endpoint is required.

CMD ["python3", "-m", "Reze"]
