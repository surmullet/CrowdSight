"""Tests verifying DB CHECK constraints enforce missing data != 0."""
from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from crowdsight.service.storage.database import DatabaseManager
from crowdsight.service.storage.models import (
    MediaAssetRecord,
    SessionRecord,
    ZoneResultRecord,
    ZoneSetRecord,
    ZoneSetVersionRecord,
)


@pytest.fixture
def in_memory_db() -> DatabaseManager:
    db = DatabaseManager("sqlite:///:memory:")
    db.init_db()
    return db


def test_zone_result_check_constraint_counted_requires_not_null(in_memory_db: DatabaseManager) -> None:
    with in_memory_db.get_session() as session:
        # Create media and zone set prerequisites
        media = MediaAssetRecord(
            display_name="test",
            relpath="test.mp4",
            sha256="a" * 64,
            duration_s=1.0,
            fps=10.0,
            frame_count=10,
            width=640,
            height=480,
            codec="h264",
            browser_playable=True,
        )
        session.add(media)
        session.flush()

        zs = ZoneSetRecord(id="zs-1", name="Zone Set 1")
        session.add(zs)
        session.flush()

        zsv = ZoneSetVersionRecord(
            zone_set_id="zs-1",
            version=1,
            image_width=640,
            image_height=480,
            polygon_data={"zones": []},
            sha256="b" * 64,
        )
        session.add(zsv)
        session.flush()

        sess = SessionRecord(
            media_asset_id=media.id,
            zone_set_version_id=zsv.id,
            model_profile_id="crowd_best_local_v2",
            model_profile_sha256="c" * 64,
            checkpoint_sha256="d" * 64,
            status="RUNNING",
        )
        session.add(sess)
        session.flush()

        # 1. Valid counted record -> should succeed
        valid_rec = ZoneResultRecord(
            session_id=sess.id,
            frame_index=0,
            media_time_s=0.0,
            zone_id="north-gate",
            availability="COUNTED",
            visible_count=3,
        )
        session.add(valid_rec)
        session.flush()

        # 2. COUNTED with visible_count=None -> must violate CHECK constraint!
        invalid_rec = ZoneResultRecord(
            session_id=sess.id,
            frame_index=1,
            media_time_s=0.1,
            zone_id="north-gate",
            availability="COUNTED",
            visible_count=None,
        )
        session.add(invalid_rec)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def test_zone_result_check_constraint_unknown_requires_null(in_memory_db: DatabaseManager) -> None:
    with in_memory_db.get_session() as session:
        media = MediaAssetRecord(
            display_name="test",
            relpath="test.mp4",
            sha256="a" * 64,
            duration_s=1.0,
            fps=10.0,
            frame_count=10,
            width=640,
            height=480,
            codec="h264",
            browser_playable=True,
        )
        session.add(media)
        session.flush()

        zs = ZoneSetRecord(id="zs-1", name="Zone Set 1")
        session.add(zs)
        session.flush()

        zsv = ZoneSetVersionRecord(
            zone_set_id="zs-1",
            version=1,
            image_width=640,
            image_height=480,
            polygon_data={"zones": []},
            sha256="b" * 64,
        )
        session.add(zsv)
        session.flush()

        sess = SessionRecord(
            media_asset_id=media.id,
            zone_set_version_id=zsv.id,
            model_profile_id="crowd_best_local_v2",
            model_profile_sha256="c" * 64,
            checkpoint_sha256="d" * 64,
            status="RUNNING",
        )
        session.add(sess)
        session.flush()

        # 1. UNKNOWN with visible_count=None -> valid
        valid_rec = ZoneResultRecord(
            session_id=sess.id,
            frame_index=0,
            media_time_s=0.0,
            zone_id="north-gate",
            availability="UNKNOWN",
            visible_count=None,
        )
        session.add(valid_rec)
        session.flush()

        # 2. UNKNOWN with visible_count=0 -> violates CHECK constraint!
        invalid_rec = ZoneResultRecord(
            session_id=sess.id,
            frame_index=1,
            media_time_s=0.1,
            zone_id="north-gate",
            availability="UNKNOWN",
            visible_count=0,
        )
        session.add(invalid_rec)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
