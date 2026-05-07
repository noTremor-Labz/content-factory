import io
import json
from collections.abc import Generator
from pathlib import Path
from zipfile import ZipFile

import pytest
from sqlalchemy.orm import Session

from content_factory_api.config import get_settings
from content_factory_api.database import get_sessionmaker, init_database, reset_database_caches
from content_factory_api.modules.domain import (
    ContentChannel,
    ContentStatus,
    JobAttemptStatus,
    PackagingProvider,
    PublishPackageStatus,
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
    PublishPackage,
    RenderJob,
    User,
    WorkflowPreset,
)
from content_factory_worker.packaging import (
    PackageStorage,
    ZipPublishPackager,
    process_publish_package,
)


@pytest.fixture
def db_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Session, None, None]:
    db_path = tmp_path / "publish-package.db"
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


class MemoryPackageStorage(PackageStorage):
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def upload_package(self, *, object_key: str, data: bytes, content_type: str) -> None:
        assert content_type == "application/zip"
        self.objects[object_key] = data


def test_process_publish_package_builds_manifest_zip(db_session: Session) -> None:
    publish_package = _seed_publish_package(
        db_session,
        response_payload={
            "outputs": {
                "video_file": "s3://content-factory-assets/renders/video.mp4",
                "cover_file": "s3://content-factory-assets/renders/cover.jpg",
            },
            "hashtags": ["#inflave"],
        },
    )
    storage = MemoryPackageStorage()

    outcome = process_publish_package(
        publish_package.id,
        db_session=db_session,
        packager=ZipPublishPackager(storage=storage),
    )

    db_session.refresh(publish_package)
    assert outcome.status == "ready"
    assert publish_package.status == PublishPackageStatus.READY.value
    assert publish_package.package_object_key in storage.objects
    assert publish_package.byte_size is not None and publish_package.byte_size > 0
    assert publish_package.manifest_payload["manual_publish"]["title"] == "Pilot short"
    assert publish_package.manifest_payload["artifacts"][0]["name"] == "video_file"

    archive = ZipFile(io.BytesIO(storage.objects[publish_package.package_object_key or ""]))
    assert sorted(archive.namelist()) == [
        "caption.txt",
        "hashtags.txt",
        "manifest.json",
        "provider-output.json",
        "title.txt",
    ]
    manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    assert manifest["render_job_id"] == publish_package.render_job_id
    assert manifest["manual_publish"]["hashtags"] == ["#inflave"]


def test_process_publish_package_marks_missing_outputs_failed(db_session: Session) -> None:
    publish_package = _seed_publish_package(db_session, response_payload={"outputs": {}})

    outcome = process_publish_package(
        publish_package.id,
        db_session=db_session,
        packager=ZipPublishPackager(storage=MemoryPackageStorage()),
    )

    db_session.refresh(publish_package)
    assert outcome.status == "failed"
    assert publish_package.status == PublishPackageStatus.FAILED.value
    assert publish_package.error_message is not None
    assert "video_file" in publish_package.error_message


def test_cancelled_publish_package_is_not_processed(db_session: Session) -> None:
    publish_package = _seed_publish_package(
        db_session,
        response_payload={
            "outputs": {
                "video_file": "s3://content-factory-assets/renders/video.mp4",
                "cover_file": "s3://content-factory-assets/renders/cover.jpg",
            }
        },
    )
    publish_package.status = PublishPackageStatus.CANCELLED.value
    db_session.commit()
    storage = MemoryPackageStorage()

    outcome = process_publish_package(
        publish_package.id,
        db_session=db_session,
        packager=ZipPublishPackager(storage=storage),
    )

    db_session.refresh(publish_package)
    assert outcome.status == "skipped_cancelled"
    assert publish_package.status == PublishPackageStatus.CANCELLED.value
    assert storage.objects == {}


def _seed_publish_package(
    db_session: Session,
    *,
    response_payload: dict[str, object],
) -> PublishPackage:
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
        status=ContentStatus.APPROVED.value,
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
            "video_file": {"artifact_type": "video", "output_path": "outputs.video_file"},
            "cover_file": {"artifact_type": "cover_image", "output_path": "outputs.cover_file"},
        },
        created_by_user_id=user.id,
    )
    db_session.add(workflow_preset)
    db_session.flush()

    render_job = RenderJob(
        content_item_id=content_item.id,
        workflow_preset_id=workflow_preset.id,
        workflow_preset_key=workflow_preset.key,
        workflow_preset_version=workflow_preset.version,
        workflow_provider=workflow_preset.workflow_provider,
        voice_provider=workflow_preset.voice_provider,
        packaging_provider=workflow_preset.packaging_provider,
        input_snapshot={"script_text": content_item.script},
        status=RenderJobStatus.SUCCEEDED.value,
        retry_budget=1,
        created_by_user_id=user.id,
    )
    db_session.add(render_job)
    db_session.flush()

    attempt = JobAttempt(
        render_job_id=render_job.id,
        attempt_number=1,
        status=JobAttemptStatus.SUCCEEDED.value,
        provider_job_id="comfyui-1",
        request_payload={"inputs": render_job.input_snapshot},
        response_payload=response_payload,
    )
    db_session.add(attempt)
    db_session.flush()

    publish_package = PublishPackage(
        render_job_id=render_job.id,
        content_item_id=content_item.id,
        status=PublishPackageStatus.QUEUED.value,
        created_by_user_id=user.id,
    )
    db_session.add(publish_package)
    db_session.commit()
    return publish_package
