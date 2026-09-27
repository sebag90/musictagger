import os
import shutil
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status

from app.config import MUSIC_DIR, ALLOWED_AUDIO_EXTENSIONS
import mutagen


def resolve_safe_path(rel_path: str) -> Path:
    """
    Safely resolves a relative path within MUSIC_DIR.
    Prevents path traversal attacks.
    """
    clean_rel = rel_path.strip().lstrip("/").replace("\\", "/")
    # Resolve against MUSIC_DIR
    target = (MUSIC_DIR / clean_rel).resolve()

    try:
        # Python 3.9+ is_relative_to
        if not target.is_relative_to(MUSIC_DIR):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Path traversal forbidden"
            )
    except AttributeError:
        # Fallback for older python
        common = os.path.commonpath([str(target), str(MUSIC_DIR)])
        if common != str(MUSIC_DIR):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Path traversal forbidden"
            )

    return target


def to_relative_path(abs_path: Path) -> str:
    """Converts an absolute Path inside MUSIC_DIR to a clean relative path string."""
    try:
        rel = abs_path.relative_to(MUSIC_DIR)
        return str(rel).replace("\\", "/") if str(rel) != "." else ""
    except ValueError:
        return ""


def get_quick_audio_summary(file_path: Path) -> Dict[str, Any]:
    """Lightweight metadata extractor for file listing."""
    ext = file_path.suffix.lower()
    summary = {
        "title": file_path.stem,
        "artist": "",
        "album": "",
        "track_number": None,
        "duration": 0.0,
        "bitrate": 0,
        "sample_rate": 0,
        "has_cover": False,
    }

    try:
        audio = mutagen.File(str(file_path))
        if audio is not None:
            if audio.info:
                summary["duration"] = round(getattr(audio.info, "length", 0.0), 2)
                summary["bitrate"] = getattr(audio.info, "bitrate", 0)
                summary["sample_rate"] = getattr(audio.info, "sample_rate", 0)

            # Check tags
            tags = audio.tags
            if tags is not None:
                # MP3 / ID3
                if hasattr(tags, "getall"):
                    # Title
                    for key in ("TIT2", "title"):
                        if key in tags:
                            summary["title"] = str(tags[key].text[0] if hasattr(tags[key], "text") else tags[key][0])
                            break
                    # Artist
                    for key in ("TPE1", "artist"):
                        if key in tags:
                            summary["artist"] = str(tags[key].text[0] if hasattr(tags[key], "text") else tags[key][0])
                            break
                    # Album
                    for key in ("TALB", "album"):
                        if key in tags:
                            summary["album"] = str(tags[key].text[0] if hasattr(tags[key], "text") else tags[key][0])
                            break
                    # Track number
                    if "TRCK" in tags:
                        raw = str(tags["TRCK"].text[0] if hasattr(tags["TRCK"], "text") else tags["TRCK"][0])
                        summary["track_number"] = raw.split("/")[0].strip()
                    # Cover
                    summary["has_cover"] = len(tags.getall("APIC")) > 0

                # FLAC / OGG (dict-like with pictures attribute)
                elif hasattr(audio, "pictures") and audio.pictures:
                    summary["has_cover"] = True
                    summary["title"] = str(tags.get("title", [summary["title"]])[0])
                    summary["artist"] = str(tags.get("artist", [""])[0])
                    summary["album"] = str(tags.get("album", [""])[0])
                    track_no = tags.get("tracknumber", [None])[0]
                    if track_no:
                        summary["track_number"] = str(track_no).split("/")[0].strip()

                # MP4 / M4A
                elif hasattr(tags, "get"):
                    summary["title"] = str(tags.get("\xa9nam", [summary["title"]])[0])
                    summary["artist"] = str(tags.get("\xa9ART", [""])[0])
                    summary["album"] = str(tags.get("\xa9alb", [""])[0])
                    trkn = tags.get("trkn")
                    if trkn and isinstance(trkn[0], tuple):
                        summary["track_number"] = str(trkn[0][0])
                    summary["has_cover"] = "covr" in tags and len(tags["covr"]) > 0

                # Generic dict
                elif isinstance(tags, dict):
                    summary["title"] = str(tags.get("title", [summary["title"]])[0])
                    summary["artist"] = str(tags.get("artist", [""])[0])
                    summary["album"] = str(tags.get("album", [""])[0])
                    trkn = tags.get("tracknumber")
                    if trkn:
                        summary["track_number"] = str(trkn[0]).split("/")[0].strip()
    except Exception:
        pass

    return summary


def get_directory_tree(current_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Generates a hierarchical tree of all folders inside MUSIC_DIR."""
    if current_dir is None:
        current_dir = MUSIC_DIR

    MUSIC_DIR.mkdir(parents=True, exist_ok=True)

    def scan_node(dir_path: Path) -> Dict[str, Any]:
        rel = to_relative_path(dir_path)
        name = dir_path.name if rel else "Music Library"
        children: List[Dict[str, Any]] = []
        audio_count = 0

        try:
            for entry in sorted(os.scandir(dir_path), key=lambda e: e.name.lower()):
                if entry.name.startswith("."):
                    continue
                if entry.is_dir(follow_symlinks=False):
                    children.append(scan_node(Path(entry.path)))
                elif entry.is_file(follow_symlinks=False):
                    ext = Path(entry.name).suffix.lower()
                    if ext in ALLOWED_AUDIO_EXTENSIONS:
                        audio_count += 1
        except Exception:
            pass

        return {
            "name": name,
            "path": rel,
            "audio_count": audio_count,
            "children": children,
        }

    return scan_node(MUSIC_DIR)


def list_directory(rel_path: str = "") -> Dict[str, Any]:
    """Lists files and subdirectories of a given relative path."""
    target = resolve_safe_path(rel_path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Directory not found")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    rel = to_relative_path(target)

    # Breadcrumbs
    breadcrumbs = [{"name": "Music Library", "path": ""}]
    if rel:
        parts = rel.split("/")
        accum = ""
        for p in parts:
            accum = f"{accum}/{p}" if accum else p
            breadcrumbs.append({"name": p, "path": accum})

    # Parent path
    parent_path = None
    if rel:
        parent_rel = to_relative_path(target.parent)
        parent_path = parent_rel

    directories = []
    files = []

    try:
        with os.scandir(target) as it:
            for entry in sorted(it, key=lambda e: e.name.lower()):
                if entry.name.startswith("."):
                    continue

                entry_path = Path(entry.path)
                entry_rel = to_relative_path(entry_path)
                stat = entry.stat()

                if entry.is_dir(follow_symlinks=False):
                    # Count items inside
                    item_count = 0
                    try:
                        with os.scandir(entry.path) as sub:
                            item_count = sum(1 for e in sub if not e.name.startswith("."))
                    except Exception:
                        pass

                    directories.append({
                        "name": entry.name,
                        "path": entry_rel,
                        "item_count": item_count,
                        "mtime": stat.st_mtime,
                    })
                elif entry.is_file(follow_symlinks=False):
                    ext = entry_path.suffix.lower()
                    is_audio = ext in ALLOWED_AUDIO_EXTENSIONS
                    item = {
                        "name": entry.name,
                        "path": entry_rel,
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                        "extension": ext,
                        "is_audio": is_audio,
                    }
                    if is_audio:
                        meta = get_quick_audio_summary(entry_path)
                        item.update(meta)
                    files.append(item)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read directory: {e}")

    return {
        "current_path": rel,
        "parent_path": parent_path,
        "breadcrumbs": breadcrumbs,
        "directories": directories,
        "files": files,
        "total_files": len(files),
        "total_directories": len(directories),
    }


def create_directory(parent_rel: str, name: str) -> Dict[str, Any]:
    """Creates a new subdirectory under parent_rel."""
    clean_name = name.strip().replace("/", "_").replace("\\", "_")
    if not clean_name or clean_name in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid directory name")

    parent = resolve_safe_path(parent_rel)
    if not parent.exists() or not parent.is_dir():
        raise HTTPException(status_code=404, detail="Parent directory not found")

    new_dir = parent / clean_name
    if new_dir.exists():
        raise HTTPException(status_code=409, detail="Directory already exists")

    new_dir.mkdir(parents=True, exist_ok=False)
    return {
        "name": clean_name,
        "path": to_relative_path(new_dir),
        "success": True,
    }


def rename_item(rel_path: str, new_name: str) -> Dict[str, Any]:
    """Renames a file or directory."""
    clean_name = new_name.strip().replace("/", "_").replace("\\", "_")
    if not clean_name or clean_name in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid name")

    target = resolve_safe_path(rel_path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Item not found")

    if target == MUSIC_DIR:
        raise HTTPException(status_code=400, detail="Cannot rename library root")

    dest = target.parent / clean_name
    if dest.exists():
        raise HTTPException(status_code=409, detail="An item with this name already exists")

    target.rename(dest)
    return {
        "old_path": rel_path,
        "new_path": to_relative_path(dest),
        "new_name": clean_name,
        "success": True,
    }


def move_items(rel_paths: List[str], target_dir_rel: str) -> Dict[str, Any]:
    """Moves multiple files/directories into target_dir_rel."""
    dest_dir = resolve_safe_path(target_dir_rel)
    if not dest_dir.exists() or not dest_dir.is_dir():
        raise HTTPException(status_code=404, detail="Destination directory not found")

    moved = []
    errors = []

    for rel_path in rel_paths:
        try:
            src = resolve_safe_path(rel_path)
            if not src.exists():
                errors.append({"path": rel_path, "error": "Source not found"})
                continue
            if src == MUSIC_DIR:
                errors.append({"path": rel_path, "error": "Cannot move root directory"})
                continue
            if src == dest_dir or dest_dir.is_relative_to(src):
                errors.append({"path": rel_path, "error": "Cannot move folder into itself"})
                continue

            target_file = dest_dir / src.name
            if target_file.exists():
                # Append duplicate suffix if name collision
                stem, suffix = src.stem, src.suffix
                counter = 1
                while target_file.exists():
                    target_file = dest_dir / f"{stem} ({counter}){suffix}"
                    counter += 1

            shutil.move(str(src), str(target_file))
            moved.append({
                "from": rel_path,
                "to": to_relative_path(target_file),
            })
        except Exception as e:
            errors.append({"path": rel_path, "error": str(e)})

    return {
        "moved": moved,
        "errors": errors,
        "success": len(errors) == 0,
    }


def delete_items(rel_paths: List[str]) -> Dict[str, Any]:
    """Deletes multiple files or directories."""
    deleted = []
    errors = []

    for rel_path in rel_paths:
        try:
            target = resolve_safe_path(rel_path)
            if not target.exists():
                errors.append({"path": rel_path, "error": "Not found"})
                continue
            if target == MUSIC_DIR:
                errors.append({"path": rel_path, "error": "Cannot delete root directory"})
                continue

            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

            deleted.append(rel_path)
        except Exception as e:
            errors.append({"path": rel_path, "error": str(e)})

    return {
        "deleted": deleted,
        "errors": errors,
        "success": len(errors) == 0,
    }
