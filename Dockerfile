FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    gettext \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-django.txt .
RUN pip install --no-cache-dir -r requirements-django.txt

COPY . .

EXPOSE 8000
