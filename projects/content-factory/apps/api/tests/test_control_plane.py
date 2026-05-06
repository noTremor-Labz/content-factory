from fastapi import FastAPI
from fastapi.testclient import TestClient


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


def test_identity_pack_creation_is_listed_for_avatar(api_client: TestClient) -> None:
    _bootstrap_owner(api_client)
    brand_id = _create_brand(api_client)
    avatar_id = _create_avatar(api_client, brand_id)

    create_response = api_client.post(
        f"/api/avatars/{avatar_id}/identity-packs",
        json={
            "name": "Core identity",
            "description": "Pilot voice and look references.",
            "storage_prefix": "identity/core",
        },
    )

    assert create_response.status_code == 201

    list_response = api_client.get(f"/api/avatars/{avatar_id}/identity-packs")

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["name"] == "Core identity"
    assert list_response.json()["items"][0]["avatar_id"] == avatar_id


def test_signed_upload_initiation_and_finalization(api_client: TestClient) -> None:
    _bootstrap_owner(api_client)
    brand_id = _create_brand(api_client)

    initiate_response = api_client.post(
        "/api/assets/uploads",
        json={
            "brand_id": brand_id,
            "filename": "script-reference.png",
            "content_type": "image/png",
            "byte_size": 128_000,
        },
    )

    assert initiate_response.status_code == 201
    upload_payload = initiate_response.json()
    assert upload_payload["asset"]["status"] == "pending_upload"
    assert upload_payload["upload"]["method"] == "PUT"
    assert upload_payload["upload"]["url"].startswith("http://localhost:9000/")
    assert "X-Amz-Signature" in upload_payload["upload"]["url"]

    duplicate_name_response = api_client.post(
        "/api/assets/uploads",
        json={
            "brand_id": brand_id,
            "filename": "script-reference.png",
            "content_type": "image/png",
            "byte_size": 64_000,
        },
    )
    assert duplicate_name_response.status_code == 201

    finalize_response = api_client.post(
        f"/api/assets/{upload_payload['asset']['id']}/finalize",
        json={"byte_size": 128_000, "checksum_sha256": "a" * 64},
    )

    assert finalize_response.status_code == 200
    assert finalize_response.json()["status"] == "ready"


def test_content_lifecycle_creates_review_task_and_audit_entries(
    api_app: FastAPI,
    api_client: TestClient,
) -> None:
    _bootstrap_owner(api_client)
    brand_id = _create_brand(api_client)
    avatar_id = _create_avatar(api_client, brand_id)

    content_response = api_client.post(
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
    content_id = content_response.json()["id"]
    assert content_response.json()["status"] == "draft"

    early_review_response = api_client.post(f"/api/content-items/{content_id}/submit-review")
    assert early_review_response.status_code == 409

    plan_response = api_client.post(f"/api/content-items/{content_id}/plan", json={})
    assert plan_response.status_code == 200
    assert plan_response.json()["status"] == "planned"

    review_response = api_client.post(f"/api/content-items/{content_id}/submit-review")
    assert review_response.status_code == 201
    review_payload = review_response.json()
    assert review_payload["status"] == "open"

    reviewer_invite = api_client.post(
        "/api/auth/invites",
        json={"email": "reviewer@inflave.test", "role": "reviewer"},
    )
    reviewer_client = TestClient(api_app)
    reviewer_client.post(
        "/api/auth/invites/accept",
        json={
            "token": reviewer_invite.json()["token"],
            "email": "reviewer@inflave.test",
            "display_name": "Reviewer",
            "password": "reviewer-password",
        },
    )

    approval_response = reviewer_client.post(
        f"/api/review/tasks/{review_payload['id']}/approve",
        json={"decision_notes": "Approved for manual publishing."},
    )
    assert approval_response.status_code == 200
    assert approval_response.json()["status"] == "approved"

    approved_content = api_client.get(f"/api/content-items/{content_id}").json()
    assert approved_content["status"] == "approved"

    audit_response = api_client.get("/api/audit/logs")
    assert audit_response.status_code == 200
    actions = [entry["action"] for entry in audit_response.json()["items"]]
    assert "content.submitted_for_review" in actions
    assert "review.approved" in actions
