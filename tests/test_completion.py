from __future__ import annotations

from collections.abc import Iterator
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from mangedong.api.app import create_app
from mangedong.api.secrets import decrypt_secret, encrypt_secret


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(database_url="sqlite://", secret_key="complete-secret", storage_dir=tmp_path / "storage")
    with TestClient(app) as test_client:
        yield test_client


def test_invite_unknown_user_reset_password_and_worker_tick(client: TestClient) -> None:
    owner = _register_and_login(client, "owner@studio.com")
    team_id = client.post("/teams", json={"name": "Done Studio"}, headers=_auth(owner)).json()["id"]
    invited = client.post(
        f"/teams/{team_id}/members",
        json={"email": "new.artist@studio.com", "role": "artist"},
        headers=_auth(owner),
    )
    assert invited.status_code == 201
    token = invited.json()["invite_token"]
    assert token

    accepted = client.post(
        "/auth/accept-invite",
        json={"token": token, "password": "password123", "display_name": "New Artist"},
    )
    assert accepted.status_code == 200
    artist_token = accepted.json()["access_token"]
    me = client.get("/auth/me", headers=_auth(artist_token))
    assert me.json()["email"] == "new.artist@studio.com"

    forgot = client.post("/auth/forgot-password", json={"email": "new.artist@studio.com"})
    assert forgot.status_code == 200
    reset_token = forgot.json()["reset_token"]
    reset = client.post("/auth/reset-password", json={"token": reset_token, "password": "password456"})
    assert reset.status_code == 200
    login = client.post("/auth/login", json={"email": "new.artist@studio.com", "password": "password456"})
    assert login.status_code == 200

    project_id = client.post("/projects", json=_project_payload(team_id), headers=_auth(owner)).json()["id"]
    patched = client.patch(
        f"/projects/{project_id}",
        json={"name": "Episode 1 Locked", "status": "in_production"},
        headers=_auth(owner),
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Episode 1 Locked"

    job = client.post(
        f"/projects/{project_id}/ai-jobs",
        json={"job_type": "analyze", "provider": "mock", "input_payload": {}},
        headers=_auth(owner),
    ).json()
    ticked = client.post("/ops/worker/tick", headers=_auth(owner))
    assert ticked.status_code == 200
    assert any(item["id"] == job["id"] and item["status"] == "succeeded" for item in ticked.json())

    health = client.get("/health")
    assert health.json()["status"] == "ok"
    assert health.json()["worker"] == "disabled"


def test_video_file_animatic_and_resource_playback(client: TestClient) -> None:
    owner = _register_and_login(client, "editor@studio.com")
    team_id = client.post("/teams", json={"name": "Edit Studio"}, headers=_auth(owner)).json()["id"]
    project_id = client.post("/projects", json=_project_payload(team_id), headers=_auth(owner)).json()["id"]
    imported = client.post(
        f"/projects/{project_id}/imports/manga",
        files={"file": ("page.png", _demo_page_png(), "image/png")},
        data={"chapter_title": "Chapter 1"},
        headers=_auth(owner),
    )
    assert imported.status_code == 201
    panel_id = imported.json()["data"]["pages"][0]["panel_id"]
    colorized = client.post(f"/panels/{panel_id}/colorize", json={"data": {"palette": "cel"}}, headers=_auth(owner)).json()
    color_file = client.get(f"/resources/{colorized['id']}/file", headers=_auth(owner))
    assert color_file.status_code == 200
    assert color_file.headers["content-type"].startswith("image/")

    video = client.post(
        f"/panels/{panel_id}/generate-video",
        json={"data": {"provider": "comfyui", "duration_seconds": 1, "fps": 4, "width": 160}},
        headers=_auth(owner),
    ).json()
    assert video["data"]["execution_mode"] in {"local_fallback", "comfyui_live"}
    clip = client.get(f"/resources/{video['id']}/file", headers=_auth(owner))
    assert clip.status_code == 200
    assert len(clip.content) > 32

    shot = client.post(
        f"/projects/{project_id}/shots",
        json={"title": "Shot 001", "source_panel_ids": [panel_id], "duration_seconds": 1},
        headers=_auth(owner),
    ).json()
    animatic = client.post(f"/shots/{shot['id']}/generate-animatic", headers=_auth(owner)).json()
    assert animatic["resource_type"] == "animatic"
    assert Path(animatic["data"]["output_asset_uri"]).exists()
    preview = client.get(f"/resources/{animatic['id']}/file", headers=_auth(owner))
    assert preview.status_code == 200


def test_secret_roundtrip_and_comfy_fallback(client: TestClient) -> None:
    packed = encrypt_secret("sk-test", "complete-secret")
    assert packed.startswith("enc:")
    assert decrypt_secret(packed, "complete-secret") == "sk-test"
    owner = _register_and_login(client, "owner@models.com")
    team_id = client.post("/teams", json={"name": "Model Studio"}, headers=_auth(owner)).json()["id"]
    instance = client.post(
        f"/teams/{team_id}/comfyui/instances",
        json={"name": "Remote", "base_url": "https://comfy.example.com", "auth_type": "none"},
        headers=_auth(owner),
    ).json()
    health = client.post(f"/comfyui/instances/{instance['id']}/health-check", headers=_auth(owner))
    assert health.json()["status"] == "fallback"
    assert health.json()["data"]["health"]["mode"] == "fallback"


def _register_and_login(client: TestClient, email: str) -> str:
    client.post("/auth/register", json={"email": email, "password": "password123", "display_name": email.split("@")[0]})
    return client.post("/auth/login", json={"email": email, "password": "password123"}).json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _demo_page_png() -> bytes:
    image = Image.new("L", (80, 110), 245)
    draw = ImageDraw.Draw(image)
    draw.rectangle((6, 6, 74, 50), outline=10, width=2)
    draw.rectangle((6, 58, 74, 104), outline=10, width=2)
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
            "target_languages": ["zh", "ja", "en"],
            "aspect_ratio": "16:9",
            "resolution": "1920x1080",
            "fps": 24,
            "authorization_status": "licensed",
        },
    }
