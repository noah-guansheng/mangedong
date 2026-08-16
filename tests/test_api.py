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
