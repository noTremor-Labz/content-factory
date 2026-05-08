from fastapi.testclient import TestClient

from content_factory_api.database import get_sessionmaker
from content_factory_api.modules.domain import (
    ComplianceCheckStatus,
    ContentStatus,
    JobAttemptStatus,
    RenderJobStatus,
)
from content_factory_api.modules.models import ComplianceCheck, ContentItem, JobAttempt, RenderJob


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


def _create_brand(client: TestClient) -> str:
    response = client.post(
        "/api/brands",
        json={"name": "Inflave", "voice_notes": "Confident, compliant, concise."},
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def _create_avatar(client: TestClient, brand_id: str) -> str:
    response = client.post(
        "/api/avatars",
        json={
            "brand_id": brand_id,
            "name": "Primary Host",
            "persona_notes": "Human-like pilot avatar.",
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def _create_content(client: TestClient, *, script: str, title: str = "Pilot short") -> str:
    brand_id = _create_brand(client)
    avatar_id = _create_avatar(client, brand_id)
    response = client.post(
        "/api/content-items",
        json={
            "brand_id": brand_id,
            "avatar_id": avatar_id,
            "title": title,
            "script": script,
            "channel": "youtube_shorts",
        },
    )
    assert response.status_code == 201
    content_item_id = str(response.json()["id"])
    plan_response = client.post(f"/api/content-items/{content_item_id}/plan", json={})
    assert plan_response.status_code == 200
    return content_item_id


def _workflow_preset_payload() -> dict[str, object]:
    return {
        "key": "pilot-reels",
        "name": "Pilot Reels",
        "description": "Primary short-form render preset.",
        "workflow_provider": "comfyui",
        "voice_provider": "none",
        "packaging_provider": "ffmpeg",
        "workflow_definition": {"nodes": {"script_prompt": {"class_type": "CLIPTextEncode"}}},
        "input_mapping": {
            "script_text": {"source_type": "content_item", "source_field": "script"},
        },
        "output_mapping": {
            "video_file": {"artifact_type": "video", "output_path": "outputs.video_file"},
        },
    }


def _seed_succeeded_render(client: TestClient, content_item_id: str) -> str:
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
        attempt = db_session.query(JobAttempt).filter_by(render_job_id=render_job_id).one()
        attempt.status = JobAttemptStatus.SUCCEEDED.value
        attempt.response_payload = {
            "outputs": {"video_file": "s3://content-factory-assets/renders/video.mp4"}
        }
        db_session.commit()
    finally:
        db_session.close()

    return render_job_id


def test_hard_fail_compliance_blocks_review_approval(api_client: TestClient) -> None:
    _bootstrap_owner(api_client)
    content_item_id = _create_content(
        api_client,
        script="Use promo code SAVE20 to buy the Inflave vape today. It is totally safe.",
    )

    review_response = api_client.post(f"/api/content-items/{content_item_id}/submit-review")
    assert review_response.status_code == 201
    approve_response = api_client.post(
        f"/api/review/tasks/{review_response.json()['id']}/approve",
        json={"decision_notes": "Looks fine."},
    )

    assert approve_response.status_code == 409
    assert "hard" in approve_response.json()["detail"].lower()

    checks_response = api_client.get("/api/compliance/checks")
    assert checks_response.status_code == 200
    check = checks_response.json()["items"][0]
    assert check["content_item_id"] == content_item_id
    assert check["status"] == "failed"
    assert check["risk_score"] == 100
    assert "hard_fail" in {flag["severity"] for flag in check["flags"]}


def test_soft_flags_require_explicit_compliance_override(api_client: TestClient) -> None:
    _bootstrap_owner(api_client)
    content_item_id = _create_content(
        api_client,
        script="Inflave vape is visible on the table while the avatar talks about weekend plans.",
    )
    review_response = api_client.post(f"/api/content-items/{content_item_id}/submit-review")
    assert review_response.status_code == 201
    task_id = str(review_response.json()["id"])

    blocked_response = api_client.post(
        f"/api/review/tasks/{task_id}/approve",
        json={"decision_notes": "Native scene placement."},
    )
    assert blocked_response.status_code == 409
    assert "override" in blocked_response.json()["detail"].lower()

    approve_response = api_client.post(
        f"/api/review/tasks/{task_id}/approve",
        json={
            "decision_notes": "Native scene placement only.",
            "compliance_override_reason": "Reviewer accepts soft product-placement risk.",
        },
    )

    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"
    assert approve_response.json()["compliance_override_reason"] == (
        "Reviewer accepts soft product-placement risk."
    )

    render_job_id = _seed_succeeded_render(api_client, content_item_id)
    package_response = api_client.post(
        "/api/publish-packages",
        json={"render_job_id": render_job_id},
    )
    assert package_response.status_code == 201

    audit_response = api_client.get("/api/audit/logs")
    actions = [entry["action"] for entry in audit_response.json()["items"]]
    assert "compliance.check_completed" in actions
    assert "review.compliance_override" in actions


def test_passed_compliance_check_allows_regular_review_approval(api_client: TestClient) -> None:
    _bootstrap_owner(api_client)
    content_item_id = _create_content(
        api_client,
        script="A careful lifestyle short about staying organized during a busy week.",
    )
    review_response = api_client.post(f"/api/content-items/{content_item_id}/submit-review")
    assert review_response.status_code == 201

    approve_response = api_client.post(
        f"/api/review/tasks/{review_response.json()['id']}/approve",
        json={"decision_notes": "Approved for manual publishing."},
    )

    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"
    assert approve_response.json()["compliance_override_reason"] is None


def test_publish_package_requires_final_compliance_decision(api_client: TestClient) -> None:
    _bootstrap_owner(api_client)
    content_item_id = _create_content(
        api_client,
        script="A careful lifestyle short about planning a weekend routine.",
    )
    review_response = api_client.post(f"/api/content-items/{content_item_id}/submit-review")
    assert review_response.status_code == 201
    approve_response = api_client.post(
        f"/api/review/tasks/{review_response.json()['id']}/approve",
        json={"decision_notes": "Approved for manual publishing."},
    )
    assert approve_response.status_code == 200

    db_session = get_sessionmaker()()
    try:
        content_item = db_session.get(ContentItem, content_item_id)
        assert content_item is not None
        assert content_item.status == ContentStatus.APPROVED.value
        check = db_session.query(ComplianceCheck).filter_by(content_item_id=content_item_id).one()
        check.status = ComplianceCheckStatus.FAILED.value
        db_session.commit()
    finally:
        db_session.close()

    render_job_id = _seed_succeeded_render(api_client, content_item_id)
    package_response = api_client.post(
        "/api/publish-packages",
        json={"render_job_id": render_job_id},
    )

    assert package_response.status_code == 409
    assert "compliance" in package_response.json()["detail"].lower()


def test_publish_package_blocks_latest_soft_flag_without_matching_override(
    api_client: TestClient,
) -> None:
    _bootstrap_owner(api_client)
    content_item_id = _create_content(
        api_client,
        script="A careful lifestyle short about planning a weekend routine.",
    )
    review_response = api_client.post(f"/api/content-items/{content_item_id}/submit-review")
    assert review_response.status_code == 201
    approve_response = api_client.post(
        f"/api/review/tasks/{review_response.json()['id']}/approve",
        json={"decision_notes": "Approved for manual publishing."},
    )
    assert approve_response.status_code == 200

    db_session = get_sessionmaker()()
    try:
        soft_check = ComplianceCheck(
            content_item_id=content_item_id,
            status=ComplianceCheckStatus.FLAGGED.value,
            risk_score=40,
            flags=[
                {
                    "rule_key": "nicotine_or_vape_reference",
                    "severity": "soft_flag",
                    "reason_code": "nicotine_or_vape_reference",
                    "message": "Nicotine or vape-adjacent placement requires reviewer attention.",
                    "matched_terms": ["vape"],
                }
            ],
            summary="1 soft compliance flag(s) require reviewer override.",
        )
        db_session.add(soft_check)
        db_session.commit()
    finally:
        db_session.close()

    render_job_id = _seed_succeeded_render(api_client, content_item_id)
    package_response = api_client.post(
        "/api/publish-packages",
        json={"render_job_id": render_job_id},
    )

    assert package_response.status_code == 409
    assert "override" in package_response.json()["detail"].lower()
