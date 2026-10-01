"""SQLAlchemy 2.0 database models with invariant CHECK constraints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _gen_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class MediaAssetRecord(Base):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_uuid)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    relpath: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    duration_s: Mapped[float] = mapped_column(Float, nullable=False)
    fps: Mapped[float] = mapped_column(Float, nullable=False)
    frame_count: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    codec: Mapped[str] = mapped_column(String(64), nullable=False)
    browser_playable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    proxy_relpath: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    sessions: Mapped[list[SessionRecord]] = relationship(back_populates="media_asset", cascade="all, delete-orphan")


class ZoneSetRecord(Base):
    __tablename__ = "zone_sets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    versions: Mapped[list[ZoneSetVersionRecord]] = relationship(back_populates="zone_set", cascade="all, delete-orphan")


class ZoneSetVersionRecord(Base):
    __tablename__ = "zone_set_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_gen_uuid)
    zone_set_id: Mapped[str] = mapped_column(String(64), ForeignKey("zone_sets.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    image_width: Mapped[int] = mapped_column(Integer, nullable=False)
    image_height: Mapped[int] = mapped_column(Integer, nullable=False)
    polygon_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    zone_set: Mapped[ZoneSetRecord] = relationship(back_populates="versions")
    sessions: Mapped[list[SessionRecord]] = relationship(back_populates="zone_set_version")

    __table_args__ = (
        Index("ix_zone_set_version_unique", "zone_set_id", "version", unique=True),
    )


class SessionRecord(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_uuid)
    media_asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False)
    zone_set_version_id: Mapped[str] = mapped_column(String(64), ForeignKey("zone_set_versions.id"), nullable=False)
    model_profile_id: Mapped[str] = mapped_column(String(128), nullable=False)
    model_profile_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    checkpoint_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    tracker_config_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    options: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="QUEUED", nullable=False)
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    processed_frames: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_frames: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_action_hint: Mapped[str | None] = mapped_column(String(512), nullable=True)
    applicability_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completeness: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False)

    media_asset: Mapped[MediaAssetRecord] = relationship(back_populates="sessions")
    zone_set_version: Mapped[ZoneSetVersionRecord] = relationship(back_populates="sessions")
    observations: Mapped[list[ObservationRecord]] = relationship(back_populates="session", cascade="all, delete-orphan")
    zone_results: Mapped[list[ZoneResultRecord]] = relationship(back_populates="session", cascade="all, delete-orphan")
    artifacts: Mapped[list[ArtifactRecord]] = relationship(back_populates="session", cascade="all, delete-orphan")
    notes: Mapped[list[NoteRecord]] = relationship(back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_sessions_status", "status"),
        Index("ix_sessions_created_at", "created_at"),
    )


class ObservationRecord(Base):
    __tablename__ = "observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    frame_index: Mapped[int] = mapped_column(Integer, nullable=False)
    media_time_s: Mapped[float] = mapped_column(Float, nullable=False)
    quality: Mapped[str] = mapped_column(String(16), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload_v1: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    session: Mapped[SessionRecord] = relationship(back_populates="observations")

    __table_args__ = (
        Index("ix_obs_session_frame", "session_id", "frame_index"),
        Index("ix_obs_session_time", "session_id", "media_time_s"),
    )


class ZoneResultRecord(Base):
    __tablename__ = "zone_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    frame_index: Mapped[int] = mapped_column(Integer, nullable=False)
    media_time_s: Mapped[float] = mapped_column(Float, nullable=False)
    zone_id: Mapped[str] = mapped_column(String(64), nullable=False)
    availability: Mapped[str] = mapped_column(String(32), nullable=False)
    visible_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    session: Mapped[SessionRecord] = relationship(back_populates="zone_results")

    __table_args__ = (
        Index("ix_zone_results_session_time", "session_id", "media_time_s"),
        Index("ix_zone_results_session_zone", "session_id", "zone_id"),
        CheckConstraint(
            "(visible_count IS NOT NULL AND availability = 'COUNTED') OR "
            "(visible_count IS NULL AND availability != 'COUNTED')",
            name="ck_zone_result_visible_count_availability",
        ),
    )


class ArtifactRecord(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_uuid)
    session_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    relpath: Mapped[str] = mapped_column(String(1024), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[SessionRecord | None] = relationship(back_populates="artifacts")

    __table_args__ = (
        Index("ix_artifacts_session_kind", "session_id", "kind"),
        Index("ix_artifacts_expires_at", "expires_at"),
    )


class NoteRecord(Base):
    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    media_time_s: Mapped[float] = mapped_column(Float, nullable=False)
    zone_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(128), default="operator", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    session: Mapped[SessionRecord] = relationship(back_populates="notes")

    __table_args__ = (
        Index("ix_notes_session_time", "session_id", "media_time_s"),
    )


class AuditLogRecord(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_uuid)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    __table_args__ = (
        Index("ix_audit_log_timestamp", "timestamp"),
        Index("ix_audit_log_entity", "entity_type", "entity_id"),
    )
