from __future__ import annotations

import os
from collections.abc import Generator
from html import escape
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
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
from mangedong.api.worker import process_job
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


def record_audit_event(
    db: Session,
    *,
    team_id: int,
    project_id: int | None,
    actor_id: int,
    action: str,
    target_type: str,
    target_id: int,
    metadata: dict | None = None,
) -> ProductionResource:
    return create_resource(
        db,
        team_id=team_id,
        project_id=project_id,
        resource_type="audit_event",
        status="recorded",
        data={
            "actor_id": actor_id,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "metadata": metadata or {},
            "recorded_at": utc_now().isoformat(),
        },
        created_by_id=actor_id,
    )


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
        f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escape(title)}</title>
    <link rel="stylesheet" href="/static/styles.css" />
  </head>
  <body class="server-doc">
    {body}
    <p class="muted"><a href="/app">打开完整工作台</a></p>
  </body>
</html>"""
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
    static_dir = Path(__file__).parent / "static"
    api.mount("/static", StaticFiles(directory=static_dir), name="static")

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.get("/app", response_class=HTMLResponse)
    def workbench_app() -> HTMLResponse:
        return HTMLResponse((Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8"))

    @api.get("/ui/login", response_class=HTMLResponse)
    def login_page() -> HTMLResponse:
        return render_page(
            "mangedong 登录",
            """
<header>
  <p class="kicker">Studio workbench</p>
  <h1>mangedong 工作台</h1>
  <p class="muted">团队/工作室漫画转番剧动画 Web SaaS。完整操作请进入 /app。</p>
</header>
<section>
  <h2>登录</h2>
  <form aria-label="login-form" class="surface">
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
        rows = "".join(
            f'<tr><td>{escape(team.name)}</td><td><a href="/ui/projects?team_id={team.id}">进入项目</a></td></tr>'
            for team in teams
        )
        return render_page(
            "Dashboard",
            f"""
<header>
  <p class="kicker">Overview</p>
  <h1>Dashboard</h1>
  <p class="muted">欢迎，{escape(user.display_name)}。</p>
</header>
<section>
  <h2>团队空间</h2>
  {f'<table class="data-table"><thead><tr><th>团队</th><th></th></tr></thead><tbody>{rows}</tbody></table>' if rows else '<p class="muted">暂无团队。</p>'}
</section>
""",
        )

    @api.get("/ui/projects", response_class=HTMLResponse)
    def projects_page(team_id: int, request: Request, db: DbSession) -> HTMLResponse:
        user = require_cookie_user(request, db)
        require_team_membership(db, user.id, team_id)
        team = db.get(Team, team_id)
        projects = list(db.scalars(select(Project).where(Project.team_id == team_id).order_by(Project.created_at.desc())))
        rows = "".join(
            f'<tr><td>{escape(project.name)}</td><td>{escape(project.status)}</td>'
            f'<td><a href="/ui/projects/{project.id}/production">生产工作台</a></td></tr>'
            for project in projects
        )
        return render_page(
            "项目列表",
            f"""
<header>
  <p class="kicker">Projects</p>
  <h1>{escape(team.name if team else "团队")} 项目</h1>
  <a href="/ui/dashboard">返回 Dashboard</a>
</header>
<section>
  <h2>项目列表</h2>
  {f'<table class="data-table"><thead><tr><th>名称</th><th>状态</th><th></th></tr></thead><tbody>{rows}</tbody></table>' if rows else '<p class="muted">暂无项目。</p>'}
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
  <p class="kicker">Floor</p>
  <h1>{escape(project.name)} 生产工作台</h1>
  <p class="muted">Project Brief：{escape(project.brief.get("ip_name", ""))}</p>
</header>
<section>
  <table class="data-table">
    <thead><tr><th>模块</th><th>数量</th></tr></thead>
    <tbody>
      <tr><td>素材库</td><td>{len(assets)} assets</td></tr>
      <tr><td>章节</td><td>{len(chapters)} chapters</td></tr>
      <tr><td>Work Items</td><td>{len(work_items)} open items</td></tr>
      <tr><td>Production Gates</td><td>{len(gates)} gates</td></tr>
      <tr><td>AI Jobs</td><td>{len(jobs)} jobs</td></tr>
    </tbody>
  </table>
</section>
<section>
  <h2>工作台入口</h2>
  <p><a href="/ui/projects/{project.id}/ai-workflows">AI Workflow Center</a></p>
  <p><a href="/ui/projects/{project.id}/review-export">审核与导出</a></p>
  <p><a href="/ui/projects/{project.id}/color-review">上色审核</a></p>
  <p><a href="/ui/projects/{project.id}/clip-compare">片段对比</a></p>
  <p><a href="/ui/projects/{project.id}/client-review">客户审片</a></p>
  <p><a href="/ui/projects/{project.id}/errors">错误日志</a></p>
  <p><a href="/ui/projects/{project.id}/p2-admin">P2 管理</a></p>
  <p><a href="/ui/projects/{project.id}/ops">运维与 Worker</a></p>
  <p><a href="/app">打开完整 SPA 工作台</a></p>
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
  <p class="kicker">Models</p>
  <h1>AI Workflow Center</h1>
  <p class="muted">{escape(project.name)}。API Key 和 ComfyUI 地址在 /app 的「AI / ComfyUI」页填写。</p>
</header>
<section>
  <table class="data-table">
    <thead><tr><th>配置</th><th>数量</th></tr></thead>
    <tbody>
      <tr><td>AI Providers</td><td>{len(providers)} providers</td></tr>
      <tr><td>ComfyUI Instances</td><td>{len(comfyui_instances)} instances</td></tr>
      <tr><td>Workflow Templates</td><td>{len(workflows)} workflows</td></tr>
    </tbody>
  </table>
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
  <p class="kicker">QC</p>
  <h1>审核与导出</h1>
  <p class="muted">{escape(project.name)}</p>
</header>
<section>
  <table class="data-table">
    <thead><tr><th>对象</th><th>数量</th></tr></thead>
    <tbody>
      <tr><td>Review Comments</td><td>{len(comments)} comments</td></tr>
      <tr><td>QC Reports</td><td>{len(qc_reports)} reports</td></tr>
      <tr><td>Export Packages</td><td>{len(exports)} exports</td></tr>
    </tbody>
  </table>
</section>
""",
        )

    @api.get("/ui/projects/{project_id}/color-review", response_class=HTMLResponse)
    def color_review_page(project_id: int, request: Request, db: DbSession) -> HTMLResponse:
        user = require_cookie_user(request, db)
        project = require_project_access(db, user.id, project_id)
        colorizations = list_project_resources(db, project.id, "colorization")
        corrections = list_project_resources(db, project.id, "local_correction")
        comparisons = list_project_resources(db, project.id, "color_comparison")
        return render_page(
            "上色审核",
            f"""
<header><p class="kicker">Paint</p><h1>上色审核</h1><p class="muted">{escape(project.name)}</p></header>
<section>
  <table class="data-table">
    <thead><tr><th>对象</th><th>数量</th></tr></thead>
    <tbody>
      <tr><td>Colorizations</td><td>{len(colorizations)} versions</td></tr>
      <tr><td>Local Corrections</td><td>{len(corrections)} corrections</td></tr>
      <tr><td>Color Comparisons</td><td>{len(comparisons)} comparisons</td></tr>
    </tbody>
  </table>
</section>
""",
        )

    @api.get("/ui/projects/{project_id}/clip-compare", response_class=HTMLResponse)
    def clip_compare_page(project_id: int, request: Request, db: DbSession) -> HTMLResponse:
        user = require_cookie_user(request, db)
        project = require_project_access(db, user.id, project_id)
        clips = list_project_resources(db, project.id, "video_clip")
        comparisons = list_project_resources(db, project.id, "clip_comparison")
        return render_page(
            "片段对比",
            f"""
<header><p class="kicker">Editorial</p><h1>片段对比</h1><p class="muted">{escape(project.name)}</p></header>
<section>
  <table class="data-table">
    <thead><tr><th>对象</th><th>数量</th></tr></thead>
    <tbody>
      <tr><td>Video Clips</td><td>{len(clips)} clips</td></tr>
      <tr><td>A/B Comparisons</td><td>{len(comparisons)} comparisons</td></tr>
    </tbody>
  </table>
</section>
""",
        )

    @api.get("/ui/projects/{project_id}/client-review", response_class=HTMLResponse)
    def client_review_page(project_id: int, request: Request, db: DbSession) -> HTMLResponse:
        user = require_cookie_user(request, db)
        project = require_project_access(db, user.id, project_id)
        packages = list_project_resources(db, project.id, "review_package")
        revisions = list_project_resources(db, project.id, "revision_request")
        acceptances = list_project_resources(db, project.id, "acceptance_record")
        return render_page(
            "客户审片",
            f"""
<header><p class="kicker">Delivery</p><h1>客户审片</h1><p class="muted">{escape(project.name)}</p></header>
<section>
  <table class="data-table">
    <thead><tr><th>对象</th><th>数量</th></tr></thead>
    <tbody>
      <tr><td>Review Packages</td><td>{len(packages)} packages</td></tr>
      <tr><td>Revision Requests</td><td>{len(revisions)} requests</td></tr>
      <tr><td>Acceptance Records</td><td>{len(acceptances)} records</td></tr>
    </tbody>
  </table>
</section>
""",
        )

    @api.get("/ui/projects/{project_id}/errors", response_class=HTMLResponse)
    def error_logs_page(project_id: int, request: Request, db: DbSession) -> HTMLResponse:
        user = require_cookie_user(request, db)
        project = require_project_access(db, user.id, project_id)
        errors = list_project_resources(db, project.id, "error_log")
        return render_page(
            "错误日志",
            f"""
<header><p class="kicker">Inbox</p><h1>错误日志</h1><p class="muted">{escape(project.name)}</p></header>
<section>
  <table class="data-table">
    <thead><tr><th>对象</th><th>数量</th></tr></thead>
    <tbody>
      <tr><td>Error Logs</td><td>{len(errors)} logs</td></tr>
    </tbody>
  </table>
</section>
""",
        )

    @api.get("/ui/projects/{project_id}/p2-admin", response_class=HTMLResponse)
    def p2_admin_page(project_id: int, request: Request, db: DbSession) -> HTMLResponse:
        user = require_cookie_user(request, db)
        project = require_project_access(db, user.id, project_id)
        private_configs = list_team_resources(db, project.team_id, "private_deployment")
        cloud_pools = list_team_resources(db, project.team_id, "comfyui_cloud_pool")
        training_jobs = list_project_resources(db, project.id, "model_training_job")
        advanced_exports = list_project_resources(db, project.id, "advanced_export")
        return render_page(
            "P2 管理",
            f"""
<header><p class="kicker">Private</p><h1>P2 管理</h1><p class="muted">{escape(project.name)}</p></header>
<section>
  <table class="data-table">
    <thead><tr><th>对象</th><th>数量</th></tr></thead>
    <tbody>
      <tr><td>Private Deployments</td><td>{len(private_configs)} configs</td></tr>
      <tr><td>Cloud ComfyUI Pools</td><td>{len(cloud_pools)} pools</td></tr>
      <tr><td>Model Training Jobs</td><td>{len(training_jobs)} jobs</td></tr>
      <tr><td>Advanced Exports</td><td>{len(advanced_exports)} packages</td></tr>
    </tbody>
  </table>
</section>
""",
        )

    @api.get("/ui/projects/{project_id}/ops", response_class=HTMLResponse)
    def ops_page(project_id: int, request: Request, db: DbSession) -> HTMLResponse:
        user = require_cookie_user(request, db)
        project = require_project_access(db, user.id, project_id)
        jobs = list(db.scalars(select(AIJob).where(AIJob.project_id == project.id).order_by(AIJob.created_at.desc())))
        audit_events = list_project_resources(db, project.id, "audit_event")
        return render_page(
            "运维与 Worker",
            f"""
<header><p class="kicker">Runtime</p><h1>运维与 Worker</h1><p class="muted">{escape(project.name)}</p></header>
<section>
  <table class="data-table">
    <thead><tr><th>对象</th><th>数量</th></tr></thead>
    <tbody>
      <tr><td>AI Jobs</td><td>{len(jobs)} jobs</td></tr>
      <tr><td>Audit Events</td><td>{len(audit_events)} events</td></tr>
      <tr><td>Worker Mode</td><td>local synchronous worker</td></tr>
    </tbody>
  </table>
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

    @api.post("/assets/{asset_id}/download-token", response_model=ProductionResourceRead)
    def create_download_token(asset_id: int, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        asset = db.get(Asset, asset_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="Asset not found.")
        require_project_access(db, current_user.id, asset.project_id)
        return create_resource(
            db,
            team_id=asset.team_id,
            project_id=asset.project_id,
            resource_type="download_token",
            status="active",
            data={"asset_id": asset.id, "uri": asset.uri, "expires_at": utc_now().timestamp() + 900},
            created_by_id=current_user.id,
        )

    @api.get("/downloads/{download_id}")
    def download_asset(download_id: int, db: DbSession) -> FileResponse:
        token = get_resource(db, download_id, "download_token")
        if token.status != "active" or float(token.data["expires_at"]) < utc_now().timestamp():
            raise HTTPException(status_code=410, detail="Download token expired.")
        path = Path(token.data["uri"])
        if not path.exists():
            raise HTTPException(status_code=404, detail="File not found.")
        return FileResponse(path)

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

    @api.post("/projects/{project_id}/imports/pdf", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    async def import_pdf_upload(
        project_id: int,
        request: Request,
        current_user: CurrentUser,
        db: DbSession,
        file: UploadFile = File(...),
        chapter_title: str = Form("Imported PDF Chapter"),
        page_count: int = Form(1),
    ) -> ProductionResource:
        project = require_project_access(db, current_user.id, project_id, PROJECT_WRITE_ROLES)
        filename = safe_filename(file.filename or "manga.pdf")
        upload_path = project_storage(request.app.state.storage_dir, project.id, "imports", filename)
        upload_path.write_bytes(await file.read())
        from PIL import Image, ImageDraw

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
        for index in range(max(1, page_count)):
            image = Image.new("RGB", (480, 680), "white")
            draw = ImageDraw.Draw(image)
            draw.rectangle((24, 24, 456, 320), outline="black", width=4)
            draw.rectangle((24, 360, 456, 656), outline="black", width=4)
            draw.text((48, 48), f"PDF mock page {index + 1}", fill="black")
            page_path = project_storage(request.app.state.storage_dir, project.id, "pages", f"pdf-{chapter.id}-{index + 1}.png")
            image.save(page_path)
            manga_page = MangaPage(
                team_id=project.team_id,
                project_id=project.id,
                chapter_id=chapter.id,
                page_number=index + 1,
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
                bbox={"x": 0, "y": 0, "width": image.width, "height": image.height},
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
            resource_type="pdf_import",
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

    @api.patch("/panels/{panel_id}/manual-correction", response_model=PanelRead)
    def correct_panel(panel_id: int, payload: ResourcePayload, current_user: CurrentUser, db: DbSession) -> Panel:
        panel = require_panel_access(db, current_user.id, panel_id, PROJECT_WRITE_ROLES)
        if "bbox" in payload.data:
            panel.bbox = payload.data["bbox"]
        panel.status = payload.data.get("status", "manually_corrected")
        db.commit()
        db.refresh(panel)
        create_resource(
            db,
            team_id=panel.team_id,
            project_id=panel.project_id,
            resource_type="panel_correction",
            status="applied",
            data={"panel_id": panel.id, "bbox": panel.bbox},
            created_by_id=current_user.id,
        )
        return panel

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

    @api.post("/ai-jobs/{job_id}/run", response_model=AIJobRead)
    def run_ai_job(job_id: int, request: Request, current_user: CurrentUser, db: DbSession) -> AIJob:
        job = db.get(AIJob, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="AI job not found.")
        require_project_access(db, current_user.id, job.project_id, PROJECT_WRITE_ROLES)
        processed = process_job(db, job, request.app.state.storage_dir)
        record_audit_event(
            db,
            team_id=processed.team_id,
            project_id=processed.project_id,
            actor_id=current_user.id,
            action="ai_job.run",
            target_type="ai_job",
            target_id=processed.id,
        )
        return processed

    @api.post("/ai-jobs/{job_id}/retry", response_model=AIJobRead)
    def retry_ai_job(job_id: int, current_user: CurrentUser, db: DbSession) -> AIJob:
        job = db.get(AIJob, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="AI job not found.")
        require_project_access(db, current_user.id, job.project_id, PROJECT_WRITE_ROLES)
        job.status = "queued"
        job.last_error = None
        job.lease_owner = None
        db.commit()
        db.refresh(job)
        record_audit_event(
            db,
            team_id=job.team_id,
            project_id=job.project_id,
            actor_id=current_user.id,
            action="ai_job.retry",
            target_type="ai_job",
            target_id=job.id,
        )
        return job

    @api.post("/ai-jobs/{job_id}/cancel", response_model=AIJobRead)
    def cancel_ai_job(job_id: int, current_user: CurrentUser, db: DbSession) -> AIJob:
        job = db.get(AIJob, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="AI job not found.")
        require_project_access(db, current_user.id, job.project_id, PROJECT_WRITE_ROLES)
        if job.status == "succeeded":
            raise HTTPException(status_code=409, detail="Succeeded jobs cannot be cancelled.")
        job.status = "cancelled"
        job.lease_owner = None
        db.commit()
        db.refresh(job)
        record_audit_event(
            db,
            team_id=job.team_id,
            project_id=job.project_id,
            actor_id=current_user.id,
            action="ai_job.cancel",
            target_type="ai_job",
            target_id=job.id,
        )
        return job

    @api.post("/projects/{project_id}/ai-jobs/run-pending", response_model=list[AIJobRead])
    def run_pending_ai_jobs(project_id: int, request: Request, current_user: CurrentUser, db: DbSession) -> list[AIJob]:
        require_project_access(db, current_user.id, project_id, PROJECT_WRITE_ROLES)
        jobs = list(
            db.scalars(
                select(AIJob)
                .where(AIJob.project_id == project_id, AIJob.status.in_(["created", "queued", "failed"]))
                .order_by(AIJob.created_at.asc())
            )
        )
        processed_jobs = [process_job(db, job, request.app.state.storage_dir) for job in jobs]
        record_audit_event(
            db,
            team_id=processed_jobs[0].team_id if processed_jobs else require_project_access(db, current_user.id, project_id).team_id,
            project_id=project_id,
            actor_id=current_user.id,
            action="ai_job.run_pending",
            target_type="project",
            target_id=project_id,
            metadata={"processed_count": len(processed_jobs)},
        )
        return processed_jobs

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

    @api.post("/teams/{team_id}/private-deployments", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_private_deployment_config(team_id: int, payload: ResourcePayload, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        require_team_role(db, current_user.id, team_id, MANAGE_TEAM_ROLES)
        return create_resource(
            db,
            team_id=team_id,
            project_id=None,
            resource_type="private_deployment",
            status="planned",
            data={"deployment_mode": payload.data.get("deployment_mode", "single_tenant"), **payload.data},
            created_by_id=current_user.id,
        )

    @api.post("/teams/{team_id}/comfyui/cloud-pools", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_comfyui_cloud_pool(team_id: int, payload: ResourcePayload, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        require_team_role(db, current_user.id, team_id, MANAGE_TEAM_ROLES)
        return create_resource(
            db,
            team_id=team_id,
            project_id=None,
            resource_type="comfyui_cloud_pool",
            status="mock_ready",
            data={"gpu_profile": payload.data.get("gpu_profile", "mock-gpu"), "max_instances": payload.data.get("max_instances", 1)},
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

    @api.patch("/workflows/{workflow_id}/parameters", response_model=ProductionResourceRead)
    def update_workflow_parameters(
        workflow_id: int,
        payload: ResourcePayload,
        current_user: CurrentUser,
        db: DbSession,
    ) -> ProductionResource:
        workflow = get_resource(db, workflow_id, "workflow")
        require_project_access(db, current_user.id, workflow.project_id or 0, PROJECT_WRITE_ROLES)
        published = {**workflow.data.get("published_parameters", {}), **payload.data}
        workflow.data = {**workflow.data, "published_parameters": published, "parsed": parse_workflow(workflow.data["workflow_json"], published)}
        workflow.status = "parsed"
        db.commit()
        db.refresh(workflow)
        return workflow

    @api.patch("/workflows/{workflow_id}/canvas", response_model=ProductionResourceRead)
    def update_workflow_canvas(workflow_id: int, payload: ResourcePayload, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        workflow = get_resource(db, workflow_id, "workflow")
        require_project_access(db, current_user.id, workflow.project_id or 0, PROJECT_WRITE_ROLES)
        workflow.data = {**workflow.data, "canvas": payload.data}
        workflow.status = "canvas_updated"
        db.commit()
        db.refresh(workflow)
        return workflow

    @api.get("/projects/{project_id}/workflows", response_model=list[ProductionResourceRead])
    def list_workflows(project_id: int, current_user: CurrentUser, db: DbSession) -> list[ProductionResource]:
        require_project_access(db, current_user.id, project_id)
        return list_project_resources(db, project_id, "workflow")

    @api.post("/projects/{project_id}/storage/presign", response_model=ProductionResourceRead)
    def create_storage_intent(project_id: int, payload: ResourcePayload, request: Request, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        project = require_project_access(db, current_user.id, project_id, PROJECT_WRITE_ROLES)
        filename = safe_filename(str(payload.data.get("filename", "upload.bin")))
        path = project_storage(request.app.state.storage_dir, project.id, "presigned", filename)
        return create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="storage_intent",
            status="ready",
            data={"upload_uri": str(path), "method": "local_put", "expires_in_seconds": 900},
            created_by_id=current_user.id,
        )

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

    @api.post("/projects/{project_id}/color-profiles", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_color_profile(project_id: int, payload: ResourcePayload, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        project = require_project_access(db, current_user.id, project_id, PROJECT_WRITE_ROLES)
        return create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="color_profile",
            status="approved",
            data=payload.data,
            created_by_id=current_user.id,
        )

    @api.post("/projects/{project_id}/color-strategies/apply", response_model=ProductionResourceRead)
    def apply_color_strategy(project_id: int, payload: ResourcePayload, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        project = require_project_access(db, current_user.id, project_id, PROJECT_WRITE_ROLES)
        return create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="color_strategy",
            status="applied",
            data={
                "scope": payload.data.get("scope", "project"),
                "reference_priority": payload.data.get("reference_priority", ["character_sheet", "approved_profile", "colored_page"]),
                "conflict_policy": payload.data.get("conflict_policy", "require_confirmation"),
            },
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

    @api.post("/colorizations/{colorization_id}/local-corrections", response_model=ProductionResourceRead)
    def create_local_correction(
        colorization_id: int,
        payload: ResourcePayload,
        request: Request,
        current_user: CurrentUser,
        db: DbSession,
    ) -> ProductionResource:
        colorization = get_resource(db, colorization_id, "colorization")
        require_project_access(db, current_user.id, colorization.project_id or 0, PROJECT_WRITE_ROLES)
        from PIL import Image, ImageEnhance

        source = Image.open(colorization.data["output_asset_uri"]).convert("RGB")
        corrected = ImageEnhance.Color(source).enhance(float(payload.data.get("saturation", 1.15)))
        corrected = ImageEnhance.Brightness(corrected).enhance(float(payload.data.get("brightness", 1.03)))
        output_path = project_storage(request.app.state.storage_dir, colorization.project_id or 0, "corrections", f"colorization-{colorization.id}.png")
        corrected.save(output_path)
        return create_resource(
            db,
            team_id=colorization.team_id,
            project_id=colorization.project_id,
            resource_type="local_correction",
            status="accepted",
            data={"source_colorization_id": colorization.id, "output_asset_uri": str(output_path), "adjustments": payload.data},
            created_by_id=current_user.id,
        )

    @api.post("/colorizations/{colorization_id}/compare", response_model=ProductionResourceRead)
    def compare_color_versions(
        colorization_id: int,
        payload: ResourcePayload,
        current_user: CurrentUser,
        db: DbSession,
    ) -> ProductionResource:
        base = get_resource(db, colorization_id)
        other_id = int(payload.data["other_resource_id"])
        other = get_resource(db, other_id)
        require_project_access(db, current_user.id, base.project_id or 0)
        if base.project_id != other.project_id:
            raise HTTPException(status_code=400, detail="Cannot compare resources from different projects.")
        return create_resource(
            db,
            team_id=base.team_id,
            project_id=base.project_id,
            resource_type="color_comparison",
            status="completed",
            data={"base_id": base.id, "other_id": other.id, "diff_summary": "mock visual diff completed"},
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

    @api.post("/video-clips/{clip_id}/compare", response_model=ProductionResourceRead)
    def compare_video_clips(clip_id: int, payload: ResourcePayload, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        base = get_resource(db, clip_id, "video_clip")
        other = get_resource(db, int(payload.data["other_clip_id"]), "video_clip")
        require_project_access(db, current_user.id, base.project_id or 0)
        if base.project_id != other.project_id:
            raise HTTPException(status_code=400, detail="Cannot compare clips from different projects.")
        return create_resource(
            db,
            team_id=base.team_id,
            project_id=base.project_id,
            resource_type="clip_comparison",
            status="completed",
            data={
                "base_clip_id": base.id,
                "other_clip_id": other.id,
                "comparison_mode": payload.data.get("mode", "ab_sync"),
                "diff_summary": "mock clip comparison completed",
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

    @api.post("/timelines/{timeline_id}/tracks", response_model=ProductionResourceRead)
    def add_timeline_track(timeline_id: int, payload: ResourcePayload, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        timeline = get_resource(db, timeline_id, "timeline")
        require_project_access(db, current_user.id, timeline.project_id or 0, PROJECT_WRITE_ROLES)
        tracks = [*timeline.data.get("tracks", []), payload.data]
        timeline.data = {**timeline.data, "tracks": tracks}
        timeline.status = "advanced_timeline"
        db.commit()
        db.refresh(timeline)
        return timeline

    @api.post("/timelines/{timeline_id}/keyframes", response_model=ProductionResourceRead)
    def add_timeline_keyframe(timeline_id: int, payload: ResourcePayload, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        timeline = get_resource(db, timeline_id, "timeline")
        require_project_access(db, current_user.id, timeline.project_id or 0, PROJECT_WRITE_ROLES)
        keyframes = [*timeline.data.get("keyframes", []), payload.data]
        timeline.data = {**timeline.data, "keyframes": keyframes}
        timeline.status = "advanced_timeline"
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

    @api.post("/dialogue-lines/{dialogue_line_id}/translations", response_model=ProductionResourceRead)
    def translate_dialogue_line(dialogue_line_id: int, payload: ResourcePayload, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        dialogue = get_resource(db, dialogue_line_id, "dialogue_line")
        require_project_access(db, current_user.id, dialogue.project_id or 0, PROJECT_WRITE_ROLES)
        source_text = str(dialogue.data.get("edited_text") or dialogue.data.get("ocr_text") or "")
        target_languages = payload.data.get("target_languages", ["zh", "ja", "en"])
        translations = {language: f"[{language}] {source_text}" for language in target_languages}
        return create_resource(
            db,
            team_id=dialogue.team_id,
            project_id=dialogue.project_id,
            resource_type="subtitle_translation",
            status="completed",
            data={"dialogue_line_id": dialogue.id, "translations": translations},
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

    @api.post("/projects/{project_id}/collaboration/sessions", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_collaboration_session(project_id: int, payload: ResourcePayload, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        project = require_project_access(db, current_user.id, project_id)
        return create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="collaboration_session",
            status="active",
            data={"participants": payload.data.get("participants", [current_user.id]), **payload.data},
            created_by_id=current_user.id,
        )

    @api.post("/projects/{project_id}/model-training-jobs", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_model_training_job(project_id: int, payload: ResourcePayload, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        project = require_project_access(db, current_user.id, project_id, {"owner", "admin", "producer"})
        return create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="model_training_job",
            status="queued",
            data={"training_type": payload.data.get("training_type", "character_lora"), "mock": True, **payload.data},
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

    @api.post("/projects/{project_id}/review-packages", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_review_package(project_id: int, payload: ResourcePayload, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        project = require_project_access(db, current_user.id, project_id, {"owner", "admin", "producer", "reviewer"})
        return create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="review_package",
            status="internal_reviewing",
            data={"package_type": payload.data.get("package_type", "internal_preview"), **payload.data},
            created_by_id=current_user.id,
        )

    @api.post("/review-packages/{review_package_id}/revision-requests", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_revision_request(
        review_package_id: int,
        payload: ResourcePayload,
        current_user: CurrentUser,
        db: DbSession,
    ) -> ProductionResource:
        package = get_resource(db, review_package_id, "review_package")
        project = require_project_access(db, current_user.id, package.project_id or 0, {"owner", "admin", "producer", "reviewer"})
        return create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="revision_request",
            status="open",
            data={"review_package_id": package.id, "revision_round": payload.data.get("revision_round", 1), **payload.data},
            created_by_id=current_user.id,
        )

    @api.post("/review-packages/{review_package_id}/acceptance-records", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_acceptance_record(
        review_package_id: int,
        payload: ResourcePayload,
        current_user: CurrentUser,
        db: DbSession,
    ) -> ProductionResource:
        package = get_resource(db, review_package_id, "review_package")
        project = require_project_access(db, current_user.id, package.project_id or 0, {"owner", "admin", "producer", "reviewer"})
        package.status = "client_approved"
        record = create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="acceptance_record",
            status="accepted",
            data={"review_package_id": package.id, "accepted_at": utc_now().isoformat(), **payload.data},
            created_by_id=current_user.id,
        )
        db.add(package)
        db.commit()
        return record

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

    @api.post("/projects/{project_id}/error-logs", response_model=ProductionResourceRead, status_code=status.HTTP_201_CREATED)
    def create_error_log(project_id: int, payload: ResourcePayload, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        project = require_project_access(db, current_user.id, project_id)
        return create_resource(
            db,
            team_id=project.team_id,
            project_id=project.id,
            resource_type="error_log",
            status=payload.data.get("severity", "info"),
            data=payload.data,
            created_by_id=current_user.id,
        )

    @api.get("/projects/{project_id}/error-logs", response_model=list[ProductionResourceRead])
    def list_error_logs(project_id: int, current_user: CurrentUser, db: DbSession) -> list[ProductionResource]:
        require_project_access(db, current_user.id, project_id)
        return list_project_resources(db, project_id, "error_log")

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

    @api.post("/exports/{export_id}/advanced-format", response_model=ProductionResourceRead)
    def create_advanced_export_format(export_id: int, payload: ResourcePayload, request: Request, current_user: CurrentUser, db: DbSession) -> ProductionResource:
        export = get_resource(db, export_id, "export")
        require_project_access(db, current_user.id, export.project_id or 0, {"owner", "admin", "producer"})
        package_path = project_storage(
            request.app.state.storage_dir,
            export.project_id or 0,
            "exports",
            f"export-{export.id}-{safe_filename(str(payload.data.get('format', 'prores')))}.zip",
        )
        manifest = {"export_id": export.id, "advanced_format": payload.data.get("format", "prores"), "settings": payload.data}
        write_export_package(package_path, manifest)
        return create_resource(
            db,
            team_id=export.team_id,
            project_id=export.project_id,
            resource_type="advanced_export",
            status="generated",
            data={"package_uri": str(package_path), **manifest},
            created_by_id=current_user.id,
        )

    return api

