"""Session lifecycle, progress streaming (SSE), and cancellation endpoints."""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
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
    ObservationRecord,
    SessionRecord,
    ZoneResultRecord,
    ZoneSetRecord,
    ZoneSetVersionRecord,
)

router = APIRouter(prefix="/api/v1/sessions", tags=["Analysis Sessions"])


class SessionCreateRequest(BaseModel):
    media_asset_id: str
    zone_set_version_id: str
    options: dict[str, Any] = Field(default_factory=dict)
    use_synthetic: bool = False  # Default to False for real AI execution
    synthetic: bool | None = None


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
    media_name: str | None = None
    zone_set_name: str | None = None
    video_src: str | None = None
    duration_s: float | None = None


def _to_session_response(sess: SessionRecord, db: Session) -> SessionResponse:
    media = db.get(MediaAssetRecord, sess.media_asset_id)
    zsv = db.get(ZoneSetVersionRecord, sess.zone_set_version_id)
    media_name = media.display_name if media else None
    duration_s = media.duration_s if media else None
    video_src = f"/api/v1/media/{media.id}/stream" if media else None
    if media and (media.display_name == "crowd6.mp4" or "crowd6" in media.relpath.lower()):
        video_src = "/crowd6.mp4"
    elif media and (media.display_name == "150.mp4" or "150" in media.relpath.lower()):
        video_src = "/150.mp4"

    zone_set_name = None
    if zsv and zsv.zone_set:
        zone_set_name = zsv.zone_set.name
    elif zsv:
        zs = db.get(ZoneSetRecord, zsv.zone_set_id)
        if zs:
            zone_set_name = zs.name

    return SessionResponse(
        id=sess.id,
        media_asset_id=sess.media_asset_id,
        zone_set_version_id=sess.zone_set_version_id,
        model_profile_id=sess.model_profile_id,
        model_profile_sha256=sess.model_profile_sha256,
        checkpoint_sha256=sess.checkpoint_sha256,
        tracker_config_sha256=sess.tracker_config_sha256,
        options=sess.options,
        status=sess.status,
        progress=sess.progress,
        processed_frames=sess.processed_frames,
        total_frames=sess.total_frames,
        error_code=sess.error_code,
        user_action_hint=sess.user_action_hint,
        synthetic=sess.synthetic,
        completeness=sess.completeness,
        created_at=sess.created_at,
        updated_at=sess.updated_at,
        media_name=media_name,
        zone_set_name=zone_set_name,
        video_src=video_src,
        duration_s=duration_s,
    )


@router.get("", response_model=list[SessionResponse], summary="List analysis sessions")
def list_sessions(
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[SessionResponse]:
    stmt = select(SessionRecord).order_by(SessionRecord.created_at.desc())
    if status:
        stmt = stmt.where(SessionRecord.status == status)
    stmt = stmt.limit(limit)
    records = list(db.scalars(stmt))
    return [_to_session_response(r, db) for r in records]


@router.post("", response_model=SessionResponse, status_code=201, summary="Create and start a new analysis session")
def create_session(
    payload: SessionCreateRequest,
    background_tasks: BackgroundTasks,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    job_mgr: JobManager = Depends(get_job_manager),
) -> SessionResponse:
    media = db.get(MediaAssetRecord, payload.media_asset_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media asset not found")

    zsv = db.get(ZoneSetVersionRecord, payload.zone_set_version_id)
    if not zsv:
        # Check if zone_set_version_id was actually zone_set_id
        stmt = (
            select(ZoneSetVersionRecord)
            .where(ZoneSetVersionRecord.zone_set_id == payload.zone_set_version_id)
            .order_by(ZoneSetVersionRecord.version.desc())
        )
        zsv = db.scalars(stmt).first()
    if not zsv:
        raise HTTPException(status_code=404, detail="Zone set version not found")

    is_synthetic = payload.synthetic if payload.synthetic is not None else payload.use_synthetic

    # Set up provenance
    if is_synthetic:
        profile_id = SYNTHETIC_PROFILE_ID
        profile_sha256 = SYNTHETIC_PROFILE_SHA256
        checkpoint_sha256 = SYNTHETIC_CHECKPOINT_SHA256
        tracker_sha256 = None
    else:
        from crowdsight.service.pipeline.model_boundary import ModelBoundaryService
        boundary = ModelBoundaryService()
        enable_tracker = bool(payload.options.get("enable_tracker", True))
        try:
            _, prov = boundary.create_detector(synthetic=False, enable_tracker=enable_tracker)
            if isinstance(prov, dict):
                profile_id = prov.get("profile_id", "crowd_best_local_v2")
                profile_sha256 = prov.get("profile_sha256", "")
                checkpoint_sha256 = prov.get("checkpoint_sha256", "")
                tracker_sha256 = prov.get("tracker_config_sha256")
            else:
                profile_id = getattr(prov, "model_profile_id", getattr(prov, "profile_id", "crowd_best_local_v2"))
                profile_sha256 = getattr(prov, "model_profile_sha256", getattr(prov, "profile_sha256", ""))
                checkpoint_sha256 = getattr(prov, "checkpoint_sha256", "")
                tracker_sha256 = getattr(prov, "tracker_config_sha256", None)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Model boundary verification failed: {e}")

    sess_record = SessionRecord(
        media_asset_id=media.id,
        zone_set_version_id=zsv.id,
        model_profile_id=profile_id,
        model_profile_sha256=profile_sha256,
        checkpoint_sha256=checkpoint_sha256,
        tracker_config_sha256=tracker_sha256,
        options=payload.options,
        status="QUEUED",
        synthetic=is_synthetic,
        total_frames=media.frame_count,
        completeness="PENDING",
    )
    db.add(sess_record)
    db.commit()
    db.refresh(sess_record)
    session_id = sess_record.id

    # Enqueue pipeline run in background
    background_tasks.add_task(job_mgr.run_session_job, session_id)

    return _to_session_response(sess_record, db)


@router.get("/{session_id}", response_model=SessionResponse, summary="Get session state and progress")
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
) -> SessionResponse:
    job = db.get(SessionRecord, session_id)
    if not job:
        raise HTTPException(status_code=404, detail="Session not found")
    return _to_session_response(job, db)


@router.get("/{session_id}/dataset", summary="Download complete session observation dataset JSON for smooth frontend playback")
def get_session_dataset(
    session_id: str,
    db: Session = Depends(get_db),
    store: ArtifactStore = Depends(get_artifact_store),
) -> Response:
    job = db.get(SessionRecord, session_id)
    if not job:
        raise HTTPException(status_code=404, detail="Session not found")

    # 1. Check for DATASET_EXPORT artifact
    art_stmt = (
        select(ArtifactRecord)
        .where(ArtifactRecord.session_id == session_id, ArtifactRecord.kind == "DATASET_EXPORT")
        .order_by(ArtifactRecord.created_at.desc())
    )
    art = db.scalars(art_stmt).first()
    if art:
        try:
            path = store.get_path(art.relpath)
            return FileResponse(path=path, media_type="application/json", filename=f"session_{session_id}_observations.json")
        except Exception:
            pass

    # 2. Dynamic fallback: reconstruct from ObservationRecord & ZoneResultRecord in SQLite
    obs_stmt = (
        select(ObservationRecord)
        .where(ObservationRecord.session_id == session_id)
        .order_by(ObservationRecord.frame_index.asc())
    )
    obs_records = list(db.scalars(obs_stmt))

    zr_stmt = (
        select(ZoneResultRecord)
        .where(ZoneResultRecord.session_id == session_id)
        .order_by(ZoneResultRecord.frame_index.asc())
    )
    zr_records = list(db.scalars(zr_stmt))

    # Group zone results by frame_index
    zr_by_frame: dict[int, list[ZoneResultRecord]] = {}
    for zr in zr_records:
        zr_by_frame.setdefault(zr.frame_index, []).append(zr)

    media = db.get(MediaAssetRecord, job.media_asset_id)
    zsv = db.get(ZoneSetVersionRecord, job.zone_set_version_id)

    palette = ["#0072B2", "#009E73", "#D55E00", "#CC79A7", "#F0E442"]
    zones_list = []
    if zsv and "zones" in zsv.polygon_data:
        for idx, zd in enumerate(zsv.polygon_data["zones"]):
            zones_list.append({
                "zone_id": zd["zone_id"],
                "name": zd["name"],
                "color": palette[idx % len(palette)],
                "vertices": zd["vertices"],
            })

    frames_list = []
    for obs in obs_records:
        payload = obs.payload_v1 or {}
        z_readings = [
            {
                "status": r.availability,
                "count": r.visible_count if r.availability == "COUNTED" else 0,
                "zoneId": r.zone_id,
                "zoneName": next((z["name"] for z in zones_list if z["zone_id"] == r.zone_id), r.zone_id),
            }
            for r in zr_by_frame.get(obs.frame_index, [])
        ]
        detections = payload.get("detections", [])
        frames_list.append({
            "frame_index": obs.frame_index,
            "media_time_s": obs.media_time_s,
            "quality": obs.quality,
            "detections": detections,
            "zone_readings": z_readings,
        })

    dataset = {
        "metadata": {
            "sessionId": job.id,
            "sourceId": media.display_name if media else "video.mp4",
            "mediaName": media.display_name if media else "video.mp4",
            "duration": media.duration_s if media else (len(frames_list) / 25.0),
            "fps": media.fps if media else 25.0,
            "width": media.width if media else 1280,
            "height": media.height if media else 720,
            "totalFrames": len(frames_list),
            "model": job.model_profile_id,
            "confidence": 0.25,
            "tracker": "BoT-SORT",
        },
        "zones": zones_list,
        "frames": frames_list,
    }
    return Response(content=json.dumps(dataset), media_type="application/json")


@router.get("/{session_id}/heatmap", summary="Download session heatmap PNG image")
def get_session_heatmap(
    session_id: str,
    db: Session = Depends(get_db),
    store: ArtifactStore = Depends(get_artifact_store),
) -> FileResponse:
    job = db.get(SessionRecord, session_id)
    if not job:
        raise HTTPException(status_code=404, detail="Session not found")

    art_stmt = (
        select(ArtifactRecord)
        .where(ArtifactRecord.session_id == session_id, ArtifactRecord.kind == "HEATMAP")
        .order_by(ArtifactRecord.created_at.desc())
    )
    art = db.scalars(art_stmt).first()
    if not art:
        raise HTTPException(status_code=404, detail="Heatmap artifact not found for session")

    try:
        path = store.get_path(art.relpath)
        return FileResponse(path=path, media_type="image/png", filename=f"heatmap_{session_id}.png")
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail="Heatmap file missing from artifact storage") from err


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
            # Emit both default data event and named progress event for maximum compatibility
            yield f"data: {json.dumps(data)}\n\n"
            yield f"event: progress\ndata: {json.dumps(data)}\n\n"

            if job.status in ("COMPLETED", "FAILED", "CANCELLED", "PARTIAL_CANCELLED"):
                yield f"data: {json.dumps({'status': job.status})}\n\n"
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
