from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.models.domain import AuditLog, Job, JobStatus
from app.services.agents import classify_invoice, generate_report, retrieve_policies, validate_compliance
from app.services.notifications import NotificationService
from app.services.ocr import extract_text
from app.services.openai_json import JSONLLMClient
from app.services.state_machine import transition
from app.services.vector_store import SQLPolicyVectorStore


class InspectionPipeline:
    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        llm: JSONLLMClient,
        notifications: NotificationService,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.llm = llm
        self.notifications = notifications

    async def process_job(self, job_id: str) -> None:
        async with self.session_factory() as session:
            job = await self._load_job(session, job_id)
            try:
                await self._set_status(session, job, JobStatus.EXTRACTING)
                job.extracted_text = await extract_text(job.file_path or "")
                session.add(AuditLog(job_id=job.id, action="TEXT_EXTRACTED"))
                await session.commit()

                classification = await classify_invoice(job.extracted_text, self.llm)
                await self._set_status(session, job, JobStatus.CLASSIFIED)
                job.fleet_type = classification["fleet_type"]
                session.add(AuditLog(job_id=job.id, action="INVOICE_CLASSIFIED", details=classification))
                await session.commit()

                await self._set_status(session, job, JobStatus.POLICY_IDENTIFIED)
                vector_store = SQLPolicyVectorStore(session)
                policies = await retrieve_policies(job.fleet_type or "Unknown", job.region, vector_store)
                job.policies_used = policies
                session.add(AuditLog(job_id=job.id, action="POLICIES_RETRIEVED", details={"count": len(policies)}))
                await session.commit()

                validation = await validate_compliance(job.extracted_text or "", policies, self.llm)
                await self._set_status(session, job, JobStatus.VALIDATED)
                job.validation_result = validation
                session.add(AuditLog(job_id=job.id, action="DOCUMENTS_VALIDATED", details=validation))
                await session.commit()

                report = await generate_report(validation, self.llm)
                await self._set_status(session, job, JobStatus.REPORT_GENERATED)
                job.report = report
                session.add(AuditLog(job_id=job.id, action="REPORT_GENERATED", details=report))
                await session.commit()

                await self._set_status(session, job, JobStatus.HUMAN_REVIEW)
                session.add(AuditLog(job_id=job.id, action="HUMAN_REVIEW_REQUIRED"))
                await session.commit()
            except Exception as exc:
                await session.rollback()
                job = await self._load_job(session, job_id)
                job.status = JobStatus.FAILED.value
                job.error = str(exc)
                session.add(AuditLog(job_id=job.id, action="JOB_FAILED", details={"error": str(exc)}))
                notification = await self.notifications.request_documents(job, str(exc))
                session.add(AuditLog(job_id=job.id, action="DOCUMENT_REQUEST_TRIGGERED", details=notification))
                await session.commit()

    async def _load_job(self, session: AsyncSession, job_id: str) -> Job:
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if job is None:
            raise ValueError(f"Job not found: {job_id}")
        return job

    async def _set_status(self, session: AsyncSession, job: Job, status: JobStatus) -> None:
        audit = transition(job, status)
        session.add(audit)

