from __future__ import annotations

from collections.abc import Iterator
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from mangedong.api.app import create_app


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(database_url="sqlite://", secret_key="human-flow-secret", storage_dir=tmp_path / "storage")
    with TestClient(app) as test_client:
        yield test_client


def test_human_can_walk_import_structure_members_and_costs(client: TestClient) -> None:
    owner = _register_and_login(client, "owner@studio.com")
    artist = _register_and_login(client, "artist@studio.com")
    team_id = client.post("/teams", json={"name": "Human Studio"}, headers=_auth(owner)).json()["id"]
    invited = client.post(
        f"/teams/{team_id}/members",
        json={"email": "artist@studio.com", "role": "artist"},
        headers=_auth(owner),
    )
    assert invited.status_code == 201
    updated = client.patch(
        f"/teams/{team_id}/members/{invited.json()['id']}",
        json={"role": "animator"},
        headers=_auth(owner),
    )
    assert updated.status_code == 200
    assert updated.json()["role"] == "animator"

    project_id = client.post("/projects", json=_project_payload(team_id), headers=_auth(owner)).json()["id"]
    imported = client.post(
        f"/projects/{project_id}/imports/manga",
        files={"file": ("page.png", _demo_page_png(), "image/png")},
        data={"chapter_title": "Chapter 1"},
        headers=_auth(owner),
    )
    assert imported.status_code == 201
    page_id = imported.json()["data"]["pages"][0]["page_id"]
    panel_id = imported.json()["data"]["pages"][0]["panel_id"]

    tree = client.get(f"/projects/{project_id}/structure", headers=_auth(owner))
    assert tree.status_code == 200
    assert tree.json()["chapters"][0]["pages"][0]["panels"][0]["id"] == panel_id

    preview = client.get(f"/pages/{page_id}/preview", headers=_auth(owner))
    assert preview.status_code == 200
    assert preview.headers["content-type"].startswith("image/")

    ocr = client.post(f"/panels/{panel_id}/ocr", headers=_auth(artist))
    assert ocr.status_code == 200
    color = client.post(f"/panels/{panel_id}/colorize", json={"data": {"palette": "cel"}}, headers=_auth(artist))
    assert color.status_code == 200
    assert Path(color.json()["data"]["output_asset_uri"]).exists()

    costs = client.get(f"/projects/{project_id}/costs", headers=_auth(owner))
    assert costs.status_code == 200
    assert costs.json()["currency"] == "USD"

    shots = client.get(f"/projects/{project_id}/resources?resource_type=shot", headers=_auth(owner))
    assert shots.status_code == 200
    assert shots.json() == []

    logout = client.post("/auth/logout", headers=_auth(owner))
    assert logout.status_code == 200
    assert logout.json()["ok"] is True


def _register_and_login(client: TestClient, email: str) -> str:
    client.post("/auth/register", json={"email": email, "password": "password123", "display_name": email.split("@")[0]})
    login = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert login.status_code == 200
    return login.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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


def _demo_page_png() -> bytes:
    image = Image.new("RGB", (320, 240), "#f2efe8")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 300, 220), outline="#171717", width=3)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
