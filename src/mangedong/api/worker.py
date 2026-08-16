from __future__ import annotations

import os
import socket
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, sessionmaker

from mangedong.api.entities import AIJob, ProductionResource, utc_now
from mangedong.api.services import project_storage, write_export_package, write_mock_wav


DEFAULT_LEASE_TTL_SECONDS = 45
DEFAULT_TEAM_MAX_RUNNING = 8


def worker_id() -> str:
    return os.getenv("MANGEDONG_WORKER_ID") or f"{socket.gethostname()}:{os.getpid()}"


def lease_ttl_seconds() -> int:
    return int(os.getenv("MANGEDONG_LEASE_TTL", str(DEFAULT_LEASE_TTL_SECONDS)))


def process_job(db: Session, job: AIJob, storage_dir: str | Path, owner: str | None = None) -> AIJob:
    if job.status == "succeeded":
        return job
    owner = owner or worker_id()
    reap_expired_leases(db)
    db.refresh(job)
    if job.status == "running" and job.lease_owner == owner:
        return _execute_job(db, job, Path(storage_dir))
    if job.status == "running" and job.lease_owner not in {None, owner} and not _lease_expired(job, _team_lease_ttl(db, job.team_id)):
        return job
    claimed = _try_claim(db, job.id, owner, statuses=("created", "queued", "failed"))
    if claimed is None:
        db.refresh(job)
        return job
    return _execute_job(db, claimed, Path(storage_dir))


def claim_queued_jobs(
    db: Session,
    storage_dir: str | Path,
    limit: int = 8,
    owner: str | None = None,
    team_limits: dict[int, int] | None = None,
) -> list[AIJob]:
    owner = owner or worker_id()
    reap_expired_leases(db)
    if team_limits is None:
        team_limits = load_team_limits(db)
    processed: list[AIJob] = []
    candidates = list(
        db.scalars(
            select(AIJob)
            .where(AIJob.status.in_(["created", "queued"]))
            .order_by(AIJob.created_at.asc())
            .limit(max(limit * 4, limit))
        )
    )
    running_by_team = _running_counts(db)
    for job in candidates:
        if len(processed) >= limit:
            break
        max_running = (team_limits or {}).get(job.team_id, DEFAULT_TEAM_MAX_RUNNING)
        if running_by_team.get(job.team_id, 0) >= max_running:
            continue
        claimed = _try_claim(db, job.id, owner, statuses=("created", "queued"))
        if claimed is None:
            continue
        running_by_team[job.team_id] = running_by_team.get(job.team_id, 0) + 1
        processed.append(_execute_job(db, claimed, Path(storage_dir)))
    return processed


def reap_expired_leases(db: Session) -> int:
    recovered = 0
    ttls = load_team_lease_ttls(db)
    jobs = list(db.scalars(select(AIJob).where(AIJob.status == "running")))
    for job in jobs:
        if _lease_expired(job, ttls.get(job.team_id)):
            job.status = "queued"
            job.lease_owner = None
            recovered += 1
    if recovered:
        db.commit()
    return recovered


def run_worker_forever(
    session_factory: sessionmaker[Session],
    storage_dir: Path,
    stop: threading.Event,
    interval: float = 1.0,
    owner: str | None = None,
) -> None:
    owner = owner or worker_id()
    while not stop.wait(timeout=interval):
        db = session_factory()
        try:
            claim_queued_jobs(db, storage_dir, owner=owner)
        except Exception:
            db.rollback()
        finally:
            db.close()


def queue_snapshot(db: Session) -> dict:
    rows = db.execute(select(AIJob.status, AIJob.team_id, func.count()).group_by(AIJob.status, AIJob.team_id)).all()
    by_status: dict[str, int] = {}
    by_team: dict[str, int] = {}
    for status, team_id, count in rows:
        by_status[str(status)] = by_status.get(str(status), 0) + int(count)
        if status == "running":
            by_team[str(team_id)] = by_team.get(str(team_id), 0) + int(count)
    owners = list(db.scalars(select(AIJob.lease_owner).where(AIJob.status == "running", AIJob.lease_owner.is_not(None)).distinct()))
    return {
        "backend": "database",
        "lease_ttl_seconds": lease_ttl_seconds(),
        "by_status": by_status,
        "running_by_team": by_team,
        "workers": owners,
        "worker_id": worker_id(),
    }


def load_team_limits(db: Session) -> dict[int, int]:
    limits: dict[int, int] = {}
    resources = db.scalars(select(ProductionResource).where(ProductionResource.resource_type == "queue_config"))
    for resource in resources:
        limits[resource.team_id] = int((resource.data or {}).get("max_running") or DEFAULT_TEAM_MAX_RUNNING)
    return limits


def load_team_lease_ttls(db: Session) -> dict[int, int]:
    ttls: dict[int, int] = {}
    resources = db.scalars(select(ProductionResource).where(ProductionResource.resource_type == "queue_config"))
    for resource in resources:
        ttls[resource.team_id] = int((resource.data or {}).get("lease_ttl_seconds") or lease_ttl_seconds())
    return ttls


def _team_lease_ttl(db: Session, team_id: int) -> int:
    return load_team_lease_ttls(db).get(team_id, lease_ttl_seconds())


def _execute_job(db: Session, job: AIJob, storage_dir: Path) -> AIJob:
    try:
        output = _run_job(db, job, storage_dir)
    except Exception as exc:  # pragma: no cover - exercised through API-level failure states.
        job.status = "failed"
        job.last_error = str(exc)
        job.lease_owner = None
        db.commit()
        db.refresh(job)
        return job
    job.output_payload = output
    job.status = "succeeded"
    job.last_error = None
    job.lease_owner = None
    db.commit()
    db.refresh(job)
    return job


def _try_claim(db: Session, job_id: int, owner: str, statuses: tuple[str, ...] = ("created", "queued")) -> AIJob | None:
    result = db.execute(
        update(AIJob)
        .where(AIJob.id == job_id, AIJob.status.in_(statuses))
        .values(
            status="running",
            lease_owner=owner,
            leased_at=utc_now(),
            attempt_count=AIJob.attempt_count + 1,
        )
    )
    db.commit()
    if int(result.rowcount or 0) != 1:
        return None
    return db.get(AIJob, job_id)


def _as_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _lease_expired(job: AIJob, ttl: int | None = None) -> bool:
    if job.leased_at is None:
        return True
    age = _as_naive_utc(utc_now()) - _as_naive_utc(job.leased_at)
    return age > timedelta(seconds=ttl if ttl is not None else lease_ttl_seconds())


def _running_counts(db: Session) -> dict[int, int]:
    rows = db.execute(select(AIJob.team_id, func.count()).where(AIJob.status == "running").group_by(AIJob.team_id)).all()
    return {int(team_id): int(count) for team_id, count in rows}


def _run_job(db: Session, job: AIJob, storage_dir: Path) -> dict:
    if job.job_type == "voice_generate":
        path = project_storage(storage_dir, job.project_id, "worker", f"job-{job.id}.wav")
        write_mock_wav(path)
        return {"audio_uri": str(path), "worker": worker_id(), "queue": "database"}

    if job.job_type == "export":
        path = project_storage(storage_dir, job.project_id, "worker", f"job-{job.id}.zip")
        write_export_package(path, {"job_id": job.id, "generated_at": utc_now().isoformat()})
        return {"package_uri": str(path), "worker": worker_id(), "queue": "database"}

    resource = ProductionResource(
        team_id=job.team_id,
        project_id=job.project_id,
        resource_type=f"job_{job.job_type}",
        status="succeeded",
        data={"job_id": job.id, "input": job.input_payload, "generated_at": utc_now().isoformat(), "worker": worker_id()},
        created_by_id=job.created_by_id,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return {"resource_id": resource.id, "worker": worker_id(), "queue": "database"}
