from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from mangedong.api.secrets import decrypt_secret


class ProviderError(RuntimeError):
    pass


def assert_safe_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ProviderError("Only http(s) provider URLs are allowed.")
    host = (parsed.hostname or "").lower()
    if host in {"169.254.169.254", "metadata.google.internal"}:
        raise ProviderError("Provider URL is not allowed.")
    return url.rstrip("/")


def http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: float = 3.0,
) -> dict[str, Any]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", **(headers or {})},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.URLError as exc:
        raise ProviderError(str(exc.reason if getattr(exc, "reason", None) else exc)) from exc
    if not raw:
        return {}
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ProviderError("Provider returned non-JSON.") from exc
    if not isinstance(parsed, dict):
        return {"data": parsed}
    return parsed


def probe_comfyui(base_url: str, token: str | None = None, auth_type: str = "none") -> dict[str, Any]:
    root = assert_safe_url(base_url)
    headers = _auth_headers(auth_type, token)
    for path in ("/system_stats", "/queue"):
        try:
            return {"ok": True, "mode": "live", "payload": http_json("GET", f"{root}{path}", headers=headers, timeout=1.5)}
        except ProviderError:
            continue
    raise ProviderError(f"ComfyUI unreachable at {root}")


def run_comfyui_prompt(
    base_url: str,
    workflow_json: dict[str, Any],
    *,
    token: str | None = None,
    auth_type: str = "none",
    timeout: float = 2.5,
) -> dict[str, Any]:
    root = assert_safe_url(base_url)
    headers = _auth_headers(auth_type, token)
    result = http_json(
        "POST",
        f"{root}/prompt",
        headers=headers,
        body={"prompt": workflow_json, "client_id": "mangedong"},
        timeout=timeout,
    )
    return {"ok": True, "mode": "live", "prompt_id": result.get("prompt_id"), "payload": result}


def chat_complete(
    base_url: str,
    api_key: str,
    *,
    model: str,
    prompt: str,
    timeout: float = 4.0,
) -> str:
    root = assert_safe_url(base_url)
    result = http_json(
        "POST",
        f"{root}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        body={"model": model or "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}], "max_tokens": 200},
        timeout=timeout,
    )
    choices = result.get("choices") or []
    if not choices:
        raise ProviderError("Provider returned no choices.")
    return str(choices[0].get("message", {}).get("content") or "").strip()


def provider_credentials(provider_data: dict[str, Any], secret_key: str) -> tuple[str, str, str]:
    config = provider_data.get("config") or {}
    base_url = str(config.get("base_url") or "")
    api_key = decrypt_secret(str(config.get("api_key") or ""), secret_key)
    model = str(config.get("model") or "gpt-4o-mini")
    return base_url, api_key, model


def comfyui_credentials(instance_data: dict[str, Any], secret_key: str) -> tuple[str, str, str]:
    base_url = str(instance_data.get("base_url") or "")
    token = decrypt_secret(str(instance_data.get("token") or ""), secret_key)
    auth_type = str(instance_data.get("auth_type") or "none")
    return base_url, token, auth_type


def _auth_headers(auth_type: str, token: str | None) -> dict[str, str]:
    if not token or auth_type == "none":
        return {}
    if auth_type == "bearer":
        return {"Authorization": f"Bearer {token}"}
    if auth_type == "custom_header":
        return {"X-API-Key": token}
    return {}


def copy_if_exists(path: str | Path) -> Path | None:
    candidate = Path(path)
    return candidate if candidate.exists() else None
