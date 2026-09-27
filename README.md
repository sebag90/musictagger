# Resonance — Minimalist Music Library & Tag Manager

A container-first web application designed for audio engineers, producers, and collectors to browse, upload, manage, and tag music libraries.

Inspired by the **Acoustic Slate** minimalist workstation design system (`stitch_minimalist_music_library_manager`), combining Swiss technical typography (`Hanken Grotesk` & `JetBrains Mono`), sleek teal accents (`#0d9488`), and studio-grade audio telemetry.

---

## Features

- **Filesystem Management**:
  - Browse directory tree and file tables with live breadcrumbs navigation.
  - Upload lossless or compressed audio files via a dedicated Ingestion Processing Queue or drag-and-drop.
  - Create directories and subdirectories.
  - Rename files (with extension hints) and directories.
  - Move single or multiple files and directories with interactive folder picker dialogs.
  - Delete files or directories with confirmation warnings.
- **Deep Metadata & Tag Editor**:
  - Edit Track Title, Artist, Album Artist, Album, Year, Genre, Track Index (`track/total`), Disc Index (`disc/total`), Composer, and Notes/Comments.
  - Embedded artwork inspector & manager:
    - View cover art with format, dimension, and size telemetry.
    - Replace/embed cover artwork from PNG, JPEG, or WEBP image files.
    - Remove embedded cover artwork.
  - Batch metadata tagging across multiple selected tracks.
  - Acoustic telemetry specs: Bitrate (kbps), Sample Rate (kHz), Bit Depth, Channels, Codec, File Size.
  - Supports **FLAC, MP3, WAV, M4A/AAC, and OGG Vorbis**.
- **Studio Audio Player & Waveform Visualizer**:
  - In-browser audio streaming with HTTP 206 Partial Content (Range request) support for instantaneous scrubbing.
  - Visual waveform bar visualizer with click-to-seek and real-time playback tracking.
- **Security & Container-First Development**:
  - Secured via Apache `htpasswd` files using Bcrypt (`-B`).
  - Container-first deployment using Podman.
  - Volume-mapped host music library (`/music`) and credentials file (`/auth/.htpasswd`).
  - Dynamic user reload: updates made to `.htpasswd` take effect immediately without restarting the container.

---

## Quick Start (Deploying Locally with `just demo`)

Deploying the local demo environment takes one command:

```bash
just demo
```

This will:
1. Initialize the `.htpasswd` file with demo credentials (`admin` / `admin`) if not already present.
2. Build the Podman container image (`musictagger`).
3. Launch the container mapping the local `music_library/` folder and `.htpasswd`.
4. Automatically populate `music_library/` with sample tracks (FLAC, MP3, WAV) complete with synthesized audio, embedded cover artwork, and rich ID3 tags.
5. Provide the live URL: `http://localhost:8080`.

Open **[http://localhost:8080](http://localhost:8080)** in your browser and sign in with:
- **Username**: `admin`
- **Password**: `admin`

---

## Just Commands Reference

| Command | Description |
|---|---|
| `just demo` | Deploy local demo container with sample library and htpasswd |
| `just build` | Build the Podman container image |
| `just run` | Run the container with mounted `music_library` and `.htpasswd` |
| `just stop` | Stop and remove the running container |
| `just logs` | Follow live container logs |
| `just htpasswd-add <user> [password]` | Add or update a user in `.htpasswd` using bcrypt |

### Adding Users to `.htpasswd`

You can add users interactively:
```bash
just htpasswd-add producer
```
Or specify the password directly:
```bash
just htpasswd-add producer secretpass
```

Newly added credentials can immediately be used to log in without needing to restart the container.

---

## Configuration & Environment Variables

The justfile and container support the following configurable parameters:

- `MUSIC_DIR`: Host path to the music library (default: `music_library`).
- `HTPASSWD_FILE`: Host path to the htpasswd file (default: `.htpasswd`).
- `PORT`: Host port to bind (default: `8080`).

Example custom deployment:
```bash
PORT=9090 MUSIC_DIR=/mnt/external_drive/Music just demo
```

---

## Technical Architecture

- **Backend**: Python 3.12, FastAPI, Uvicorn, Mutagen (audio tagging), Bcrypt, Pillow (image telemetry).
- **Frontend**: Vanilla JavaScript SPA, Tailwind CSS, Google Fonts (`Hanken Grotesk`, `JetBrains Mono`), Material Symbols.
- **Audio Pipeline**: Chunked streaming response generator with HTTP 206 range headers for seekable playback.
