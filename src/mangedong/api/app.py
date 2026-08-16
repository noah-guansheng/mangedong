from __future__ import annotations

import os
from collections.abc import Generator
from html import escape
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from mangedong.api.db import build_session_factory, init_db, session_scope
from mangedong.api.entities import AIJob, Asset, Chapter, MangaPage, Panel, ProductionGate, Project, Team, TeamMember, User, WorkItem, utc_now
from mangedong.api.schemas import (
    AIJobCreate,
    AIJobRead,
    AssetCreate,
    AssetRead,
    ChapterCreate,
    ChapterRead,
    PageCreate,
    PageRead,
    PanelCreate,
    PanelRead,
    ProductionGateCreate,
    ProductionGateRead,
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
    WorkItemCreate,
    WorkItemRead,
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


def require_project_access(db: Session, user_id: int, project_id: int, allowed_roles: set[str] | None = None) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    if allowed_roles is None:
        require_team_membership(db, user_id, project.team_id)
    else:
        require_team_role(db, user_id, project.team_id, allowed_roles)
    return project


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


def current_user_from_cookie(request: Request, db: Session) -> User | None:
    token = request.cookies.get("md_session")
    if not token:
        return None
    token_payload = parse_access_token(token, request.app.state.secret_key)
    if token_payload is None:
        return None
    return db.get(User, token_payload.user_id)


def render_page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        """
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <style>
      body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #f8fafc; color: #0f172a; }}
      header, section {{ background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1rem; margin-bottom: 1rem; }}
      a {{ color: #2563eb; }}
      .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; }}
      .card {{ border: 1px solid #e2e8f0; border-radius: 10px; padding: 1rem; }}
      .muted {{ color: #64748b; }}
    </style>
  </head>
  <body>
    {body}
  </body>
</html>
""".format(title=escape(title), body=body)
    )


def require_cookie_user(request: Request, db: Session) -> User:
    user = current_user_from_cookie(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Login required.")
    return user


def create_app(database_url: str | None = None, secret_key: str | None = None) -> FastAPI:
    session_factory = build_session_factory(database_url or os.getenv("MANGEDONG_DATABASE_URL", DEFAULT_DATABASE_URL))
    init_db(session_factory)

    api = FastAPI(title="mangedong Web SaaS API", version="0.1.0")
    api.state.session_factory = session_factory
    api.state.secret_key = secret_key or os.getenv("MANGEDONG_SECRET_KEY", "dev-secret-change-me")

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.get("/ui/login", response_class=HTMLResponse)
    def login_page() -> HTMLResponse:
        return render_page(
            "mangedong 登录",
            """
<header>
  <h1>mangedong 工作台</h1>
  <p class="muted">团队/工作室漫画转番剧动画 Web SaaS。</p>
</header>
<section>
  <h2>登录</h2>
  <p>当前页面用于工作台自动化测试和前端接入占位。</p>
  <form aria-label="login-form">
    <label>Email <input name="email" type="email" /></label>
    <label>Password <input name="password" type="password" /></label>
  </form>
</section>
""",
        )

    @api.get("/ui/dashboard", response_class=HTMLResponse)
    def dashboard_page(request: Request, db: DbSession) -> HTMLResponse:
        user = require_cookie_user(request, db)
        teams = list(
            db.scalars(
                select(Team)
                .join(TeamMember, TeamMember.team_id == Team.id)
                .where(TeamMember.user_id == user.id)
                .order_by(Team.created_at.desc())
            )
        )
        cards = "".join(
            f'<div class="card"><h3>{escape(team.name)}</h3><a href="/ui/projects?team_id={team.id}">进入项目</a></div>'
            for team in teams
        )
        return render_page(
            "Dashboard",
            f"""
<header>
  <h1>Dashboard</h1>
  <p class="muted">欢迎，{escape(user.display_name)}。</p>
</header>
<section>
  <h2>团队空间</h2>
  <div class="grid">{cards or '<p class="muted">暂无团队。</p>'}</div>
</section>
""",
        )

    @api.get("/ui/projects", response_class=HTMLResponse)
    def projects_page(team_id: int, request: Request, db: DbSession) -> HTMLResponse:
        user = require_cookie_user(request, db)
        require_team_membership(db, user.id, team_id)
        team = db.get(Team, team_id)
        projects = list(db.scalars(select(Project).where(Project.team_id == team_id).order_by(Project.created_at.desc())))
        cards = "".join(
            f'<div class="card"><h3>{escape(project.name)}</h3><p>Status: {escape(project.status)}</p>'
            f'<a href="/ui/projects/{project.id}/production">生产工作台</a></div>'
            for project in projects
        )
        return render_page(
            "项目列表",
            f"""
<header>
  <h1>{escape(team.name if team else "团队")} 项目</h1>
  <a href="/ui/dashboard">返回 Dashboard</a>
</header>
<section>
  <h2>项目列表</h2>
  <div class="grid">{cards or '<p class="muted">暂无项目。</p>'}</div>
</section>
""",
        )

    @api.get("/ui/projects/{project_id}/production", response_class=HTMLResponse)
    def production_page(project_id: int, request: Request, db: DbSession) -> HTMLResponse:
        user = require_cookie_user(request, db)
        project = require_project_access(db, user.id, project_id)
        assets = list(db.scalars(select(Asset).where(Asset.project_id == project_id).order_by(Asset.created_at.desc())))
        chapters = list(db.scalars(select(Chapter).where(Chapter.project_id == project_id).order_by(Chapter.created_at.asc())))
        work_items = list(db.scalars(select(WorkItem).where(WorkItem.project_id == project_id).order_by(WorkItem.created_at.desc())))
        gates = list(
            db.scalars(select(ProductionGate).where(ProductionGate.project_id == project_id).order_by(ProductionGate.created_at.desc()))
        )
        jobs = list(db.scalars(select(AIJob).where(AIJob.project_id == project_id).order_by(AIJob.created_at.desc())))
        return render_page(
            f"{project.name} 生产工作台",
            f"""
<header>
  <h1>{escape(project.name)} 生产工作台</h1>
  <p class="muted">Project Brief：{escape(project.brief.get("ip_name", ""))}</p>
</header>
<section class="grid">
  <div class="card"><h2>素材库</h2><p>{len(assets)} assets</p></div>
  <div class="card"><h2>章节</h2><p>{len(chapters)} chapters</p></div>
  <div class="card"><h2>Work Items</h2><p>{len(work_items)} open items</p></div>
  <div class="card"><h2>Production Gates</h2><p>{len(gates)} gates</p></div>
  <div class="card"><h2>AI Jobs</h2><p>{len(jobs)} jobs</p></div>
</section>
""",
        )

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

    @api.post("/projects/{project_id}/assets", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
    def create_asset(project_id: int, payload: AssetCreate, current_user: CurrentUser, db: DbSession) -> Asset:
        project = require_project_access(db, current_user.id, project_id, PROJECT_WRITE_ROLES)
        asset = Asset(
            team_id=project.team_id,
            project_id=project.id,
            name=payload.name,
            asset_type=payload.asset_type,
            uri=payload.uri,
            asset_metadata=payload.metadata,
            created_by_id=current_user.id,
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset

    @api.get("/projects/{project_id}/assets", response_model=list[AssetRead])
    def list_assets(project_id: int, current_user: CurrentUser, db: DbSession) -> list[Asset]:
        require_project_access(db, current_user.id, project_id)
        return list(db.scalars(select(Asset).where(Asset.project_id == project_id).order_by(Asset.created_at.desc())))

    @api.post("/projects/{project_id}/chapters", response_model=ChapterRead, status_code=status.HTTP_201_CREATED)
    def create_chapter(project_id: int, payload: ChapterCreate, current_user: CurrentUser, db: DbSession) -> Chapter:
        project = require_project_access(db, current_user.id, project_id, PROJECT_WRITE_ROLES)
        chapter = Chapter(
            team_id=project.team_id,
            project_id=project.id,
            title=payload.title,
            source_language=payload.source_language,
            created_by_id=current_user.id,
        )
        db.add(chapter)
        db.commit()
        db.refresh(chapter)
        return chapter

    @api.get("/projects/{project_id}/chapters", response_model=list[ChapterRead])
    def list_chapters(project_id: int, current_user: CurrentUser, db: DbSession) -> list[Chapter]:
        require_project_access(db, current_user.id, project_id)
        return list(db.scalars(select(Chapter).where(Chapter.project_id == project_id).order_by(Chapter.created_at.asc())))

    @api.post("/chapters/{chapter_id}/pages", response_model=PageRead, status_code=status.HTTP_201_CREATED)
    def create_page(chapter_id: int, payload: PageCreate, current_user: CurrentUser, db: DbSession) -> MangaPage:
        chapter = db.get(Chapter, chapter_id)
        if chapter is None:
            raise HTTPException(status_code=404, detail="Chapter not found.")
        require_project_access(db, current_user.id, chapter.project_id, PROJECT_WRITE_ROLES)
        page = MangaPage(
            team_id=chapter.team_id,
            project_id=chapter.project_id,
            chapter_id=chapter.id,
            page_number=payload.page_number,
            image_uri=payload.image_uri,
            created_by_id=current_user.id,
        )
        db.add(page)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail="Page number already exists in this chapter.") from exc
        db.refresh(page)
        return page

    @api.get("/chapters/{chapter_id}/pages", response_model=list[PageRead])
    def list_pages(chapter_id: int, current_user: CurrentUser, db: DbSession) -> list[MangaPage]:
        chapter = db.get(Chapter, chapter_id)
        if chapter is None:
            raise HTTPException(status_code=404, detail="Chapter not found.")
        require_project_access(db, current_user.id, chapter.project_id)
        return list(db.scalars(select(MangaPage).where(MangaPage.chapter_id == chapter_id).order_by(MangaPage.page_number.asc())))

    @api.post("/pages/{page_id}/panels", response_model=PanelRead, status_code=status.HTTP_201_CREATED)
    def create_panel(page_id: int, payload: PanelCreate, current_user: CurrentUser, db: DbSession) -> Panel:
        page = db.get(MangaPage, page_id)
        if page is None:
            raise HTTPException(status_code=404, detail="Page not found.")
        require_project_access(db, current_user.id, page.project_id, PROJECT_WRITE_ROLES)
        panel = Panel(
            team_id=page.team_id,
            project_id=page.project_id,
            chapter_id=page.chapter_id,
            page_id=page.id,
            panel_index=payload.panel_index,
            bbox=payload.bbox,
            created_by_id=current_user.id,
        )
        db.add(panel)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail="Panel index already exists on this page.") from exc
        db.refresh(panel)
        return panel

    @api.get("/pages/{page_id}/panels", response_model=list[PanelRead])
    def list_panels(page_id: int, current_user: CurrentUser, db: DbSession) -> list[Panel]:
        page = db.get(MangaPage, page_id)
        if page is None:
            raise HTTPException(status_code=404, detail="Page not found.")
        require_project_access(db, current_user.id, page.project_id)
        return list(db.scalars(select(Panel).where(Panel.page_id == page_id).order_by(Panel.panel_index.asc())))

    @api.post("/projects/{project_id}/work-items", response_model=WorkItemRead, status_code=status.HTTP_201_CREATED)
    def create_work_item(project_id: int, payload: WorkItemCreate, current_user: CurrentUser, db: DbSession) -> WorkItem:
        project = require_project_access(db, current_user.id, project_id, PROJECT_WRITE_ROLES)
        if payload.assignee_id is not None:
            require_team_membership(db, payload.assignee_id, project.team_id)
        work_item = WorkItem(
            team_id=project.team_id,
            project_id=project.id,
            title=payload.title,
            stage=payload.stage,
            priority=payload.priority,
            assignee_id=payload.assignee_id,
            checklist=payload.checklist,
            created_by_id=current_user.id,
        )
        db.add(work_item)
        db.commit()
        db.refresh(work_item)
        return work_item

    @api.get("/projects/{project_id}/work-items", response_model=list[WorkItemRead])
    def list_work_items(project_id: int, current_user: CurrentUser, db: DbSession) -> list[WorkItem]:
        require_project_access(db, current_user.id, project_id)
        return list(db.scalars(select(WorkItem).where(WorkItem.project_id == project_id).order_by(WorkItem.created_at.desc())))

    @api.post("/projects/{project_id}/production-gates", response_model=ProductionGateRead, status_code=status.HTTP_201_CREATED)
    def create_production_gate(
        project_id: int,
        payload: ProductionGateCreate,
        current_user: CurrentUser,
        db: DbSession,
    ) -> ProductionGate:
        project = require_project_access(db, current_user.id, project_id, PROJECT_WRITE_ROLES)
        gate = ProductionGate(
            team_id=project.team_id,
            project_id=project.id,
            gate_type=payload.gate_type,
            scope=payload.scope,
            required_checks=payload.required_checks,
            evidence=payload.evidence,
            created_by_id=current_user.id,
        )
        db.add(gate)
        db.commit()
        db.refresh(gate)
        return gate

    @api.post("/production-gates/{gate_id}/approve", response_model=ProductionGateRead)
    def approve_production_gate(gate_id: int, current_user: CurrentUser, db: DbSession) -> ProductionGate:
        gate = db.get(ProductionGate, gate_id)
        if gate is None:
            raise HTTPException(status_code=404, detail="Production gate not found.")
        require_team_role(db, current_user.id, gate.team_id, {"owner", "admin", "producer", "reviewer"})
        gate.status = "approved"
        gate.approved_by_id = current_user.id
        gate.approved_at = utc_now()
        db.commit()
        db.refresh(gate)
        return gate

    @api.get("/projects/{project_id}/production-gates", response_model=list[ProductionGateRead])
    def list_production_gates(project_id: int, current_user: CurrentUser, db: DbSession) -> list[ProductionGate]:
        require_project_access(db, current_user.id, project_id)
        return list(
            db.scalars(select(ProductionGate).where(ProductionGate.project_id == project_id).order_by(ProductionGate.created_at.desc()))
        )

    @api.post("/projects/{project_id}/ai-jobs", response_model=AIJobRead, status_code=status.HTTP_201_CREATED)
    def create_ai_job(project_id: int, payload: AIJobCreate, current_user: CurrentUser, db: DbSession) -> AIJob:
        project = require_project_access(db, current_user.id, project_id, PROJECT_WRITE_ROLES)
        job = AIJob(
            team_id=project.team_id,
            project_id=project.id,
            job_type=payload.job_type,
            provider=payload.provider,
            input_payload=payload.input_payload,
            created_by_id=current_user.id,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @api.get("/projects/{project_id}/ai-jobs", response_model=list[AIJobRead])
    def list_ai_jobs(project_id: int, current_user: CurrentUser, db: DbSession) -> list[AIJob]:
        require_project_access(db, current_user.id, project_id)
        return list(db.scalars(select(AIJob).where(AIJob.project_id == project_id).order_by(AIJob.created_at.desc())))

    return api

