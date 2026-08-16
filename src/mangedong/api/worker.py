from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from mangedong.api.entities import AIJob, ProductionResource, utc_now
from mangedong.api.services import project_storage, write_export_package, write_mock_wav


def process_job(db: Session, job: AIJob, storage_dir: str | Path) -> AIJob:
    if job.status in {"succeeded", "running"}:
        return job

    job.status = "running"
    db.commit()
    db.refresh(job)

    output = _run_job(db, job, Path(storage_dir))
    job.output_payload = output
    job.status = "succeeded"
    db.commit()
    db.refresh(job)
    return job


def _run_job(db: Session, job: AIJob, storage_dir: Path) -> dict:
    if job.job_type == "voice_generate":
        path = project_storage(storage_dir, job.project_id, "worker", f"job-{job.id}.wav")
        write_mock_wav(path)
        return {"audio_uri": str(path)}

    if job.job_type == "export":
        path = project_storage(storage_dir, job.project_id, "worker", f"job-{job.id}.zip")
        write_export_package(path, {"job_id": job.id, "generated_at": utc_now().isoformat()})
        return {"package_uri": str(path)}

    resource = ProductionResource(
        team_id=job.team_id,
        project_id=job.project_id,
        resource_type=f"job_{job.job_type}",
        status="succeeded",
        data={"job_id": job.id, "input": job.input_payload, "generated_at": utc_now().isoformat()},
        created_by_id=job.created_by_id,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return {"resource_id": resource.id}
