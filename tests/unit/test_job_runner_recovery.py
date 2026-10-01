"""Tests for JobManager crash recovery and state transitions."""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from crowdsight.service.jobs.runner import JobManager
from crowdsight.service.storage.database import DatabaseManager
from crowdsight.service.storage.media_registry import MediaRegistry
from crowdsight.service.storage.models import (
    AuditLogRecord,
    MediaAssetRecord,
    SessionRecord,
    ZoneSetRecord,
    ZoneSetVersionRecord,
)


@pytest.fixture
def job_setup(tmp_path: Path) -> tuple[JobManager, DatabaseManager]:
    db = DatabaseManager(f"sqlite:///{tmp_path}/jobs.db")
    db.init_db()
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    registry = MediaRegistry(media_dir, db)
    manager = JobManager(db, registry)
    return manager, db


def test_recover_orphaned_jobs_on_worker_startup(job_setup: tuple[JobManager, DatabaseManager]) -> None:
    job_mgr, db = job_setup

    with db.get_session() as session:
        media = MediaAssetRecord(
            display_name="test.mp4",
            relpath="test.mp4",
            sha256="a" * 64,
            duration_s=10.0,
            fps=10.0,
            frame_count=100,
            width=640,
            height=480,
            codec="h264",
            browser_playable=True,
        )
        session.add(media)
        session.flush()

        zs = ZoneSetRecord(id="zs-rec", name="Recovery Zone Set")
        session.add(zs)
        session.flush()

        zsv = ZoneSetVersionRecord(
            zone_set_id="zs-rec",
            version=1,
            image_width=640,
            image_height=480,
            polygon_data={"zones": []},
            sha256="b" * 64,
        )
        session.add(zsv)
        session.flush()

        # Job 1 left in RUNNING (worker died)
        j1 = SessionRecord(
            media_asset_id=media.id,
            zone_set_version_id=zsv.id,
            model_profile_id="crowd_best_local_v2",
            model_profile_sha256="c" * 64,
            checkpoint_sha256="d" * 64,
            status="RUNNING",
        )
        # Job 2 left in CANCELLING
        j2 = SessionRecord(
            media_asset_id=media.id,
            zone_set_version_id=zsv.id,
            model_profile_id="crowd_best_local_v2",
            model_profile_sha256="c" * 64,
            checkpoint_sha256="d" * 64,
            status="CANCELLING",
        )
        # Job 3 already COMPLETED (should remain untouched)
        j3 = SessionRecord(
            media_asset_id=media.id,
            zone_set_version_id=zsv.id,
            model_profile_id="crowd_best_local_v2",
            model_profile_sha256="c" * 64,
            checkpoint_sha256="d" * 64,
            status="COMPLETED",
        )
        session.add_all([j1, j2, j3])

    recovered_count = job_mgr.recover_orphaned_jobs()
    assert recovered_count == 2

    with db.get_session() as session:
        jobs = list(session.scalars(select(SessionRecord).order_by(SessionRecord.created_at)))
        assert jobs[0].status == "FAILED"
        assert jobs[0].error_code == "WORKER_CRASH_RECOVERED"
        assert jobs[1].status == "FAILED"
        assert jobs[2].status == "COMPLETED"

        # Check audit log
        logs = list(session.scalars(select(AuditLogRecord)))
        assert len(logs) == 2
