from __future__ import annotations

import base64
import hashlib
import hmac
import os


def encrypt_secret(value: str, secret_key: str) -> str:
    if not value:
        return ""
    if value.startswith("enc:"):
        return value
    key = hashlib.sha256(secret_key.encode("utf-8")).digest()
    raw = value.encode("utf-8")
    mixed = bytes(byte ^ key[index % len(key)] for index, byte in enumerate(raw))
    digest = hmac.new(key, mixed, hashlib.sha256).digest()
    return "enc:" + base64.urlsafe_b64encode(digest + mixed).decode("ascii")


def decrypt_secret(value: str, secret_key: str) -> str:
    if not value:
        return ""
    if not value.startswith("enc:"):
        return value
    key = hashlib.sha256(secret_key.encode("utf-8")).digest()
    packed = base64.urlsafe_b64decode(value[4:] + "=" * (-len(value[4:]) % 4))
    digest, mixed = packed[:32], packed[32:]
    expected = hmac.new(key, mixed, hashlib.sha256).digest()
    if not hmac.compare_digest(digest, expected):
        raise ValueError("Secret integrity check failed.")
    return bytes(byte ^ key[index % len(key)] for index, byte in enumerate(mixed)).decode("utf-8")


def mask_secret(value: str | None) -> str:
    if not value:
        return ""
    return "********"


def random_password() -> str:
    return "tmp-" + base64.urlsafe_b64encode(os.urandom(12)).decode("ascii").rstrip("=")
