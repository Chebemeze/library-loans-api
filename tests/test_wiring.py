"""Registration checks, not a substitute for M2's PostgreSQL integration tests."""

from fastapi.testclient import TestClient

from app.main import app


def test_readiness_is_mounted_outside_v1() -> None:
    with TestClient(app) as client:
        paths = client.get("/openapi.json").json()["paths"]
    assert "get" in paths["/health/ready"]
    assert "/v1/health/ready" not in paths
