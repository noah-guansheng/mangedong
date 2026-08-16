from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from mangedong.api.app import create_app


@pytest.fixture()
def client() -> Iterator[TestClient]:
    app = create_app(database_url="sqlite://", secret_key="page-test-secret")
    with TestClient(app) as test_client:
        yield test_client


def test_login_page_renders_workbench_entry(client: TestClient) -> None:
    response = client.get("/ui/login")

    assert response.status_code == 200
    assert "mangedong 工作台" in response.text
    assert 'aria-label="login-form"' in response.text


def test_dashboard_projects_and_production_pages_render(client: TestClient) -> None:
    token = _register_and_login(client, "producer@example.com")
    client.cookies.set("md_session", token)
    team_id = client.post("/teams", json={"name": "Studio UI"}, headers=_auth(token)).json()["id"]
    project_id = client.post("/projects", json=_project_payload(team_id), headers=_auth(token)).json()["id"]

    client.post(
        f"/projects/{project_id}/assets",
        json={"name": "reference.png", "asset_type": "reference_coloring", "uri": "s3://asset/reference.png"},
        headers=_auth(token),
    )
    client.post(
        f"/projects/{project_id}/work-items",
        json={"title": "Prepare animatic", "stage": "shot", "priority": "normal"},
        headers=_auth(token),
    )
    client.post(
        f"/projects/{project_id}/production-gates",
        json={"gate_type": "animatic", "scope": "project", "required_checks": ["animatic approved"]},
        headers=_auth(token),
    )
    client.post(
        f"/projects/{project_id}/ai-jobs",
        json={"job_type": "video_generate", "provider": "comfyui", "input_payload": {"shot": "shot-001"}},
        headers=_auth(token),
    )

    dashboard = client.get("/ui/dashboard")
    assert dashboard.status_code == 200
    assert "Dashboard" in dashboard.text
    assert "Studio UI" in dashboard.text

    projects = client.get(f"/ui/projects?team_id={team_id}")
    assert projects.status_code == 200
    assert "Episode 1" in projects.text
    assert "生产工作台" in projects.text

    production = client.get(f"/ui/projects/{project_id}/production")
    assert production.status_code == 200
    assert "Manga IP" in production.text
    assert "素材库" in production.text
    assert "Work Items" in production.text
    assert "Production Gates" in production.text
    assert "AI Jobs" in production.text


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
