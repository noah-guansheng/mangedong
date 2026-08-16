from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


TeamRole = Literal["owner", "admin", "producer", "artist", "animator", "reviewer", "viewer"]
LanguageCode = Literal["zh", "ja", "en"]


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=120)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_by_id: int
    created_at: datetime


class TeamMemberCreate(BaseModel):
    email: EmailStr
    role: TeamRole


class TeamMemberUpdate(BaseModel):
    role: TeamRole


class TeamMemberRead(BaseModel):
    id: int
    team_id: int
    user_id: int
    email: EmailStr
    display_name: str
    role: TeamRole
    created_at: datetime
    invite_token: str | None = None


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    password: str = Field(min_length=8)


class InviteAccept(BaseModel):
    token: str
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=120)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    status: str | None = None
    brief: ProjectBrief | None = None


class WorkItemUpdate(BaseModel):
    status: str | None = None
    assignee_id: int | None = None
    priority: Literal["low", "normal", "high", "urgent"] | None = None


class ProjectBrief(BaseModel):
    customer_name: str = Field(min_length=1)
    ip_name: str = Field(min_length=1)
    chapter_scope: str = Field(min_length=1)
    estimated_runtime_minutes: float = Field(gt=0)
    target_languages: list[LanguageCode] = Field(min_length=1)
    aspect_ratio: Literal["16:9", "9:16", "1:1", "4:3"]
    resolution: str = Field(pattern=r"^\d+x\d+$")
    fps: int = Field(ge=1, le=120)
    delivery_date: date | None = None
    budget_limit: float | None = Field(default=None, ge=0)
    authorization_status: Literal["unknown", "internal_owned", "licensed", "user_provided", "restricted"] = "unknown"
    client_review_mode: Literal["internal_only", "external_link", "managed_client_account"] = "internal_only"
    acceptance_checklist: list[str] = Field(default_factory=list)


class ProjectCreate(BaseModel):
    team_id: int
    name: str = Field(min_length=1, max_length=200)
    brief: ProjectBrief


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    name: str
    status: str
    brief: dict[str, Any]
    created_by_id: int
    created_at: datetime


class AssetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    asset_type: Literal["manga_page", "reference_coloring", "character_sheet", "bgm", "voice", "export"]
    uri: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    project_id: int
    name: str
    asset_type: str
    uri: str
    asset_metadata: dict[str, Any]
    created_by_id: int
    created_at: datetime


class ChapterCreate(BaseModel):
    title: str = Field(min_length=1, max_length=220)
    source_language: LanguageCode = "zh"


class ChapterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    project_id: int
    title: str
    source_language: str
    status: str
    created_by_id: int
    created_at: datetime


class PageCreate(BaseModel):
    page_number: int = Field(ge=1)
    image_uri: str = Field(min_length=1)


class PageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    project_id: int
    chapter_id: int
    page_number: int
    image_uri: str
    status: str
    created_by_id: int
    created_at: datetime


class PanelCreate(BaseModel):
    panel_index: int = Field(ge=1)
    bbox: dict[str, Any]


class PanelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    project_id: int
    chapter_id: int
    page_id: int
    panel_index: int
    bbox: dict[str, Any]
    status: str
    created_by_id: int
    created_at: datetime


class WorkItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    stage: Literal["brief", "import", "ocr", "color", "shot", "video", "audio", "review", "export"]
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    assignee_id: int | None = None
    checklist: list[str] = Field(default_factory=list)


class WorkItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    project_id: int
    title: str
    stage: str
    status: str
    priority: str
    assignee_id: int | None
    checklist: list[str]
    created_by_id: int
    created_at: datetime


class ProductionGateCreate(BaseModel):
    gate_type: Literal["brief", "color_bible", "shot_list", "animatic", "video", "audio", "qc", "export"]
    scope: str = Field(min_length=1, max_length=160)
    required_checks: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)


class ProductionGateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    project_id: int
    gate_type: str
    scope: str
    status: str
    required_checks: list[str]
    evidence: dict[str, Any]
    approved_by_id: int | None
    created_by_id: int
    created_at: datetime
    approved_at: datetime | None


class AIJobCreate(BaseModel):
    job_type: Literal["import", "preprocess", "ocr", "analyze", "colorize", "video_generate", "voice_generate", "export"]
    provider: str = Field(default="manual", min_length=1, max_length=120)
    input_payload: dict[str, Any] = Field(default_factory=dict)


class AIJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    project_id: int
    job_type: str
    status: str
    provider: str
    input_payload: dict[str, Any]
    output_payload: dict[str, Any]
    attempt_count: int
    last_error: str | None
    lease_owner: str | None
    leased_at: datetime | None
    created_by_id: int
    created_at: datetime


class ProductionResourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    project_id: int | None
    resource_type: str
    status: str
    data: dict[str, Any]
    created_by_id: int
    created_at: datetime
    updated_at: datetime


class ProviderCreate(BaseModel):
    name: str = Field(min_length=1)
    provider_type: Literal["third_party_api", "remote_comfyui", "local_model", "custom_http"]
    capabilities: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class ComfyUIInstanceCreate(BaseModel):
    name: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    auth_type: Literal["none", "bearer", "basic", "custom_header"] = "none"
    token: str | None = None
    custom_header_name: str | None = None
    max_concurrency: int = Field(default=1, ge=1)
    tunnel_url: str | None = None


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1)
    workflow_type: Literal["colorize", "image_to_video", "first_last_frame_video", "upscale", "inpaint"]
    workflow_json: dict[str, Any]
    published_parameters: dict[str, Any] = Field(default_factory=dict)


class ResourcePayload(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class ShotCreate(BaseModel):
    title: str = Field(min_length=1)
    source_panel_ids: list[int] = Field(default_factory=list)
    camera: str = "slow zoom in"
    action: str = ""
    duration_seconds: float = Field(default=3.0, gt=0)
    prompt: str = ""


class TimelineCreate(BaseModel):
    name: str = Field(min_length=1)


class TimelineItemCreate(BaseModel):
    item_type: Literal["video", "subtitle", "voice", "bgm"]
    resource_id: int
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)


class DialogueLineCreate(BaseModel):
    speaker_id: str | None = None
    line_type: Literal["dialogue", "narration", "sfx", "thought"] = "dialogue"
    source_language: LanguageCode = "zh"
    edited_text: str = Field(min_length=1)


class ReviewCommentCreate(BaseModel):
    object_type: str = Field(min_length=1)
    object_id: int
    category: str = Field(min_length=1)
    content: str = Field(min_length=1)
    severity: Literal["low", "medium", "high", "blocker"] = "medium"


class SMTPConfig(BaseModel):
    host: str = Field(min_length=1)
    port: int = Field(default=587, ge=1, le=65535)
    username: str = ""
    password: str | None = None
    from_address: str = ""
    use_tls: bool = True
    use_ssl: bool = False
    public_base_url: str = ""


class S3Config(BaseModel):
    backend: Literal["local", "s3", "memory"] = "s3"
    endpoint: str = ""
    bucket: str = ""
    region: str = "us-east-1"
    access_key: str = ""
    secret_key: str | None = None
    prefix: str = ""
    use_path_style: bool = True


class QueueConfig(BaseModel):
    max_running: int = Field(default=8, ge=1, le=256)
    lease_ttl_seconds: int = Field(default=45, ge=5, le=3600)


class TokenPlanConfig(BaseModel):
    api_key: str | None = None
    tool_profile: Literal["cursor", "qwen-code", "claude-code", "cline", "openclaw"] = "qwen-code"
    text_model: str = "qwen3.6-plus"
    image_model: str = "qwen-image-2.0"
    video_model: str = "happyhorse-1.1-t2v"


class StudioAgentTurn(BaseModel):
    message: str = Field(min_length=1)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    model: str | None = None


class TokenPlanSkillRequest(BaseModel):
    skill: Literal["text-to-image", "text-to-video"]
    prompt: str = Field(min_length=1)
    model: str | None = None
    size: str = "1024*1024"
    resolution: str = "720P"
    ratio: str = "16:9"
    duration: int = Field(default=5, ge=1, le=15)
