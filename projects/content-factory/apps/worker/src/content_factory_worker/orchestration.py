from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from content_factory_api.modules.domain import JobAttemptStatus, RenderJobStatus
from content_factory_api.modules.models import JobAttempt, RenderJob, WorkflowPreset
from content_factory_api.modules.security import utcnow

TERMINAL_RENDER_JOB_STATUSES = {
    RenderJobStatus.SUCCEEDED.value,
    RenderJobStatus.FAILED.value,
    RenderJobStatus.CANCELLED.value,
}

ProcessingStatus = Literal[
    "succeeded",
    "failed",
    "retry_queued",
    "skipped_terminal",
    "skipped_no_attempt",
]


class RenderExecutionError(RuntimeError):
    """Raised by a render executor when a provider attempt fails."""


class RenderJobNotFoundError(LookupError):
    """Raised when a queued worker message references a missing render job."""


class RenderJobStateError(RuntimeError):
    """Raised when a render job cannot be processed because its state is invalid."""


@dataclass(frozen=True)
class RenderExecutionResult:
    provider_job_id: str | None = None
    response_payload: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RenderJobProcessingOutcome:
    render_job_id: str
    attempt_id: str | None
    status: ProcessingStatus


class RenderExecutor(Protocol):
    def execute(
        self,
        *,
        render_job: RenderJob,
        workflow_preset: WorkflowPreset,
        attempt: JobAttempt,
    ) -> RenderExecutionResult:
        """Run a single render attempt against the configured provider."""


def process_render_job(
    render_job_id: str,
    *,
    db_session: Session,
    executor: RenderExecutor,
) -> RenderJobProcessingOutcome:
    render_job = db_session.get(RenderJob, render_job_id)
    if render_job is None:
        raise RenderJobNotFoundError(f"Render job '{render_job_id}' not found")

    if render_job.status in TERMINAL_RENDER_JOB_STATUSES:
        return RenderJobProcessingOutcome(
            render_job_id=render_job.id,
            attempt_id=None,
            status="skipped_terminal",
        )

    workflow_preset = db_session.get(WorkflowPreset, render_job.workflow_preset_id)
    if workflow_preset is None:
        raise RenderJobStateError(
            f"Workflow preset '{render_job.workflow_preset_id}' not found",
        )

    attempts = _attempts_for_job(db_session, render_job.id)
    attempt = _next_queued_attempt(attempts)
    if attempt is None:
        return RenderJobProcessingOutcome(
            render_job_id=render_job.id,
            attempt_id=None,
            status="skipped_no_attempt",
        )

    _mark_attempt_running(render_job, attempt)
    db_session.commit()

    try:
        result = executor.execute(
            render_job=render_job,
            workflow_preset=workflow_preset,
            attempt=attempt,
        )
    except RenderExecutionError as exc:
        return _fail_attempt(
            db_session,
            render_job=render_job,
            attempt=attempt,
            attempts=attempts,
            error_message=str(exc),
        )
    except Exception as exc:
        return _fail_attempt(
            db_session,
            render_job=render_job,
            attempt=attempt,
            attempts=attempts,
            error_message=f"{exc.__class__.__name__}: {exc}",
        )

    attempt.status = JobAttemptStatus.SUCCEEDED.value
    attempt.provider_job_id = result.provider_job_id
    attempt.response_payload = result.response_payload
    attempt.finished_at = utcnow()
    render_job.status = RenderJobStatus.SUCCEEDED.value
    db_session.commit()
    return RenderJobProcessingOutcome(
        render_job_id=render_job.id,
        attempt_id=attempt.id,
        status="succeeded",
    )


def _attempts_for_job(db_session: Session, render_job_id: str) -> list[JobAttempt]:
    return list(
        db_session.scalars(
            select(JobAttempt)
            .where(JobAttempt.render_job_id == render_job_id)
            .order_by(JobAttempt.attempt_number.asc())
        )
    )


def _next_queued_attempt(attempts: list[JobAttempt]) -> JobAttempt | None:
    for attempt in attempts:
        if attempt.status == JobAttemptStatus.QUEUED.value:
            return attempt
    return None


def _mark_attempt_running(render_job: RenderJob, attempt: JobAttempt) -> None:
    now = utcnow()
    render_job.status = RenderJobStatus.RUNNING.value
    attempt.status = JobAttemptStatus.RUNNING.value
    attempt.started_at = now


def _fail_attempt(
    db_session: Session,
    *,
    render_job: RenderJob,
    attempt: JobAttempt,
    attempts: list[JobAttempt],
    error_message: str,
) -> RenderJobProcessingOutcome:
    attempt.status = JobAttemptStatus.FAILED.value
    attempt.error_message = error_message
    attempt.finished_at = utcnow()

    if attempt.attempt_number < render_job.retry_budget:
        next_attempt_number = (
            max(existing_attempt.attempt_number for existing_attempt in attempts) + 1
        )
        next_attempt = JobAttempt(
            render_job_id=render_job.id,
            attempt_number=next_attempt_number,
            status=JobAttemptStatus.QUEUED.value,
            request_payload=attempt.request_payload,
        )
        db_session.add(next_attempt)
        render_job.status = RenderJobStatus.QUEUED.value
        db_session.commit()
        return RenderJobProcessingOutcome(
            render_job_id=render_job.id,
            attempt_id=next_attempt.id,
            status="retry_queued",
        )

    render_job.status = RenderJobStatus.FAILED.value
    db_session.commit()
    return RenderJobProcessingOutcome(
        render_job_id=render_job.id,
        attempt_id=attempt.id,
        status="failed",
    )
