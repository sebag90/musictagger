import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import HTMLResponse, JSONResponse, Response as RawResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import (
    MUSIC_DIR, HTPASSWD_PATH, SESSION_COOKIE_NAME,
    ALLOWED_AUDIO_EXTENSIONS, ALLOWED_IMAGE_EXTENSIONS
)
from app.auth import (
    authenticate_user, create_session_token, get_authenticated_user, require_user
)
from app.fs_ops import (
    resolve_safe_path, to_relative_path, get_directory_tree,
    list_directory, create_directory, rename_item, move_items, delete_items
)
from app.metadata_ops import (
    get_audio_metadata, update_audio_metadata, get_artwork_bytes,
    set_artwork_bytes, remove_artwork
)
from app.audio_stream import stream_audio_file
from app.waveform import generate_waveform_peaks
from app.demo_data import populate_demo_library


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure music directory exists and populate demo data if empty
    try:
        populate_demo_library(force=False)
    except Exception as e:
        print(f"Warning: demo library generation: {e}")
    yield


app = FastAPI(title="Resonance Sound Studio - Music Library Manager", lifespan=lifespan)

# Mount static directory
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Pydantic Request Models
class LoginRequest(BaseModel):
    username: str
    password: str


class MkdirRequest(BaseModel):
    parent_path: str = ""
    name: str


class RenameRequest(BaseModel):
    path: str
    new_name: str


class MoveRequest(BaseModel):
    paths: List[str]
    target_dir: str


class DeleteRequest(BaseModel):
    paths: List[str]


class MetadataUpdateRequest(BaseModel):
    path: str
    title: Optional[str] = ""
    artist: Optional[str] = ""
    album_artist: Optional[str] = ""
    album: Optional[str] = ""
    year: Optional[str] = ""
    genre: Optional[str] = ""
    track_number: Optional[str] = ""
    track_total: Optional[str] = ""
    disc_number: Optional[str] = ""
    disc_total: Optional[str] = ""
    composer: Optional[str] = ""
    comment: Optional[str] = ""


class BatchMetadataUpdateRequest(BaseModel):
    paths: List[str]
    artist: Optional[str] = None
    album_artist: Optional[str] = None
    album: Optional[str] = None
    year: Optional[str] = None
    genre: Optional[str] = None
    composer: Optional[str] = None
    comment: Optional[str] = None


# --------------------------------------------------------------------------
# Auth Endpoints
# --------------------------------------------------------------------------

@app.post("/api/auth/login")
async def login(req: LoginRequest, response: Response):
    if not authenticate_user(req.username, req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    token = create_session_token(req.username)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=72 * 3600,
        path="/"
    )
    return {"username": req.username, "authenticated": True}


@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return {"authenticated": False}


@app.get("/api/auth/me")
async def get_me(request: Request):
    user = get_authenticated_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in")
    return {"username": user, "authenticated": True}


# --------------------------------------------------------------------------
# Filesystem Endpoints
# --------------------------------------------------------------------------

@app.get("/api/fs/tree")
async def api_get_tree(user: str = Depends(require_user)):
    return get_directory_tree()


@app.get("/api/fs/ls")
async def api_list_directory(path: str = "", user: str = Depends(require_user)):
    return list_directory(path)


@app.post("/api/fs/mkdir")
async def api_create_directory(req: MkdirRequest, user: str = Depends(require_user)):
    return create_directory(req.parent_path, req.name)


@app.post("/api/fs/rename")
async def api_rename(req: RenameRequest, user: str = Depends(require_user)):
    return rename_item(req.path, req.new_name)


@app.post("/api/fs/move")
async def api_move(req: MoveRequest, user: str = Depends(require_user)):
    return move_items(req.paths, req.target_dir)


@app.post("/api/fs/delete")
async def api_delete(req: DeleteRequest, user: str = Depends(require_user)):
    return delete_items(req.paths)


@app.post("/api/fs/upload")
async def api_upload(
    target_dir: str = Form(""),
    files: List[UploadFile] = File(...),
    user: str = Depends(require_user)
):
    dest_dir = resolve_safe_path(target_dir)
    if not dest_dir.exists() or not dest_dir.is_dir():
        raise HTTPException(status_code=404, detail="Destination directory not found")

    saved_files = []
    for upload in files:
        if not upload.filename:
            continue
        clean_name = Path(upload.filename).name.replace("/", "_").replace("\\", "_")
        dest_path = dest_dir / clean_name

        # Avoid collision
        if dest_path.exists():
            stem, suffix = dest_path.stem, dest_path.suffix
            counter = 1
            while dest_path.exists():
                dest_path = dest_dir / f"{stem} ({counter}){suffix}"
                counter += 1

        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)

        saved_files.append(to_relative_path(dest_path))

    return {
        "success": True,
        "count": len(saved_files),
        "files": saved_files,
    }


# --------------------------------------------------------------------------
# Audio & Metadata Endpoints
# --------------------------------------------------------------------------

@app.get("/api/audio/metadata")
async def api_get_metadata(path: str, user: str = Depends(require_user)):
    return get_audio_metadata(path)


@app.post("/api/audio/metadata")
async def api_update_metadata(req: MetadataUpdateRequest, user: str = Depends(require_user)):
    return update_audio_metadata(req.path, req.model_dump())


@app.post("/api/audio/batch-metadata")
async def api_batch_update_metadata(req: BatchMetadataUpdateRequest, user: str = Depends(require_user)):
    updated = []
    errors = []
    update_dict = {k: v for k, v in req.model_dump().items() if k != "paths" and v is not None and v != ""}

    for path in req.paths:
        try:
            current = get_audio_metadata(path)
            merged = {**current, **update_dict}
            res = update_audio_metadata(path, merged)
            updated.append(path)
        except Exception as e:
            errors.append({"path": path, "error": str(e)})

    return {
        "success": len(errors) == 0,
        "updated": updated,
        "errors": errors,
    }


@app.get("/api/audio/artwork")
async def api_get_artwork(path: str, user: str = Depends(require_user)):
    img_bytes, mime = get_artwork_bytes(path)
    return RawResponse(
        content=img_bytes,
        media_type=mime,
        headers={"Cache-Control": "public, max-age=60"}
    )


@app.post("/api/audio/artwork")
async def api_set_artwork(
    path: str = Form(...),
    file: UploadFile = File(...),
    user: str = Depends(require_user)
):
    img_bytes = await file.read()
    if not img_bytes:
        raise HTTPException(status_code=400, detail="Empty image file")
    mime = file.content_type or "image/jpeg"
    return set_artwork_bytes(path, img_bytes, mime)


@app.delete("/api/audio/artwork")
async def api_remove_artwork(path: str, user: str = Depends(require_user)):
    return remove_artwork(path)


@app.get("/api/audio/waveform")
async def api_get_waveform(path: str, user: str = Depends(require_user)):
    peaks = generate_waveform_peaks(path)
    return {"path": path, "peaks": peaks}


@app.get("/api/audio/stream")
async def api_stream_audio(request: Request, path: str, user: str = Depends(require_user)):
    return stream_audio_file(request, path)


# --------------------------------------------------------------------------
# Root Web Application
# --------------------------------------------------------------------------

@app.api_route("/favicon.ico", methods=["GET", "HEAD"], include_in_schema=False)
async def favicon():
    ico_file = STATIC_DIR / "favicon.ico"
    if ico_file.exists():
        return FileResponse(ico_file, media_type="image/x-icon")
    svg_file = STATIC_DIR / "favicon.svg"
    if svg_file.exists():
        return FileResponse(svg_file, media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/", response_class=HTMLResponse)
async def index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Index file not found")
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
