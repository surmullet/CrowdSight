"""Tests for FastAPI HTTP endpoints, RFC 9457 errors, and governance boundaries."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from crowdsight.service.api.app import create_app
from crowdsight.service.api.deps import init_service_dependencies


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "api_test.db"
    media_dir = tmp_path / "media"
    artifacts_dir = tmp_path / "artifacts"

    media_dir.mkdir()
    artifacts_dir.mkdir()

    init_service_dependencies(
        db_url=f"sqlite:///{db_path}",
        media_dir=media_dir,
        artifacts_dir=artifacts_dir,
    )
    app = create_app()
    return TestClient(app)


def test_health_endpoints(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "crowdsight"}

    res_ready = client.get("/health/ready")
    assert res_ready.status_code == 200
    assert res_ready.json() == {"status": "ready", "database": "connected"}


def test_model_profile_and_governance(client: TestClient) -> None:
    res = client.get("/api/v1/model/profile")
    assert res.status_code == 200
    data = res.json()
    assert data["profile_id"] == "crowd_best_local_v2"
    assert data["confidence_semantics"] == "RAW_MODEL_SCORE"
    assert "Thử nghiệm" in data["experimental_warning"]

    # Operational alerts must be strictly false
    assert data["operational_alerts_allowed"] is False
    assert data["applicability_status"] == "EXPERIMENTAL_NO_APPROVAL"


def test_alerts_status_endpoint(client: TestClient) -> None:
    res = client.get("/api/v1/alerts/status")
    assert res.status_code == 200
    data = res.json()
    assert data["operational_alerts_allowed"] is False
    assert data["status"] == "EXPERIMENTAL_NO_APPROVAL"
    assert "disabled" in data["reason"].lower()


def test_rfc9457_error_on_missing_media(client: TestClient) -> None:
    res = client.get("/api/v1/media/non-existent-uuid")
    assert res.status_code == 404
    assert res.headers["content-type"] == "application/problem+json"
    data = res.json()
    assert data["status"] == 404
    assert data["code"] == "NOT_FOUND"
    assert "Media asset not found" in data["detail"]


def test_zone_set_validation_endpoint(client: TestClient) -> None:
    valid_payload = {
        "image_width": 1920,
        "image_height": 1080,
        "zones": [
            {
                "zone_id": "z1",
                "name": "Zone 1",
                "vertices": [[100, 100], [500, 100], [500, 500], [100, 500]],
            }
        ],
    }
    res = client.post("/api/v1/zone-sets/validate", json=valid_payload)
    assert res.status_code == 200
    assert res.json()["is_valid"] is True
    assert len(res.json()["errors"]) == 0

    invalid_payload = {
        "image_width": 1920,
        "image_height": 1080,
        "zones": [
            {
                "zone_id": "z_bad",
                "name": "Out of bounds",
                "vertices": [[3000, 100], [5000, 100], [5000, 500]],
            }
        ],
    }
    res_bad = client.post("/api/v1/zone-sets/validate", json=invalid_payload)
    assert res_bad.status_code == 200
    assert res_bad.json()["is_valid"] is False
    assert len(res_bad.json()["errors"]) > 0


def test_zone_set_create_and_retrieve(client: TestClient) -> None:
    payload = {
        "id": "zs-api-test",
        "name": "API Zone Set",
        "image_width": 1280,
        "image_height": 720,
        "zones": [
            {
                "zone_id": "gate-1",
                "name": "Gate 1",
                "vertices": [[0, 0], [400, 0], [400, 400], [0, 400]],
            }
        ],
    }
    res = client.post("/api/v1/zone-sets", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "zs-api-test"
    assert len(data["versions"]) == 1
    assert data["versions"][0]["version"] == 1

    # Fetch by ID
    get_res = client.get("/api/v1/zone-sets/zs-api-test")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "API Zone Set"
