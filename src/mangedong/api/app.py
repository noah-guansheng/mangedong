from __future__ import annotations

import os
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from mangedong.api.db import build_session_factory, init_db, session_scope
from mangedong.api.entities import Project, Team, TeamMember, User
from mangedong.api.schemas import (
    ProjectCreate,
    ProjectRead,
    TeamCreate,
    TeamMemberCreate,
    TeamMemberRead,
    TeamRead,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserRead,
)
from mangedong.api.security import create_access_token, hash_password, parse_access_token, verify_password


DEFAULT_DATABASE_URL = "sqlite:///./mangedong.db"
MANAGE_TEAM_ROLES = {"owner", "admin"}
PROJECT_WRITE_ROLES = {"owner", "admin", "producer"}

bearer_scheme = HTTPBearer(auto_error=False)


def get_db(request: Request) -> Generator[Session, None, None]:
    session_factory: sessionmaker[Session] = request.app.state.session_factory
    yield from session_scope(session_factory)


DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    request: Request,
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    token_payload = parse_access_token(credentials.credentials, request.app.state.secret_key)
    if token_payload is None:
        raise HTTPException(status_code=401, detail="Invalid bearer token.")
    user = db.get(User, token_payload.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exists.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_team_membership(db: Session, user_id: int, team_id: int) -> TeamMember:
    member = db.scalar(select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id))
    if member is None:
        raise HTTPException(status_code=403, detail="You are not a member of this team.")
    return member


def require_team_role(db: Session, user_id: int, team_id: int, allowed_roles: set[str]) -> TeamMember:
    member = require_team_membership(db, user_id, team_id)
    if member.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="You do not have permission for this action.")
    return member


def member_response(member: TeamMember, user: User) -> TeamMemberRead:
    return TeamMemberRead(
        id=member.id,
        team_id=member.team_id,
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=member.role,  # type: ignore[arg-type]
        created_at=member.created_at,
    )


def create_app(database_url: str | None = None, secret_key: str | None = None) -> FastAPI:
    session_factory = build_session_factory(database_url or os.getenv("MANGEDONG_DATABASE_URL", DEFAULT_DATABASE_URL))
    init_db(session_factory)

    api = FastAPI(title="mangedong Web SaaS API", version="0.1.0")
    api.state.session_factory = session_factory
    api.state.secret_key = secret_key or os.getenv("MANGEDONG_SECRET_KEY", "dev-secret-change-me")

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.post("/auth/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
    def register(payload: UserCreate, db: DbSession) -> User:
        user = User(
            email=payload.email.lower(),
            display_name=payload.display_name,
            password_hash=hash_password(payload.password),
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail="Email is already registered.") from exc
        db.refresh(user)
        return user

    @api.post("/auth/login", response_model=TokenResponse)
    def login(payload: UserLogin, request: Request, db: DbSession) -> TokenResponse:
        user = db.scalar(select(User).where(User.email == payload.email.lower()))
        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        token = create_access_token(user.id, request.app.state.secret_key)
        return TokenResponse(access_token=token)

    @api.get("/auth/me", response_model=UserRead)
    def me(current_user: CurrentUser) -> User:
        return current_user

    @api.post("/teams", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
    def create_team(payload: TeamCreate, current_user: CurrentUser, db: DbSession) -> Team:
        team = Team(name=payload.name, created_by_id=current_user.id)
        db.add(team)
        db.flush()
        db.add(TeamMember(team_id=team.id, user_id=current_user.id, role="owner"))
        db.commit()
        db.refresh(team)
        return team

    @api.get("/teams", response_model=list[TeamRead])
    def list_teams(current_user: CurrentUser, db: DbSession) -> list[Team]:
        return list(
            db.scalars(
                select(Team)
                .join(TeamMember, TeamMember.team_id == Team.id)
                .where(TeamMember.user_id == current_user.id)
                .order_by(Team.created_at.desc())
            )
        )

    @api.post("/teams/{team_id}/members", response_model=TeamMemberRead, status_code=status.HTTP_201_CREATED)
    def add_team_member(
        team_id: int,
        payload: TeamMemberCreate,
        current_user: CurrentUser,
        db: DbSession,
    ) -> TeamMemberRead:
        require_team_role(db, current_user.id, team_id, MANAGE_TEAM_ROLES)
        user = db.scalar(select(User).where(User.email == payload.email.lower()))
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")
        member = TeamMember(team_id=team_id, user_id=user.id, role=payload.role)
        db.add(member)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail="User is already a team member.") from exc
        db.refresh(member)
        return member_response(member, user)

    @api.get("/teams/{team_id}/members", response_model=list[TeamMemberRead])
    def list_team_members(team_id: int, current_user: CurrentUser, db: DbSession) -> list[TeamMemberRead]:
        require_team_membership(db, current_user.id, team_id)
        members = db.execute(
            select(TeamMember, User)
            .join(User, User.id == TeamMember.user_id)
            .where(TeamMember.team_id == team_id)
            .order_by(TeamMember.created_at.asc())
        ).all()
        return [member_response(member, user) for member, user in members]

    @api.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
    def create_project(payload: ProjectCreate, current_user: CurrentUser, db: DbSession) -> Project:
        require_team_role(db, current_user.id, payload.team_id, PROJECT_WRITE_ROLES)
        project = Project(
            team_id=payload.team_id,
            name=payload.name,
            brief=payload.brief.model_dump(mode="json"),
            created_by_id=current_user.id,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @api.get("/projects", response_model=list[ProjectRead])
    def list_projects(team_id: int, current_user: CurrentUser, db: DbSession) -> list[Project]:
        require_team_membership(db, current_user.id, team_id)
        return list(db.scalars(select(Project).where(Project.team_id == team_id).order_by(Project.created_at.desc())))

    @api.get("/projects/{project_id}", response_model=ProjectRead)
    def get_project(project_id: int, current_user: CurrentUser, db: DbSession) -> Project:
        project = db.get(Project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        require_team_membership(db, current_user.id, project.team_id)
        return project

    return api

