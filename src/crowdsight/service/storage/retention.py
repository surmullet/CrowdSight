"""Data retention policy and cascade purge manager."""
from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from crowdsight.service.artifacts.store import ArtifactStore
from crowdsight.service.storage.models import (
    ArtifactRecord,
    AuditLogRecord,
    NoteRecord,
    ObservationRecord,
    SessionRecord,
    ZoneResultRecord,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class RetentionManager:
    """Manages data retention and automated purging of aged sessions and artifacts."""

    def __init__(self, artifact_store: ArtifactStore) -> None:
        self.artifact_store = artifact_store

    def purge_expired_sessions(
        self, db: Session, max_age_days: int, *, actor: str = "system_retention_worker"
    ) -> int:
        """Purge sessions older than max_age_days along with all associated artifacts.

        Returns:
            Number of sessions purged.
        """
        if max_age_days <= 0:
            return 0

        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=max_age_days)

        # Find sessions created before cutoff
        stmt = select(SessionRecord).where(SessionRecord.created_at < cutoff)
        old_sessions = list(db.scalars(stmt).all())

        if not old_sessions:
            return 0

        purged_count = 0
        for session in old_sessions:
            session_id = session.id

            # 1. Delete associated physical files
            artifact_stmt = select(ArtifactRecord).where(
                ArtifactRecord.session_id == session_id
            )
            artifacts = list(db.scalars(artifact_stmt).all())
            for art in artifacts:
                try:
                    self.artifact_store.delete_artifact(art.relpath)
                except Exception:
                    pass  # Continue purging even if individual file is missing

            # 2. Delete database records
            db.execute(
                delete(ZoneResultRecord).where(
                    ZoneResultRecord.session_id == session_id
                )
            )
            db.execute(
                delete(ObservationRecord).where(
                    ObservationRecord.session_id == session_id
                )
            )
            db.execute(
                delete(ArtifactRecord).where(ArtifactRecord.session_id == session_id)
            )
            db.execute(delete(NoteRecord).where(NoteRecord.session_id == session_id))
            db.execute(delete(SessionRecord).where(SessionRecord.id == session_id))

            # 3. Create audit log record
            audit = AuditLogRecord(
                action="SESSION_RETENTION_PURGED",
                entity_type="session",
                entity_id=session_id,
                details={
                    "session_id": session_id,
                    "actor": actor,
                    "max_age_days": max_age_days,
                    "created_at": session.created_at.isoformat(),
                    "artifacts_removed": len(artifacts),
                },
            )
            db.add(audit)
            purged_count += 1

        db.commit()
        return purged_count

    def purge_expired_artifacts(self, db: Session) -> int:
        """Purge temporary artifacts whose expires_at timestamp has passed."""
        now = dt.datetime.now(dt.timezone.utc)
        stmt = select(ArtifactRecord).where(
            ArtifactRecord.expires_at.is_not(None),
            ArtifactRecord.expires_at < now,
        )
        expired_artifacts = list(db.scalars(stmt).all())

        if not expired_artifacts:
            return 0

        for art in expired_artifacts:
            try:
                self.artifact_store.delete_artifact(art.relpath)
            except Exception:
                pass
            db.delete(art)

        db.commit()
        return len(expired_artifacts)
