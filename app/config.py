import os
from pathlib import Path

# Paths
MUSIC_DIR = Path(os.environ.get("MUSIC_DIR", "./music_library")).resolve()
HTPASSWD_PATH = Path(os.environ.get("HTPASSWD_PATH", "./.htpasswd")).resolve()

# App settings
SECRET_KEY = os.environ.get("SECRET_KEY", "musictagger-secret-key-change-in-prod-2025")
SESSION_COOKIE_NAME = "musictagger_session"
SESSION_TTL_HOURS = 72

ALLOWED_AUDIO_EXTENSIONS = {
    ".mp3", ".flac", ".wav", ".m4a", ".mp4", ".aac", ".ogg", ".opus", ".aif", ".aiff"
}

ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp"
}
