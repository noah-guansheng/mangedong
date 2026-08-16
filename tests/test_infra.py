from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from mangedong.api.app import create_app
from mangedong.api.entities import AIJob, utc_now
from mangedong.api.objectstore import MEMORY_OBJECTS, signed_s3_request
from mangedong.api.worker import _try_claim, reap_expired_leases


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[TestClient]:
    MEMORY_OBJECTS.clear()
    app = create_app(database_url="sqlite://", secret_key="infra-secret", storage_dir=tmp_path / "storage")
    with TestClient(app) as test_client:
        yield test_client


def test_team_smtp_s3_queue_and_delivery_fallback(client: TestClient) -> None:
    owner = _register_and_login(client, "owner@infra.com")
    team_id = client.post("/teams", json={"name": "Infra Studio"}, headers=_auth(owner)).json()["id"]

    smtp = client.put(
        f"/teams/{team_id}/smtp",
        json={
            "host": "127.0.0.1",
            "port": 9,
            "username": "studio",
            "password": "smtp-secret",
            "from_address": "studio@example.com",
            "public_base_url": "https://studio.example.com",
        },
        headers=_auth(owner),
    )
    assert smtp.status_code == 200
    assert smtp.json()["data"]["password"] == "********"
    saved = client.get(f"/teams/{team_id}/smtp", headers=_auth(owner)).json()
    assert saved["source"] == "team"
    assert saved["data"]["host"] == "127.0.0.1"
    probed = client.post(f"/teams/{team_id}/smtp/test", headers=_auth(owner)).json()
    assert probed["mode"] in {"fallback", "unconfigured"}

    invited = client.post(
        f"/teams/{team_id}/members",
        json={"email": "new.artist@infra.com", "role": "artist"},
        headers=_auth(owner),
    )
    assert invited.status_code == 201
    assert invited.json()["invite_token"]

    forgot = client.post("/auth/forgot-password", json={"email": "owner@infra.com"}).json()
    assert forgot["reset_token"]
    assert forgot["delivery"] == "local_fallback"

    storage = client.put(
        f"/teams/{team_id}/storage",
        json={"backend": "memory", "bucket": "studio-bucket", "access_key": "ak", "secret_key": "sk"},
        headers=_auth(owner),
    )
    assert storage.status_code == 200
    assert storage.json()["data"]["secret_key"] == "********"
    assert client.post(f"/teams/{team_id}/storage/test", headers=_auth(owner)).json()["backend"] == "memory"

    queue = client.put(f"/teams/{team_id}/queue", json={"max_running": 3, "lease_ttl_seconds": 30}, headers=_auth(owner))
    assert queue.json()["data"]["max_running"] == 3
    snapshot = client.get("/ops/queue", headers=_auth(owner)).json()
    assert snapshot["backend"] == "database"
    assert "worker_id" in snapshot

    health = client.get("/health").json()
    assert health["queue"] == "database"
    assert health["worker"] == "disabled"


def test_memory_storage_persists_color_and_lease_is_exclusive(client: TestClient) -> None:
    owner = _register_and_login(client, "editor@infra.com")
    team_id = client.post("/teams", json={"name": "Store Studio"}, headers=_auth(owner)).json()["id"]
    client.put(
        f"/teams/{team_id}/storage",
        json={"backend": "memory", "bucket": "clips"},
        headers=_auth(owner),
    )
    project_id = client.post("/projects", json=_project_payload(team_id), headers=_auth(owner)).json()["id"]
    imported = client.post(
        f"/projects/{project_id}/imports/manga",
        files={"file": ("page.png", _demo_page_png(), "image/png")},
        data={"chapter_title": "Chapter 1"},
        headers=_auth(owner),
    )
    panel_id = imported.json()["data"]["pages"][0]["panel_id"]
    colorized = client.post(f"/panels/{panel_id}/colorize", json={"data": {"palette": "cel"}}, headers=_auth(owner)).json()
    assert colorized["data"]["storage_backend"] == "memory"
    assert colorized["data"]["object_uri"].startswith("memory://")
    assert Path(colorized["data"]["output_asset_uri"]).exists()
    fetched = client.get(f"/resources/{colorized['id']}/file", headers=_auth(owner))
    assert fetched.status_code == 200

    job = client.post(
        f"/projects/{project_id}/ai-jobs",
        json={"job_type": "analyze", "provider": "mock", "input_payload": {}},
        headers=_auth(owner),
    ).json()
    db = client.app.state.session_factory()
    try:
        first = _try_claim(db, job["id"], "worker-a")
        second = _try_claim(db, job["id"], "worker-b")
        assert first is not None
        assert first.lease_owner == "worker-a"
        assert second is None
        first.leased_at = utc_now() - timedelta(seconds=120)
        db.commit()
        assert reap_expired_leases(db) >= 1
        refreshed = db.get(AIJob, job["id"])
        assert refreshed is not None
        assert refreshed.status == "queued"
        assert refreshed.lease_owner is None
    finally:
        db.close()


def test_s3_signature_and_comfy_tunnel_url(client: TestClient) -> None:
    url, headers = signed_s3_request(
        {
            "access_key": "AKIAEXAMPLE",
            "secret_key": "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY",
            "bucket": "mangedong",
            "region": "us-east-1",
            "endpoint": "https://s3.example.com",
            "use_path_style": True,
        },
        "PUT",
        "teams/1/projects/2/assets/file.png",
        b"hello",
    )
    assert url.startswith("https://s3.example.com/mangedong/teams/1/projects/2/assets/file.png")
    assert headers["Authorization"].startswith("AWS4-HMAC-SHA256 Credential=AKIAEXAMPLE/")
    assert headers["x-amz-content-sha256"]

    owner = _register_and_login(client, "comfy@infra.com")
    team_id = client.post("/teams", json={"name": "Tunnel Studio"}, headers=_auth(owner)).json()["id"]
    instance = client.post(
        f"/teams/{team_id}/comfyui/instances",
        json={
            "name": "Tunneled Comfy",
            "base_url": "http://127.0.0.1:8188",
            "tunnel_url": "https://comfy.example.ngrok-free.app",
            "auth_type": "none",
        },
        headers=_auth(owner),
    ).json()
    assert instance["data"]["tunnel_url"] == "https://comfy.example.ngrok-free.app"
    health = client.post(f"/comfyui/instances/{instance['id']}/health-check", headers=_auth(owner)).json()
    assert health["status"] == "fallback"


def _register_and_login(client: TestClient, email: str) -> str:
    client.post("/auth/register", json={"email": email, "password": "password123", "display_name": email.split("@")[0]})
    return client.post("/auth/login", json={"email": email, "password": "password123"}).json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _demo_page_png() -> bytes:
    image = Image.new("L", (80, 110), 245)
    draw = ImageDraw.Draw(image)
    draw.rectangle((6, 6, 74, 50), outline=10, width=2)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _project_payload(team_id: int) -> dict[str, object]:
    return {
        "team_id": team_id,
        "name": "Episode 1",
        "brief": {
            "customer_name": "Client Studio",
            "ip_name": "Manga IP",
            "chapter_scope": "Chapter 1",
            "estimated_runtime_minutes": 3.5,
            "target_languages": ["zh"],
            "aspect_ratio": "16:9",
            "resolution": "1920x1080",
            "fps": 24,
            "authorization_status": "licensed",
        },
    }
