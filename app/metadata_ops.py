import io
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from PIL import Image
from fastapi import HTTPException

import mutagen
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
from mutagen.id3 import (
    ID3, TIT2, TPE1, TPE2, TALB, TDRC, TCON, TRCK, TPOS, TCOM, COMM, APIC, ID3NoHeaderError
)

from app.fs_ops import resolve_safe_path, to_relative_path


def format_duration(seconds: float) -> str:
    """Formats seconds into MM:SS or HH:MM:SS."""
    if seconds <= 0:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_size(bytes_num: int) -> str:
    """Formats bytes into human readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if abs(bytes_num) < 1024.0:
            return f"{bytes_num:3.1f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f} TB"


def sniff_image_mime(raw_bytes: bytes) -> str:
    """Detects MIME type from image bytes header or Pillow."""
    if not raw_bytes:
        return "image/jpeg"
    if raw_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if raw_bytes.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if raw_bytes.startswith(b"RIFF") and b"WEBP" in raw_bytes[:16]:
        return "image/webp"
    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            return Image.MIME.get(img.format, "image/jpeg")
    except Exception:
        return "image/jpeg"


def get_image_info(img_bytes: bytes) -> Dict[str, Any]:
    """Inspects image dimensions, format and mime type using Pillow."""
    try:
        with Image.open(io.BytesIO(img_bytes)) as img:
            mime = Image.MIME.get(img.format, sniff_image_mime(img_bytes))
            return {
                "width": img.width,
                "height": img.height,
                "format": img.format or "JPEG",
                "mime": mime,
                "size_bytes": len(img_bytes),
                "size_str": format_size(len(img_bytes)),
            }
    except Exception:
        return {
            "width": 0,
            "height": 0,
            "format": "UNKNOWN",
            "mime": sniff_image_mime(img_bytes),
            "size_bytes": len(img_bytes),
            "size_str": format_size(len(img_bytes)),
        }


def get_audio_metadata(rel_path: str) -> Dict[str, Any]:
    """Reads comprehensive metadata and acoustic specs from an audio file."""
    file_path = resolve_safe_path(rel_path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found")

    ext = file_path.suffix.lower()
    stat = file_path.stat()

    result = {
        "path": rel_path,
        "filename": file_path.name,
        "extension": ext,
        "file_size": stat.st_size,
        "file_size_str": format_size(stat.st_size),
        # Core metadata
        "title": file_path.stem,
        "artist": "",
        "album_artist": "",
        "album": "",
        "year": "",
        "genre": "",
        "track_number": "",
        "track_total": "",
        "disc_number": "",
        "disc_total": "",
        "composer": "",
        "comment": "",
        # Acoustic specs
        "duration": 0.0,
        "duration_str": "00:00",
        "bitrate": 0,
        "sample_rate": 0,
        "channels": 2,
        "channel_mode": "Stereo (2.0)",
        "bit_depth": None,
        "codec": ext.upper().lstrip("."),
        # Artwork
        "has_cover": False,
        "artwork_info": None,
    }

    try:
        audio = mutagen.File(str(file_path))
        if audio is None:
            return result

        # Acoustic specs
        if audio.info:
            length = getattr(audio.info, "length", 0.0)
            result["duration"] = round(length, 2)
            result["duration_str"] = format_duration(length)
            result["bitrate"] = getattr(audio.info, "bitrate", 0)
            result["sample_rate"] = getattr(audio.info, "sample_rate", 0)
            channels = getattr(audio.info, "channels", 2)
            result["channels"] = channels
            if channels == 1:
                result["channel_mode"] = "Mono (1.0)"
            elif channels == 2:
                result["channel_mode"] = "Stereo (2.0)"
            else:
                result["channel_mode"] = f"Surround ({channels} ch)"

            # Bit depth
            bits = getattr(audio.info, "bits_per_sample", None)
            if bits:
                result["bit_depth"] = bits

        # Codec designation
        if ext == ".flac":
            result["codec"] = "FLAC (Free Lossless Audio)"
            if not result["bit_depth"]:
                result["bit_depth"] = getattr(audio.info, "bits_per_sample", 16)
        elif ext == ".mp3":
            result["codec"] = "MP3 (MPEG-1 Audio Layer III)"
            result["bit_depth"] = 16
        elif ext in (".wav", ".aif", ".aiff"):
            result["codec"] = "WAV (Linear PCM)"
            result["bit_depth"] = getattr(audio.info, "bits_per_sample", 16)
        elif ext in (".m4a", ".mp4", ".aac"):
            result["codec"] = "M4A / AAC"
            result["bit_depth"] = 16
        elif ext in (".ogg", ".opus"):
            result["codec"] = "OGG / Vorbis"

        # Check artwork & read tags according to format
        tags = audio.tags

        # 1. FLAC
        if isinstance(audio, FLAC):
            if audio.pictures:
                result["has_cover"] = True
                result["artwork_info"] = get_image_info(audio.pictures[0].data)
            if tags:
                result["title"] = tags.get("title", [result["title"]])[0]
                result["artist"] = tags.get("artist", [""])[0]
                result["album_artist"] = tags.get("albumartist", [""])[0]
                result["album"] = tags.get("album", [""])[0]
                result["year"] = tags.get("date", [""])[0]
                result["genre"] = tags.get("genre", [""])[0]
                trkn = tags.get("tracknumber", [""])[0]
                if trkn:
                    parts = str(trkn).split("/")
                    result["track_number"] = parts[0].strip()
                    if len(parts) > 1:
                        result["track_total"] = parts[1].strip()
                if "tracktotal" in tags:
                    result["track_total"] = tags.get("tracktotal", [""])[0]
                disc = tags.get("discnumber", [""])[0]
                if disc:
                    parts = str(disc).split("/")
                    result["disc_number"] = parts[0].strip()
                    if len(parts) > 1:
                        result["disc_total"] = parts[1].strip()
                if "disctotal" in tags:
                    result["disc_total"] = tags.get("disctotal", [""])[0]
                result["composer"] = tags.get("composer", [""])[0]
                result["comment"] = tags.get("comment", [""])[0]

        # 2. MP3 or WAV with ID3
        elif isinstance(audio, (MP3, WAVE)) or (tags and hasattr(tags, "getall")):
            if tags:
                # Cover art
                apics = tags.getall("APIC")
                if apics:
                    result["has_cover"] = True
                    result["artwork_info"] = get_image_info(apics[0].data)

                # Tags
                def get_id3(key: str) -> str:
                    frame = tags.get(key)
                    if frame and hasattr(frame, "text") and frame.text:
                        return str(frame.text[0])
                    return ""

                t = get_id3("TIT2")
                if t:
                    result["title"] = t
                result["artist"] = get_id3("TPE1")
                result["album_artist"] = get_id3("TPE2")
                result["album"] = get_id3("TALB")
                result["year"] = get_id3("TDRC")
                result["genre"] = get_id3("TCON")
                result["composer"] = get_id3("TCOM")

                trck = get_id3("TRCK")
                if trck:
                    parts = trck.split("/")
                    result["track_number"] = parts[0].strip()
                    if len(parts) > 1:
                        result["track_total"] = parts[1].strip()

                tpos = get_id3("TPOS")
                if tpos:
                    parts = tpos.split("/")
                    result["disc_number"] = parts[0].strip()
                    if len(parts) > 1:
                        result["disc_total"] = parts[1].strip()

                comms = tags.getall("COMM")
                if comms and hasattr(comms[0], "text") and comms[0].text:
                    result["comment"] = str(comms[0].text[0])

        # 3. MP4 / M4A
        elif isinstance(audio, MP4):
            if tags:
                if "covr" in tags and tags["covr"]:
                    result["has_cover"] = True
                    result["artwork_info"] = get_image_info(bytes(tags["covr"][0]))

                result["title"] = tags.get("\xa9nam", [result["title"]])[0]
                result["artist"] = tags.get("\xa9ART", [""])[0]
                result["album_artist"] = tags.get("aART", [""])[0]
                result["album"] = tags.get("\xa9alb", [""])[0]
                result["year"] = tags.get("\xa9day", [""])[0]
                result["genre"] = tags.get("\xa9gen", [""])[0]
                result["composer"] = tags.get("\xa9wrt", [""])[0]
                result["comment"] = tags.get("\xa9cmt", [""])[0]

                trkn = tags.get("trkn")
                if trkn and isinstance(trkn[0], tuple):
                    result["track_number"] = str(trkn[0][0]) if trkn[0][0] else ""
                    result["track_total"] = str(trkn[0][1]) if len(trkn[0]) > 1 and trkn[0][1] else ""

                disk = tags.get("disk")
                if disk and isinstance(disk[0], tuple):
                    result["disc_number"] = str(disk[0][0]) if disk[0][0] else ""
                    result["disc_total"] = str(disk[0][1]) if len(disk[0]) > 1 and disk[0][1] else ""

        # 4. OGG Vorbis
        elif isinstance(audio, (OggVorbis, OggOpus)):
            if tags:
                result["title"] = tags.get("title", [result["title"]])[0]
                result["artist"] = tags.get("artist", [""])[0]
                result["album_artist"] = tags.get("albumartist", [""])[0]
                result["album"] = tags.get("album", [""])[0]
                result["year"] = tags.get("date", [""])[0]
                result["genre"] = tags.get("genre", [""])[0]
                trkn = tags.get("tracknumber", [""])[0]
                if trkn:
                    result["track_number"] = str(trkn)
                result["composer"] = tags.get("composer", [""])[0]
                result["comment"] = tags.get("comment", [""])[0]
                # Check for metadata_block_picture
                if "metadata_block_picture" in tags:
                    result["has_cover"] = True

    except Exception as e:
        # Fall back to base result if mutagen failed
        pass

    # If no embedded artwork found, check if a folder cover image exists (e.g. cover.jpg)
    if not result["has_cover"]:
        folder = file_path.parent
        for cand in ("cover.jpg", "cover.png", "cover.jpeg", "folder.jpg", "folder.png", "folder.jpeg", "front.jpg", "front.png"):
            cand_path = folder / cand
            if cand_path.exists() and cand_path.is_file():
                try:
                    cdata = cand_path.read_bytes()
                    result["has_cover"] = True
                    result["is_folder_cover"] = True
                    result["artwork_info"] = get_image_info(cdata)
                    break
                except Exception:
                    pass

    return result


def update_audio_metadata(rel_path: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Writes updated tags to an audio file."""
    file_path = resolve_safe_path(rel_path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found")

    ext = file_path.suffix.lower()

    title = str(data.get("title", "")).strip()
    artist = str(data.get("artist", "")).strip()
    album_artist = str(data.get("album_artist", "")).strip()
    album = str(data.get("album", "")).strip()
    year = str(data.get("year", "")).strip()
    genre = str(data.get("genre", "")).strip()
    track_number = str(data.get("track_number", "")).strip()
    track_total = str(data.get("track_total", "")).strip()
    disc_number = str(data.get("disc_number", "")).strip()
    disc_total = str(data.get("disc_total", "")).strip()
    composer = str(data.get("composer", "")).strip()
    comment = str(data.get("comment", "")).strip()

    try:
        # 1. FLAC
        if ext == ".flac":
            audio = FLAC(str(file_path))
            if title: audio["title"] = [title]
            if artist: audio["artist"] = [artist]
            if album_artist: audio["albumartist"] = [album_artist]
            if album: audio["album"] = [album]
            if year: audio["date"] = [year]
            if genre: audio["genre"] = [genre]
            if track_number: audio["tracknumber"] = [track_number]
            if track_total: audio["tracktotal"] = [track_total]
            if disc_number: audio["discnumber"] = [disc_number]
            if disc_total: audio["disctotal"] = [disc_total]
            if composer: audio["composer"] = [composer]
            if comment: audio["comment"] = [comment]
            audio.save()

        # 2. MP3
        elif ext == ".mp3":
            try:
                audio = MP3(str(file_path), ID3=ID3)
            except Exception:
                audio = MP3(str(file_path))
            if audio.tags is None:
                audio.add_tags()

            if title: audio.tags.setall("TIT2", [TIT2(encoding=3, text=[title])])
            if artist: audio.tags.setall("TPE1", [TPE1(encoding=3, text=[artist])])
            if album_artist: audio.tags.setall("TPE2", [TPE2(encoding=3, text=[album_artist])])
            if album: audio.tags.setall("TALB", [TALB(encoding=3, text=[album])])
            if year: audio.tags.setall("TDRC", [TDRC(encoding=3, text=[year])])
            if genre: audio.tags.setall("TCON", [TCON(encoding=3, text=[genre])])
            if composer: audio.tags.setall("TCOM", [TCOM(encoding=3, text=[composer])])
            if comment: audio.tags.setall("COMM", [COMM(encoding=3, lang="eng", desc="", text=[comment])])

            if track_number or track_total:
                trck_val = f"{track_number}/{track_total}" if track_total else track_number
                audio.tags.setall("TRCK", [TRCK(encoding=3, text=[trck_val])])

            if disc_number or disc_total:
                tpos_val = f"{disc_number}/{disc_total}" if disc_total else disc_number
                audio.tags.setall("TPOS", [TPOS(encoding=3, text=[tpos_val])])

            audio.save()

        # 3. WAV
        elif ext in (".wav", ".wave"):
            audio = WAVE(str(file_path))
            if audio.tags is None:
                audio.add_tags()

            if title: audio.tags.setall("TIT2", [TIT2(encoding=3, text=[title])])
            if artist: audio.tags.setall("TPE1", [TPE1(encoding=3, text=[artist])])
            if album_artist: audio.tags.setall("TPE2", [TPE2(encoding=3, text=[album_artist])])
            if album: audio.tags.setall("TALB", [TALB(encoding=3, text=[album])])
            if year: audio.tags.setall("TDRC", [TDRC(encoding=3, text=[year])])
            if genre: audio.tags.setall("TCON", [TCON(encoding=3, text=[genre])])
            if composer: audio.tags.setall("TCOM", [TCOM(encoding=3, text=[composer])])
            if comment: audio.tags.setall("COMM", [COMM(encoding=3, lang="eng", desc="", text=[comment])])

            if track_number or track_total:
                trck_val = f"{track_number}/{track_total}" if track_total else track_number
                audio.tags.setall("TRCK", [TRCK(encoding=3, text=[trck_val])])

            if disc_number or disc_total:
                tpos_val = f"{disc_number}/{disc_total}" if disc_total else disc_number
                audio.tags.setall("TPOS", [TPOS(encoding=3, text=[tpos_val])])

            audio.save()

        # 4. MP4 / M4A
        elif ext in (".m4a", ".mp4", ".aac"):
            audio = MP4(str(file_path))
            if title: audio["\xa9nam"] = [title]
            if artist: audio["\xa9ART"] = [artist]
            if album_artist: audio["aART"] = [album_artist]
            if album: audio["\xa9alb"] = [album]
            if year: audio["\xa9day"] = [year]
            if genre: audio["\xa9gen"] = [genre]
            if composer: audio["\xa9wrt"] = [composer]
            if comment: audio["\xa9cmt"] = [comment]

            trkn_num = int(track_number) if track_number.isdigit() else 0
            trkn_tot = int(track_total) if track_total.isdigit() else 0
            if trkn_num or trkn_tot:
                audio["trkn"] = [(trkn_num, trkn_tot)]

            disc_num = int(disc_number) if disc_number.isdigit() else 0
            disc_tot = int(disc_total) if disc_total.isdigit() else 0
            if disc_num or disc_tot:
                audio["disk"] = [(disc_num, disc_tot)]

            audio.save()

        # 5. OGG Vorbis
        elif ext in (".ogg", ".opus"):
            audio = mutagen.File(str(file_path))
            if title: audio["title"] = [title]
            if artist: audio["artist"] = [artist]
            if album_artist: audio["albumartist"] = [album_artist]
            if album: audio["album"] = [album]
            if year: audio["date"] = [year]
            if genre: audio["genre"] = [genre]
            if track_number: audio["tracknumber"] = [track_number]
            if track_total: audio["tracktotal"] = [track_total]
            if composer: audio["composer"] = [composer]
            if comment: audio["comment"] = [comment]
            audio.save()

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {ext}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update metadata: {e}")

    # Return refreshed metadata
    return get_audio_metadata(rel_path)


def get_artwork_bytes(rel_path: str) -> Tuple[bytes, str]:
    """Retrieves embedded artwork raw bytes and MIME type, with folder cover fallback."""
    file_path = resolve_safe_path(rel_path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    ext = file_path.suffix.lower()

    # Direct image file request
    if ext in (".jpg", ".jpeg", ".png", ".webp"):
        raw = file_path.read_bytes()
        return raw, sniff_image_mime(raw)

    try:
        audio = mutagen.File(str(file_path))
    except Exception:
        audio = None

    if audio:
        # 1. MP4 / M4A
        if isinstance(audio, MP4) and audio.tags and "covr" in audio.tags:
            covr_list = audio.tags.get("covr", [])
            if covr_list:
                raw = bytes(covr_list[0])
                c_fmt = getattr(covr_list[0], "imageformat", None)
                mime = "image/png" if c_fmt == MP4Cover.FORMAT_PNG else sniff_image_mime(raw)
                return raw, mime

        # 2. FLAC
        elif isinstance(audio, FLAC) and audio.pictures:
            pic = audio.pictures[0]
            return pic.data, pic.mime or sniff_image_mime(pic.data)

        # 3. MP3 / WAV (ID3)
        elif hasattr(audio, "tags") and audio.tags and hasattr(audio.tags, "getall"):
            apics = audio.tags.getall("APIC")
            if apics:
                return apics[0].data, apics[0].mime or sniff_image_mime(apics[0].data)

        # 4. Ogg Vorbis / Opus
        elif isinstance(audio, (OggVorbis, OggOpus)) and audio.tags:
            import base64
            from mutagen.flac import Picture
            for block in audio.tags.get("metadata_block_picture", []):
                try:
                    pic = Picture(base64.b64decode(block))
                    return pic.data, pic.mime or sniff_image_mime(pic.data)
                except Exception:
                    pass

    # 5. Fallback: Folder Cover Image (cover.jpg, folder.jpg, etc.)
    folder = file_path.parent
    for cand in ("cover.jpg", "cover.png", "cover.jpeg", "folder.jpg", "folder.png", "folder.jpeg", "front.jpg", "front.png"):
        cand_path = folder / cand
        if cand_path.exists() and cand_path.is_file():
            raw = cand_path.read_bytes()
            return raw, sniff_image_mime(raw)

    raise HTTPException(status_code=404, detail="No embedded artwork found")


def set_artwork_bytes(rel_path: str, img_bytes: bytes, mime_type: str) -> Dict[str, Any]:
    """Embeds new artwork into the audio file."""
    file_path = resolve_safe_path(rel_path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found")

    ext = file_path.suffix.lower()

    # Normalize mime
    if not mime_type or mime_type == "application/octet-stream":
        # Sniff image format
        try:
            with Image.open(io.BytesIO(img_bytes)) as img:
                mime_type = Image.MIME.get(img.format, "image/jpeg")
        except Exception:
            mime_type = "image/jpeg"

    try:
        # FLAC
        if ext == ".flac":
            audio = FLAC(str(file_path))
            pic = Picture()
            pic.type = 3  # Front cover
            pic.mime = mime_type
            pic.desc = "Front Cover"
            pic.data = img_bytes
            audio.clear_pictures()
            audio.add_picture(pic)
            audio.save()

        # MP3
        elif ext == ".mp3":
            try:
                audio = MP3(str(file_path), ID3=ID3)
            except Exception:
                audio = MP3(str(file_path))
            if audio.tags is None:
                audio.add_tags()
            audio.tags.delall("APIC")
            audio.tags.add(APIC(
                encoding=3,
                mime=mime_type,
                type=3,
                desc="Front Cover",
                data=img_bytes,
            ))
            audio.save()

        # WAV
        elif ext in (".wav", ".wave"):
            audio = WAVE(str(file_path))
            if audio.tags is None:
                audio.add_tags()
            audio.tags.delall("APIC")
            audio.tags.add(APIC(
                encoding=3,
                mime=mime_type,
                type=3,
                desc="Front Cover",
                data=img_bytes,
            ))
            audio.save()

        # MP4 / M4A
        elif ext in (".m4a", ".mp4", ".aac"):
            audio = MP4(str(file_path))
            covr_fmt = MP4Cover.FORMAT_PNG if "png" in mime_type.lower() else MP4Cover.FORMAT_JPEG
            audio["covr"] = [MP4Cover(img_bytes, imageformat=covr_fmt)]
            audio.save()

        else:
            raise HTTPException(status_code=400, detail=f"Artwork embedding not supported for {ext}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save artwork: {e}")

    return {
        "success": True,
        "artwork_info": get_image_info(img_bytes),
    }


def remove_artwork(rel_path: str) -> Dict[str, Any]:
    """Removes embedded artwork from the audio file."""
    file_path = resolve_safe_path(rel_path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found")

    ext = file_path.suffix.lower()
    try:
        if ext == ".flac":
            audio = FLAC(str(file_path))
            audio.clear_pictures()
            audio.save()
        elif ext in (".mp3", ".wav", ".wave"):
            audio = mutagen.File(str(file_path))
            if audio and hasattr(audio, "tags") and audio.tags:
                audio.tags.delall("APIC")
                audio.save()
        elif ext in (".m4a", ".mp4", ".aac"):
            audio = MP4(str(file_path))
            if "covr" in audio:
                del audio["covr"]
                audio.save()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove artwork: {e}")

    return {"success": True}
