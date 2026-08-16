from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from mangedong.api.app import create_app


@pytest.fixture()
def client() -> Iterator[TestClient]:
    app = create_app(database_url="sqlite://", secret_key="prd-flow-secret")
    with TestClient(app) as test_client:
        yield test_client


def test_prd_p0_workflow_from_provider_to_frozen_export(client: TestClient) -> None:
    token = _register_and_login(client, "owner@example.com")
    client.cookies.set("md_session", token)
    team_id = client.post("/teams", json={"name": "Full Studio"}, headers=_auth(token)).json()["id"]
    project_id = client.post("/projects", json=_project_payload(team_id), headers=_auth(token)).json()["id"]

    provider = client.post(
        f"/teams/{team_id}/ai-providers",
        json={"name": "Mock Video API", "provider_type": "third_party_api", "capabilities": ["video_generate"]},
        headers=_auth(token),
    )
    assert provider.status_code == 201

    comfyui = client.post(
        f"/teams/{team_id}/comfyui/instances",
        json={"name": "Remote ComfyUI", "base_url": "https://comfy.example.com", "auth_type": "bearer"},
        headers=_auth(token),
    )
    assert comfyui.status_code == 201
    health = client.post(f"/comfyui/instances/{comfyui.json()['id']}/health-check", headers=_auth(token))
    assert health.json()["status"] == "healthy"

    workflow = client.post(
        f"/projects/{project_id}/workflows",
        json={
            "name": "Image to Video",
            "workflow_type": "image_to_video",
            "workflow_json": {"1": {"class_type": "LoadImage", "inputs": {}}},
            "published_parameters": {"prompt": {"node_id": "1", "input": "text"}, "output": {"node_id": "9"}},
        },
        headers=_auth(token),
    )
    assert workflow.status_code == 201
    tested_workflow = client.post(f"/workflows/{workflow.json()['id']}/test-run", headers=_auth(token))
    assert tested_workflow.json()["status"] == "production_ready"

    reference = client.post(
        f"/projects/{project_id}/references",
        json={"data": {"name": "colored-page", "uri": "s3://refs/colored.png"}},
        headers=_auth(token),
    )
    assert reference.status_code == 201
    character = client.post(
        f"/projects/{project_id}/characters",
        json={"data": {"name": "Hero", "hair_color": "#111827"}},
        headers=_auth(token),
    )
    assert character.status_code == 201

    chapter_id = client.post(
        f"/projects/{project_id}/chapters",
        json={"title": "Chapter 1", "source_language": "zh"},
        headers=_auth(token),
    ).json()["id"]
    page_id = client.post(
        f"/chapters/{chapter_id}/pages",
        json={"page_number": 1, "image_uri": "s3://pages/001.png"},
        headers=_auth(token),
    ).json()["id"]
    panel_id = client.post(
        f"/pages/{page_id}/panels",
        json={"panel_index": 1, "bbox": {"x": 0, "y": 0, "width": 100, "height": 100}},
        headers=_auth(token),
    ).json()["id"]

    assert client.post(f"/panels/{panel_id}/ocr", headers=_auth(token)).json()["resource_type"] == "dialogue_line"
    assert client.post(f"/panels/{panel_id}/analyze", headers=_auth(token)).json()["resource_type"] == "analysis"
    assert client.post(f"/panels/{panel_id}/colorize", json={"data": {"palette": "cel"}}, headers=_auth(token)).json()["status"] == "succeeded"
    assert client.post(f"/projects/{project_id}/batch-colorize", json={"data": {"scope": "chapter-1", "estimated_items": 1}}, headers=_auth(token)).json()["status"] == "queued"
    video_clip = client.post(
        f"/panels/{panel_id}/generate-video",
        json={"data": {"provider": "comfyui", "duration_seconds": 3}},
        headers=_auth(token),
    )
    assert video_clip.json()["resource_type"] == "video_clip"

    shot = client.post(
        f"/projects/{project_id}/shots",
        json={"title": "Shot 001", "source_panel_ids": [panel_id], "camera": "slow zoom", "duration_seconds": 3},
        headers=_auth(token),
    )
    shot_id = shot.json()["id"]
    assert client.post(f"/shots/{shot_id}/generate-animatic", headers=_auth(token)).json()["resource_type"] == "animatic"

    timeline_id = client.post(f"/projects/{project_id}/timelines", json={"name": "Main Timeline"}, headers=_auth(token)).json()["id"]
    timeline = client.post(
        f"/timelines/{timeline_id}/items",
        json={"item_type": "video", "resource_id": video_clip.json()["id"], "start_seconds": 0, "end_seconds": 3},
        headers=_auth(token),
    )
    assert len(timeline.json()["data"]["items"]) == 1

    dialogue_id = client.post(
        f"/shots/{shot_id}/dialogue-lines",
        json={"speaker_id": "hero", "line_type": "dialogue", "source_language": "zh", "edited_text": "开始吧"},
        headers=_auth(token),
    ).json()["id"]
    assert client.post(f"/dialogue-lines/{dialogue_id}/voice", json={"data": {"voice": "hero-zh"}}, headers=_auth(token)).json()["resource_type"] == "voice_line"
    assert client.post(f"/dialogue-lines/{dialogue_id}/subtitle", json={"data": {"text": "开始吧", "start": 0, "end": 2}}, headers=_auth(token)).json()["resource_type"] == "subtitle_cue"
    assert client.post(f"/projects/{project_id}/music-cues", json={"data": {"asset_uri": "s3://bgm/theme.wav"}}, headers=_auth(token)).json()["resource_type"] == "music_cue"
    assert client.post(f"/projects/{project_id}/audio-mixes", json={"data": {"loudness_target": "-16 LUFS"}}, headers=_auth(token)).json()["status"] == "rendered"

    comment = client.post(
        "/review-comments",
        json={"object_type": "panel", "object_id": panel_id, "category": "color", "content": "Looks good", "severity": "low"},
        headers=_auth(token),
    )
    assert comment.status_code == 201
    assert client.post(f"/projects/{project_id}/qc-reports", json={"data": {"checks": {"video_playable": True, "authorized": True}}}, headers=_auth(token)).json()["status"] == "passed"

    export = client.post(f"/projects/{project_id}/exports", json={"data": {"resolution": "1920x1080"}}, headers=_auth(token))
    export_id = export.json()["id"]
    preflight = client.post(f"/exports/{export_id}/preflight", headers=_auth(token))
    assert preflight.json()["status"] == "qc_passed"
    frozen = client.post(f"/exports/{export_id}/freeze", headers=_auth(token))
    assert frozen.json()["status"] == "frozen"

    ai_page = client.get(f"/ui/projects/{project_id}/ai-workflows")
    assert ai_page.status_code == 200
    assert "AI Workflow Center" in ai_page.text
    review_page = client.get(f"/ui/projects/{project_id}/review-export")
    assert review_page.status_code == 200
    assert "Review Comments" in review_page.text
    assert "Export Packages" in review_page.text


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
            "delivery_date": "2026-09-01",
            "budget_limit": 1000,
            "authorization_status": "licensed",
            "client_review_mode": "external_link",
            "acceptance_checklist": ["internal review", "client approval", "commercial export"],
        },
    }
