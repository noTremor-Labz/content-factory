import json

from fastapi.testclient import TestClient

from content_factory_api.database import get_sessionmaker
from content_factory_api.modules.domain import RenderJobStatus
from content_factory_api.modules.models import RenderJob


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


def _create_identity_pack(client: TestClient, avatar_id: str) -> str:
    response = client.post(
        f"/api/avatars/{avatar_id}/identity-packs",
        json={
            "name": "Core identity",
            "description": "Pilot voice and look references.",
            "storage_prefix": "identity/core",
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def _create_content_item(client: TestClient, brand_id: str, avatar_id: str) -> str:
    response = client.post(
        "/api/content-items",
        json={
            "brand_id": brand_id,
            "avatar_id": avatar_id,
            "title": "Pilot short",
            "script": "A careful, platform-safe short script.",
            "channel": "youtube_shorts",
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def _plan_content_item(client: TestClient, content_item_id: str) -> None:
    response = client.post(f"/api/content-items/{content_item_id}/plan", json={})
    assert response.status_code == 200


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
            "brand_voice_notes": {"source_type": "brand", "source_field": "voice_notes"},
            "host_name": {"source_type": "avatar", "source_field": "name"},
            "identity_pack_prefix": {
                "source_type": "identity_pack",
                "source_field": "storage_prefix",
            },
        },
        "output_mapping": {
            "video_file": {"artifact_type": "video", "output_path": "outputs.primary.video"},
            "cover_file": {"artifact_type": "cover_image", "output_path": "outputs.primary.cover"},
        },
    }


def test_workflow_preset_versions_are_incremented_and_immutable(api_client: TestClient) -> None:
    _bootstrap_owner(api_client)

    first_response = api_client.post("/api/workflow-presets", json=_workflow_preset_payload())
    assert first_response.status_code == 201
    first_payload = first_response.json()
    assert first_payload["version"] == 1

    second_payload = _workflow_preset_payload()
    second_payload["description"] = "Updated preset with a refined prompt."
    second_payload["workflow_definition"] = {
        "nodes": {
            "script_prompt": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": "render an approved and on-brand short"},
            }
        }
    }
    second_response = api_client.post("/api/workflow-presets", json=second_payload)

    assert second_response.status_code == 201
    assert second_response.json()["version"] == 2

    first_detail = api_client.get(f"/api/workflow-presets/{first_payload['id']}")
    assert first_detail.status_code == 200
    assert first_detail.json()["version"] == 1
    assert first_detail.json()["description"] == "Primary short-form render preset."
    assert (
        first_detail.json()["workflow_definition"]["nodes"]["script_prompt"]["inputs"]["text"]
        == "render a compliant host short"
    )

    list_response = api_client.get("/api/workflow-presets")
    assert list_response.status_code == 200
    versions = [
        item["version"]
        for item in list_response.json()["items"]
        if item["key"] == "pilot-reels"
    ]
    assert versions == [2, 1]


def test_workflow_preset_rejects_invalid_provider_contract(api_client: TestClient) -> None:
    _bootstrap_owner(api_client)
    invalid_payload = _workflow_preset_payload()
    invalid_payload["workflow_definition"] = {"graph": []}

    response = api_client.post("/api/workflow-presets", json=invalid_payload)

    assert response.status_code == 422
    assert "nodes" in response.json()["detail"]


def test_render_job_creation_snapshots_preset_and_seeds_first_attempt(
    api_client: TestClient,
) -> None:
    _bootstrap_owner(api_client)
    brand_id = _create_brand(api_client)
    avatar_id = _create_avatar(api_client, brand_id)
    identity_pack_id = _create_identity_pack(api_client, avatar_id)
    content_item_id = _create_content_item(api_client, brand_id, avatar_id)
    _plan_content_item(api_client, content_item_id)

    preset_response = api_client.post("/api/workflow-presets", json=_workflow_preset_payload())
    assert preset_response.status_code == 201
    preset_id = str(preset_response.json()["id"])

    render_job_response = api_client.post(
        "/api/render-jobs",
        json={
            "content_item_id": content_item_id,
            "workflow_preset_id": preset_id,
            "identity_pack_id": identity_pack_id,
            "retry_budget": 3,
        },
    )

    assert render_job_response.status_code == 201
    render_job_payload = render_job_response.json()
    assert render_job_payload["status"] == "queued"
    assert render_job_payload["workflow_preset_key"] == "pilot-reels"
    assert render_job_payload["workflow_preset_version"] == 1
    assert render_job_payload["input_snapshot"] == {
        "brand_voice_notes": "Confident, compliant, concise.",
        "host_name": "Primary Host",
        "identity_pack_prefix": "identity/core",
        "script_text": "A careful, platform-safe short script.",
    }
    assert render_job_payload["attempts"][0]["attempt_number"] == 1
    assert render_job_payload["attempts"][0]["status"] == "queued"
    assert render_job_payload["attempts"][0]["response_payload"] == {}
    assert render_job_payload["attempts"][0]["request_payload"]["inputs"] == {
        "brand_voice_notes": "Confident, compliant, concise.",
        "host_name": "Primary Host",
        "identity_pack_prefix": "identity/core",
        "script_text": "A careful, platform-safe short script.",
    }

    second_preset_payload = _workflow_preset_payload()
    second_preset_payload["description"] = "Version two."
    second_preset_response = api_client.post("/api/workflow-presets", json=second_preset_payload)
    assert second_preset_response.status_code == 201
    assert second_preset_response.json()["version"] == 2

    render_job_detail = api_client.get(f"/api/render-jobs/{render_job_payload['id']}")
    assert render_job_detail.status_code == 200
    assert render_job_detail.json()["workflow_preset_version"] == 1


def test_render_job_events_stream_terminal_snapshot(api_client: TestClient) -> None:
    _bootstrap_owner(api_client)
    brand_id = _create_brand(api_client)
    avatar_id = _create_avatar(api_client, brand_id)
    identity_pack_id = _create_identity_pack(api_client, avatar_id)
    content_item_id = _create_content_item(api_client, brand_id, avatar_id)
    _plan_content_item(api_client, content_item_id)
    preset_response = api_client.post("/api/workflow-presets", json=_workflow_preset_payload())
    assert preset_response.status_code == 201

    render_job_response = api_client.post(
        "/api/render-jobs",
        json={
            "content_item_id": content_item_id,
            "workflow_preset_id": str(preset_response.json()["id"]),
            "identity_pack_id": identity_pack_id,
        },
    )
    assert render_job_response.status_code == 201
    render_job_id = str(render_job_response.json()["id"])

    db_session = get_sessionmaker()()
    try:
        render_job = db_session.get(RenderJob, render_job_id)
        assert render_job is not None
        render_job.status = RenderJobStatus.SUCCEEDED.value
        db_session.commit()
    finally:
        db_session.close()

    with api_client.stream("GET", f"/api/render-jobs/{render_job_id}/events") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        stream_body = response.read().decode()

    assert "event: render_job.snapshot" in stream_body
    raw_payload = stream_body.split("data: ", 1)[1].split("\n\n", 1)[0]
    payload = json.loads(raw_payload)
    assert payload["render_job"]["id"] == render_job_id
    assert payload["render_job"]["status"] == "succeeded"
