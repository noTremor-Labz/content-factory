from fastapi import FastAPI
from fastapi.testclient import TestClient


def _bootstrap_owner(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/auth/bootstrap-owner",
        json={
            "email": "owner@inflave.test",
            "display_name": "Owner",
            "password": "very-secure-password",
        },
    )

    assert response.status_code == 201
    return response.json()


def test_bootstrap_owner_starts_session_and_is_single_use(api_client: TestClient) -> None:
    payload = _bootstrap_owner(api_client)

    assert payload["user"]["email"] == "owner@inflave.test"
    assert payload["user"]["role"] == "owner"
    assert api_client.get("/api/auth/session").json()["user"]["email"] == "owner@inflave.test"

    second_response = api_client.post(
        "/api/auth/bootstrap-owner",
        json={
            "email": "second@inflave.test",
            "display_name": "Second",
            "password": "very-secure-password",
        },
    )

    assert second_response.status_code == 409


def test_invite_accept_login_and_logout_flow(api_app: FastAPI, api_client: TestClient) -> None:
    _bootstrap_owner(api_client)

    invite_response = api_client.post(
        "/api/auth/invites",
        json={"email": "reviewer@inflave.test", "role": "reviewer"},
    )
    assert invite_response.status_code == 201
    invite_token = invite_response.json()["token"]

    reviewer_client = TestClient(api_app)
    accept_response = reviewer_client.post(
        "/api/auth/invites/accept",
        json={
            "token": invite_token,
            "email": "reviewer@inflave.test",
            "display_name": "Reviewer",
            "password": "reviewer-password",
        },
    )

    assert accept_response.status_code == 201
    assert accept_response.json()["user"]["role"] == "reviewer"
    session_payload = reviewer_client.get("/api/auth/session").json()
    assert session_payload["user"]["email"] == "reviewer@inflave.test"

    logout_response = reviewer_client.post("/api/auth/logout")
    assert logout_response.status_code == 200
    assert reviewer_client.get("/api/auth/session").status_code == 401

    login_response = reviewer_client.post(
        "/api/auth/login",
        json={"email": "reviewer@inflave.test", "password": "reviewer-password"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["user"]["email"] == "reviewer@inflave.test"


def test_rbac_blocks_viewer_from_mutating_control_plane(
    api_app: FastAPI,
    api_client: TestClient,
) -> None:
    _bootstrap_owner(api_client)
    invite_response = api_client.post(
        "/api/auth/invites",
        json={"email": "viewer@inflave.test", "role": "viewer"},
    )

    viewer_client = TestClient(api_app)
    viewer_client.post(
        "/api/auth/invites/accept",
        json={
            "token": invite_response.json()["token"],
            "email": "viewer@inflave.test",
            "display_name": "Viewer",
            "password": "viewer-password",
        },
    )

    response = viewer_client.post("/api/brands", json={"name": "Inflave"})

    assert response.status_code == 403
