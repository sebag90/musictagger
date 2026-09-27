HTPASSWD_FILE := env_var_or_default("HTPASSWD_FILE", ".htpasswd")
MUSIC_DIR := env_var_or_default("MUSIC_DIR", "music_library")
PORT := env_var_or_default("PORT", "8080")
IMAGE_NAME := "musictagger"
CONTAINER_NAME := "musictagger"

# Add or update user credentials in the htpasswd file using bcrypt (prompts for password if omitted)
htpasswd-add user password="":
    @touch {{HTPASSWD_FILE}}
    @if [ -n "{{password}}" ]; then \
        podman run --rm -i -v $(pwd)/{{HTPASSWD_FILE}}:/htpasswd:z \
            docker.io/httpd:2.4-alpine htpasswd -B -b /htpasswd {{user}} "{{password}}"; \
    else \
        podman run --rm -it -v $(pwd)/{{HTPASSWD_FILE}}:/htpasswd:z \
            docker.io/httpd:2.4-alpine htpasswd -B /htpasswd {{user}}; \
    fi
    @echo "Updated {{HTPASSWD_FILE}}"

# Build the container image
build:
    podman build -t {{IMAGE_NAME}} -f Containerfile .

# Run the container with mounted music library and htpasswd
run:
    @mkdir -p {{MUSIC_DIR}}
    @touch {{HTPASSWD_FILE}}
    -podman rm -f {{CONTAINER_NAME}} 2>/dev/null || true
    podman run -d --name {{CONTAINER_NAME}} \
        -p {{PORT}}:8080 \
        -v $(pwd)/{{MUSIC_DIR}}:/music:z \
        -v $(pwd)/{{HTPASSWD_FILE}}:/auth/.htpasswd:z,ro \
        -e MUSIC_DIR=/music \
        -e HTPASSWD_PATH=/auth/.htpasswd \
        {{IMAGE_NAME}}
    @echo "Music Tagger running on http://localhost:{{PORT}}"

# Stop the running container
stop:
    -podman stop {{CONTAINER_NAME}} 2>/dev/null || true
    -podman rm {{CONTAINER_NAME}} 2>/dev/null || true
    @echo "Stopped {{CONTAINER_NAME}}"

# View live container logs
logs:
    podman logs -f {{CONTAINER_NAME}}

# Deploy local demo environment with sample tracks, htpasswd, and container run
demo:
    @echo "===> Setting up demo environment for Music Tagger..."
    @mkdir -p {{MUSIC_DIR}}
    @if [ ! -s {{HTPASSWD_FILE}} ]; then \
        echo "===> Creating demo htpasswd with user 'admin' (password: 'admin')..."; \
        touch {{HTPASSWD_FILE}}; \
        podman run --rm -i -v $(pwd)/{{HTPASSWD_FILE}}:/htpasswd:z \
            docker.io/httpd:2.4-alpine htpasswd -B -b /htpasswd admin admin; \
    else \
        echo "===> Existing {{HTPASSWD_FILE}} found."; \
    fi
    @echo "===> Building container image '{{IMAGE_NAME}}'..."
    podman build -t {{IMAGE_NAME}} -f Containerfile .
    @echo "===> Stopping any existing demo container..."
    -podman rm -f {{CONTAINER_NAME}} 2>/dev/null || true
    @echo "===> Starting Music Tagger container..."
    podman run -d --name {{CONTAINER_NAME}} \
        -p {{PORT}}:8080 \
        -v $(pwd)/{{MUSIC_DIR}}:/music:z \
        -v $(pwd)/{{HTPASSWD_FILE}}:/auth/.htpasswd:z,ro \
        -e MUSIC_DIR=/music \
        -e HTPASSWD_PATH=/auth/.htpasswd \
        {{IMAGE_NAME}}
    @sleep 2
    @echo ""
    @echo "================================================================"
    @echo "  Resonance Music Library & Tag Manager is LIVE!"
    @echo "  URL:         http://localhost:{{PORT}}"
    @echo "  Credentials: username: admin  |  password: admin"
    @echo "  Library:     $(pwd)/{{MUSIC_DIR}}"
    @echo "  Auth File:   $(pwd)/{{HTPASSWD_FILE}}"
    @echo "================================================================"
    @echo "  Useful commands:"
    @echo "    just logs            # Follow live container logs"
    @echo "    just htpasswd-add <user> # Add another user"
    @echo "    just stop            # Stop the container"
    @echo "================================================================"
