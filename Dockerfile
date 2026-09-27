FROM docker.io/library/python:3.12-slim

# Install flac and lame for lossless and mp3 processing & demo generation
RUN apt-get update && \
    apt-get install -y --no-install-recommends flac lame && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definitions and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY app/ ./app

# Create default directories for volume mounts
RUN mkdir -p /music /auth

# Environment configuration
ENV PYTHONUNBUFFERED=1
ENV MUSIC_DIR=/music
ENV HTPASSWD_PATH=/auth/.htpasswd
ENV PORT=8080

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
