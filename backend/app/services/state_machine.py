from app.models.domain import AuditLog, Job, JobStatus


ALLOWED_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.CREATED: {JobStatus.EXTRACTING, JobStatus.FAILED},
    JobStatus.EXTRACTING: {JobStatus.CLASSIFIED, JobStatus.FAILED},
    JobStatus.CLASSIFIED: {JobStatus.POLICY_IDENTIFIED, JobStatus.FAILED},
    JobStatus.POLICY_IDENTIFIED: {JobStatus.VALIDATED, JobStatus.FAILED},
    JobStatus.VALIDATED: {JobStatus.REPORT_GENERATED, JobStatus.FAILED},
    JobStatus.REPORT_GENERATED: {JobStatus.HUMAN_REVIEW, JobStatus.FAILED},
    JobStatus.HUMAN_REVIEW: {JobStatus.APPROVED, JobStatus.REJECTED, JobStatus.NEED_INFO, JobStatus.FAILED},
    JobStatus.NEED_INFO: {JobStatus.HUMAN_REVIEW, JobStatus.FAILED},
    JobStatus.APPROVED: set(),
    JobStatus.REJECTED: set(),
    JobStatus.FAILED: set(),
}


def status_of(job: Job) -> JobStatus:
    return JobStatus(job.status)


def transition(job: Job, next_status: JobStatus, *, action: str | None = None) -> AuditLog:
    current = status_of(job)
    if next_status not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"Invalid transition: {current.value} -> {next_status.value}")
    job.status = next_status.value
    return AuditLog(job_id=job.id, action=action or f"{current.value}->{next_status.value}")

