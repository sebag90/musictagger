import os
import time
import json
import base64
import hmac
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict

import bcrypt
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

from app.config import HTPASSWD_PATH, SECRET_KEY, SESSION_COOKIE_NAME, SESSION_TTL_HOURS

logger = logging.getLogger(__name__)

# Cache for htpasswd file
_cached_mtime: Optional[float] = None
_cached_users: Dict[str, str] = {}


def _load_htpasswd() -> Dict[str, str]:
    global _cached_mtime, _cached_users
    if not HTPASSWD_PATH.exists():
        logger.warning(f"htpasswd file does not exist at {HTPASSWD_PATH}")
        return {}

    try:
        current_mtime = HTPASSWD_PATH.stat().st_mtime
        if _cached_mtime == current_mtime:
            return _cached_users

        users: Dict[str, str] = {}
        with open(HTPASSWD_PATH, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    username, hash_val = line.split(":", 1)
                    users[username.strip()] = hash_val.strip()

        _cached_mtime = current_mtime
        _cached_users = users
        logger.info(f"Loaded {len(users)} user(s) from {HTPASSWD_PATH}")
        return users
    except Exception as e:
        logger.error(f"Error reading htpasswd file: {e}")
        return _cached_users


def _verify_password(password: str, hashed: str) -> bool:
    try:
        # Bcrypt ($2y$, $2b$, $2a$)
        if hashed.startswith(("$2y$", "$2b$", "$2a$")):
            # Convert $2y$ to $2b$ for python-bcrypt compatibility
            compat_hash = hashed.replace("$2y$", "$2b$", 1).encode("ascii")
            pw_bytes = password.encode("utf-8")[:72]
            return bcrypt.checkpw(pw_bytes, compat_hash)

        # SHA-1 ({SHA})
        if hashed.startswith("{SHA}"):
            expected = "{SHA}" + base64.b64encode(hashlib.sha1(password.encode("utf-8")).digest()).decode("ascii")
            return hmac.compare_digest(hashed, expected)

        # Apache MD5 ($apr1$)
        if hashed.startswith("$apr1$"):
            # Simple fallback check
            import passlib.hash
            return passlib.hash.apr_md5_crypt.verify(password, hashed)

        # Plaintext (unhashed fallback)
        return hmac.compare_digest(password, hashed)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def authenticate_user(username: str, password: str) -> bool:
    users = _load_htpasswd()
    if not users:
        return False
    hashed = users.get(username)
    if not hashed:
        return False
    return _verify_password(password, hashed)


def create_session_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": int(time.time()) + (SESSION_TTL_HOURS * 3600),
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    sig = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_session_token(token: str) -> Optional[str]:
    try:
        if "." not in token:
            return None
        payload_b64, sig = token.split(".", 1)
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode("ascii")).decode("utf-8"))
        if payload.get("exp", 0) < time.time():
            return None
        return payload.get("sub")
    except Exception:
        return None


def get_authenticated_user(request: Request) -> Optional[str]:
    # 1. Check HTTP Basic Auth Header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Basic "):
        try:
            b64_creds = auth_header[6:].strip()
            decoded = base64.b64decode(b64_creds).decode("utf-8")
            if ":" in decoded:
                user, pwd = decoded.split(":", 1)
                if authenticate_user(user, pwd):
                    return user
        except Exception:
            pass

    # 2. Check Session Cookie
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_token:
        username = verify_session_token(cookie_token)
        if username:
            # Ensure the user still exists in htpasswd
            users = _load_htpasswd()
            if username in users:
                return username

    return None


def require_user(request: Request) -> str:
    user = get_authenticated_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": 'Basic realm="Resonance Studio"'}
        )
    return user
