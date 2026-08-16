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
    app = create_app(database_url="sqlite://", secret_key="enhancement-secret", storage_dir=tmp_path / "storage")
    with TestClient(app) as test_client:
        yield test_client


def test_enhancement_workflow_and_review_features(client: TestClient) -> None:
    token = _register_and_login(client, "owner@example.com")
    client.cookies.set("md_session", token)
    team_id = client.post("/teams", json={"name": "Enhancement Studio"}, headers=_auth(token)).json()["id"]
    project_id = client.post("/projects", json=_project_payload(team_id), headers=_auth(token)).json()["id"]

    storage = client.post(
        f"/projects/{project_id}/storage/presign",
        json={"data": {"filename": "reference.png"}},
        headers=_auth(token),
    )
    assert storage.status_code == 200
    assert storage.json()["data"]["method"] == "local_put"

    workflow_id = client.post(
        f"/projects/{project_id}/workflows",
        json={
            "name": "Editable Workflow",
            "workflow_type": "colorize",
            "workflow_json": {"1": {"class_type": "CLIPTextEncode", "inputs": {}}},
            "published_parameters": {"prompt": {"node_id": "1", "input": "text"}},
        },
        headers=_auth(token),
    ).json()["id"]
    updated = client.patch(
        f"/workflows/{workflow_id}/parameters",
        json={"data": {"seed": {"node_id": "2", "input": "seed"}}},
        headers=_auth(token),
    )
    assert updated.status_code == 200
    assert "seed" in updated.json()["data"]["published_parameters"]

    panel_id = _import_panel(client, project_id, token)
    colorization = client.post(f"/panels/{panel_id}/colorize", json={"data": {"palette": "cel"}}, headers=_auth(token)).json()
    correction = client.post(
        f"/colorizations/{colorization['id']}/local-corrections",
        json={"data": {"saturation": 1.2, "brightness": 1.05}},
        headers=_auth(token),
    )
    assert correction.status_code == 200
    assert Path(correction.json()["data"]["output_asset_uri"]).exists()

    comparison = client.post(
        f"/colorizations/{colorization['id']}/compare",
        json={"data": {"other_resource_id": correction.json()["id"]}},
        headers=_auth(token),
    )
    assert comparison.json()["resource_type"] == "color_comparison"

    first_clip = client.post(
        f"/panels/{panel_id}/generate-video",
        json={"data": {"duration_seconds": 1, "fps": 4}},
        headers=_auth(token),
    ).json()
    second_clip = client.post(
        f"/panels/{panel_id}/generate-video",
        json={"data": {"duration_seconds": 1, "fps": 4, "provider": "alternate-mock"}},
        headers=_auth(token),
    ).json()
    clip_comparison = client.post(
        f"/video-clips/{first_clip['id']}/compare",
        json={"data": {"other_clip_id": second_clip["id"], "mode": "ab_sync"}},
        headers=_auth(token),
    )
    assert clip_comparison.json()["resource_type"] == "clip_comparison"

    review_package = client.post(
        f"/projects/{project_id}/review-packages",
        json={"data": {"package_type": "client_review", "version": "R1"}},
        headers=_auth(token),
    ).json()
    revision = client.post(
        f"/review-packages/{review_package['id']}/revision-requests",
        json={"data": {"revision_round": 1, "scope": "shot-001"}},
        headers=_auth(token),
    )
    assert revision.json()["resource_type"] == "revision_request"
    acceptance = client.post(
        f"/review-packages/{review_package['id']}/acceptance-records",
        json={"data": {"accepted_by": "client@example.com"}},
        headers=_auth(token),
    )
    assert acceptance.json()["status"] == "accepted"

    color_page = client.get(f"/ui/projects/{project_id}/color-review")
    assert color_page.status_code == 200
    assert "Local Corrections" in color_page.text
    clip_page = client.get(f"/ui/projects/{project_id}/clip-compare")
    assert clip_page.status_code == 200
    assert "A/B Comparisons" in clip_page.text
    client_page = client.get(f"/ui/projects/{project_id}/client-review")
    assert client_page.status_code == 200
    assert "Acceptance Records" in client_page.text


def _import_panel(client: TestClient, project_id: int, token: str) -> int:
    response = client.post(
        f"/projects/{project_id}/imports/manga",
        files={"file": ("page.png", _demo_page_png(), "image/png")},
        data={"chapter_title": "Chapter 1"},
        headers=_auth(token),
    )
    assert response.status_code == 201
    return response.json()["data"]["pages"][0]["panel_id"]


def _register_and_login(client: TestClient, email: str) -> str:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": email.split("@")[0]},
    )
    assert response.status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert login.status_code == 200
    return login.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _demo_page_png() -> bytes:
    image = Image.new("L", (160, 220), 245)
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 150, 100), outline=10, width=3)
    draw.ellipse((55, 25, 105, 75), outline=20, width=3)
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
