from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


TeamRole = Literal["owner", "admin", "producer", "artist", "animator", "reviewer", "viewer"]


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


class TeamMemberRead(BaseModel):
    id: int
    team_id: int
    user_id: int
    email: EmailStr
    display_name: str
    role: TeamRole
    created_at: datetime


class ProjectBrief(BaseModel):
    customer_name: str = Field(min_length=1)
    ip_name: str = Field(min_length=1)
    chapter_scope: str = Field(min_length=1)
    estimated_runtime_minutes: float = Field(gt=0)
    target_languages: list[Literal["zh", "ja", "en"]] = Field(min_length=1)
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
