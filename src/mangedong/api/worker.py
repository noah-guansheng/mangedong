from __future__ import annotations

import threading
import time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from mangedong.api.entities import AIJob, ProductionResource, utc_now
from mangedong.api.services import project_storage, write_export_package, write_mock_wav


def process_job(db: Session, job: AIJob, storage_dir: str | Path) -> AIJob:
    if job.status in {"succeeded", "running"}:
        return job

    job.status = "running"
    job.attempt_count += 1
    job.lease_owner = "local-worker"
    job.leased_at = utc_now()
    db.commit()
    db.refresh(job)

    try:
        output = _run_job(db, job, Path(storage_dir))
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


def claim_queued_jobs(db: Session, storage_dir: str | Path, limit: int = 8) -> list[AIJob]:
    jobs = list(
        db.scalars(
            select(AIJob)
            .where(AIJob.status.in_(["created", "queued"]))
            .order_by(AIJob.created_at.asc())
            .limit(limit)
        )
    )
    return [process_job(db, job, storage_dir) for job in jobs]


def run_worker_forever(session_factory: sessionmaker[Session], storage_dir: Path, stop: threading.Event, interval: float = 1.0) -> None:
    while not stop.wait(timeout=interval):
        db = session_factory()
        try:
            claim_queued_jobs(db, storage_dir)
        except Exception:
            db.rollback()
        finally:
            db.close()


def _run_job(db: Session, job: AIJob, storage_dir: Path) -> dict:
    if job.job_type == "voice_generate":
        path = project_storage(storage_dir, job.project_id, "worker", f"job-{job.id}.wav")
        write_mock_wav(path)
        return {"audio_uri": str(path), "worker": "async"}

    if job.job_type == "export":
        path = project_storage(storage_dir, job.project_id, "worker", f"job-{job.id}.zip")
        write_export_package(path, {"job_id": job.id, "generated_at": utc_now().isoformat()})
        return {"package_uri": str(path), "worker": "async"}

    resource = ProductionResource(
        team_id=job.team_id,
        project_id=job.project_id,
        resource_type=f"job_{job.job_type}",
        status="succeeded",
        data={"job_id": job.id, "input": job.input_payload, "generated_at": utc_now().isoformat(), "worker": "async"},
        created_by_id=job.created_by_id,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return {"resource_id": resource.id, "worker": "async"}
