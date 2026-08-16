from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from mangedong.api.secrets import decrypt_secret
from mangedong.api.services import project_storage, safe_filename


MEMORY_OBJECTS: dict[str, bytes] = {}


@dataclass(frozen=True)
class StoredObject:
    uri: str
    backend: str
    key: str
    local_path: str | None = None


def s3_from_env() -> dict[str, Any]:
    bucket = os.getenv("MANGEDONG_S3_BUCKET", "")
    if not bucket:
        return {}
    return {
        "backend": "s3",
        "endpoint": os.getenv("MANGEDONG_S3_ENDPOINT", ""),
        "bucket": bucket,
        "region": os.getenv("MANGEDONG_S3_REGION", "us-east-1"),
        "access_key": os.getenv("MANGEDONG_S3_ACCESS_KEY", ""),
        "secret_key": os.getenv("MANGEDONG_S3_SECRET_KEY", ""),
        "prefix": os.getenv("MANGEDONG_S3_PREFIX", ""),
        "use_path_style": os.getenv("MANGEDONG_S3_PATH_STYLE", "1").lower() not in {"0", "false", "off"},
        "source": "env",
    }


def decode_storage_config(data: dict[str, Any], secret_key: str) -> dict[str, Any]:
    config = dict(data)
    if config.get("secret_key"):
        config["secret_key"] = decrypt_secret(str(config["secret_key"]), secret_key)
    config.setdefault("backend", "s3" if config.get("bucket") else "local")
    config.setdefault("region", "us-east-1")
    config.setdefault("prefix", "")
    config.setdefault("use_path_style", True)
    config["source"] = "team"
    return config


def resolve_storage(team_data: dict[str, Any] | None, secret_key: str) -> dict[str, Any]:
    if team_data and team_data.get("backend", "s3") != "local" and (team_data.get("bucket") or team_data.get("backend") == "memory"):
        return decode_storage_config(team_data, secret_key)
    env = s3_from_env()
    if env:
        return env
    return {"backend": "local", "source": "local"}


def object_key(team_id: int, project_id: int, rel_path: str, prefix: str = "") -> str:
    cleaned = "/".join(safe_filename(part) for part in Path(rel_path).parts)
    base = f"teams/{team_id}/projects/{project_id}/{cleaned}"
    prefix = str(prefix or "").strip("/")
    return f"{prefix}/{base}" if prefix else base


def put_bytes(
    config: dict[str, Any],
    *,
    team_id: int,
    project_id: int,
    rel_path: str,
    payload: bytes,
    local_root: Path | None = None,
) -> StoredObject:
    key = object_key(team_id, project_id, rel_path, str(config.get("prefix") or ""))
    local_path = None
    if local_root is not None:
        path = project_storage(local_root, project_id, *Path(rel_path).parts)
        path.write_bytes(payload)
        local_path = str(path)
    backend = str(config.get("backend") or "local")
    if backend == "memory":
        uri = f"memory://{key}"
        MEMORY_OBJECTS[uri] = payload
        return StoredObject(uri=uri, backend="memory", key=key, local_path=local_path)
    if backend == "s3":
        uri = put_s3_object(config, key, payload)
        return StoredObject(uri=uri, backend="s3", key=key, local_path=local_path)
    return StoredObject(uri=local_path or f"file://{key}", backend="local", key=key, local_path=local_path)


def persist_local_file(
    config: dict[str, Any],
    *,
    team_id: int,
    project_id: int,
    local_path: str | Path,
    kind: str,
) -> dict[str, str]:
    path = Path(local_path)
    backend = str(config.get("backend") or "local")
    if backend == "local":
        return {
            "object_uri": str(path),
            "storage_backend": "local",
            "storage_key": object_key(team_id, project_id, f"{kind}/{path.name}", str(config.get("prefix") or "")),
            "local_path": str(path),
        }
    stored = put_bytes(
        config,
        team_id=team_id,
        project_id=project_id,
        rel_path=f"{kind}/{path.name}",
        payload=path.read_bytes(),
        local_root=None,
    )
    return {
        "object_uri": stored.uri,
        "storage_backend": stored.backend,
        "storage_key": stored.key,
        "local_path": str(path),
    }


def get_bytes(uri: str, config: dict[str, Any] | None = None) -> bytes:
    if uri.startswith("memory://"):
        if uri not in MEMORY_OBJECTS:
            raise FileNotFoundError(uri)
        return MEMORY_OBJECTS[uri]
    if uri.startswith("s3://"):
        return get_s3_object(config or {}, uri)
    path = Path(uri.removeprefix("file://"))
    return path.read_bytes()


def put_s3_object(config: dict[str, Any], key: str, payload: bytes) -> str:
    url, headers = signed_s3_request(config, "PUT", key, payload)
    request = Request(url, data=payload, headers=headers, method="PUT")
    try:
        with urlopen(request, timeout=8) as response:
            response.read()
    except (URLError, HTTPError) as exc:
        raise RuntimeError(f"S3 PUT failed: {exc}") from exc
    return f"s3://{config['bucket']}/{key}"


def get_s3_object(config: dict[str, Any], uri: str) -> bytes:
    parsed = urlparse(uri)
    key = parsed.path.lstrip("/")
    bucket = parsed.netloc or str(config.get("bucket") or "")
    merged = {**config, "bucket": bucket}
    url, headers = signed_s3_request(merged, "GET", key, b"")
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=8) as response:
            return response.read()
    except (URLError, HTTPError) as exc:
        raise RuntimeError(f"S3 GET failed: {exc}") from exc


def signed_s3_request(
    config: dict[str, Any],
    method: str,
    key: str,
    payload: bytes,
    unsigned: bool = False,
) -> tuple[str, dict[str, str]]:
    access_key = str(config.get("access_key") or "")
    secret_key = str(config.get("secret_key") or "")
    region = str(config.get("region") or "us-east-1")
    bucket = str(config.get("bucket") or "")
    if not access_key or not secret_key or not bucket:
        raise RuntimeError("S3 access_key, secret_key, and bucket are required.")
    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    datestamp = now.strftime("%Y%m%d")
    payload_hash = "UNSIGNED-PAYLOAD" if unsigned else hashlib.sha256(payload).hexdigest()
    host, canonical_uri, url = _s3_url(config, key)
    canonical_headers = f"host:{host}\nx-amz-content-sha256:{payload_hash}\nx-amz-date:{amz_date}\n"
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = "\n".join(
        [method, canonical_uri, "", canonical_headers, signed_headers, payload_hash]
    )
    credential_scope = f"{datestamp}/{region}/s3/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    signing_key = _s3_signing_key(secret_key, datestamp, region, "s3")
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = (
        f"AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    headers = {
        "Host": host,
        "x-amz-date": amz_date,
        "x-amz-content-sha256": payload_hash,
        "Authorization": authorization,
    }
    if method == "PUT":
        headers["Content-Length"] = str(len(payload))
    return url, headers


def probe_storage(config: dict[str, Any]) -> dict[str, Any]:
    backend = str(config.get("backend") or "local")
    if backend == "local":
        return {"ok": True, "mode": "local", "backend": "local"}
    if backend == "memory":
        MEMORY_OBJECTS["memory://health"] = b"ok"
        return {"ok": True, "mode": "live", "backend": "memory"}
    try:
        put_s3_object(config, object_key(0, 0, ".health", str(config.get("prefix") or "")), b"mangedong-ok")
    except Exception as exc:
        return {"ok": False, "mode": "fallback", "backend": "s3", "error": str(exc)}
    return {"ok": True, "mode": "live", "backend": "s3", "bucket": config.get("bucket")}


def _s3_url(config: dict[str, Any], key: str) -> tuple[str, str, str]:
    bucket = str(config["bucket"])
    encoded_key = quote(key, safe="/")
    endpoint = str(config.get("endpoint") or "").rstrip("/")
    use_path = bool(config.get("use_path_style", True))
    if endpoint:
        parsed = urlparse(endpoint if "://" in endpoint else f"https://{endpoint}")
        host = parsed.netloc or parsed.path
        scheme = parsed.scheme or "https"
        if use_path:
            canonical_uri = f"/{bucket}/{encoded_key}"
            return host, canonical_uri, f"{scheme}://{host}{canonical_uri}"
        host = f"{bucket}.{host}"
        canonical_uri = f"/{encoded_key}"
        return host, canonical_uri, f"{scheme}://{host}{canonical_uri}"
    region = str(config.get("region") or "us-east-1")
    host = f"{bucket}.s3.{region}.amazonaws.com"
    canonical_uri = f"/{encoded_key}"
    return host, canonical_uri, f"https://{host}{canonical_uri}"


def _s3_signing_key(secret_key: str, datestamp: str, region: str, service: str) -> bytes:
    def sign(key: bytes, message: str) -> bytes:
        return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()

    date_key = sign(f"AWS4{secret_key}".encode("utf-8"), datestamp)
    region_key = sign(date_key, region)
    service_key = sign(region_key, service)
    return sign(service_key, "aws4_request")
