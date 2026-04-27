from __future__ import annotations

from typing import Any

from app.models.domain import Job


class NotificationService:
    async def send_success_email(self, job: Job) -> dict[str, Any]:
        return {
            "channel": "email",
            "type": "approval",
            "recipient": job.submitter_email,
            "sent": bool(job.submitter_email),
            "message": "Inspection approved.",
        }

    async def send_rejection_email(self, job: Job) -> dict[str, Any]:
        validation = job.validation_result or {}
        return {
            "channel": "email",
            "type": "rejection",
            "recipient": job.submitter_email,
            "sent": bool(job.submitter_email),
            "reasons": validation.get("reasons", []),
            "missing_documents": validation.get("missing_documents", []),
        }

    async def request_documents(self, job: Job, reason: str) -> dict[str, Any]:
        return {
            "channel": "email",
            "type": "document_request",
            "recipient": job.submitter_email,
            "sent": bool(job.submitter_email),
            "reason": reason,
            "missing_documents": ["Corrected invoice", "Supporting fleet documents"],
        }

