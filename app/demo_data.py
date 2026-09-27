import os
import io
import math
import struct
import wave
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TALB, TDRC, TCON, TRCK, TPOS, TCOM, COMM, APIC

from app.config import MUSIC_DIR


def generate_synthesized_wav(dest_wav: Path, duration_sec: float = 3.5, base_freq: float = 220.0, wave_type: str = "pad"):
    """Generates a genuine pleasant musical audio tone in WAV format."""
    sr = 44100
    n_samples = int(sr * duration_sec)
    dest_wav.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(dest_wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = bytearray()

        chord_offsets = [1.0, 1.25, 1.5, 1.875]  # Major 7th / harmonic structure
        if wave_type == "minor":
            chord_offsets = [1.0, 1.2, 1.5, 1.78]
        elif wave_type == "bass":
            chord_offsets = [0.5, 1.0, 1.5]

        for i in range(n_samples):
            t = i / sr
            # Smooth envelope (ADSR style fade in/out)
            attack = min(1.0, t * 3.0)
            release = min(1.0, (duration_sec - t) * 2.0)
            env = attack * release

            # Multi-oscillator synthesis with subtle chorus
            signal = 0.0
            for mult in chord_offsets:
                freq = base_freq * mult
                signal += math.sin(2 * math.pi * freq * t) * 0.25
                # Subtle detune for width
                signal += math.sin(2 * math.pi * (freq * 1.004) * t) * 0.15

            # Dynamic harmonic modulation
            lfo = 1.0 + 0.15 * math.sin(2 * math.pi * 1.5 * t)
            sample_val = int(max(-32767, min(32767, signal * env * lfo * 14000)))
            frames.extend(struct.pack("<hh", sample_val, sample_val))

        wf.writeframes(frames)


def generate_artwork(title: str, artist: str, color1: tuple, color2: tuple) -> bytes:
    """Generates a stylish modern album cover art image matching the Acoustic Slate palette."""
    w, h = 600, 600
    img = Image.new("RGB", (w, h), color=color2)
    draw = ImageDraw.Draw(img)

    # Vertical gradient
    for y in range(h):
        ratio = y / float(h)
        r = int(color2[0] * (1 - ratio) + color1[0] * ratio)
        g = int(color2[1] * (1 - ratio) + color1[1] * ratio)
        b = int(color2[2] * (1 - ratio) + color1[2] * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # Architectural geometric studio rings / grid
    cx, cy = 300, 240
    for r in range(40, 220, 30):
        alpha_color = (255, 255, 255)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=alpha_color, width=2)

    # Central audio wave glyph
    for i in range(-5, 6):
        bar_h = 30 + (6 - abs(i)) * 12
        x = cx + i * 16
        draw.line([(x, cy - bar_h // 2), (x, cy + bar_h // 2)], fill=(20, 184, 166), width=3)

    # Clean typography
    # Title
    draw.text((45, 470), title.upper(), fill=(255, 255, 255))
    # Artist
    draw.text((45, 510), artist, fill=(204, 251, 241))
    # Telemetry badge
    draw.text((45, 545), "LOSSLESS MASTER • 24-BIT / 96KHZ • STUDIO ENGINE", fill=(148, 163, 184))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def convert_wav_to_flac(src_wav: Path, dest_flac: Path) -> bool:
    """Converts WAV to FLAC using CLI tool if available, else moves as WAV."""
    if shutil.which("flac"):
        try:
            subprocess.run(["flac", "--silent", "-f", str(src_wav), "-o", str(dest_flac)], check=True)
            src_wav.unlink(missing_ok=True)
            return True
        except Exception:
            pass
    return False


def convert_wav_to_mp3(src_wav: Path, dest_mp3: Path) -> bool:
    """Converts WAV to MP3 using LAME if available."""
    if shutil.which("lame"):
        try:
            subprocess.run(["lame", "--silent", "-b", "320", str(src_wav), str(dest_mp3)], check=True)
            src_wav.unlink(missing_ok=True)
            return True
        except Exception:
            pass
    return False


def populate_demo_library(force: bool = False):
    """Populates the demo music library with sample files if empty or forced."""
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)

    # Check if files already exist
    existing = list(MUSIC_DIR.glob("**/*"))
    has_audio = any(p.suffix.lower() in (".mp3", ".flac", ".wav", ".m4a") for p in existing if p.is_file())
    if has_audio and not force:
        return

    print("Generating demo music library with realistic metadata and artwork...")

    # Folder 1: Nebula Sessions (2025)
    nebula_dir = MUSIC_DIR / "Nebula Sessions (2025)"
    nebula_dir.mkdir(parents=True, exist_ok=True)

    nebula_cover = generate_artwork(
        "Nebula Sessions Vol. 1",
        "Aethel & Kaelen",
        color1=(13, 148, 136), # Teal
        color2=(15, 23, 42)    # Dark slate
    )

    nebula_tracks = [
        ("01 - Subsurface Awakening", 220.0, "pad", "1", "Subsurface Awakening"),
        ("02 - Spectral Dispersion", 277.18, "minor", "2", "Spectral Dispersion"),
        ("03 - Monolith Frequency Sweep", 164.81, "bass", "3", "Monolith Frequency Sweep"),
        ("04 - Ethereal Resonance (Extended Mix)", 329.63, "pad", "4", "Ethereal Resonance (Extended Mix)"),
    ]

    for filename_stem, freq, wave_mode, trk_num, title in nebula_tracks:
        tmp_wav = nebula_dir / f"{filename_stem}.wav"
        dest_flac = nebula_dir / f"{filename_stem}.flac"

        generate_synthesized_wav(tmp_wav, duration_sec=4.0, base_freq=freq, wave_type=wave_mode)
        is_flac = convert_wav_to_flac(tmp_wav, dest_flac)

        target_file = dest_flac if is_flac else tmp_wav

        if is_flac:
            f = FLAC(str(target_file))
            f["title"] = [title]
            f["artist"] = ["Aethel & Kaelen" if trk_num == "4" else "Aethel"]
            f["albumartist"] = ["Aethel"]
            f["album"] = ["Nebula Sessions Vol. 1"]
            f["date"] = ["2025"]
            f["genre"] = ["Deep Minimal"]
            f["tracknumber"] = [trk_num]
            f["tracktotal"] = ["4"]
            f["discnumber"] = ["1"]
            f["disctotal"] = ["1"]
            f["composer"] = ["Aethel"]
            f["comment"] = ["Mastered at Resonance Sound Studio 2025"]

            pic = Picture()
            pic.type = 3
            pic.mime = "image/jpeg"
            pic.desc = "Front Cover"
            pic.data = nebula_cover
            f.clear_pictures()
            f.add_picture(pic)
            f.save()
        else:
            w = WAVE(str(target_file))
            if w.tags is None:
                w.add_tags()
            w.tags.add(TIT2(encoding=3, text=[title]))
            w.tags.add(TPE1(encoding=3, text=["Aethel"]))
            w.tags.add(TALB(encoding=3, text=["Nebula Sessions Vol. 1"]))
            w.tags.add(TRCK(encoding=3, text=[f"{trk_num}/4"]))
            w.tags.add(TDRC(encoding=3, text=["2025"]))
            w.tags.add(TCON(encoding=3, text=["Deep Minimal"]))
            w.tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=nebula_cover))
            w.save()

    # Folder 2: Acoustic Horizons (2024)
    acoustic_dir = MUSIC_DIR / "Acoustic Horizons (2024)"
    acoustic_dir.mkdir(parents=True, exist_ok=True)

    acoustic_cover = generate_artwork(
        "Acoustic Horizons",
        "Kaelen",
        color1=(14, 116, 144), # Cyan / blue
        color2=(30, 41, 59)
    )

    acoustic_tracks = [
        ("01 - Dawn Reverie", 293.66, "pad", "1", "Dawn Reverie"),
        ("02 - Solitude Echo", 196.00, "minor", "2", "Solitude Echo"),
    ]

    for filename_stem, freq, wave_mode, trk_num, title in acoustic_tracks:
        tmp_wav = acoustic_dir / f"{filename_stem}.wav"
        dest_mp3 = acoustic_dir / f"{filename_stem}.mp3"

        generate_synthesized_wav(tmp_wav, duration_sec=3.5, base_freq=freq, wave_type=wave_mode)
        is_mp3 = convert_wav_to_mp3(tmp_wav, dest_mp3)

        target_file = dest_mp3 if is_mp3 else tmp_wav

        if is_mp3:
            m = MP3(str(target_file), ID3=ID3)
            if m.tags is None:
                m.add_tags()
            m.tags.add(TIT2(encoding=3, text=[title]))
            m.tags.add(TPE1(encoding=3, text=["Kaelen"]))
            m.tags.add(TPE2(encoding=3, text=["Kaelen"]))
            m.tags.add(TALB(encoding=3, text=["Acoustic Horizons"]))
            m.tags.add(TDRC(encoding=3, text=["2024"]))
            m.tags.add(TCON(encoding=3, text=["Ambient"]))
            m.tags.add(TRCK(encoding=3, text=[f"{trk_num}/2"]))
            m.tags.add(TPOS(encoding=3, text=["1/1"]))
            m.tags.add(TCOM(encoding=3, text=["Kaelen"]))
            m.tags.add(COMM(encoding=3, lang="eng", desc="", text=["Recorded with acoustic analog modules"]))
            m.tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=acoustic_cover))
            m.save()
        else:
            w = WAVE(str(target_file))
            if w.tags is None:
                w.add_tags()
            w.tags.add(TIT2(encoding=3, text=[title]))
            w.tags.add(TPE1(encoding=3, text=["Kaelen"]))
            w.tags.add(TALB(encoding=3, text=["Acoustic Horizons"]))
            w.tags.add(TRCK(encoding=3, text=[f"{trk_num}/2"]))
            w.tags.add(TDRC(encoding=3, text=["2024"]))
            w.tags.add(TCON(encoding=3, text=["Ambient"]))
            w.tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=acoustic_cover))
            w.save()

    # Folder 3: Modular Vault (Single WAV track)
    vault_dir = MUSIC_DIR / "Modular Vault"
    vault_dir.mkdir(parents=True, exist_ok=True)

    vault_cover = generate_artwork(
        "Modular Vault 01",
        "Subsurface Labs",
        color1=(16, 185, 129), # Emerald
        color2=(17, 24, 39)
    )

    vault_wav = vault_dir / "01 - Dark Matter Pulse.wav"
    generate_synthesized_wav(vault_wav, duration_sec=3.0, base_freq=110.0, wave_type="bass")
    w = WAVE(str(vault_wav))
    if w.tags is None:
        w.add_tags()
    w.tags.add(TIT2(encoding=3, text=["Dark Matter Pulse"]))
    w.tags.add(TPE1(encoding=3, text=["Subsurface Labs"]))
    w.tags.add(TALB(encoding=3, text=["Modular Vault 01"]))
    w.tags.add(TRCK(encoding=3, text=["1/1"]))
    w.tags.add(TDRC(encoding=3, text=["2025"]))
    w.tags.add(TCON(encoding=3, text=["Modular Synth"]))
    w.tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Front Cover", data=vault_cover))
    w.save()

    print("Demo music library successfully generated!")


if __name__ == "__main__":
    populate_demo_library()
