from fastapi.testclient import TestClient


def test_root_reports_bootstrap_status(api_client: TestClient) -> None:
    response = api_client.get("/")

    assert response.status_code == 200
    assert response.json()["phase"] == "phase-1-bootstrap"


def test_liveness_endpoint_reports_ok(api_client: TestClient) -> None:
    response = api_client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_endpoint_reports_configured_services(api_client: TestClient) -> None:
    response = api_client.get("/health/ready")
    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "ready"
    assert payload["checks"]["object_storage_bucket"] == "content-factory-assets"
