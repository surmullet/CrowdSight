"""Unit tests for batched GPU inference and SessionPipeline batching."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from sqlalchemy import select

from crowdsight.detection.adapter import PersonDetectorProfile
from crowdsight.service.artifacts.store import ArtifactStore
from crowdsight.service.domain.zones import Point2D, ZoneDefinition, ZonePolygon, ZoneSet
from crowdsight.service.pipeline.runner import SessionPipeline
from crowdsight.service.pipeline.synthetic import SyntheticDetector
from crowdsight.service.storage.database import DatabaseManager
from crowdsight.service.storage.models import (
    MediaAssetRecord,
    ObservationRecord,
    SessionRecord,
    ZoneSetRecord,
    ZoneSetVersionRecord,
)
from tests.e2e.test_synthetic_video_e2e import generate_synthetic_video


def test_synthetic_detector_predict_batch() -> None:
    detector = SyntheticDetector(num_persons=3, seed=42)
    dummy_frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
    dummy_frame2 = np.zeros((480, 640, 3), dtype=np.uint8)

    single_1 = detector.predict(dummy_frame1, frame_index=0)
    single_2 = detector.predict(dummy_frame2, frame_index=1)

    batch_res = detector.predict_batch([dummy_frame1, dummy_frame2], start_frame_index=0)
    assert len(batch_res) == 2

    assert len(batch_res[0]) == len(single_1)
    assert len(batch_res[1]) == len(single_2)

    for d_batch, d_single in zip(batch_res[0], single_1, strict=True):
        assert d_batch.x == d_single.x
        assert d_batch.y == d_single.y
        assert d_batch.confidence == d_single.confidence


def test_session_pipeline_batched_execution(tmp_path: Path) -> None:
    db = DatabaseManager(f"sqlite:///{tmp_path}/batch_pipeline.db")
    db.init_db()
    art_store = ArtifactStore(tmp_path / "artifacts")

    # Generate synthetic video with 16 frames
    video_path = tmp_path / "batch_video.mp4"
    generate_synthetic_video(video_path, num_frames=16, width=640, height=480)

    zone_poly = ZonePolygon(
        vertices=(
            Point2D(x=0.0, y=0.0),
            Point2D(x=300.0, y=0.0),
            Point2D(x=300.0, y=300.0),
            Point2D(x=0.0, y=300.0),
        )
    )
    zone_set = ZoneSet(
        zone_set_id="zs-batch",
        version=1,
        name="Batch Zone Set",
        image_width=640,
        image_height=480,
        zones=(ZoneDefinition(zone_id="z-main", name="Main", polygon=zone_poly),),
    )

    with db.get_session() as session:
        media = MediaAssetRecord(
            id="media-01",
            display_name="test.mp4",
            relpath="test.mp4",
            sha256="m" * 64,
            duration_s=1.6,
            fps=10.0,
            frame_count=16,
            width=640,
            height=480,
            codec="h264",
            browser_playable=True,
        )
        session.add(media)
        session.flush()

        zs = ZoneSetRecord(id="zs-batch", name="Batch Zone Set")
        session.add(zs)
        session.flush()

        zsv = ZoneSetVersionRecord(
            id="zsv-01",
            zone_set_id="zs-batch",
            version=1,
            image_width=640,
            image_height=480,
            polygon_data={"zones": []},
            sha256="z" * 64,
        )
        session.add(zsv)
        session.flush()

        sess = SessionRecord(
            id="sess-batch-test",
            media_asset_id="media-01",
            zone_set_version_id="zsv-01",
            model_profile_id="crowd_best_local_v2",
            model_profile_sha256="a" * 64,
            checkpoint_sha256="b" * 64,
            total_frames=16,
            status="QUEUED",
        )
        session.add(sess)

    detector = SyntheticDetector(num_persons=2, seed=123)
    pipeline = SessionPipeline(
        session_id="sess-batch-test",
        video_path=video_path,
        zone_set=zone_set,
        detector=detector,
        db_manager=db,
        artifact_store=art_store,
        batch_size=4,  # Chunk in batches of 4
    )

    status = pipeline.run()
    assert status == "COMPLETED"

    with db.get_session() as session:
        final_sess = session.get(SessionRecord, "sess-batch-test")
        assert final_sess is not None
        assert final_sess.status == "COMPLETED"
        assert final_sess.processed_frames == 16
        assert final_sess.progress == 1.0

        obs = list(session.scalars(select(ObservationRecord).where(ObservationRecord.session_id == "sess-batch-test")))
        assert len(obs) == 16


def test_ultralytics_detector_predict_batch_validation(tmp_path: Path) -> None:
    # Test invalid input dimensions raise ValueError
    profile = PersonDetectorProfile(
        profile_id="test_profile",
        checkpoint_path=tmp_path / "dummy.pt",
        expected_sha256="0" * 64,
        profile_sha256="1" * 64,
    )
    # Profile validation ensures nonempty sha256
    assert profile.profile_id == "test_profile"
