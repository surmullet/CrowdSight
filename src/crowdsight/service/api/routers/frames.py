"""Frame-level observation queries and time-synchronized playback endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from crowdsight.service.api.deps import get_db
from crowdsight.service.domain.freshness import (
    FreshnessPolicy,
    apply_freshness_to_observation,
    assess_freshness,
)
from crowdsight.service.domain.models import CrowdFrameObservationV1, QualityState
from crowdsight.service.storage.models import (
    ObservationRecord,
    SessionRecord,
    ZoneResultRecord,
)

router = APIRouter(prefix="/api/v1/sessions", tags=["Frame Observations"])


class ZoneResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zone_id: str
    availability: str
    visible_count: int | None
    density_people_per_m2: float | None = None
    density_status: str = "UNAVAILABLE_NO_CALIBRATION"


class FrameDataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    frame_index: int
    media_time_s: float
    quality: str
    observation: dict[str, Any]
    zones: list[ZoneResultResponse]
    freshness: str


@router.get("/{session_id}/frames", summary="Query observations within a media time window")
def get_frames_in_range(
    session_id: str,
    from_t: float = Query(0.0, ge=0.0),
    to_t: float = Query(30.0, ge=0.0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    job = db.get(SessionRecord, session_id)
    if not job:
        raise HTTPException(status_code=404, detail="Session not found")

    stmt = (
        select(ObservationRecord)
        .where(
            ObservationRecord.session_id == session_id,
            ObservationRecord.media_time_s >= from_t,
            ObservationRecord.media_time_s <= to_t,
        )
        .order_by(ObservationRecord.media_time_s.asc())
        .limit(limit)
    )
    records = list(db.scalars(stmt))
    return [rec.payload_v1 for rec in records]


@router.get(
    "/{session_id}/frames/at",
    response_model=FrameDataResponse,
    summary="Get nearest frame observation at time t with freshness policy applied",
)
def get_frame_at_time(
    session_id: str,
    t: float = Query(..., ge=0.0, description="Playback media_time_s"),
    max_gap_s: float = Query(2.0, ge=0.1, le=10.0),
    db: Session = Depends(get_db),
) -> FrameDataResponse:
    job = db.get(SessionRecord, session_id)
    if not job:
        raise HTTPException(status_code=404, detail="Session not found")

    # Find nearest observation by media_time_s difference
    stmt = (
        select(ObservationRecord)
        .where(ObservationRecord.session_id == session_id)
        .order_by(func.abs(ObservationRecord.media_time_s - t))
        .limit(1)
    )
    nearest_obs = db.scalar(stmt)
    if not nearest_obs:
        raise HTTPException(status_code=404, detail="No observations found for session")

    # Parse and apply freshness
    raw_obs = CrowdFrameObservationV1.model_validate(nearest_obs.payload_v1)
    policy = FreshnessPolicy(max_gap_s=max_gap_s)
    assessment = assess_freshness(t, nearest_obs.media_time_s, policy)

    final_obs = apply_freshness_to_observation(raw_obs, t, policy)

    # Fetch zone results for this frame
    zr_stmt = select(ZoneResultRecord).where(
        ZoneResultRecord.session_id == session_id,
        ZoneResultRecord.frame_index == nearest_obs.frame_index,
    )
    zone_records = list(db.scalars(zr_stmt))

    zones_out: list[ZoneResultResponse] = []
    if final_obs.quality == QualityState.STALE:
        # If stale, all zones must report STALE and None count
        for zr in zone_records:
            zones_out.append(
                ZoneResultResponse(
                    zone_id=zr.zone_id,
                    availability="STALE",
                    visible_count=None,
                    density_people_per_m2=None,
                    density_status="UNAVAILABLE_NO_CALIBRATION",
                )
            )
    else:
        for zr in zone_records:
            zones_out.append(
                ZoneResultResponse(
                    zone_id=zr.zone_id,
                    availability=zr.availability,
                    visible_count=zr.visible_count,
                    density_people_per_m2=None,
                    density_status="UNAVAILABLE_NO_CALIBRATION",
                )
            )

    return FrameDataResponse(
        session_id=session_id,
        frame_index=nearest_obs.frame_index,
        media_time_s=nearest_obs.media_time_s,
        quality=final_obs.quality.value,
        observation=final_obs.model_dump(mode="json"),
        zones=zones_out,
        freshness=assessment.status,
    )
