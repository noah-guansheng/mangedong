from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mangedong.api.app import create_app
from mangedong.api.tokenplan import (
    catalog,
    model_supported,
    resolve_outbound_model,
    tool_headers,
)


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[TestClient]:
    app = create_app(database_url="sqlite://", secret_key="tokenplan-secret", storage_dir=tmp_path / "storage")
    with TestClient(app) as test_client:
        yield test_client


def test_catalog_is_exact_whitelist() -> None:
    data = catalog()
    assert data["openai_base_url"].endswith("/compatible-mode/v1")
    assert data["anthropic_base_url"].endswith("/apps/anthropic")
    assert "qwen3.6-plus" in data["models"]["text"]
    assert "qwen-image-2.0" in data["models"]["image"]
    assert "happyhorse-1.1-t2v" in data["models"]["video"]
    assert not model_supported("qwen3-coder-next", "text")
    assert resolve_outbound_model("glm-5", "cursor") == "glm-5-0"
    assert resolve_outbound_model("glm-5", "qwen-code") == "glm-5"


def test_tool_headers_match_coding_clients() -> None:
    openai = tool_headers({"api_key": "sk-sp-test", "tool_profile": "cursor"})
    assert openai["User-Agent"].startswith("Cursor/")
    assert openai["Authorization"] == "Bearer sk-sp-test"
    anthropic = tool_headers({"api_key": "sk-sp-test", "tool_profile": "claude-code"})
    assert anthropic["User-Agent"].startswith("claude-cli/")
    assert anthropic["x-api-key"] == "sk-sp-test"
    assert anthropic["anthropic-version"] == "2023-06-01"
    skill = tool_headers({"api_key": "sk-sp-test", "tool_profile": "claude-code"}, for_skill=True)
    assert skill["Authorization"] == "Bearer sk-sp-test"


def test_tokenplan_save_probe_agent_and_skills(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[str, str, dict, dict | None]] = []

    def fake_http(method: str, url: str, *, headers: dict | None = None, body: dict | None = None, timeout: float = 3.0) -> dict:
        calls.append((method, url, dict(headers or {}), body))
        if url.endswith("/models"):
            return {"data": [{"id": "qwen3.6-plus"}, {"id": "qwen-image-2.0"}]}
        if url.endswith("/chat/completions"):
            messages = (body or {}).get("messages") or []
            if any(item.get("role") == "tool" for item in messages):
                return {"choices": [{"message": {"content": "开场用近景，再切角色定妆。"}}]}
            last = messages[-1] if messages else {}
            if "pong" in str(last.get("content") or "").lower():
                return {"choices": [{"message": {"content": "pong"}}]}
            return {
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "tool_calls": [{"id": "call-brief", "type": "function", "function": {"name": "read_project_brief", "arguments": "{}"}}],
                        }
                    }
                ]
            }
        if "multimodal-generation" in url:
            return {"output": {"choices": [{"message": {"content": [{"image": "https://cdn.example.com/still.png"}]}}]}}
        if "video-synthesis" in url:
            return {"output": {"task_id": "video-task-1", "task_status": "PENDING"}}
        return {}

    monkeypatch.setattr("mangedong.api.tokenplan.http_json", fake_http)
    monkeypatch.setattr("mangedong.api.app.download_bytes", lambda url, timeout=20.0: b"fake-png")

    owner = _register_and_login(client, "plan@studio.com")
    team_id = client.post("/teams", json={"name": "Token Studio"}, headers=_auth(owner)).json()["id"]
    catalog_payload = client.get("/token-plan/catalog", headers=_auth(owner)).json()
    assert catalog_payload["api_key_prefix"] == "sk-sp-"

    saved = client.put(
        f"/teams/{team_id}/token-plan",
        json={
            "api_key": "sk-sp-secret",
            "tool_profile": "qwen-code",
            "text_model": "qwen3.6-plus",
            "image_model": "qwen-image-2.0",
            "video_model": "happyhorse-1.1-t2v",
        },
        headers=_auth(owner),
    )
    assert saved.status_code == 200
    assert saved.json()["data"]["api_key"] == "********"
    listed = client.get(f"/teams/{team_id}/token-plan", headers=_auth(owner)).json()
    assert listed["configured"] is True
    assert listed["data"]["tool_profile"] == "qwen-code"

    probed = client.post(f"/teams/{team_id}/token-plan/test", headers=_auth(owner)).json()
    assert probed["ok"] is True
    assert probed["user_agent"].startswith("QwenCode/")
    assert probed["base_url"].endswith("/compatible-mode/v1")
    assert probed["model_count"] == 2

    project_id = client.post("/projects", json=_project_payload(team_id), headers=_auth(owner)).json()["id"]
    turn = client.post(
        f"/projects/{project_id}/studio-agent/turn",
        json={"message": "根据 Brief 给出分镜建议"},
        headers=_auth(owner),
    ).json()
    assert turn["ok"] is True
    assert turn["mode"] == "live"
    assert "定妆" in turn["text"]
    assert turn["tool_trace"][0]["name"] == "read_project_brief"

    image = client.post(
        f"/projects/{project_id}/studio-agent/skill",
        json={"skill": "text-to-image", "prompt": "anime character color key"},
        headers=_auth(owner),
    ).json()
    assert image["ok"] is True
    assert image["image_urls"][0].endswith("still.png")
    assert Path(image["local_path"]).exists()

    video = client.post(
        f"/projects/{project_id}/studio-agent/skill",
        json={"skill": "text-to-video", "prompt": "character walks in rain"},
        headers=_auth(owner),
    ).json()
    assert video["task_id"] == "video-task-1"

    chat_calls = [item for item in calls if item[1].endswith("/chat/completions")]
    assert chat_calls
    assert chat_calls[0][2]["User-Agent"].startswith("QwenCode/")
    assert (chat_calls[0][3] or {}).get("enable_thinking") is True


def test_unknown_model_is_rejected() -> None:
    from mangedong.api.providers import ProviderError
    from mangedong.api.tokenplan import chat_as_tool

    with pytest.raises(ProviderError):
        chat_as_tool({"api_key": "sk-sp-x", "tool_profile": "cursor", "text_model": "qwen3-coder-next"}, [{"role": "user", "content": "hi"}])


def _register_and_login(client: TestClient, email: str) -> str:
    client.post("/auth/register", json={"email": email, "password": "password123", "display_name": email.split("@")[0]})
    return client.post("/auth/login", json={"email": email, "password": "password123"}).json()["access_token"]


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
            "target_languages": ["zh"],
            "aspect_ratio": "16:9",
            "resolution": "1920x1080",
            "fps": 24,
            "authorization_status": "licensed",
        },
    }
