import os
import mimetypes
from pathlib import Path
from typing import Generator
from fastapi import Request, HTTPException, status
from fastapi.responses import StreamingResponse

from app.fs_ops import resolve_safe_path

CHUNK_SIZE = 64 * 1024  # 64 KB

AUDIO_MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
    ".wav": "audio/wav",
    ".wave": "audio/wav",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".opus": "audio/opus",
    ".aif": "audio/x-aiff",
    ".aiff": "audio/x-aiff",
}


def _file_chunk_generator(file_path: Path, start: int, end: int) -> Generator[bytes, None, None]:
    with open(file_path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk = f.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def stream_audio_file(request: Request, rel_path: str) -> StreamingResponse:
    file_path = resolve_safe_path(rel_path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found")

    ext = file_path.suffix.lower()
    media_type = AUDIO_MIME_TYPES.get(ext, mimetypes.guess_type(str(file_path))[0] or "application/octet-stream")
    file_size = file_path.stat().st_size

    range_header = request.headers.get("Range")

    if not range_header:
        headers = {
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Content-Type": media_type,
        }
        return StreamingResponse(
            _file_chunk_generator(file_path, 0, file_size - 1),
            status_code=status.HTTP_200_OK,
            headers=headers,
            media_type=media_type,
        )

    # Range header present, e.g. "bytes=0-1023" or "bytes=1024-"
    try:
        units, ranges = range_header.split("=", 1)
        if units.strip() != "bytes":
            raise ValueError()

        parts = ranges.strip().split("-", 1)
        start_str, end_str = parts[0].strip(), parts[1].strip()

        if start_str and end_str:
            start = int(start_str)
            end = int(end_str)
        elif start_str:
            start = int(start_str)
            end = file_size - 1
        elif end_str:
            # Suffix range
            length = int(end_str)
            start = max(0, file_size - length)
            end = file_size - 1
        else:
            raise ValueError()

        if start >= file_size or end >= file_size or start > end:
            return StreamingResponse(
                b"",
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                headers={"Content-Range": f"bytes */{file_size}"}
            )

        content_length = end - start + 1
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": media_type,
        }

        return StreamingResponse(
            _file_chunk_generator(file_path, start, end),
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            headers=headers,
            media_type=media_type,
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="Invalid range request"
        )
