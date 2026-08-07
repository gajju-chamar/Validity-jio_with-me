FROM python:3.11-slim

LABEL maintainer="Sanji_fr"
LABEL description="Reze - Telegram Group Management Bot"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# System deps:
#  - build-essential: compiles TgCrypto (speed boost for MTProto)
#  - libjpeg/zlib/libwebp: Pillow image + WEBP sticker support
#  - ffmpeg: video/gif -> VP9 webm video sticker encoding, downloader module
#  - fonts: quote-card + sticker text rendering with broad unicode/emoji coverage
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libwebp-dev \
    ffmpeg \
    fonts-dejavu-core \
    fonts-noto-color-emoji \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway injects $PORT for web services; Reze is a polling bot (no web server),
# so no EXPOSE/health endpoint is required. See Reze/__main__.py.
CMD ["python3", "-m", "Reze"]
