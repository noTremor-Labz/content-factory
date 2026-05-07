from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from content_factory_api.config import get_settings
from content_factory_api.database import get_sessionmaker, init_database, reset_database_caches
from content_factory_api.modules.domain import (
    ContentChannel,
    ContentStatus,
    JobAttemptStatus,
    PackagingProvider,
    RenderJobStatus,
    UserRole,
    UserStatus,
    VoiceProvider,
    WorkflowProvider,
)
from content_factory_api.modules.models import (
    Avatar,
    Brand,
    ContentItem,
    JobAttempt,
    RenderJob,
    User,
    WorkflowPreset,
)
from content_factory_worker.orchestration import (
    RenderExecutionError,
    RenderExecutionResult,
    process_render_job,
)


@pytest.fixture
def db_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Session, None, None]:
    db_path = tmp_path / "worker-orchestration.db"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    get_settings.cache_clear()
    reset_database_caches()
    init_database()
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()
        get_settings.cache_clear()
        reset_database_caches()


class SuccessfulExecutor:
    def __init__(self) -> None:
        self.calls = 0

    def execute(
        self,
        *,
        render_job: RenderJob,
        workflow_preset: WorkflowPreset,
        attempt: JobAttempt,
    ) -> RenderExecutionResult:
        self.calls += 1
        return RenderExecutionResult(
            provider_job_id=f"comfyui-{attempt.id}",
            response_payload={
                "workflow_key": workflow_preset.key,
                "outputs": {"video_file": f"renders/{render_job.id}/video.mp4"},
            },
        )


class FailingExecutor:
    def __init__(self) -> None:
        self.calls = 0

    def execute(
        self,
        *,
        render_job: RenderJob,
        workflow_preset: WorkflowPreset,
        attempt: JobAttempt,
    ) -> RenderExecutionResult:
        self.calls += 1
        raise RenderExecutionError("ComfyUI request timed out")


def test_process_render_job_marks_attempt_succeeded(db_session: Session) -> None:
    render_job, attempt = _seed_render_job(db_session, retry_budget=2)
    executor = SuccessfulExecutor()

    outcome = process_render_job(render_job.id, db_session=db_session, executor=executor)

    db_session.refresh(render_job)
    db_session.refresh(attempt)
    assert outcome.status == "succeeded"
    assert executor.calls == 1
    assert render_job.status == RenderJobStatus.SUCCEEDED.value
    assert attempt.status == JobAttemptStatus.SUCCEEDED.value
    assert attempt.provider_job_id == f"comfyui-{attempt.id}"
    assert attempt.response_payload["outputs"]["video_file"] == f"renders/{render_job.id}/video.mp4"
    assert attempt.started_at is not None
    assert attempt.finished_at is not None


def test_failed_attempt_queues_retry_until_budget_is_exhausted(db_session: Session) -> None:
    render_job, first_attempt = _seed_render_job(db_session, retry_budget=2)
    executor = FailingExecutor()

    outcome = process_render_job(render_job.id, db_session=db_session, executor=executor)

    attempts = _attempts_for_job(db_session, render_job.id)
    db_session.refresh(render_job)
    db_session.refresh(first_attempt)
    assert outcome.status == "retry_queued"
    assert executor.calls == 1
    assert render_job.status == RenderJobStatus.QUEUED.value
    assert first_attempt.status == JobAttemptStatus.FAILED.value
    assert first_attempt.error_message == "ComfyUI request timed out"
    assert len(attempts) == 2
    assert attempts[1].attempt_number == 2
    assert attempts[1].status == JobAttemptStatus.QUEUED.value
    assert attempts[1].request_payload == first_attempt.request_payload


def test_failed_attempt_marks_job_failed_when_retry_budget_is_exhausted(
    db_session: Session,
) -> None:
    render_job, first_attempt = _seed_render_job(db_session, retry_budget=1)
    executor = FailingExecutor()

    outcome = process_render_job(render_job.id, db_session=db_session, executor=executor)

    attempts = _attempts_for_job(db_session, render_job.id)
    db_session.refresh(render_job)
    db_session.refresh(first_attempt)
    assert outcome.status == "failed"
    assert render_job.status == RenderJobStatus.FAILED.value
    assert first_attempt.status == JobAttemptStatus.FAILED.value
    assert len(attempts) == 1


def test_terminal_render_job_is_not_processed_again(db_session: Session) -> None:
    render_job, attempt = _seed_render_job(db_session, retry_budget=2)
    render_job.status = RenderJobStatus.SUCCEEDED.value
    attempt.status = JobAttemptStatus.SUCCEEDED.value
    db_session.commit()
    executor = FailingExecutor()

    outcome = process_render_job(render_job.id, db_session=db_session, executor=executor)

    assert outcome.status == "skipped_terminal"
    assert executor.calls == 0


def _seed_render_job(db_session: Session, *, retry_budget: int) -> tuple[RenderJob, JobAttempt]:
    user = User(
        email="owner@inflave.test",
        display_name="Owner",
        role=UserRole.OWNER.value,
        status=UserStatus.ACTIVE.value,
        password_hash="hash",
    )
    db_session.add(user)
    db_session.flush()

    brand = Brand(
        name="Inflave",
        voice_notes="Confident, compliant, concise.",
        created_by_user_id=user.id,
    )
    db_session.add(brand)
    db_session.flush()

    avatar = Avatar(
        brand_id=brand.id,
        name="Primary Host",
        persona_notes="Human-like pilot avatar.",
        created_by_user_id=user.id,
    )
    db_session.add(avatar)
    db_session.flush()

    content_item = ContentItem(
        brand_id=brand.id,
        avatar_id=avatar.id,
        title="Pilot short",
        script="A careful, platform-safe short script.",
        channel=ContentChannel.YOUTUBE_SHORTS.value,
        status=ContentStatus.PLANNED.value,
        created_by_user_id=user.id,
    )
    db_session.add(content_item)
    db_session.flush()

    workflow_preset = WorkflowPreset(
        key="pilot-reels",
        version=1,
        name="Pilot Reels",
        workflow_provider=WorkflowProvider.COMFYUI.value,
        voice_provider=VoiceProvider.NONE.value,
        packaging_provider=PackagingProvider.FFMPEG.value,
        workflow_definition={"nodes": {"script_prompt": {"class_type": "CLIPTextEncode"}}},
        input_mapping={"script_text": {"source_type": "content_item", "source_field": "script"}},
        output_mapping={
            "video_file": {"artifact_type": "video", "output_path": "outputs.primary.video"},
        },
        created_by_user_id=user.id,
    )
    db_session.add(workflow_preset)
    db_session.flush()

    input_snapshot = {"script_text": content_item.script}
    render_job = RenderJob(
        content_item_id=content_item.id,
        workflow_preset_id=workflow_preset.id,
        workflow_preset_key=workflow_preset.key,
        workflow_preset_version=workflow_preset.version,
        workflow_provider=workflow_preset.workflow_provider,
        voice_provider=workflow_preset.voice_provider,
        packaging_provider=workflow_preset.packaging_provider,
        input_snapshot=input_snapshot,
        status=RenderJobStatus.QUEUED.value,
        retry_budget=retry_budget,
        created_by_user_id=user.id,
    )
    db_session.add(render_job)
    db_session.flush()

    attempt = JobAttempt(
        render_job_id=render_job.id,
        attempt_number=1,
        status=JobAttemptStatus.QUEUED.value,
        request_payload={"inputs": input_snapshot},
    )
    db_session.add(attempt)
    db_session.commit()
    return render_job, attempt


def _attempts_for_job(db_session: Session, render_job_id: str) -> list[JobAttempt]:
    return sorted(
        db_session.query(JobAttempt)
        .filter(JobAttempt.render_job_id == render_job_id)
        .all(),
        key=lambda attempt: attempt.attempt_number,
    )
