import json
from pathlib import Path

from content_factory_api.export_openapi import export_openapi_schema


def test_export_openapi_schema_includes_health_routes(tmp_path: Path) -> None:
    output_path = export_openapi_schema(tmp_path / "openapi.json")
    schema = json.loads(output_path.read_text(encoding="utf-8"))

    assert output_path.exists()
    assert "/health/live" in schema["paths"]
    assert "/health/ready" in schema["paths"]
    assert "/api/auth/login" in schema["paths"]
    assert "/api/workflow-presets" in schema["paths"]
    assert "/api/render-jobs" in schema["paths"]
    assert "/api/render-jobs/{render_job_id}/events" in schema["paths"]
    assert "/api/publish-packages" in schema["paths"]
    assert "/api/publish-packages/{package_id}/download" in schema["paths"]
    assert "/api/content-items/{content_item_id}/submit-review" in schema["paths"]
    assert "/api/review/tasks/{task_id}/approve" in schema["paths"]
