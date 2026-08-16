from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mangedong.api.app import create_app


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(database_url="sqlite://", secret_key="worker-secret", storage_dir=tmp_path / "storage")
    with TestClient(app) as test_client:
        yield test_client


def test_worker_runs_pending_jobs_and_generates_outputs(client: TestClient) -> None:
    token = _register_and_login(client, "owner@example.com")
    team_id = client.post("/teams", json={"name": "Worker Studio"}, headers=_auth(token)).json()["id"]
    project_id = client.post("/projects", json=_project_payload(team_id), headers=_auth(token)).json()["id"]

    voice_job = client.post(
        f"/projects/{project_id}/ai-jobs",
        json={"job_type": "voice_generate", "provider": "mock", "input_payload": {"text": "hello"}},
        headers=_auth(token),
    ).json()
    export_job = client.post(
        f"/projects/{project_id}/ai-jobs",
        json={"job_type": "export", "provider": "mock", "input_payload": {"format": "zip"}},
        headers=_auth(token),
    ).json()

    processed = client.post(f"/projects/{project_id}/ai-jobs/run-pending", headers=_auth(token))
    assert processed.status_code == 200
    payload = processed.json()
    assert {job["id"] for job in payload} == {voice_job["id"], export_job["id"]}
    assert all(job["status"] == "succeeded" for job in payload)
    assert Path(payload[0]["output_payload"].get("audio_uri") or payload[0]["output_payload"].get("package_uri")).exists()
    assert Path(payload[1]["output_payload"].get("audio_uri") or payload[1]["output_payload"].get("package_uri")).exists()


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
