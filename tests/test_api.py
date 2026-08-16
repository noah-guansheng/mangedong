from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from mangedong.api.app import create_app


@pytest.fixture()
def client() -> Iterator[TestClient]:
    app = create_app(database_url="sqlite://", secret_key="test-secret")
    with TestClient(app) as test_client:
        yield test_client


def test_register_login_and_get_current_user(client: TestClient) -> None:
    register = client.post(
        "/auth/register",
        json={"email": "owner@example.com", "password": "password123", "display_name": "Owner"},
    )
    assert register.status_code == 201

    login = client.post("/auth/login", json={"email": "owner@example.com", "password": "password123"})
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/auth/me", headers=_auth(token))
    assert me.status_code == 200
    assert me.json()["email"] == "owner@example.com"


def test_team_owner_can_invite_member_and_member_cannot_invite(client: TestClient) -> None:
    owner_token = _register_and_login(client, "owner@example.com")
    artist_token = _register_and_login(client, "artist@example.com")

    team = client.post("/teams", json={"name": "Studio"}, headers=_auth(owner_token))
    assert team.status_code == 201
    team_id = team.json()["id"]

    invite = client.post(
        f"/teams/{team_id}/members",
        json={"email": "artist@example.com", "role": "artist"},
        headers=_auth(owner_token),
    )
    assert invite.status_code == 201
    assert invite.json()["role"] == "artist"

    denied = client.post(
        f"/teams/{team_id}/members",
        json={"email": "owner@example.com", "role": "viewer"},
        headers=_auth(artist_token),
    )
    assert denied.status_code == 403


def test_project_brief_requires_producer_level_role(client: TestClient) -> None:
    owner_token = _register_and_login(client, "owner@example.com")
    viewer_token = _register_and_login(client, "viewer@example.com")

    team_id = client.post("/teams", json={"name": "Anime Studio"}, headers=_auth(owner_token)).json()["id"]
    client.post(
        f"/teams/{team_id}/members",
        json={"email": "viewer@example.com", "role": "viewer"},
        headers=_auth(owner_token),
    )

    viewer_project = client.post(
        "/projects",
        json=_project_payload(team_id),
        headers=_auth(viewer_token),
    )
    assert viewer_project.status_code == 403

    owner_project = client.post(
        "/projects",
        json=_project_payload(team_id),
        headers=_auth(owner_token),
    )
    assert owner_project.status_code == 201
    project = owner_project.json()
    assert project["status"] == "draft"
    assert project["brief"]["ip_name"] == "Manga IP"

    projects = client.get(f"/projects?team_id={team_id}", headers=_auth(owner_token))
    assert projects.status_code == 200
    assert [item["id"] for item in projects.json()] == [project["id"]]


def test_project_production_objects_flow(client: TestClient) -> None:
    owner_token = _register_and_login(client, "owner@example.com")
    team_id = client.post("/teams", json={"name": "Production Team"}, headers=_auth(owner_token)).json()["id"]
    project_id = client.post("/projects", json=_project_payload(team_id), headers=_auth(owner_token)).json()["id"]

    asset = client.post(
        f"/projects/{project_id}/assets",
        json={"name": "page-001.png", "asset_type": "manga_page", "uri": "s3://team/project/page-001.png"},
        headers=_auth(owner_token),
    )
    assert asset.status_code == 201

    chapter = client.post(
        f"/projects/{project_id}/chapters",
        json={"title": "Chapter 1", "source_language": "zh"},
        headers=_auth(owner_token),
    )
    assert chapter.status_code == 201
    chapter_id = chapter.json()["id"]

    page = client.post(
        f"/chapters/{chapter_id}/pages",
        json={"page_number": 1, "image_uri": "s3://team/project/page-001.png"},
        headers=_auth(owner_token),
    )
    assert page.status_code == 201
    page_id = page.json()["id"]

    panel = client.post(
        f"/pages/{page_id}/panels",
        json={"panel_index": 1, "bbox": {"x": 0, "y": 0, "width": 100, "height": 200}},
        headers=_auth(owner_token),
    )
    assert panel.status_code == 201

    work_item = client.post(
        f"/projects/{project_id}/work-items",
        json={"title": "Approve character colors", "stage": "color", "priority": "high"},
        headers=_auth(owner_token),
    )
    assert work_item.status_code == 201
    assert work_item.json()["stage"] == "color"

    gate = client.post(
        f"/projects/{project_id}/production-gates",
        json={"gate_type": "color_bible", "scope": "chapter-1", "required_checks": ["character colors approved"]},
        headers=_auth(owner_token),
    )
    assert gate.status_code == 201

    approved_gate = client.post(f"/production-gates/{gate.json()['id']}/approve", headers=_auth(owner_token))
    assert approved_gate.status_code == 200
    assert approved_gate.json()["status"] == "approved"

    job = client.post(
        f"/projects/{project_id}/ai-jobs",
        json={"job_type": "colorize", "provider": "manual", "input_payload": {"page_id": page_id}},
        headers=_auth(owner_token),
    )
    assert job.status_code == 201
    assert job.json()["status"] == "created"

    assert len(client.get(f"/projects/{project_id}/assets", headers=_auth(owner_token)).json()) == 1
    assert len(client.get(f"/projects/{project_id}/chapters", headers=_auth(owner_token)).json()) == 1
    assert len(client.get(f"/chapters/{chapter_id}/pages", headers=_auth(owner_token)).json()) == 1
    assert len(client.get(f"/pages/{page_id}/panels", headers=_auth(owner_token)).json()) == 1
    assert len(client.get(f"/projects/{project_id}/work-items", headers=_auth(owner_token)).json()) == 1
    assert len(client.get(f"/projects/{project_id}/production-gates", headers=_auth(owner_token)).json()) == 1
    assert len(client.get(f"/projects/{project_id}/ai-jobs", headers=_auth(owner_token)).json()) == 1


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
