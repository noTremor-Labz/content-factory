from io import BytesIO
from urllib.parse import urlparse

import boto3
import dramatiq
from botocore.client import Config

from content_factory_api.database import get_sessionmaker
from content_factory_worker.config import WorkerSettings, get_worker_settings
from content_factory_worker.packaging import (
    FfmpegMediaNormalizer,
    PackageStorage,
    PublishPackageError,
    PublishPackager,
    ZipPublishPackager,
    process_publish_package,
)


class S3PackageStorage(PackageStorage):
    def __init__(self, settings: WorkerSettings) -> None:
        addressing_style = "path" if settings.s3_force_path_style else "virtual"
        self._bucket = settings.s3_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=str(settings.s3_endpoint).rstrip("/"),
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": addressing_style}),
        )

    def upload_package(self, *, object_key: str, data: bytes, content_type: str) -> None:
        self._client.upload_fileobj(
            BytesIO(data),
            self._bucket,
            object_key,
            ExtraArgs={"ContentType": content_type},
        )

    def download_artifact(self, artifact_reference: str) -> bytes:
        bucket, key = self._resolve_artifact_reference(artifact_reference)
        buffer = BytesIO()
        self._client.download_fileobj(bucket, key, buffer)
        return buffer.getvalue()

    def _resolve_artifact_reference(self, artifact_reference: str) -> tuple[str, str]:
        parsed = urlparse(artifact_reference)
        if parsed.scheme == "s3":
            bucket = parsed.netloc
            key = parsed.path.lstrip("/")
            if bucket != self._bucket:
                raise PublishPackageError(
                    f"Artifact bucket '{bucket}' does not match configured bucket '{self._bucket}'",
                )
            if key == "":
                raise PublishPackageError("S3 artifact reference has no object key")
            return bucket, key
        if parsed.scheme in {"http", "https"}:
            raise PublishPackageError("HTTP media artifact references are not supported")
        if parsed.scheme:
            raise PublishPackageError(
                f"Unsupported media artifact reference scheme '{parsed.scheme}'",
            )
        object_key = artifact_reference.lstrip("/")
        if object_key == "":
            raise PublishPackageError("Media artifact reference has no object key")
        return self._bucket, object_key


def build_publish_packager(settings: WorkerSettings) -> PublishPackager:
    return ZipPublishPackager(
        storage=S3PackageStorage(settings),
        media_normalizer=FfmpegMediaNormalizer(
            ffmpeg_path=settings.ffmpeg_path,
            timeout_seconds=settings.ffmpeg_timeout_seconds,
        ),
    )


@dramatiq.actor(queue_name="publish-packages", max_retries=0)
def process_publish_package_message(publish_package_id: str) -> None:
    settings = get_worker_settings()
    db_session = get_sessionmaker()()
    try:
        process_publish_package(
            publish_package_id,
            db_session=db_session,
            packager=build_publish_packager(settings),
        )
    finally:
        db_session.close()
