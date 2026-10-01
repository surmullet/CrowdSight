"""Integration tests for analytics, notes, and export endpoints."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from crowdsight.service.api.app import create_app
from crowdsight.service.api.deps import init_service_dependencies


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_file = tmp_path / "test.db"
    media_dir = tmp_path / "media"
    art_dir = tmp_path / "artifacts"
    init_service_dependencies(
        db_url=f"sqlite:///{db_file.as_posix()}",
        media_dir=media_dir,
        artifacts_dir=art_dir,
    )
    app = create_app()
    return TestClient(app)


def _setup_session_with_data(client: TestClient, tmp_path: Path) -> tuple[str, str]:
    # 1. Register a fake video asset
    import cv2

    from crowdsight.service.api.deps import get_media_registry

    media_dir = tmp_path / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    video_file = media_dir / "sample.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # type: ignore[attr-defined]
    out = cv2.VideoWriter(str(video_file), fourcc, 10.0, (320, 240))
    for idx in range(20):
        frame = np.full((240, 320, 3), 120, dtype=np.uint8)
        cv2.circle(frame, (20 + idx * 10, 20 + idx * 5), 15, (255, 0, 0), -1)
        out.write(frame)
    out.release()

    reg = get_media_registry()
    asset_rec = reg.register_file(video_file)
    media_id = asset_rec.id

    # 2. Create zone set
    zs_res = client.post(
        "/api/v1/zone-sets",
        json={
            "id": "test_zone_set",
            "name": "Test Zone Set",
            "image_width": 320,
            "image_height": 240,
            "zones": [
                {
                    "zone_id": "zone_lobby",
                    "name": "Lobby",
                    "vertices": [[10, 10], [100, 10], [100, 100], [10, 100]],
                }
            ],
        },
    )
    assert zs_res.status_code == 200 or zs_res.status_code == 201
    zs_data = zs_res.json()
    version_id = zs_data["versions"][0]["id"]

    # 4. Create synthetic session
    sess_res = client.post(
        "/api/v1/sessions",
        json={
            "media_asset_id": media_id,
            "zone_set_version_id": version_id,
            "synthetic": True,
        },
    )
    assert sess_res.status_code == 201
    session_id = sess_res.json()["id"]

    # Verify session completed processing
    status_res = client.get(f"/api/v1/sessions/{session_id}")
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "COMPLETED"

    return session_id, "zone_lobby"


def test_trends_endpoint(client: TestClient, tmp_path: Path) -> None:
    session_id, zone_id = _setup_session_with_data(client, tmp_path)

    # 1. Bucketed trends
    res = client.get(f"/api/v1/sessions/{session_id}/trends?zone_id={zone_id}&bucket_s=1.0&series=BUCKETED")
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == session_id
    assert data["zone_id"] == zone_id
    assert len(data["buckets"]) > 0
    assert data["buckets"][0]["n_counted"] > 0

    # 2. Raw trends
    res_raw = client.get(f"/api/v1/sessions/{session_id}/trends?zone_id={zone_id}&series=RAW")
    assert res_raw.status_code == 200
    assert len(res_raw.json()["raw_points"]) == 20

    # 3. Smoothed trends
    res_smoothed = client.get(f"/api/v1/sessions/{session_id}/trends?zone_id={zone_id}&series=SMOOTHED")
    assert res_smoothed.status_code == 200
    assert len(res_smoothed.json()["smoothed_points"]) == 20


def test_peaks_endpoint(client: TestClient, tmp_path: Path) -> None:
    session_id, zone_id = _setup_session_with_data(client, tmp_path)
    res = client.get(f"/api/v1/sessions/{session_id}/peaks?zone_id={zone_id}&limit=3")
    assert res.status_code == 200
    peaks = res.json()["peaks"]
    assert len(peaks) > 0
    assert peaks[0]["visible_count"] == 1
    assert "nguy hiểm" not in peaks[0]["description_vi"]


def test_quality_summary_endpoint(client: TestClient, tmp_path: Path) -> None:
    session_id, zone_id = _setup_session_with_data(client, tmp_path)
    res = client.get(f"/api/v1/sessions/{session_id}/summary")
    assert res.status_code == 200
    summary = res.json()
    assert summary["total_frames"] == 20
    assert summary["valid_frames"] == 20
    assert summary["synthetic"] is True
    assert summary["zone_availability"][zone_id]["n_counted"] == 20


def test_heatmaps_generate_and_download(client: TestClient, tmp_path: Path) -> None:
    session_id, _ = _setup_session_with_data(client, tmp_path)

    # Generate heat map
    res = client.post(
        f"/api/v1/sessions/{session_id}/heatmaps",
        json={"normalization_method": "SESSION_MAX"},
    )
    assert res.status_code == 200
    meta = res.json()
    art_id = meta["artifact_id"]
    assert meta["kind"] == "IMAGE_SPACE"

    # Download heat map
    res_dl = client.get(f"/api/v1/sessions/{session_id}/heatmaps/{art_id}")
    assert res_dl.status_code == 200
    assert res_dl.headers["content-type"] == "image/png"
    assert len(res_dl.content) > 0


def test_notes_crud(client: TestClient, tmp_path: Path) -> None:
    session_id, zone_id = _setup_session_with_data(client, tmp_path)

    # 1. Create note
    res = client.post(
        f"/api/v1/sessions/{session_id}/notes",
        json={
            "media_time_s": 0.5,
            "zone_id": zone_id,
            "text": "Observed person entering lobby.",
            "author": "analyst_1",
        },
    )
    assert res.status_code == 200
    note_id = res.json()["id"]

    # 2. List notes
    res_list = client.get(f"/api/v1/sessions/{session_id}/notes")
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1

    # 3. Delete note
    res_del = client.delete(f"/api/v1/sessions/{session_id}/notes/{note_id}")
    assert res_del.status_code == 204

    # 4. Verify empty
    res_empty = client.get(f"/api/v1/sessions/{session_id}/notes")
    assert len(res_empty.json()) == 0


def test_export_endpoints(client: TestClient, tmp_path: Path) -> None:
    session_id, _ = _setup_session_with_data(client, tmp_path)

    # CSV export
    res_csv = client.get(f"/api/v1/sessions/{session_id}/export?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "DISCLAIMER" in res_csv.text

    # JSONL export
    res_jsonl = client.get(f"/api/v1/sessions/{session_id}/export?format=jsonl")
    assert res_jsonl.status_code == 200
    assert "application/x-ndjson" in res_jsonl.headers["content-type"]
    lines = res_jsonl.text.strip().splitlines()
    assert len(lines) == 21  # 1 manifest line + 20 observation lines
