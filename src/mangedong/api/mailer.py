from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Any

from mangedong.api.secrets import decrypt_secret


class MailError(RuntimeError):
    pass


def smtp_from_env() -> dict[str, Any]:
    host = os.getenv("MANGEDONG_SMTP_HOST", "")
    if not host:
        return {}
    return {
        "host": host,
        "port": int(os.getenv("MANGEDONG_SMTP_PORT", "587")),
        "username": os.getenv("MANGEDONG_SMTP_USER", ""),
        "password": os.getenv("MANGEDONG_SMTP_PASSWORD", ""),
        "from_address": os.getenv("MANGEDONG_SMTP_FROM", os.getenv("MANGEDONG_SMTP_USER", "noreply@localhost")),
        "use_tls": os.getenv("MANGEDONG_SMTP_TLS", "1").lower() not in {"0", "false", "off"},
        "use_ssl": os.getenv("MANGEDONG_SMTP_SSL", "0").lower() in {"1", "true", "on"},
        "public_base_url": os.getenv("MANGEDONG_PUBLIC_URL", "http://127.0.0.1:8000"),
        "source": "env",
    }


def decode_smtp_config(data: dict[str, Any], secret_key: str) -> dict[str, Any]:
    config = dict(data)
    if config.get("password"):
        config["password"] = decrypt_secret(str(config["password"]), secret_key)
    config.setdefault("port", 587)
    config.setdefault("use_tls", True)
    config.setdefault("use_ssl", False)
    config.setdefault("public_base_url", os.getenv("MANGEDONG_PUBLIC_URL", "http://127.0.0.1:8000"))
    config["source"] = "team"
    return config


def resolve_smtp(team_data: dict[str, Any] | None, secret_key: str) -> dict[str, Any]:
    if team_data and team_data.get("host"):
        return decode_smtp_config(team_data, secret_key)
    return smtp_from_env()


def send_mail(
    config: dict[str, Any],
    *,
    to_address: str,
    subject: str,
    body: str,
    timeout: float = 4.0,
) -> dict[str, Any]:
    if not config.get("host"):
        return {"ok": False, "mode": "local_fallback", "error": "SMTP is not configured."}
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = str(config.get("from_address") or config.get("username") or "noreply@localhost")
    message["To"] = to_address
    message.set_content(body)
    try:
        _deliver(config, message, timeout=timeout)
    except Exception as exc:
        return {"ok": False, "mode": "local_fallback", "error": str(exc)}
    return {"ok": True, "mode": "live"}


def probe_smtp(config: dict[str, Any], timeout: float = 3.0) -> dict[str, Any]:
    if not config.get("host"):
        return {"ok": False, "mode": "unconfigured", "error": "SMTP host is empty."}
    try:
        client = _connect(config, timeout=timeout)
        client.noop()
        client.quit()
    except Exception as exc:
        return {"ok": False, "mode": "fallback", "error": str(exc)}
    return {"ok": True, "mode": "live", "host": config["host"], "port": int(config.get("port") or 587)}


def _deliver(config: dict[str, Any], message: EmailMessage, timeout: float) -> None:
    client = _connect(config, timeout=timeout)
    try:
        username = str(config.get("username") or "")
        password = str(config.get("password") or "")
        if username:
            client.login(username, password)
        client.send_message(message)
    finally:
        try:
            client.quit()
        except Exception:
            client.close()


def _connect(config: dict[str, Any], timeout: float):
    host = str(config["host"])
    port = int(config.get("port") or 587)
    if config.get("use_ssl"):
        return smtplib.SMTP_SSL(host, port, timeout=timeout)
    client = smtplib.SMTP(host, port, timeout=timeout)
    client.ehlo()
    if config.get("use_tls", True):
        client.starttls()
        client.ehlo()
    return client
