"""Session lifecycle, progress streaming (SSE), and cancellation endpoints."""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from crowdsight.service.api.deps import (
    get_artifact_store,
    get_db,
    get_job_manager,
)
from crowdsight.service.artifacts.store import ArtifactStore
from crowdsight.service.jobs.runner import JobManager
from crowdsight.service.pipeline.synthetic import (
    SYNTHETIC_CHECKPOINT_SHA256,
    SYNTHETIC_PROFILE_ID,
    SYNTHETIC_PROFILE_SHA256,
)
from crowdsight.service.storage.models import (
    ArtifactRecord,
    AuditLogRecord,
    MediaAssetRecord,
    SessionRecord,
    ZoneSetVersionRecord,
)

router = APIRouter(prefix="/api/v1/sessions", tags=["Analysis Sessions"])


class SessionCreateRequest(BaseModel):
    media_asset_id: str
    zone_set_version_id: str
    options: dict[str, Any] = Field(default_factory=dict)
    use_synthetic: bool = True  # Default to True for zero-weight environments


class SessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    media_asset_id: str
    zone_set_version_id: str
    model_profile_id: str
    model_profile_sha256: str
    checkpoint_sha256: str
    tracker_config_sha256: str | None
    options: dict[str, Any]
    status: str
    progress: float
    processed_frames: int
    total_frames: int
    error_code: str | None
    user_action_hint: str | None
    synthetic: bool
    completeness: str
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=list[SessionResponse], summary="List analysis sessions")
def list_sessions(
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[SessionRecord]:
    stmt = select(SessionRecord).order_by(SessionRecord.created_at.desc())
    if status:
        stmt = stmt.where(SessionRecord.status == status)
    stmt = stmt.limit(limit)
    return list(db.scalars(stmt))


@router.post("", response_model=SessionResponse, status_code=201, summary="Create and start a new analysis session")
def create_session(
    payload: SessionCreateRequest,
    background_tasks: BackgroundTasks,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    job_mgr: JobManager = Depends(get_job_manager),
) -> SessionRecord:
    media = db.get(MediaAssetRecord, payload.media_asset_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media asset not found")

    zsv = db.get(ZoneSetVersionRecord, payload.zone_set_version_id)
    if not zsv:
        raise HTTPException(status_code=404, detail="Zone set version not found")

    # Set up provenance
    profile_id = SYNTHETIC_PROFILE_ID
    profile_sha256 = SYNTHETIC_PROFILE_SHA256
    checkpoint_sha256 = SYNTHETIC_CHECKPOINT_SHA256

    sess_record = SessionRecord(
        media_asset_id=media.id,
        zone_set_version_id=zsv.id,
        model_profile_id=profile_id,
        model_profile_sha256=profile_sha256,
        checkpoint_sha256=checkpoint_sha256,
        tracker_config_sha256=None,
        options=payload.options,
        status="QUEUED",
        synthetic=payload.use_synthetic,
        total_frames=media.frame_count,
        completeness="PENDING",
    )
    db.add(sess_record)
    db.commit()
    db.refresh(sess_record)
    session_id = sess_record.id

    # Enqueue pipeline run in background
    background_tasks.add_task(job_mgr.run_session_job, session_id)

    return sess_record


@router.get("/{session_id}", response_model=SessionResponse, summary="Get session state and progress")
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
) -> SessionRecord:
    job = db.get(SessionRecord, session_id)
    if not job:
        raise HTTPException(status_code=404, detail="Session not found")
    return job


@router.post("/{session_id}/cancel", summary="Request cooperative cancellation of a running session")
def cancel_session(
    session_id: str,
    db: Session = Depends(get_db),
    job_mgr: JobManager = Depends(get_job_manager),
) -> dict[str, str]:
    job = db.get(SessionRecord, session_id)
    if not job:
        raise HTTPException(status_code=404, detail="Session not found")

    if job.status not in ("QUEUED", "RUNNING"):
        return {"status": job.status, "message": "Job cannot be cancelled in current state"}

    job_mgr.request_cancellation(session_id)
    return {"status": "CANCELLING", "message": "Cancellation requested"}


@router.delete("/{session_id}", summary="Purge session, related records, and artifacts")
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    store: ArtifactStore = Depends(get_artifact_store),
) -> dict[str, str]:
    job = db.get(SessionRecord, session_id)
    if not job:
        raise HTTPException(status_code=404, detail="Session not found")

    # Delete on-disk artifacts
    artifacts = list(db.scalars(select(ArtifactRecord).where(ArtifactRecord.session_id == session_id)))
    for art in artifacts:
        try:
            store.delete_artifact(art.relpath)
        except Exception:
            pass

    # Record audit log
    audit = AuditLogRecord(
        action="SESSION_PURGED",
        entity_type="session",
        entity_id=session_id,
        details={"purged_at": datetime.utcnow().isoformat()},
    )
    db.add(audit)

    # Delete session (cascades to observations, zone_results, artifacts, notes)
    db.delete(job)
    return {"status": "DELETED", "session_id": session_id}


@router.get("/{session_id}/events", summary="Stream session progress via Server-Sent Events (SSE)")
async def stream_session_events(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    async def event_generator() -> AsyncGenerator[str, None]:
        while True:
            if await request.is_disconnected():
                break

            job = db.get(SessionRecord, session_id)
            if not job:
                yield f"event: error\ndata: {json.dumps({'error': 'Session not found'})}\n\n"
                break

            data = {
                "session_id": job.id,
                "status": job.status,
                "progress": job.progress,
                "processed_frames": job.processed_frames,
                "total_frames": job.total_frames,
                "error_code": job.error_code,
                "user_action_hint": job.user_action_hint,
            }
            yield f"event: progress\ndata: {json.dumps(data)}\n\n"

            if job.status in ("COMPLETED", "FAILED", "CANCELLED", "PARTIAL_CANCELLED"):
                yield f"event: done\ndata: {json.dumps({'status': job.status})}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
