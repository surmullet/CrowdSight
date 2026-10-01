"""Tests for session management, frames querying, and artifact retrieval endpoints."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from crowdsight.service.api.app import create_app
from crowdsight.service.api.deps import (
    get_artifact_store,
    get_media_registry,
    init_service_dependencies,
)
from tests.e2e.test_synthetic_video_e2e import generate_synthetic_video


@pytest.fixture
def api_context(tmp_path: Path) -> tuple[TestClient, str, str]:
    db_path = tmp_path / "sess_test.db"
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
    client = TestClient(app)

    # Register media
    video_path = media_dir / "test_video.mp4"
    generate_synthetic_video(video_path, num_frames=15, width=640, height=480)
    registry = get_media_registry()
    asset = registry.register_file(video_path, display_name="Test Video")

    # Create zone set
    zs_payload = {
        "id": "zs-sess-test",
        "name": "Session Test Zone Set",
        "image_width": 640,
        "image_height": 480,
        "zones": [
            {
                "zone_id": "main-gate",
                "name": "Main Gate",
                "vertices": [[0, 0], [300, 0], [300, 300], [0, 300]],
            }
        ],
    }
    res_zs = client.post("/api/v1/zone-sets", json=zs_payload)
    zsv_id = res_zs.json()["versions"][0]["id"]

    return client, asset.id, zsv_id


def test_session_lifecycle_and_deletion(api_context: tuple[TestClient, str, str]) -> None:
    client, asset_id, zsv_id = api_context

    # Create session
    create_payload = {
        "media_asset_id": asset_id,
        "zone_set_version_id": zsv_id,
        "use_synthetic": True,
    }
    create_res = client.post("/api/v1/sessions", json=create_payload)
    assert create_res.status_code == 201
    sess_id = create_res.json()["id"]

    # List sessions
    list_res = client.get("/api/v1/sessions")
    assert list_res.status_code == 200
    assert any(s["id"] == sess_id for s in list_res.json())

    # Get session details
    detail_res = client.get(f"/api/v1/sessions/{sess_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["synthetic"] is True

    # Cancel session
    cancel_res = client.post(f"/api/v1/sessions/{sess_id}/cancel")
    assert cancel_res.status_code == 200

    # Delete session
    del_res = client.delete(f"/api/v1/sessions/{sess_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "DELETED"

    # Confirm 404
    after_del = client.get(f"/api/v1/sessions/{sess_id}")
    assert after_del.status_code == 404


def test_artifact_download(api_context: tuple[TestClient, str, str]) -> None:
    client, _, _ = api_context
    store = get_artifact_store()
    art_id, relpath, sha256 = store.save_bytes(
        b"png image data",
        kind="IMAGE_SPACE_HEATMAP",
        suffix=".png",
    )

    # In DB, create artifact record so endpoint finds it
    from crowdsight.service.api.deps import get_db_manager
    from crowdsight.service.storage.models import ArtifactRecord

    db = get_db_manager()
    with db.get_session() as session:
        rec = ArtifactRecord(
            id=art_id,
            kind="IMAGE_SPACE_HEATMAP",
            relpath=relpath,
            sha256=sha256,
        )
        session.add(rec)

    res = client.get(f"/api/v1/artifacts/{art_id}")
    assert res.status_code == 200
    assert res.content == b"png image data"
