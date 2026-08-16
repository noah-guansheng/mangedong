from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mangedong.api.app import create_app


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(database_url="sqlite://", secret_key="p1-p2-secret", storage_dir=tmp_path / "storage")
    with TestClient(app) as test_client:
        yield test_client


def test_p1_and_p2_scaffolds_are_available(client: TestClient) -> None:
    token = _register_and_login(client, "owner@example.com")
    client.cookies.set("md_session", token)
    team_id = client.post("/teams", json={"name": "P1P2 Studio"}, headers=_auth(token)).json()["id"]
    project_id = client.post("/projects", json=_project_payload(team_id), headers=_auth(token)).json()["id"]

    pdf_import = client.post(
        f"/projects/{project_id}/imports/pdf",
        files={"file": ("chapter.pdf", b"%PDF-1.4 mock", "application/pdf")},
        data={"chapter_title": "PDF Chapter", "page_count": 2},
        headers=_auth(token),
    )
    assert pdf_import.status_code == 201
    first_panel_id = pdf_import.json()["data"]["pages"][0]["panel_id"]
    assert Path(pdf_import.json()["data"]["pages"][0]["image_uri"]).exists()

    corrected = client.patch(
        f"/panels/{first_panel_id}/manual-correction",
        json={"data": {"bbox": {"x": 5, "y": 5, "width": 120, "height": 180}}},
        headers=_auth(token),
    )
    assert corrected.status_code == 200
    assert corrected.json()["status"] == "manually_corrected"

    color_profile = client.post(
        f"/projects/{project_id}/color-profiles",
        json={"data": {"character": "Hero", "slots": {"hair": "#111827"}}},
        headers=_auth(token),
    )
    assert color_profile.json()["resource_type"] == "color_profile"
    strategy = client.post(
        f"/projects/{project_id}/color-strategies/apply",
        json={"data": {"scope": "chapter", "conflict_policy": "require_confirmation"}},
        headers=_auth(token),
    )
    assert strategy.json()["status"] == "applied"

    shot_id = client.post(f"/projects/{project_id}/shots", json={"title": "Shot for dialogue"}, headers=_auth(token)).json()["id"]
    dialogue_id = client.post(
        f"/shots/{shot_id}/dialogue-lines",
        json={"edited_text": "Hello", "source_language": "en"},
        headers=_auth(token),
    ).json()["id"]
    translations = client.post(
        f"/dialogue-lines/{dialogue_id}/translations",
        json={"data": {"target_languages": ["zh", "ja"]}},
        headers=_auth(token),
    )
    assert translations.json()["data"]["translations"]["zh"] == "[zh] Hello"

    error_log = client.post(
        f"/projects/{project_id}/error-logs",
        json={"data": {"severity": "warning", "message": "mock provider retry"}},
        headers=_auth(token),
    )
    assert error_log.json()["resource_type"] == "error_log"

    private_deployment = client.post(
        f"/teams/{team_id}/private-deployments",
        json={"data": {"deployment_mode": "single_tenant"}},
        headers=_auth(token),
    )
    assert private_deployment.json()["status"] == "planned"
    cloud_pool = client.post(
        f"/teams/{team_id}/comfyui/cloud-pools",
        json={"data": {"gpu_profile": "mock-a10", "max_instances": 2}},
        headers=_auth(token),
    )
    assert cloud_pool.json()["resource_type"] == "comfyui_cloud_pool"

    workflow_id = client.post(
        f"/projects/{project_id}/workflows",
        json={"name": "Canvas Workflow", "workflow_type": "inpaint", "workflow_json": {"1": {"class_type": "Node"}}},
        headers=_auth(token),
    ).json()["id"]
    canvas = client.patch(
        f"/workflows/{workflow_id}/canvas",
        json={"data": {"nodes": [{"id": "1", "x": 10, "y": 20}], "links": []}},
        headers=_auth(token),
    )
    assert canvas.json()["status"] == "canvas_updated"

    timeline_id = client.post(f"/projects/{project_id}/timelines", json={"name": "Advanced Timeline"}, headers=_auth(token)).json()["id"]
    tracks = client.post(
        f"/timelines/{timeline_id}/tracks",
        json={"data": {"track_type": "video", "name": "V1"}},
        headers=_auth(token),
    )
    assert tracks.json()["status"] == "advanced_timeline"
    keyframes = client.post(
        f"/timelines/{timeline_id}/keyframes",
        json={"data": {"property": "opacity", "time": 1.0, "value": 0.5}},
        headers=_auth(token),
    )
    assert len(keyframes.json()["data"]["keyframes"]) == 1

    collaboration = client.post(
        f"/projects/{project_id}/collaboration/sessions",
        json={"data": {"participants": [1], "mode": "review"}},
        headers=_auth(token),
    )
    assert collaboration.json()["status"] == "active"
    training = client.post(
        f"/projects/{project_id}/model-training-jobs",
        json={"data": {"training_type": "character_lora"}},
        headers=_auth(token),
    )
    assert training.json()["status"] == "queued"

    export_id = client.post(f"/projects/{project_id}/exports", json={"data": {"resolution": "4k"}}, headers=_auth(token)).json()["id"]
    advanced_export = client.post(
        f"/exports/{export_id}/advanced-format",
        json={"data": {"format": "prores"}},
        headers=_auth(token),
    )
    assert advanced_export.json()["resource_type"] == "advanced_export"
    assert Path(advanced_export.json()["data"]["package_uri"]).exists()

    errors_page = client.get(f"/ui/projects/{project_id}/errors")
    assert errors_page.status_code == 200
    assert "Error Logs" in errors_page.text
    p2_page = client.get(f"/ui/projects/{project_id}/p2-admin")
    assert p2_page.status_code == 200
    assert "Private Deployments" in p2_page.text
    assert "Advanced Exports" in p2_page.text


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
