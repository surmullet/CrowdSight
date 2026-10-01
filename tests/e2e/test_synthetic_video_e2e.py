"""End-to-End test of the full video pipeline using an OpenCV synthetic video."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
from sqlalchemy import select

from crowdsight.service.jobs.runner import JobManager
from crowdsight.service.pipeline.synthetic import (
    SYNTHETIC_CHECKPOINT_SHA256,
    SYNTHETIC_PROFILE_ID,
    SYNTHETIC_PROFILE_SHA256,
    SyntheticDetector,
)
from crowdsight.service.storage.database import DatabaseManager
from crowdsight.service.storage.media_registry import MediaRegistry
from crowdsight.service.storage.models import (
    ObservationRecord,
    SessionRecord,
    ZoneResultRecord,
    ZoneSetRecord,
    ZoneSetVersionRecord,
)


def generate_synthetic_video(path: Path, num_frames: int = 20, width: int = 640, height: int = 480) -> None:
    fourcc = int(cv2.VideoWriter_fourcc(*"mp4v"))  # type: ignore[attr-defined]
    writer = cv2.VideoWriter(str(path), fourcc, 10.0, (width, height))
    for i in range(num_frames):
        # Frame with moving gradient so it is not blank
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.rectangle(frame, (i * 10, i * 5), (i * 10 + 100, i * 5 + 100), (200, 150, 100), -1)
        writer.write(frame)
    writer.release()


@pytest.fixture
def e2e_env(tmp_path: Path) -> tuple[JobManager, DatabaseManager, MediaRegistry, Path]:
    db = DatabaseManager(f"sqlite:///{tmp_path}/e2e.db")
    db.init_db()

    media_dir = tmp_path / "media"
    media_dir.mkdir()
    registry = MediaRegistry(media_dir, db)
    job_mgr = JobManager(db, registry)

    video_path = media_dir / "e2e_video.mp4"
    generate_synthetic_video(video_path, num_frames=20, width=640, height=480)
    return job_mgr, db, registry, video_path


def test_full_pipeline_e2e_execution(e2e_env: tuple[JobManager, DatabaseManager, MediaRegistry, Path]) -> None:
    job_mgr, db, registry, video_path = e2e_env

    # 1. Register media asset
    asset = registry.register_file(video_path, display_name="E2E Video")
    assert asset.frame_count >= 20

    # 2. Configure zone set
    with db.get_session() as session:
        zs = ZoneSetRecord(id="zs-e2e", name="E2E Zone Set")
        session.add(zs)
        session.flush()

        zsv = ZoneSetVersionRecord(
            zone_set_id="zs-e2e",
            version=1,
            image_width=640,
            image_height=480,
            polygon_data={
                "zones": [
                    {
                        "zone_id": "zone-left",
                        "name": "Left Half",
                        "vertices": [[0, 0], [320, 0], [320, 480], [0, 480]],
                        "blind_regions": [],
                    },
                    {
                        "zone_id": "zone-right",
                        "name": "Right Half",
                        "vertices": [[320, 0], [640, 0], [640, 480], [320, 480]],
                        "blind_regions": [],
                    },
                ]
            },
            sha256="z" * 64,
        )
        session.add(zsv)
        session.flush()

        # 3. Create session record
        sess_record = SessionRecord(
            media_asset_id=asset.id,
            zone_set_version_id=zsv.id,
            model_profile_id=SYNTHETIC_PROFILE_ID,
            model_profile_sha256=SYNTHETIC_PROFILE_SHA256,
            checkpoint_sha256=SYNTHETIC_CHECKPOINT_SHA256,
            synthetic=True,
            total_frames=asset.frame_count,
            status="QUEUED",
        )
        session.add(sess_record)
        session.flush()
        session_id = sess_record.id

    # 4. Run job using SyntheticDetector
    detector = SyntheticDetector(num_persons=4, seed=42)
    final_status = job_mgr.run_session_job(session_id, detector=detector)
    assert final_status == "COMPLETED"

    # 5. Verify database state
    with db.get_session() as session:
        completed_session = session.get(SessionRecord, session_id)
        assert completed_session is not None
        assert completed_session.status == "COMPLETED"
        assert completed_session.progress == 1.0
        assert completed_session.processed_frames == completed_session.total_frames
        assert completed_session.completeness == "FULL"

        # Check observations
        observations = list(session.scalars(select(ObservationRecord).where(ObservationRecord.session_id == session_id)))
        assert len(observations) == completed_session.total_frames

        for obs in observations:
            assert obs.quality == "VALID"
            assert "detections" in obs.payload_v1
            assert len(obs.payload_v1["detections"]) == 4

        # Check zone results
        zone_results = list(session.scalars(select(ZoneResultRecord).where(ZoneResultRecord.session_id == session_id)))
        assert len(zone_results) == len(observations) * 2  # 2 zones per frame

        for zr in zone_results:
            assert zr.availability == "COUNTED"
            assert zr.visible_count is not None
            assert zr.visible_count >= 0


def test_pipeline_cancellation_preserves_partial_results(
    e2e_env: tuple[JobManager, DatabaseManager, MediaRegistry, Path],
) -> None:
    job_mgr, db, registry, video_path = e2e_env
    asset = registry.register_file(video_path, display_name="Cancellation Test Video")

    with db.get_session() as session:
        zs = ZoneSetRecord(id="zs-cancel", name="Cancel Zone Set")
        session.add(zs)
        session.flush()

        zsv = ZoneSetVersionRecord(
            zone_set_id="zs-cancel",
            version=1,
            image_width=640,
            image_height=480,
            polygon_data={
                "zones": [
                    {
                        "zone_id": "zone-cancel",
                        "name": "Full Frame",
                        "vertices": [[0, 0], [640, 0], [640, 480], [0, 480]],
                        "blind_regions": [],
                    }
                ]
            },
            sha256="c" * 64,
        )
        session.add(zsv)
        session.flush()

        sess_record = SessionRecord(
            media_asset_id=asset.id,
            zone_set_version_id=zsv.id,
            model_profile_id=SYNTHETIC_PROFILE_ID,
            model_profile_sha256=SYNTHETIC_PROFILE_SHA256,
            checkpoint_sha256=SYNTHETIC_CHECKPOINT_SHA256,
            synthetic=True,
            total_frames=asset.frame_count,
            status="QUEUED",
        )
        session.add(sess_record)
        session.flush()
        session_id = sess_record.id

    # Request cancellation before/during execution
    job_mgr.request_cancellation(session_id)
    final_status = job_mgr.run_session_job(session_id)

    assert final_status == "PARTIAL_CANCELLED"

    with db.get_session() as session:
        cancelled_session = session.get(SessionRecord, session_id)
        assert cancelled_session is not None
        assert cancelled_session.status == "PARTIAL_CANCELLED"
        assert cancelled_session.completeness == "PARTIAL"
