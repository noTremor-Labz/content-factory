from fastapi import FastAPI
from fastapi.testclient import TestClient

from content_factory_api.database import get_sessionmaker
from content_factory_api.modules.domain import (
    ContentStatus,
    JobAttemptStatus,
    PublishPackageStatus,
    RenderJobStatus,
)
from content_factory_api.modules.models import ContentItem, JobAttempt, PublishPackage, RenderJob


def _bootstrap_owner(client: TestClient) -> None:
    response = client.post(
        "/api/auth/bootstrap-owner",
        json={
            "email": "owner@inflave.test",
            "display_name": "Owner",
            "password": "very-secure-password",
        },
    )
    assert response.status_code == 201


def _workflow_preset_payload() -> dict[str, object]:
    return {
        "key": "pilot-reels",
        "name": "Pilot Reels",
        "description": "Primary short-form render preset.",
        "workflow_provider": "comfyui",
        "voice_provider": "none",
        "packaging_provider": "ffmpeg",
        "workflow_definition": {
            "nodes": {
                "script_prompt": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"text": "render a compliant host short"},
                }
            }
        },
        "input_mapping": {
            "script_text": {"source_type": "content_item", "source_field": "script"},
        },
        "output_mapping": {
            "video_file": {"artifact_type": "video", "output_path": "outputs.video_file"},
            "cover_file": {"artifact_type": "cover_image", "output_path": "outputs.cover_file"},
        },
    }


def _seed_approved_render_job(client: TestClient) -> str:
    brand_response = client.post(
        "/api/brands",
        json={"name": "Inflave", "voice_notes": "Confident, compliant, concise."},
    )
    assert brand_response.status_code == 201
    brand_id = str(brand_response.json()["id"])

    avatar_response = client.post(
        "/api/avatars",
        json={
            "brand_id": brand_id,
            "name": "Primary Host",
            "persona_notes": "Human-like pilot avatar.",
        },
    )
    assert avatar_response.status_code == 201
    avatar_id = str(avatar_response.json()["id"])

    content_response = client.post(
        "/api/content-items",
        json={
            "brand_id": brand_id,
            "avatar_id": avatar_id,
            "title": "Pilot short",
            "script": "A careful, platform-safe short script.",
            "channel": "youtube_shorts",
        },
    )
    assert content_response.status_code == 201
    content_item_id = str(content_response.json()["id"])

    plan_response = client.post(f"/api/content-items/{content_item_id}/plan", json={})
    assert plan_response.status_code == 200
    review_response = client.post(f"/api/content-items/{content_item_id}/submit-review")
    assert review_response.status_code == 201
    approve_response = client.post(
        f"/api/review/tasks/{review_response.json()['id']}/approve",
        json={"decision_notes": "Approved for manual publishing."},
    )
    assert approve_response.status_code == 200

    preset_response = client.post("/api/workflow-presets", json=_workflow_preset_payload())
    assert preset_response.status_code == 201

    render_response = client.post(
        "/api/render-jobs",
        json={
            "content_item_id": content_item_id,
            "workflow_preset_id": str(preset_response.json()["id"]),
        },
    )
    assert render_response.status_code == 201
    render_job_id = str(render_response.json()["id"])

    db_session = get_sessionmaker()()
    try:
        render_job = db_session.get(RenderJob, render_job_id)
        assert render_job is not None
        render_job.status = RenderJobStatus.SUCCEEDED.value
        attempt = (
            db_session.query(JobAttempt)
            .filter(JobAttempt.render_job_id == render_job_id)
            .one()
        )
        attempt.status = JobAttemptStatus.SUCCEEDED.value
        attempt.response_payload = {
            "outputs": {
                "video_file": "s3://content-factory-assets/renders/video.mp4",
                "cover_file": "s3://content-factory-assets/renders/cover.jpg",
            }
        }
        db_session.commit()
    finally:
        db_session.close()

    return render_job_id


def test_create_publish_package_is_gated_and_idempotent(api_client: TestClient) -> None:
    _bootstrap_owner(api_client)
    render_job_id = _seed_approved_render_job(api_client)

    response = api_client.post("/api/publish-packages", json={"render_job_id": render_job_id})

    assert response.status_code == 201
    payload = response.json()
    assert payload["render_job_id"] == render_job_id
    assert payload["status"] == "queued"
    assert payload["package_object_key"] is None

    second_response = api_client.post(
        "/api/publish-packages",
        json={"render_job_id": render_job_id},
    )
    assert second_response.status_code == 200
    assert second_response.json()["id"] == payload["id"]

    list_response = api_client.get("/api/publish-packages")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()["items"]] == [payload["id"]]


def test_publish_package_requires_approved_content_and_succeeded_render(
    api_client: TestClient,
) -> None:
    _bootstrap_owner(api_client)
    render_job_id = _seed_approved_render_job(api_client)

    db_session = get_sessionmaker()()
    try:
        render_job = db_session.get(RenderJob, render_job_id)
        assert render_job is not None
        render_job.status = RenderJobStatus.RUNNING.value
        db_session.commit()
    finally:
        db_session.close()

    running_response = api_client.post(
        "/api/publish-packages",
        json={"render_job_id": render_job_id},
    )
    assert running_response.status_code == 409
    assert "succeed" in running_response.json()["detail"]

    db_session = get_sessionmaker()()
    try:
        render_job = db_session.get(RenderJob, render_job_id)
        assert render_job is not None
        render_job.status = RenderJobStatus.SUCCEEDED.value
        content_item = db_session.get(ContentItem, render_job.content_item_id)
        assert content_item is not None
        content_item.status = ContentStatus.REWORK.value
        db_session.commit()
    finally:
        db_session.close()

    review_response = api_client.post(
        "/api/publish-packages",
        json={"render_job_id": render_job_id},
    )
    assert review_response.status_code == 409
    assert "approved" in review_response.json()["detail"]


def test_publish_package_download_requires_ready_package(api_client: TestClient) -> None:
    _bootstrap_owner(api_client)
    render_job_id = _seed_approved_render_job(api_client)
    create_response = api_client.post(
        "/api/publish-packages",
        json={"render_job_id": render_job_id},
    )
    assert create_response.status_code == 201
    package_id = str(create_response.json()["id"])

    queued_download = api_client.get(f"/api/publish-packages/{package_id}/download")
    assert queued_download.status_code == 409

    db_session = get_sessionmaker()()
    try:
        package = db_session.get(PublishPackage, package_id)
        assert package is not None
        package.status = PublishPackageStatus.READY.value
        package.package_object_key = "publish-packages/content/package.zip"
        package.byte_size = 123
        db_session.commit()
    finally:
        db_session.close()

    ready_download = api_client.get(f"/api/publish-packages/{package_id}/download")
    assert ready_download.status_code == 200
    payload = ready_download.json()
    assert payload["package"]["id"] == package_id
    assert payload["download"]["method"] == "GET"
    assert "publish-packages/content/package.zip" in payload["download"]["url"]


def test_publish_package_operator_actions_cancel_retry_and_requeue(
    api_client: TestClient,
) -> None:
    _bootstrap_owner(api_client)
    render_job_id = _seed_approved_render_job(api_client)
    create_response = api_client.post(
        "/api/publish-packages",
        json={"render_job_id": render_job_id},
    )
    assert create_response.status_code == 201
    package_id = str(create_response.json()["id"])

    requeue_response = api_client.post(f"/api/publish-packages/{package_id}/requeue")
    assert requeue_response.status_code == 200
    assert requeue_response.json()["status"] == "queued"

    cancel_response = api_client.post(f"/api/publish-packages/{package_id}/cancel")
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    db_session = get_sessionmaker()()
    try:
        publish_package = db_session.get(PublishPackage, package_id)
        assert publish_package is not None
        publish_package.status = PublishPackageStatus.FAILED.value
        publish_package.package_object_key = "publish-packages/stale.zip"
        publish_package.manifest_payload = {"stale": True}
        publish_package.byte_size = 10
        publish_package.error_message = "Missing output"
        db_session.commit()
    finally:
        db_session.close()

    retry_response = api_client.post(f"/api/publish-packages/{package_id}/retry")
    assert retry_response.status_code == 200
    retry_payload = retry_response.json()
    assert retry_payload["status"] == "queued"
    assert retry_payload["package_object_key"] is None
    assert retry_payload["manifest_payload"] == {}
    assert retry_payload["byte_size"] is None
    assert retry_payload["error_message"] is None

    audit_response = api_client.get("/api/audit/logs")
    actions = [entry["action"] for entry in audit_response.json()["items"]]
    assert "publish_package.requeued" in actions
    assert "publish_package.cancelled" in actions
    assert "publish_package.retried" in actions


def test_publish_package_actions_are_role_gated(
    api_app: FastAPI,
    api_client: TestClient,
) -> None:
    _bootstrap_owner(api_client)
    render_job_id = _seed_approved_render_job(api_client)
    create_response = api_client.post(
        "/api/publish-packages",
        json={"render_job_id": render_job_id},
    )
    assert create_response.status_code == 201

    invite_response = api_client.post(
        "/api/auth/invites",
        json={"email": "viewer@inflave.test", "role": "viewer"},
    )
    viewer_client = TestClient(api_app)
    accept_response = viewer_client.post(
        "/api/auth/invites/accept",
        json={
            "token": invite_response.json()["token"],
            "email": "viewer@inflave.test",
            "display_name": "Viewer",
            "password": "viewer-password",
        },
    )
    assert accept_response.status_code == 201

    response = viewer_client.post(
        f"/api/publish-packages/{create_response.json()['id']}/cancel",
    )

    assert response.status_code == 403
