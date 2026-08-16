from __future__ import annotations

import os
from collections.abc import Generator
from html import escape
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from mangedong.animate import KenBurnsAnimator
from mangedong.api.db import build_session_factory, init_db, session_scope
from mangedong.api.entities import (
    AIJob,
    Asset,
    Chapter,
    MangaPage,
    Panel,
    ProductionGate,
    ProductionResource,
    Project,
    Team,
    TeamMember,
    User,
    WorkItem,
    utc_now,
)
from mangedong.api.schemas import (
    AIJobCreate,
    AIJobRead,
    AssetCreate,
    AssetRead,
    ChapterCreate,
    ChapterRead,
    ComfyUIInstanceCreate,
    DialogueLineCreate,
    PageCreate,
    PageRead,
    PanelCreate,
    PanelRead,
    ProductionResourceRead,
    ProductionGateCreate,
    ProductionGateRead,
    ProjectCreate,
    ProjectRead,
    ProviderCreate,
    ResourcePayload,
    ReviewCommentCreate,
    ShotCreate,
    TeamCreate,
    TeamMemberCreate,
    TeamMemberRead,
    TeamRead,
    TimelineCreate,
    TimelineItemCreate,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserRead,
    WorkflowCreate,
    WorkItemCreate,
    WorkItemRead,
)
from mangedong.api.security import create_access_token, hash_password, parse_access_token, verify_password
from mangedong.api.services import project_storage, safe_filename, write_export_package, write_mock_wav, write_srt
from mangedong.colorize import AlgorithmicColorizer
from mangedong.export import VideoExporter
from mangedong.importer import import_pages


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


def require_panel_access(db: Session, user_id: int, panel_id: int, allowed_roles: set[str] | None = None) -> Panel:
    panel = db.get(Panel, panel_id)
    if panel is None:
        raise HTTPException(status_code=404, detail="Panel not found.")
    require_project_access(db, user_id, panel.project_id, allowed_roles)
    return panel


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


def create_resource(
    db: Session,
    *,
    team_id: int,
    project_id: int | None,
    resource_type: str,
    status: str,
    data: dict,
    created_by_id: int,
) -> ProductionResource:
    resource = ProductionResource(
        team_id=team_id,
        project_id=project_id,
        resource_type=resource_type,
        status=status,
        data=data,
        created_by_id=created_by_id,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


def list_project_resources(db: Session, project_id: int, resource_type: str) -> list[ProductionResource]:
    return list(
        db.scalars(
            select(ProductionResource)
            .where(ProductionResource.project_id == project_id, ProductionResource.resource_type == resource_type)
            .order_by(ProductionResource.created_at.desc())
        )
    )


def list_team_resources(db: Session, team_id: int, resource_type: str) -> list[ProductionResource]:
    return list(
        db.scalars(
            select(ProductionResource)
            .where(ProductionResource.team_id == team_id, ProductionResource.resource_type == resource_type)
            .order_by(ProductionResource.created_at.desc())
        )
    )


def get_resource(db: Session, resource_id: int, resource_type: str | None = None) -> ProductionResource:
    resource = db.get(ProductionResource, resource_id)
    if resource is None or (resource_type is not None and resource.resource_type != resource_type):
        raise HTTPException(status_code=404, detail="Resource not found.")
    return resource


def parse_workflow(workflow_json: dict, published_parameters: dict) -> dict:
    if "nodes" in workflow_json:
        node_count = len(workflow_json.get("nodes", []))
        workflow_format = "ui"
    else:
        node_count = len(workflow_json)
        workflow_format = "api"
    detected_inputs = sorted(published_parameters.keys()) if published_parameters else []
    return {
        "format": workflow_format,
        "node_count": node_count,
        "published_parameter_keys": detected_inputs,
        "production_ready_checks": {
            "json_valid": True,
            "output_bound": bool(published_parameters.get("output") or node_count > 0),
            "test_run_required": True,
        },
    }


def resolve_review_project_id(db: Session, object_type: str, object_id: int) -> int:
    if object_type == "project":
        project = db.get(Project, object_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Review target not found.")
        return project.id
    if object_type == "panel":
        panel = db.get(Panel, object_id)
        if panel is None:
            raise HTTPException(status_code=404, detail="Review target not found.")
        return panel.project_id
    resource = db.get(ProductionResource, object_id)
    if resource is None or resource.project_id is None:
        raise HTTPException(status_code=404, detail="Review target not found.")
    return resource.project_id


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


def create_app(database_url: str | None = None, secret_key: str | None = None, storage_dir: str | Path | None = None) -> FastAPI:
    session_factory = build_session_factory(database_url or os.getenv("MANGEDONG_DATABASE_URL", DEFAULT_DATABASE_URL))
    init_db(session_factory)

    api = FastAPI(title="mangedong Web SaaS API", version="0.1.0")
    api.state.session_factory = session_factory
    api.state.secret_key = secret_key or os.getenv("MANGEDONG_SECRET_KEY", "dev-secret-change-me")
    api.state.storage_dir = Path(storage_dir or os.getenv("MANGEDONG_STORAGE_DIR", "./mangedong_storage")).resolve()
    api.state.storage_dir.mkdir(parents=True, exist_ok=True)

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
<section>
  <h2>工作台入口</h2>
  <a href="/ui/projects/{project.id}/ai-workflows">AI Workflow Center</a>
  <a href="/ui/projects/{project.id}/review-export">审核与导出</a>
</section>
""",
        )

    @api.get("/ui/projects/{project_id}/ai-workflows", response_class=HTMLResponse)
    def ai_workflows_page(project_id: int, request: Request, db: DbSession) -> HTMLResponse:
        user = require_cookie_user(request, db)
        project = require_project_access(db, user.id, project_id)
        providers = list_team_resources(db, project.team_id, "ai_provider")
        comfyui_instances = list_team_resources(db, project.team_id, "comfyui_instance")
        workflows = list_project_resources(db, project.id, "workflow")
        return render_page(
            "AI Workflow Center",
            f"""
<header>
  <h1>AI Workflow Center</h1>
  <p class="muted">{escape(project.name)}</p>
</header>
<section class="grid">
  <div class="card"><h2>AI Providers</h2><p>{len(providers)} providers</p></div>
  <div class="card"><h2>ComfyUI Instances</h2><p>{len(comfyui_instances)} instances</p></div>
  <div class="card"><h2>Workflow Templates</h2><p>{len(workflows)} workflows</p></div>
</section>
""",
        )

    @api.get("/ui/projects/{project_id}/review-export", response_class=HTMLResponse)
    def review_export_page(project_id: int, request: Request, db: DbSession) -> HTMLResponse:
        user = require_cookie_user(request, db)
        project = require_project_access(db, user.id, project_id)
        comments = list_project_resources(db, project.id, "review_comment")
        qc_reports = list_project_resources(db, project.id, "qc_report")
        exports = list_project_resources(db, project.id, "export")
        return render_page(
            "审核与导出",
            f"""
<header>
  <h1>审核与导出</h1>
  <p class="muted">{escape(project.name)}</p>
</header>
<section class="grid">
  <div class="card"><h2>Review Comments</h2><p>{len(comments)} comments</p></div>
  <div class="card"><h2>QC Reports</h2><p>{len(qc_reports)} reports</p></div>
  <div class="card"><h2>Export Packages</h2><p>{len(exports)} exports</p></div>
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

    @api.post("/projects/{project_id}/uploads", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
    async def upload_asset(
        project_id: int,
        request: Request,
        current_user: CurrentUser,
        db: DbSession,
        file: UploadFile = File(...),
        asset_type: str = Form("manga_page"),
    ) -> Asset:
        project = require_project_access(db, current_user.id, project_id, PROJECT_WRITE_ROLES)
        filename = safe_filename(file.filename or "upload.bin")
        path = project_storage(request.app.state.storage_dir, project.id, "uploads", filename)
        path.write_bytes(await file.read())
        asset = Asset(
            team_id=project.team_id,
            project_id=project.id,
            name=filename,
            asset_type=asset_type,
            uri=str(path),
            asset_metadata={"content_type": file.content_type},
            created_by_id=current_user.id,
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset

    @api.post("/projects/{project_id}/imports/manga", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    async def import_manga_upload(
        project_id: int,
        request: Request,
        current_user: CurrentUser,
        db: DbSession,
        file: UploadFile = File(...),
        chapter_title: str = Form("Imported Chapter"),
    ) -> ProductionResource:
        project = require_project_access(db, current_user.id, project_id, PROJECT_WRITE_ROLES)
        filename = safe_filename(file.filename or "manga.png")
        upload_path = project_storage(request.app.state.storage_dir, project.id, "imports", filename)
        upload_path.write_bytes(await file.read())
        pages = import_pages(upload_path)
        chapter = Chapter(
            team_id=project.team_id,
            project_id=project.id,
            title=chapter_title,
            source_language=project.brief.get("target_languages", ["zh"])[0],
            status="imported",
            created_by_id=current_user.id,
        )
        db.add(chapter)
        db.flush()
        created_pages = []
        for page in pages:
            page_path = project_storage(request.app.state.storage_dir, project.id, "pages", f"{chapter.id}-{page.page_index + 1}.png")
            page.image.save(page_path)
            manga_page = MangaPage(
                team_id=project.team_id,
                project_id=project.id,
                chapter_id=chapter.id,
                page_number=page.page_index + 1,
                image_uri=str(page_path),
                created_by_id=current_user.id,
            )
            db.add(manga_page)
            db.flush()
            panel = Panel(
                team_id=project.team_id,
                project_id=project.id,
                chapter_id=chapter.id,
                page_id=manga_page.id,
                panel_index=1,
                bbox={"x": 0, "y": 0, "width": page.image.width, "height": page.image.height},
                created_by_id=current_user.id,
            )
            db.add(panel)
            db.flush()
            created_pages.append({"page_id": manga_page.id, "panel_id": panel.id, "image_uri": str(page_path)})
        db.commit()
        return create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="import",
            status="succeeded",
            data={"chapter_id": chapter.id, "page_count": len(created_pages), "pages": created_pages, "source_uri": str(upload_path)},
            created_by_id=current_user.id,
        )

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

    @api.post("/teams/{team_id}/ai-providers", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_ai_provider(
        team_id: int,
        payload: ProviderCreate,
        current_user: CurrentUser,
        db: DbSession,
    ) -> ProductionResource:
        require_team_role(db, current_user.id, team_id, MANAGE_TEAM_ROLES)
        return create_resource(
            db,
            team_id=team_id,
            project_id=None,
            resource_type="ai_provider",
            status="active",
            data=payload.model_dump(mode="json"),
            created_by_id=current_user.id,
        )

    @api.get("/teams/{team_id}/ai-providers", response_model=list[ProductionResourceRead])
    def list_ai_providers(team_id: int, current_user: CurrentUser, db: DbSession) -> list[ProductionResource]:
        require_team_membership(db, current_user.id, team_id)
        return list_team_resources(db, team_id, "ai_provider")

    @api.post("/teams/{team_id}/comfyui/instances", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_comfyui_instance(
        team_id: int,
        payload: ComfyUIInstanceCreate,
        current_user: CurrentUser,
        db: DbSession,
    ) -> ProductionResource:
        require_team_role(db, current_user.id, team_id, MANAGE_TEAM_ROLES)
        instance_data = payload.model_dump(mode="json")
        instance_data["health"] = {"status": "unchecked"}
        return create_resource(
            db,
            team_id=team_id,
            project_id=None,
            resource_type="comfyui_instance",
            status="configured",
            data=instance_data,
            created_by_id=current_user.id,
        )

    @api.post("/comfyui/instances/{instance_id}/health-check", response_model=ProductionResourceRead)
    def check_comfyui_instance(instance_id: int, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        instance = get_resource(db, instance_id, "comfyui_instance")
        require_team_role(db, current_user.id, instance.team_id, MANAGE_TEAM_ROLES)
        instance.data = {**instance.data, "health": {"status": "ok", "checked_at": utc_now().isoformat()}}
        instance.status = "healthy"
        db.commit()
        db.refresh(instance)
        return instance

    @api.post("/projects/{project_id}/workflows", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_workflow(
        project_id: int,
        payload: WorkflowCreate,
        current_user: CurrentUser,
        db: DbSession,
    ) -> ProductionResource:
        project = require_project_access(db, current_user.id, project_id, PROJECT_WRITE_ROLES)
        parsed = parse_workflow(payload.workflow_json, payload.published_parameters)
        return create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="workflow",
            status="parsed",
            data={**payload.model_dump(mode="json"), "parsed": parsed},
            created_by_id=current_user.id,
        )

    @api.post("/workflows/{workflow_id}/test-run", response_model=ProductionResourceRead)
    def test_run_workflow(workflow_id: int, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        workflow = get_resource(db, workflow_id, "workflow")
        if workflow.project_id is None:
            raise HTTPException(status_code=400, detail="Workflow is not project scoped.")
        require_project_access(db, current_user.id, workflow.project_id, PROJECT_WRITE_ROLES)
        workflow.status = "production_ready"
        workflow.data = {
            **workflow.data,
            "test_run": {"status": "succeeded", "checked_at": utc_now().isoformat(), "output_type": "mock_asset"},
        }
        db.commit()
        db.refresh(workflow)
        return workflow

    @api.get("/projects/{project_id}/workflows", response_model=list[ProductionResourceRead])
    def list_workflows(project_id: int, current_user: CurrentUser, db: DbSession) -> list[ProductionResource]:
        require_project_access(db, current_user.id, project_id)
        return list_project_resources(db, project_id, "workflow")

    @api.post("/projects/{project_id}/references", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_reference(project_id: int, payload: ResourcePayload, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        project = require_project_access(db, current_user.id, project_id, PROJECT_WRITE_ROLES)
        return create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="reference_image",
            status="uploaded",
            data=payload.data,
            created_by_id=current_user.id,
        )

    @api.post("/projects/{project_id}/characters", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_character(project_id: int, payload: ResourcePayload, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        project = require_project_access(db, current_user.id, project_id, PROJECT_WRITE_ROLES)
        return create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="character",
            status="draft",
            data=payload.data,
            created_by_id=current_user.id,
        )

    @api.post("/panels/{panel_id}/ocr", response_model=ProductionResourceRead)
    def run_panel_ocr(panel_id: int, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        panel = require_panel_access(db, current_user.id, panel_id, PROJECT_WRITE_ROLES)
        return create_resource(
            db,
            team_id=panel.team_id,
            project_id=panel.project_id,
            resource_type="dialogue_line",
            status="ocr_draft",
            data={"panel_id": panel.id, "ocr_text": "示例台词", "source_language": "zh", "confidence": 0.82},
            created_by_id=current_user.id,
        )

    @api.post("/panels/{panel_id}/analyze", response_model=ProductionResourceRead)
    def analyze_panel(panel_id: int, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        panel = require_panel_access(db, current_user.id, panel_id, PROJECT_WRITE_ROLES)
        return create_resource(
            db,
            team_id=panel.team_id,
            project_id=panel.project_id,
            resource_type="analysis",
            status="succeeded",
            data={
                "panel_id": panel.id,
                "scene": "cinematic manga panel",
                "action": "character reacts",
                "camera": "slow zoom in",
                "prompt": "anime cinematic shot, clean line art, expressive acting",
            },
            created_by_id=current_user.id,
        )

    @api.post("/panels/{panel_id}/colorize", response_model=ProductionResourceRead)
    def colorize_panel(panel_id: int, payload: ResourcePayload, request: Request, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        panel = require_panel_access(db, current_user.id, panel_id, PROJECT_WRITE_ROLES)
        page = db.get(MangaPage, panel.page_id)
        if page is None:
            raise HTTPException(status_code=404, detail="Page not found.")
        from PIL import Image

        image = Image.open(page.image_uri).convert("RGB")
        bbox = panel.bbox
        cropped = image.crop(
            (
                int(bbox.get("x", 0)),
                int(bbox.get("y", 0)),
                int(bbox.get("x", 0)) + int(bbox.get("width", image.width)),
                int(bbox.get("y", 0)) + int(bbox.get("height", image.height)),
            )
        )
        palette = payload.data.get("palette", "cel")
        colorized = AlgorithmicColorizer(palette=palette).colorize(cropped)
        output_path = project_storage(request.app.state.storage_dir, panel.project_id, "colorized", f"panel-{panel.id}.png")
        colorized.save(output_path)
        return create_resource(
            db,
            team_id=panel.team_id,
            project_id=panel.project_id,
            resource_type="colorization",
            status="succeeded",
            data={"panel_id": panel.id, "palette": palette, "output_asset_uri": str(output_path)},
            created_by_id=current_user.id,
        )

    @api.post("/projects/{project_id}/batch-colorize", response_model=ProductionResourceRead)
    def batch_colorize(project_id: int, payload: ResourcePayload, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        project = require_project_access(db, current_user.id, project_id, PROJECT_WRITE_ROLES)
        return create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="batch_colorization",
            status="queued",
            data={"scope": payload.data.get("scope", "project"), "estimated_items": payload.data.get("estimated_items", 0)},
            created_by_id=current_user.id,
        )

    @api.post("/panels/{panel_id}/generate-video", response_model=ProductionResourceRead)
    def generate_panel_video(panel_id: int, payload: ResourcePayload, request: Request, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        panel = require_panel_access(db, current_user.id, panel_id, PROJECT_WRITE_ROLES)
        from PIL import Image

        colorization = next(
            (
                resource
                for resource in list_project_resources(db, panel.project_id, "colorization")
                if resource.data.get("panel_id") == panel.id
            ),
            None,
        )
        if colorization is not None:
            source_image = Image.open(colorization.data["output_asset_uri"]).convert("RGB")
        else:
            page = db.get(MangaPage, panel.page_id)
            if page is None:
                raise HTTPException(status_code=404, detail="Page not found.")
            source_image = AlgorithmicColorizer().colorize(Image.open(page.image_uri).convert("RGB"))
        duration = float(payload.data.get("duration_seconds", 3))
        fps = int(payload.data.get("fps", 8))
        frame_dir = project_storage(request.app.state.storage_dir, panel.project_id, "frames", f"panel-{panel.id}") / "frames"
        frame_paths = KenBurnsAnimator(duration_seconds=duration, fps=fps, width=int(payload.data.get("width", 480))).render_frames(
            source_image,
            frame_dir,
            f"panel_{panel.id}",
        )
        output_path = project_storage(request.app.state.storage_dir, panel.project_id, "videos", f"panel-{panel.id}.mp4")
        VideoExporter().export(frame_paths, output_path, fps=fps)
        return create_resource(
            db,
            team_id=panel.team_id,
            project_id=panel.project_id,
            resource_type="video_clip",
            status="generated",
            data={
                "panel_id": panel.id,
                "provider": payload.data.get("provider", "mock_video"),
                "output_asset_uri": str(output_path),
                "duration_seconds": duration,
                "fps": fps,
                "frame_count": len(frame_paths),
            },
            created_by_id=current_user.id,
        )

    @api.post("/projects/{project_id}/shots", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_shot(project_id: int, payload: ShotCreate, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        project = require_project_access(db, current_user.id, project_id, PROJECT_WRITE_ROLES)
        return create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="shot",
            status="draft",
            data=payload.model_dump(mode="json"),
            created_by_id=current_user.id,
        )

    @api.post("/shots/{shot_id}/generate-animatic", response_model=ProductionResourceRead)
    def generate_animatic(shot_id: int, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        shot = get_resource(db, shot_id, "shot")
        require_project_access(db, current_user.id, shot.project_id or 0, PROJECT_WRITE_ROLES)
        return create_resource(
            db,
            team_id=shot.team_id,
            project_id=shot.project_id,
            resource_type="animatic",
            status="generated",
            data={"shot_id": shot.id, "preview_uri": f"mock://animatics/{shot.id}.mp4"},
            created_by_id=current_user.id,
        )

    @api.post("/projects/{project_id}/timelines", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_timeline(project_id: int, payload: TimelineCreate, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        project = require_project_access(db, current_user.id, project_id, PROJECT_WRITE_ROLES)
        return create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="timeline",
            status="draft",
            data={"name": payload.name, "items": []},
            created_by_id=current_user.id,
        )

    @api.post("/timelines/{timeline_id}/items", response_model=ProductionResourceRead)
    def add_timeline_item(timeline_id: int, payload: TimelineItemCreate, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        timeline = get_resource(db, timeline_id, "timeline")
        require_project_access(db, current_user.id, timeline.project_id or 0, PROJECT_WRITE_ROLES)
        items = [*timeline.data.get("items", []), payload.model_dump(mode="json")]
        timeline.data = {**timeline.data, "items": items}
        db.commit()
        db.refresh(timeline)
        return timeline

    @api.post("/shots/{shot_id}/dialogue-lines", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_dialogue_line(shot_id: int, payload: DialogueLineCreate, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        shot = get_resource(db, shot_id, "shot")
        require_project_access(db, current_user.id, shot.project_id or 0, PROJECT_WRITE_ROLES)
        return create_resource(
            db,
            team_id=shot.team_id,
            project_id=shot.project_id,
            resource_type="dialogue_line",
            status="approved",
            data={**payload.model_dump(mode="json"), "shot_id": shot.id},
            created_by_id=current_user.id,
        )

    @api.post("/dialogue-lines/{dialogue_line_id}/voice", response_model=ProductionResourceRead)
    def generate_voice_line(
        dialogue_line_id: int,
        payload: ResourcePayload,
        request: Request,
        current_user: CurrentUser,
        db: DbSession,
    ) -> ProductionResource:
        dialogue = get_resource(db, dialogue_line_id, "dialogue_line")
        require_project_access(db, current_user.id, dialogue.project_id or 0, PROJECT_WRITE_ROLES)
        audio_path = project_storage(request.app.state.storage_dir, dialogue.project_id or 0, "voice", f"dialogue-{dialogue.id}.wav")
        write_mock_wav(audio_path, duration_seconds=float(payload.data.get("duration_seconds", 1.2)), frequency=440.0)
        return create_resource(
            db,
            team_id=dialogue.team_id,
            project_id=dialogue.project_id,
            resource_type="voice_line",
            status="generated",
            data={"dialogue_line_id": dialogue.id, "voice": payload.data.get("voice", "default"), "audio_uri": str(audio_path)},
            created_by_id=current_user.id,
        )

    @api.post("/dialogue-lines/{dialogue_line_id}/subtitle", response_model=ProductionResourceRead)
    def create_subtitle_cue(
        dialogue_line_id: int,
        payload: ResourcePayload,
        request: Request,
        current_user: CurrentUser,
        db: DbSession,
    ) -> ProductionResource:
        dialogue = get_resource(db, dialogue_line_id, "dialogue_line")
        require_project_access(db, current_user.id, dialogue.project_id or 0, PROJECT_WRITE_ROLES)
        subtitle_path = project_storage(request.app.state.storage_dir, dialogue.project_id or 0, "subtitles", f"dialogue-{dialogue.id}.srt")
        text = str(payload.data.get("text") or dialogue.data.get("edited_text") or dialogue.data.get("ocr_text") or "")
        write_srt(subtitle_path, text=text, start=float(payload.data.get("start", 0)), end=float(payload.data.get("end", 2)))
        return create_resource(
            db,
            team_id=dialogue.team_id,
            project_id=dialogue.project_id,
            resource_type="subtitle_cue",
            status="approved",
            data={"dialogue_line_id": dialogue.id, "subtitle_uri": str(subtitle_path), **payload.data},
            created_by_id=current_user.id,
        )

    @api.post("/projects/{project_id}/music-cues", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_music_cue(project_id: int, payload: ResourcePayload, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        project = require_project_access(db, current_user.id, project_id, PROJECT_WRITE_ROLES)
        return create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="music_cue",
            status="approved",
            data=payload.data,
            created_by_id=current_user.id,
        )

    @api.post("/projects/{project_id}/audio-mixes", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_audio_mix(project_id: int, payload: ResourcePayload, request: Request, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        project = require_project_access(db, current_user.id, project_id, PROJECT_WRITE_ROLES)
        mix_path = project_storage(request.app.state.storage_dir, project.id, "audio-mixes", "final-mix.wav")
        write_mock_wav(mix_path, duration_seconds=float(payload.data.get("duration_seconds", 2.0)), frequency=330.0)
        return create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="audio_mix",
            status="rendered",
            data={"mix_uri": str(mix_path), **payload.data},
            created_by_id=current_user.id,
        )

    @api.post("/review-comments", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_review_comment(payload: ReviewCommentCreate, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        project_id = resolve_review_project_id(db, payload.object_type, payload.object_id)
        project = require_project_access(db, current_user.id, project_id)
        return create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="review_comment",
            status="open",
            data=payload.model_dump(mode="json"),
            created_by_id=current_user.id,
        )

    @api.post("/projects/{project_id}/qc-reports", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_qc_report(project_id: int, payload: ResourcePayload, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        project = require_project_access(db, current_user.id, project_id, {"owner", "admin", "producer", "reviewer"})
        checks = payload.data.get("checks", {"video_playable": True, "manifest_complete": True, "authorized": True})
        passed = all(bool(value) for value in checks.values())
        return create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="qc_report",
            status="passed" if passed else "failed",
            data={"checks": checks},
            created_by_id=current_user.id,
        )

    @api.post("/projects/{project_id}/exports", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_export(project_id: int, payload: ResourcePayload, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        project = require_project_access(db, current_user.id, project_id, {"owner", "admin", "producer"})
        return create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="export",
            status="draft",
            data={"settings": payload.data, "manifest": {}},
            created_by_id=current_user.id,
        )

    @api.post("/exports/{export_id}/preflight", response_model=ProductionResourceRead)
    def preflight_export(export_id: int, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        export = get_resource(db, export_id, "export")
        require_project_access(db, current_user.id, export.project_id or 0, {"owner", "admin", "producer"})
        export.status = "qc_passed"
        export.data = {
            **export.data,
            "manifest": {
                "export_id": export.id,
                "files": [{"path": "deliverables/final.mp4", "type": "video", "sha256": "mock"}],
                "generated_at": utc_now().isoformat(),
            },
        }
        db.commit()
        db.refresh(export)
        return export

    @api.post("/exports/{export_id}/freeze", response_model=ProductionResourceRead)
    def freeze_export(export_id: int, request: Request, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        export = get_resource(db, export_id, "export")
        require_project_access(db, current_user.id, export.project_id or 0, {"owner", "admin", "producer"})
        if export.status != "qc_passed":
            raise HTTPException(status_code=409, detail="Export must pass preflight before freeze.")
        package_path = project_storage(request.app.state.storage_dir, export.project_id or 0, "exports", f"export-{export.id}.zip")
        write_export_package(package_path, export.data.get("manifest", {}))
        export.status = "frozen"
        export.data = {**export.data, "package_uri": str(package_path)}
        db.commit()
        db.refresh(export)
        return export

    return api

