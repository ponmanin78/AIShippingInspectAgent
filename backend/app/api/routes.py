from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import AuditLog, Job, JobStatus, ReviewAction
from app.schemas.api import JobRead, MetricsResponse, ReviewRequest, ReviewResponse, SubmitResponse
from app.services.notifications import NotificationService

router = APIRouter()


async def session_dep(request: Request):
    async with request.app.state.session_factory() as session:
        yield session


@router.post("/submit", response_model=SubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_invoice(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    region: str = Form("US"),
    submitter_email: str | None = Form(None),
    session: AsyncSession = Depends(session_dep),
) -> SubmitResponse:
    storage_dir: Path = request.app.state.settings.storage_dir
    storage_dir.mkdir(parents=True, exist_ok=True)

    job = Job(status=JobStatus.CREATED.value, region=region, file_name=file.filename, submitter_email=submitter_email)
    session.add(job)
    await session.flush()

    safe_name = Path(file.filename or "invoice.bin").name
    file_path = storage_dir / f"{job.id}-{safe_name}"
    with file_path.open("wb") as target:
        shutil.copyfileobj(file.file, target)

    job.file_path = str(file_path)
    session.add(AuditLog(job_id=job.id, action="JOB_CREATED", details={"file_name": file.filename}))
    await session.commit()

    await request.app.state.queue.enqueue(job.id, background_tasks, request.app.state.pipeline)
    return SubmitResponse(job_id=job.id, status=JobStatus.CREATED)


@router.get("/jobs", response_model=list[JobRead])
async def list_jobs(session: AsyncSession = Depends(session_dep)) -> list[Job]:
    result = await session.execute(select(Job).order_by(Job.created_at.desc()))
    return list(result.scalars().all())


@router.get("/jobs/{job_id}", response_model=JobRead)
async def get_job(job_id: str, session: AsyncSession = Depends(session_dep)) -> Job:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail={"error": "JOB_NOT_FOUND", "job_id": job_id})
    return job


@router.post("/review/{job_id}", response_model=ReviewResponse)
async def review_job(
    job_id: str,
    review: ReviewRequest,
    session: AsyncSession = Depends(session_dep),
) -> ReviewResponse:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail={"error": "JOB_NOT_FOUND", "job_id": job_id})
    if JobStatus(job.status) not in {JobStatus.HUMAN_REVIEW, JobStatus.NEED_INFO}:
        raise HTTPException(
            status_code=409,
            detail={"error": "JOB_NOT_REVIEWABLE", "status": job.status},
        )

    notifications = NotificationService()
    if review.action == ReviewAction.APPROVE:
        job.status = JobStatus.APPROVED.value
        notification = await notifications.send_success_email(job)
    elif review.action == ReviewAction.REJECT:
        job.status = JobStatus.REJECTED.value
        notification = await notifications.send_rejection_email(job)
    else:
        job.status = JobStatus.NEED_INFO.value
        notification = await notifications.request_documents(job, review.comments or "Inspector requested more information.")

    session.add(
        AuditLog(
            job_id=job.id,
            action=f"HUMAN_REVIEW_{review.action.value}",
            details={"comments": review.comments, "notification": notification},
        )
    )
    await session.commit()
    await session.refresh(job)
    return ReviewResponse(job=job, notification=notification)


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(session: AsyncSession = Depends(session_dep)) -> MetricsResponse:
    result = await session.execute(select(Job))
    jobs = list(result.scalars().all())
    failure_reasons = Counter(job.error or "Validation failed" for job in jobs if job.status == JobStatus.FAILED.value)
    pass_count = sum(1 for job in jobs if (job.validation_result or {}).get("passed") is True)
    fail_count = sum(1 for job in jobs if (job.validation_result or {}).get("passed") is False)

    return MetricsResponse(
        total_requests=len(jobs),
        approved=sum(1 for job in jobs if job.status == JobStatus.APPROVED.value),
        rejected=sum(1 for job in jobs if job.status == JobStatus.REJECTED.value),
        failed=sum(1 for job in jobs if job.status == JobStatus.FAILED.value),
        pending_reviews=sum(1 for job in jobs if job.status == JobStatus.HUMAN_REVIEW.value),
        pass_count=pass_count,
        fail_count=fail_count,
        failure_reasons=[{"reason": reason, "count": count} for reason, count in failure_reasons.items()],
    )

