"""Tests for path traversal prevention and automated retention purge."""
from __future__ import annotations

import datetime as dt
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from crowdsight.service.artifacts.store import ArtifactSecurityError, ArtifactStore
from crowdsight.service.storage.models import (
    ArtifactRecord,
    AuditLogRecord,
    Base,
    MediaAssetRecord,
    ObservationRecord,
    SessionRecord,
    ZoneSetRecord,
    ZoneSetVersionRecord,
)
from crowdsight.service.storage.retention import RetentionManager


@pytest.fixture
def temp_store(tmp_path: Path) -> ArtifactStore:
    return ArtifactStore(tmp_path / "artifacts")


@pytest.fixture
def memory_db() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_path_traversal_prevention(temp_store: ArtifactStore) -> None:
    """ArtifactStore must raise ArtifactSecurityError on path traversal attempts."""
    traversal_payloads = [
        "../../etc/passwd",
        "..\\..\\windows\\win.ini",
        "/absolute/path/attempt",
        "\\system32\\cmd.exe",
        "C:\\Windows\\system32",
        "subfolder/../../escaped.bin",
        "nested/../../../root.txt",
    ]

    for payload in traversal_payloads:
        with pytest.raises(ArtifactSecurityError):
            temp_store._resolve_safe(payload)


def test_retention_purge_cascade(temp_store: ArtifactStore, memory_db: Session) -> None:
    """RetentionManager purges sessions older than max_age_days and removes disk files."""
    retention = RetentionManager(temp_store)

    # Setup parent records
    media = MediaAssetRecord(
        id="src-1",
        display_name="test.mp4",
        relpath="raw/test.mp4",
        sha256="abc",
        duration_s=60.0,
        fps=30.0,
        frame_count=1800,
        width=1920,
        height=1080,
        codec="h264",
        browser_playable=True,
    )
    memory_db.add(media)

    zone_set = ZoneSetRecord(id="zs-1", name="Test Zones")
    memory_db.add(zone_set)

    zsv = ZoneSetVersionRecord(
        id="zsv-1",
        zone_set_id="zs-1",
        version=1,
        image_width=1920,
        image_height=1080,
        polygon_data={"zones": []},
        sha256="zsv-sha",
    )
    memory_db.add(zsv)

    # 1. Create old session (40 days old)
    old_time = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=40)
    old_session = SessionRecord(
        id="old-session-123",
        media_asset_id="src-1",
        zone_set_version_id="zsv-1",
        model_profile_id="prof-1",
        model_profile_sha256="prof-sha",
        checkpoint_sha256="ckpt-sha",
        status="COMPLETED",
        created_at=old_time,
    )
    memory_db.add(old_session)

    # Add old session artifact on disk and in DB
    art_id, relpath, digest = temp_store.save_bytes(
        b"some old export data",
        kind="export",
        suffix=".jsonl",
        session_id="old-session-123",
    )
    disk_file = temp_store.get_path(relpath)
    assert disk_file.is_file()

    old_art = ArtifactRecord(
        id=art_id,
        session_id="old-session-123",
        kind="EXPORT",
        relpath=relpath,
        sha256=digest,
    )
    memory_db.add(old_art)

    # Add old observation
    old_obs = ObservationRecord(
        session_id="old-session-123",
        frame_index=0,
        media_time_s=0.0,
        quality="VALID",
        payload_v1={},
    )
    memory_db.add(old_obs)

    # 2. Create fresh session (2 days old)
    fresh_time = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=2)
    fresh_session = SessionRecord(
        id="fresh-session-456",
        media_asset_id="src-1",
        zone_set_version_id="zsv-1",
        model_profile_id="prof-1",
        model_profile_sha256="prof-sha",
        checkpoint_sha256="ckpt-sha",
        status="COMPLETED",
        created_at=fresh_time,
    )
    memory_db.add(fresh_session)
    memory_db.commit()

    # 3. Run purge with 30 days retention
    purged_count = retention.purge_expired_sessions(memory_db, max_age_days=30)
    assert purged_count == 1

    # Verify old session was deleted
    assert memory_db.get(SessionRecord, "old-session-123") is None
    # Verify old observation was deleted
    old_obs_check = memory_db.scalars(
        select(ObservationRecord).where(
            ObservationRecord.session_id == "old-session-123"
        )
    ).first()
    assert old_obs_check is None
    # Verify physical artifact file was unlinked from disk
    assert not disk_file.exists()

    # Verify fresh session remains untouched
    assert memory_db.get(SessionRecord, "fresh-session-456") is not None

    # Verify audit log entry was created
    audit_entry = memory_db.scalars(
        select(AuditLogRecord).where(
            AuditLogRecord.action == "SESSION_RETENTION_PURGED"
        )
    ).first()
    assert audit_entry is not None
    assert audit_entry.details["session_id"] == "old-session-123"
