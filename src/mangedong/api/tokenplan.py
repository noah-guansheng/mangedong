from __future__ import annotations

import json
import os
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from mangedong.api.providers import ProviderError, http_json
from mangedong.api.secrets import decrypt_secret


OPENAI_BASE = "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
ANTHROPIC_BASE = "https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic"
MULTIMODAL_URL = "https://token-plan.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
VIDEO_SUBMIT_URL = "https://token-plan.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"
VIDEO_TASK_URL = "https://token-plan.cn-beijing.maas.aliyuncs.com/api/v1/tasks"

# Exact model IDs from Token Plan 团队版 docs. Do not invent nearby versions.
TEXT_MODELS = (
    "qwen3.8-max",
    "qwen3.7-max",
    "qwen3.7-plus",
    "qwen3.6-plus",
    "qwen3.6-flash",
    "deepseek-v4-pro",
    "deepseek-v4-pro-0813",
    "deepseek-v4-flash",
    "deepseek-v4-flash-0731",
    "deepseek-v3.2",
    "kimi-k2.7-code",
    "kimi-k2.6",
    "kimi-k2.5",
    "glm-5.2",
    "glm-5.1",
    "glm-5",
    "MiniMax-M2.5",
)
IMAGE_MODELS = (
    "qwen-image-2.0",
    "qwen-image-2.0-pro",
    "qwen-image-3.0-pro",
    "wan2.7-image",
    "wan2.7-image-pro",
)
VIDEO_MODELS = (
    "happyhorse-1.1-t2v",
    "happyhorse-1.1-i2v",
    "happyhorse-1.1-r2v",
)
AUDIO_MODELS = (
    "qwen-audio-3.0-tts-plus",
    "qwen-audio-3.0-realtime-plus",
    "qwen-audio-3.0-asr-flash",
)

CURSOR_MODEL_ALIASES = {
    "kimi-k2.6": "kimi-k2-6",
    "kimi-k2.5": "kimi-k2-5",
    "glm-5.2": "glm-5-2",
    "glm-5.1": "glm-5-1",
    "glm-5": "glm-5-0",
}

TOOL_PROFILES: dict[str, dict[str, str]] = {
    "cursor": {
        "protocol": "openai",
        "user_agent": "Cursor/1.7.0",
        "base_url": OPENAI_BASE,
    },
    "qwen-code": {
        "protocol": "openai",
        "user_agent": "QwenCode/0.5.0",
        "base_url": OPENAI_BASE,
    },
    "claude-code": {
        "protocol": "anthropic",
        "user_agent": "claude-cli/1.0.41 (external, cli)",
        "base_url": ANTHROPIC_BASE,
    },
    "cline": {
        "protocol": "openai",
        "user_agent": "Cline/3.16.0",
        "base_url": OPENAI_BASE,
    },
    "openclaw": {
        "protocol": "openai",
        "user_agent": "OpenClaw/1.0",
        "base_url": OPENAI_BASE,
    },
}

DEFAULT_TEXT_MODEL = "qwen3.6-plus"
DEFAULT_IMAGE_MODEL = "qwen-image-2.0"
DEFAULT_VIDEO_MODEL = "happyhorse-1.1-t2v"

JsonTransport = Callable[..., dict[str, Any]]


def catalog() -> dict[str, Any]:
    return {
        "product": "Token Plan 团队版",
        "usage": "interactive_ai_coding_tool",
        "openai_base_url": OPENAI_BASE,
        "anthropic_base_url": ANTHROPIC_BASE,
        "multimodal_url": MULTIMODAL_URL,
        "video_submit_url": VIDEO_SUBMIT_URL,
        "api_key_prefix": "sk-sp-",
        "models": {
            "text": list(TEXT_MODELS),
            "image": list(IMAGE_MODELS),
            "video": list(VIDEO_MODELS),
            "audio": list(AUDIO_MODELS),
        },
        "cursor_model_aliases": dict(CURSOR_MODEL_ALIASES),
        "tool_profiles": {name: dict(profile) for name, profile in TOOL_PROFILES.items()},
        "notes": [
            "仅限 AI 编程 / 智能体工具交互使用，不可用于自动化脚本或应用后端。",
            "API Key 以 sk-sp- 开头，必须搭配 token-plan.cn-beijing Base URL，不可与 dashscope 按量 Key 混用。",
            "图像 / 视频走 Skill 独立接口，不是 /chat/completions。",
        ],
    }


def model_supported(model_id: str, kind: str | None = None) -> bool:
    buckets = {
        "text": TEXT_MODELS,
        "image": IMAGE_MODELS,
        "video": VIDEO_MODELS,
        "audio": AUDIO_MODELS,
    }
    if kind:
        return model_id in buckets.get(kind, ())
    return any(model_id in names for names in buckets.values())


def resolve_outbound_model(model_id: str, tool_profile: str) -> str:
    if tool_profile == "cursor":
        return CURSOR_MODEL_ALIASES.get(model_id, model_id)
    return model_id


def tokenplan_from_env() -> dict[str, Any]:
    api_key = os.getenv("MANGEDONG_TOKENPLAN_API_KEY", "")
    if not api_key:
        return {}
    profile = os.getenv("MANGEDONG_TOKENPLAN_TOOL", "qwen-code")
    return {
        "api_key": api_key,
        "tool_profile": profile if profile in TOOL_PROFILES else "qwen-code",
        "text_model": os.getenv("MANGEDONG_TOKENPLAN_TEXT_MODEL", DEFAULT_TEXT_MODEL),
        "image_model": os.getenv("MANGEDONG_TOKENPLAN_IMAGE_MODEL", DEFAULT_IMAGE_MODEL),
        "video_model": os.getenv("MANGEDONG_TOKENPLAN_VIDEO_MODEL", DEFAULT_VIDEO_MODEL),
        "source": "env",
    }


def decode_tokenplan_config(data: dict[str, Any], secret_key: str) -> dict[str, Any]:
    config = dict(data)
    if config.get("api_key"):
        config["api_key"] = decrypt_secret(str(config["api_key"]), secret_key)
    config.setdefault("tool_profile", "qwen-code")
    config.setdefault("text_model", DEFAULT_TEXT_MODEL)
    config.setdefault("image_model", DEFAULT_IMAGE_MODEL)
    config.setdefault("video_model", DEFAULT_VIDEO_MODEL)
    config["source"] = "team"
    return config


def resolve_tokenplan(team_data: dict[str, Any] | None, secret_key: str) -> dict[str, Any]:
    if team_data and team_data.get("api_key"):
        return decode_tokenplan_config(team_data, secret_key)
    return tokenplan_from_env()


def profile_settings(config: dict[str, Any]) -> dict[str, str]:
    name = str(config.get("tool_profile") or "qwen-code")
    return dict(TOOL_PROFILES.get(name) or TOOL_PROFILES["qwen-code"])


def tool_headers(config: dict[str, Any], *, for_skill: bool = False) -> dict[str, str]:
    profile = profile_settings(config)
    api_key = str(config.get("api_key") or "")
    headers = {
        "User-Agent": profile["user_agent"],
        "Accept": "application/json",
        "X-Title": "mangedong-studio-agent",
    }
    if for_skill or profile["protocol"] == "openai":
        headers["Authorization"] = f"Bearer {api_key}"
    else:
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
    return headers


def studio_tools() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "read_project_brief",
                "description": "Read the current manga-to-anime project brief and production context.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_panels",
                "description": "List imported manga panels in the current project.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "text_to_image",
                "description": "Skill: generate a still via Token Plan multimodal API. Use when the user asks to draw or generate an image.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"},
                        "model": {"type": "string", "description": "Exact Token Plan image model ID."},
                        "size": {"type": "string", "description": "e.g. 1024*1024"},
                    },
                    "required": ["prompt"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "text_to_video",
                "description": "Skill: submit Token Plan HappyHorse video generation. Use when the user asks to generate a clip.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"},
                        "model": {"type": "string"},
                        "resolution": {"type": "string"},
                        "ratio": {"type": "string"},
                        "duration": {"type": "integer"},
                    },
                    "required": ["prompt"],
                },
            },
        },
    ]


def probe_tokenplan(config: dict[str, Any], *, transport: JsonTransport | None = None) -> dict[str, Any]:
    if not config.get("api_key"):
        return {"ok": False, "mode": "unconfigured", "error": "Token Plan API Key is empty."}
    profile = profile_settings(config)
    model = resolve_outbound_model(str(config.get("text_model") or DEFAULT_TEXT_MODEL), str(config.get("tool_profile") or "qwen-code"))
    try:
        if profile["protocol"] == "openai":
            listing = _json_call(
                "GET",
                f"{profile['base_url']}/models",
                headers=tool_headers(config),
                timeout=12.0,
                transport=transport,
            )
            ids = [str(item.get("id")) for item in (listing.get("data") or []) if isinstance(item, dict) and item.get("id")]
            return {
                "ok": True,
                "mode": "live",
                "tool_profile": config.get("tool_profile"),
                "protocol": profile["protocol"],
                "base_url": profile["base_url"],
                "user_agent": profile["user_agent"],
                "model": model,
                "model_count": len(ids),
                "models": ids[:16],
                "preview": f"models {len(ids)}",
            }
        reply = chat_as_tool(
            config,
            [{"role": "user", "content": "Reply with the single word pong."}],
            model=model,
            max_tokens=16,
            tools=None,
            timeout=25.0,
            transport=transport,
        )
    except Exception as exc:
        return {
            "ok": False,
            "mode": "fallback",
            "error": str(exc),
            "tool_profile": config.get("tool_profile"),
            "protocol": profile["protocol"],
            "base_url": profile["base_url"],
            "user_agent": profile["user_agent"],
        }
    return {
        "ok": True,
        "mode": "live",
        "tool_profile": config.get("tool_profile"),
        "protocol": profile["protocol"],
        "base_url": profile["base_url"],
        "user_agent": profile["user_agent"],
        "model": model,
        "preview": (reply.get("text") or "")[:120],
    }


def chat_as_tool(
    config: dict[str, Any],
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    max_tokens: int = 800,
    tools: list[dict[str, Any]] | None = studio_tools,
    timeout: float = 45.0,
    transport: JsonTransport | None = None,
) -> dict[str, Any]:
    profile = profile_settings(config)
    tool_profile = str(config.get("tool_profile") or "qwen-code")
    requested = model or str(config.get("text_model") or DEFAULT_TEXT_MODEL)
    outbound_model = resolve_outbound_model(requested, tool_profile)
    alias_values = set(CURSOR_MODEL_ALIASES.values())
    if not model_supported(requested, "text") and requested not in alias_values:
        raise ProviderError(f"Model {requested} is not on the Token Plan team whitelist.")
    tool_payload = tools() if callable(tools) else tools
    if profile["protocol"] == "anthropic":
        return _anthropic_messages(
            config, messages, model=outbound_model, max_tokens=max_tokens, tools=tool_payload, timeout=timeout, transport=transport
        )
    return _openai_chat(
        config, messages, model=outbound_model, max_tokens=max_tokens, tools=tool_payload, timeout=timeout, transport=transport
    )


def run_agent_turn(
    config: dict[str, Any],
    messages: list[dict[str, Any]],
    *,
    execute_tool: Callable[[str, dict[str, Any]], Any],
    max_rounds: int = 3,
    transport: JsonTransport | None = None,
) -> dict[str, Any]:
    if not config.get("api_key"):
        return {
            "ok": False,
            "mode": "local_fallback",
            "text": "还没配置 Token Plan。打开模型配置，填 sk-sp- 席位 Key，并选择 Cursor / Qwen Code / Claude Code 工具画像。",
            "messages": messages,
            "tool_trace": [],
        }
    working = [dict(item) for item in messages]
    if not any(item.get("role") == "system" for item in working):
        working.insert(0, {"role": "system", "content": _system_prompt()})
    trace: list[dict[str, Any]] = []
    last: dict[str, Any] = {}
    try:
        for _ in range(max_rounds):
            last = chat_as_tool(config, working, transport=transport)
            calls = last.get("tool_calls") or []
            if not calls:
                working.append({"role": "assistant", "content": last.get("text") or ""})
                return {"ok": True, "mode": "live", "text": last.get("text") or "", "messages": working, "tool_trace": trace, "usage": last.get("usage")}
            working.append({"role": "assistant", "content": last.get("text") or "", "tool_calls": calls})
            for call in calls:
                name = str(call.get("name") or "")
                arguments = call.get("arguments") or {}
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        arguments = {"raw": arguments}
                result = execute_tool(name, dict(arguments))
                trace.append({"name": name, "arguments": arguments, "result": result})
                working.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id") or name,
                        "name": name,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )
    except Exception as exc:
        return {
            "ok": False,
            "mode": "local_fallback",
            "text": f"Token Plan 当前不可达，制片助手走本地说明：{exc}",
            "messages": working,
            "tool_trace": trace,
            "error": str(exc),
        }
    working.append({"role": "assistant", "content": last.get("text") or "工具调用已完成。"})
    return {"ok": True, "mode": "live", "text": last.get("text") or "工具调用已完成。", "messages": working, "tool_trace": trace}


def generate_image(
    config: dict[str, Any],
    *,
    prompt: str,
    model: str | None = None,
    size: str = "1024*1024",
    timeout: float = 60.0,
    transport: JsonTransport | None = None,
) -> dict[str, Any]:
    chosen = model or str(config.get("image_model") or DEFAULT_IMAGE_MODEL)
    if not model_supported(chosen, "image"):
        raise ProviderError(f"Image model {chosen} is not on the Token Plan team whitelist.")
    payload = {
        "model": chosen,
        "input": {"messages": [{"role": "user", "content": [{"text": prompt}]}]},
        "parameters": {"size": size},
    }
    result = _json_call("POST", MULTIMODAL_URL, headers=tool_headers(config, for_skill=True), body=payload, timeout=timeout, transport=transport)
    urls = _extract_image_urls(result)
    return {"ok": True, "mode": "live", "skill": "text-to-image", "model": chosen, "prompt": prompt, "size": size, "image_urls": urls, "raw": _trim_raw(result)}


def submit_video(
    config: dict[str, Any],
    *,
    prompt: str,
    model: str | None = None,
    resolution: str = "720P",
    ratio: str = "16:9",
    duration: int = 5,
    timeout: float = 20.0,
    transport: JsonTransport | None = None,
) -> dict[str, Any]:
    chosen = model or str(config.get("video_model") or DEFAULT_VIDEO_MODEL)
    if not model_supported(chosen, "video"):
        raise ProviderError(f"Video model {chosen} is not on the Token Plan team whitelist.")
    payload = {
        "model": chosen,
        "input": {"prompt": prompt},
        "parameters": {"resolution": resolution, "ratio": ratio, "duration": duration},
    }
    headers = {**tool_headers(config, for_skill=True), "X-DashScope-Async": "enable"}
    result = _json_call("POST", VIDEO_SUBMIT_URL, headers=headers, body=payload, timeout=timeout, transport=transport)
    output = result.get("output") if isinstance(result.get("output"), dict) else result
    task_id = (output or {}).get("task_id") or result.get("task_id")
    return {
        "ok": True,
        "mode": "live",
        "skill": "text-to-video",
        "model": chosen,
        "prompt": prompt,
        "task_id": task_id,
        "status": (output or {}).get("task_status") or "PENDING",
        "raw": _trim_raw(result),
    }


def poll_video_task(
    config: dict[str, Any],
    task_id: str,
    *,
    timeout: float = 15.0,
    transport: JsonTransport | None = None,
) -> dict[str, Any]:
    result = _json_call("GET", f"{VIDEO_TASK_URL}/{task_id}", headers=tool_headers(config, for_skill=True), timeout=timeout, transport=transport)
    output = result.get("output") if isinstance(result.get("output"), dict) else result
    return {
        "ok": True,
        "task_id": task_id,
        "status": (output or {}).get("task_status"),
        "video_url": (output or {}).get("video_url"),
        "raw": _trim_raw(result),
    }


def download_bytes(url: str, timeout: float = 20.0) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ProviderError("Only http(s) download URLs are allowed.")
    request = Request(url, headers={"User-Agent": "QwenCode/0.5.0"}, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except (URLError, HTTPError) as exc:
        raise ProviderError(f"Download failed: {exc}") from exc


def _system_prompt() -> str:
    return (
        "You are mangedong Studio Agent, an interactive AI coding/production tool "
        "for a manga-to-anime team. Speak Chinese unless the user writes in another language. "
        "Use tools for project facts and Token Plan Skills for image/video generation. "
        "Do not claim you can run background batch jobs with this subscription."
    )


def _openai_chat(
    config: dict[str, Any],
    messages: list[dict[str, Any]],
    *,
    model: str,
    max_tokens: int,
    tools: list[dict[str, Any]] | None,
    timeout: float,
    transport: JsonTransport | None,
) -> dict[str, Any]:
    profile = profile_settings(config)
    body: dict[str, Any] = {
        "model": model,
        "messages": _openai_messages(messages),
        "max_tokens": max_tokens,
        "stream": False,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    if model.startswith("qwen3."):
        # Probe and short pings must turn thinking off; qwen3.6-plus otherwise spends ~7s+ and trips the old 8s timeout.
        body["enable_thinking"] = bool(tools)
    result = _json_call(
        "POST",
        f"{profile['base_url']}/chat/completions",
        headers=tool_headers(config),
        body=body,
        timeout=timeout,
        transport=transport,
    )
    choice = (result.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    return {
        "text": str(message.get("content") or "").strip(),
        "tool_calls": _openai_tool_calls(message.get("tool_calls") or []),
        "usage": result.get("usage") or {},
        "raw": _trim_raw(result),
    }


def _anthropic_messages(
    config: dict[str, Any],
    messages: list[dict[str, Any]],
    *,
    model: str,
    max_tokens: int,
    tools: list[dict[str, Any]] | None,
    timeout: float,
    transport: JsonTransport | None,
) -> dict[str, Any]:
    profile = profile_settings(config)
    system, converted = _anthropic_messages_payload(messages)
    body: dict[str, Any] = {"model": model, "max_tokens": max_tokens, "messages": converted}
    if system:
        body["system"] = system
    if tools:
        body["tools"] = [
            {
                "name": item["function"]["name"],
                "description": item["function"].get("description") or "",
                "input_schema": item["function"].get("parameters") or {"type": "object", "properties": {}},
            }
            for item in tools
            if item.get("function")
        ]
    result = _json_call(
        "POST",
        f"{profile['base_url']}/v1/messages",
        headers=tool_headers(config),
        body=body,
        timeout=timeout,
        transport=transport,
    )
    text_parts: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    for block in result.get("content") or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            text_parts.append(str(block.get("text") or ""))
        elif block.get("type") == "tool_use":
            tool_calls.append({"id": block.get("id"), "name": block.get("name"), "arguments": block.get("input") or {}})
    return {"text": "".join(text_parts).strip(), "tool_calls": tool_calls, "usage": result.get("usage") or {}, "raw": _trim_raw(result)}


def _openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for item in messages:
        role = str(item.get("role") or "user")
        if role == "tool":
            converted.append(
                {
                    "role": "tool",
                    "tool_call_id": item.get("tool_call_id") or item.get("name") or "tool",
                    "content": str(item.get("content") or ""),
                }
            )
            continue
        payload: dict[str, Any] = {"role": role, "content": item.get("content") or ""}
        if item.get("tool_calls"):
            payload["tool_calls"] = [
                {
                    "id": call.get("id") or call.get("name"),
                    "type": "function",
                    "function": {"name": call.get("name"), "arguments": json.dumps(call.get("arguments") or {}, ensure_ascii=False)},
                }
                for call in item["tool_calls"]
            ]
        converted.append(payload)
    return converted


def _anthropic_messages_payload(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    system = ""
    converted: list[dict[str, Any]] = []
    pending_tools: list[dict[str, Any]] = []
    for item in messages:
        role = str(item.get("role") or "user")
        if role == "system":
            system = str(item.get("content") or "")
            continue
        if role == "tool":
            pending_tools.append(
                {
                    "type": "tool_result",
                    "tool_use_id": item.get("tool_call_id") or item.get("name"),
                    "content": str(item.get("content") or ""),
                }
            )
            continue
        if pending_tools:
            converted.append({"role": "user", "content": pending_tools})
            pending_tools = []
        if role == "assistant" and item.get("tool_calls"):
            content: list[dict[str, Any]] = []
            if item.get("content"):
                content.append({"type": "text", "text": str(item.get("content"))})
            for call in item["tool_calls"]:
                content.append({"type": "tool_use", "id": call.get("id") or call.get("name"), "name": call.get("name"), "input": call.get("arguments") or {}})
            converted.append({"role": "assistant", "content": content})
            continue
        converted.append({"role": "user" if role == "user" else "assistant", "content": str(item.get("content") or "")})
    if pending_tools:
        converted.append({"role": "user", "content": pending_tools})
    return system, converted


def _openai_tool_calls(raw_calls: list[Any]) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for call in raw_calls:
        if not isinstance(call, dict):
            continue
        function = call.get("function") or {}
        arguments = function.get("arguments") or {}
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments or "{}")
            except json.JSONDecodeError:
                arguments = {"raw": arguments}
        parsed.append({"id": call.get("id"), "name": function.get("name"), "arguments": arguments})
    return parsed


def _extract_image_urls(result: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    output = result.get("output") if isinstance(result.get("output"), dict) else result
    for choice in output.get("choices") or []:
        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("image"):
                    urls.append(str(part["image"]))
        elif isinstance(content, dict) and content.get("image"):
            urls.append(str(content["image"]))
    return urls


def _json_call(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    body: dict[str, Any] | None = None,
    timeout: float,
    transport: JsonTransport | None,
) -> dict[str, Any]:
    caller = transport or http_json
    try:
        result = caller(method, url, headers=headers, body=body, timeout=timeout)
    except TypeError:
        result = caller(method, url, headers=headers, body=body)
    if isinstance(result, dict) and result.get("code") and str(result.get("code")) not in {"200", "0", ""}:
        raise ProviderError(str(result.get("message") or result.get("code")))
    return result if isinstance(result, dict) else {"data": result}


def _trim_raw(result: dict[str, Any]) -> dict[str, Any]:
    keep = {key: result[key] for key in ("id", "model", "object", "created", "usage", "output") if key in result}
    if "choices" in result:
        keep["choice_count"] = len(result.get("choices") or [])
    return keep
