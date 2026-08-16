from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass


DEFAULT_TOKEN_TTL_SECONDS = 60 * 60 * 24
PASSWORD_ITERATIONS = 260_000


@dataclass(frozen=True)
class TokenPayload:
    user_id: int
    expires_at: int


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return "pbkdf2_sha256${iterations}${salt}${digest}".format(
        iterations=PASSWORD_ITERATIONS,
        salt=_b64(salt),
        digest=_b64(digest),
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, iterations, salt, digest = password_hash.split("$", 3)
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        _b64decode(salt),
        int(iterations),
    )
    return hmac.compare_digest(_b64(candidate), digest)


def create_access_token(user_id: int, secret_key: str, ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS) -> str:
    payload = {"sub": user_id, "exp": int(time.time()) + ttl_seconds}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _sign(body, secret_key)
    return f"{body}.{signature}"


def parse_access_token(token: str, secret_key: str) -> TokenPayload | None:
    try:
        body, signature = token.split(".", 1)
    except ValueError:
        return None
    if not hmac.compare_digest(_sign(body, secret_key), signature):
        return None
    try:
        payload = json.loads(_b64decode(body))
    except (ValueError, TypeError):
        return None
    expires_at = int(payload.get("exp", 0))
    if expires_at < int(time.time()):
        return None
    return TokenPayload(user_id=int(payload["sub"]), expires_at=expires_at)


def _sign(body: str, secret_key: str) -> str:
    digest = hmac.new(secret_key.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()
    return _b64(digest)


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
