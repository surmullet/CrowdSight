"""Analytics endpoints: trends, peak moments, heat maps, quality summaries, notes, and exports."""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import Response as FastApiResponse
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from crowdsight.service.analytics.exports import (
    DataExporter,
)
from crowdsight.service.analytics.heatmaps import ImageSpaceHeatmapGenerator
from crowdsight.service.analytics.peaks import PeakAnalyzer
from crowdsight.service.analytics.summary import QualitySummaryCalculator
from crowdsight.service.analytics.trends import (
    SeriesMode,
    TrendAnalyzer,
    TrendPoint,
    lttb_downsample,
)
from crowdsight.service.api.deps import get_artifact_store, get_db
from crowdsight.service.api.errors import APIProblemException
from crowdsight.service.artifacts.store import ArtifactStore
from crowdsight.service.domain.zones import ZoneSet
from crowdsight.service.storage.models import (
    ArtifactRecord,
    NoteRecord,
    ObservationRecord,
    SessionRecord,
    ZoneResultRecord,
    ZoneSetVersionRecord,
)

router = APIRouter(prefix="/api/v1/sessions/{session_id}", tags=["Analytics & Export"])


class TrendBucketModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bucket_index: int
    from_t: float
    to_t: float
    n_frames: int
    n_counted: int
    availability_ratio: float
    min: float | None = None
    mean: float | None = None
    median: float | None = None
    p95: float | None = None
    max: float | None = None


class RawPointModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media_time_s: float
    visible_count: int | None = None
    availability: str


class SmoothedPointModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media_time_s: float
    smoothed_value: float | None = None
    is_derived: bool = True


class TrendsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    zone_id: str
    series_mode: SeriesMode
    bucket_s: float | None = None
    buckets: list[TrendBucketModel] | None = None
    raw_points: list[RawPointModel] | None = None
    smoothed_points: list[SmoothedPointModel] | None = None
    experimental_warning: str


class PeakMomentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zone_id: str
    media_time_s: float
    frame_index: int
    visible_count: int
    description: str
    description_vi: str


class PeaksResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    zone_id: str
    peaks: list[PeakMomentModel]
    experimental_warning: str


class HeatmapMetadataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    kind: str = "IMAGE_SPACE"
    image_width: int
    image_height: int
    window_from_t: float | None
    window_to_t: float | None
    frames_used: int
    frames_discarded: int
    normalization_method: str
    colormap: str
    sha256: str
    disclaimer: str


class HeatmapGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    window_from_t: float | None = None
    window_to_t: float | None = None
    normalization_method: Literal["SESSION_MAX", "WINDOW_MAX"] = "SESSION_MAX"


class NoteCreateModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media_time_s: float = Field(..., ge=0.0)
    zone_id: str | None = None
    text: str = Field(..., min_length=1, max_length=2000)
    author: str = "operator"


class NoteResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str
    media_time_s: float
    zone_id: str | None
    text: str
    author: str
    created_at: str


def _get_session_or_404(session_id: str, db: Session) -> SessionRecord:
    rec = db.scalar(select(SessionRecord).where(SessionRecord.id == session_id))
    if not rec:
        raise APIProblemException(
            status_code=404,
            title="Session Not Found",
            detail=f"Session with ID '{session_id}' does not exist.",
            code="SESSION_NOT_FOUND",
            user_action_hint="Verify session ID in URL.",
        )
    return rec


@router.get("/trends", response_model=TrendsResponse, summary="Query visible person time trends for a zone")
def get_trends(
    session_id: str,
    zone_id: str = Query(..., description="Target zone ID"),
    bucket_s: float = Query(1.0, ge=0.1, le=60.0, description="Bucket duration in seconds"),
    series: SeriesMode = Query(SeriesMode.BUCKETED, description="Series presentation mode"),
    max_points: int = Query(1000, ge=10, le=10000, description="Max downsample points"),
    db: Session = Depends(get_db),
) -> TrendsResponse:
    session = _get_session_or_404(session_id, db)

    stmt = (
        select(ZoneResultRecord)
        .where(ZoneResultRecord.session_id == session_id, ZoneResultRecord.zone_id == zone_id)
        .order_by(ZoneResultRecord.media_time_s.asc())
    )
    results = list(db.scalars(stmt))

    if not results:
        # Check if zone exists in zone set version
        zsv = db.scalar(select(ZoneSetVersionRecord).where(ZoneSetVersionRecord.id == session.zone_set_version_id))
        if zsv:
            known_zones = [z["zone_id"] for z in zsv.polygon_data.get("zones", [])]
            if zone_id not in known_zones:
                raise APIProblemException(
                    status_code=404,
                    title="Zone Not Found",
                    detail=f"Zone '{zone_id}' does not exist in this session's zone set.",
                    code="ZONE_NOT_FOUND",
                    user_action_hint="Specify a valid zone ID configured for this session.",
                )

    records = [
        {
            "media_time_s": r.media_time_s,
            "availability": r.availability,
            "visible_count": r.visible_count,
        }
        for r in results
    ]

    total_duration = float(session.media_asset.duration_s) if session.media_asset else None

    if series == SeriesMode.BUCKETED:
        buckets = TrendAnalyzer.compute_buckets(records, bucket_s=bucket_s, total_duration_s=total_duration)
        bucket_models = [
            TrendBucketModel(
                bucket_index=b.bucket_index,
                from_t=b.from_t,
                to_t=b.to_t,
                n_frames=b.n_frames,
                n_counted=b.n_counted,
                availability_ratio=b.availability_ratio,
                min=b.min,
                mean=b.mean,
                median=b.median,
                p95=b.p95,
                max=b.max,
            )
            for b in buckets
        ]
        return TrendsResponse(
            session_id=session_id,
            zone_id=zone_id,
            series_mode=series,
            bucket_s=bucket_s,
            buckets=bucket_models,
            experimental_warning="Thử nghiệm — mô hình chưa được duyệt cho vận hành thực tế. Có thể đếm thiếu ở cảnh đông.",
        )

    raw_points_list = [
        TrendPoint(
            media_time_s=r.media_time_s,
            visible_count=r.visible_count,
            availability=r.availability,
        )
        for r in results
    ]

    if series == SeriesMode.RAW:
        # Optional LTTB downsampling
        if len(raw_points_list) > max_points:
            pts_tuples = [(p.media_time_s, float(p.visible_count) if p.visible_count is not None else None) for p in raw_points_list]
            sampled = lttb_downsample(pts_tuples, max_points)
            # Reconstruct raw models
            sampled_models = [
                RawPointModel(
                    media_time_s=t,
                    visible_count=int(v) if v is not None else None,
                    availability="COUNTED" if v is not None else "UNKNOWN",
                )
                for t, v in sampled
            ]
            return TrendsResponse(
                session_id=session_id,
                zone_id=zone_id,
                series_mode=series,
                raw_points=sampled_models,
                experimental_warning="Thử nghiệm — mô hình chưa được duyệt cho vận hành thực tế. Có thể đếm thiếu ở cảnh đông.",
            )

        raw_models = [
            RawPointModel(media_time_s=p.media_time_s, visible_count=p.visible_count, availability=p.availability)
            for p in raw_points_list
        ]
        return TrendsResponse(
            session_id=session_id,
            zone_id=zone_id,
            series_mode=series,
            raw_points=raw_models,
            experimental_warning="Thử nghiệm — mô hình chưa được duyệt cho vận hành thực tế. Có thể đếm thiếu ở cảnh đông.",
        )

    # series == SeriesMode.SMOOTHED
    smoothed = TrendAnalyzer.compute_smoothed(raw_points_list)
    smoothed_models = [
        SmoothedPointModel(media_time_s=s.media_time_s, smoothed_value=s.smoothed_value, is_derived=True)
        for s in smoothed
    ]
    return TrendsResponse(
        session_id=session_id,
        zone_id=zone_id,
        series_mode=series,
        smoothed_points=smoothed_models,
        experimental_warning="Thử nghiệm — mô hình chưa được duyệt cho vận hành thực tế. Có thể đếm thiếu ở cảnh đông.",
    )


@router.get("/peaks", response_model=PeaksResponse, summary="Get highlight peak visible person moments")
def get_peaks(
    session_id: str,
    zone_id: str = Query(..., description="Target zone ID"),
    limit: int = Query(5, ge=1, le=50, description="Max highlights"),
    db: Session = Depends(get_db),
) -> PeaksResponse:
    _get_session_or_404(session_id, db)

    stmt = (
        select(ZoneResultRecord)
        .where(ZoneResultRecord.session_id == session_id, ZoneResultRecord.zone_id == zone_id)
        .order_by(ZoneResultRecord.media_time_s.asc())
    )
    results = list(db.scalars(stmt))
    records = [
        {
            "zone_id": r.zone_id,
            "media_time_s": r.media_time_s,
            "frame_index": r.frame_index,
            "visible_count": r.visible_count,
            "availability": r.availability,
        }
        for r in results
    ]

    peaks = PeakAnalyzer.find_peaks(records, zone_id=zone_id, limit=limit)
    peak_models = [
        PeakMomentModel(
            zone_id=p.zone_id,
            media_time_s=p.media_time_s,
            frame_index=p.frame_index,
            visible_count=p.visible_count,
            description=p.description,
            description_vi=p.description_vi,
        )
        for p in peaks
    ]

    return PeaksResponse(
        session_id=session_id,
        zone_id=zone_id,
        peaks=peak_models,
        experimental_warning="Thử nghiệm — mô hình chưa được duyệt cho vận hành thực tế. Có thể đếm thiếu ở cảnh đông.",
    )


@router.get("/summary", summary="Get comprehensive session quality summary")
def get_quality_summary(
    session_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    session = _get_session_or_404(session_id, db)

    obs_records = list(
        db.scalars(
            select(ObservationRecord)
            .where(ObservationRecord.session_id == session_id)
            .order_by(ObservationRecord.frame_index.asc())
        )
    )
    zone_res_records = list(
        db.scalars(
            select(ZoneResultRecord)
            .where(ZoneResultRecord.session_id == session_id)
        )
    )

    zsv = db.scalar(select(ZoneSetVersionRecord).where(ZoneSetVersionRecord.id == session.zone_set_version_id))
    zone_ids = [z["zone_id"] for z in zsv.polygon_data.get("zones", [])] if zsv else []

    obs_dicts = [
        {
            "frame_index": o.frame_index,
            "media_time_s": o.media_time_s,
            "quality": o.quality,
            "reason_code": o.reason_code,
            "detections": o.payload_v1.get("detections", []),
        }
        for o in obs_records
    ]
    zone_res_dicts = [
        {
            "zone_id": zr.zone_id,
            "availability": zr.availability,
            "visible_count": zr.visible_count,
        }
        for zr in zone_res_records
    ]

    duration = float(session.media_asset.duration_s) if session.media_asset else 0.0

    summary = QualitySummaryCalculator.calculate(
        session_id=session_id,
        observations=obs_dicts,
        zone_results=zone_res_dicts,
        zone_ids=zone_ids,
        duration_s=duration,
        synthetic=session.synthetic,
        completeness=session.completeness,
        applicability_snapshot=session.applicability_snapshot,
    )

    return {
        "session_id": summary.session_id,
        "total_frames": summary.total_frames,
        "duration_s": summary.duration_s,
        "processing_fps": summary.processing_fps,
        "valid_frames": summary.valid_frames,
        "partial_frames": summary.partial_frames,
        "unknown_frames": summary.unknown_frames,
        "stale_frames": summary.stale_frames,
        "valid_ratio": summary.valid_ratio,
        "partial_ratio": summary.partial_ratio,
        "unknown_ratio": summary.unknown_ratio,
        "stale_ratio": summary.stale_ratio,
        "zone_availability": {
            k: {
                "zone_id": v.zone_id,
                "n_frames": v.n_frames,
                "n_counted": v.n_counted,
                "availability_ratio": v.availability_ratio,
            }
            for k, v in summary.zone_availability.items()
        },
        "reason_code_distribution": summary.reason_code_distribution,
        "raw_score_distribution": [
            {
                "bin_range": b.bin_range,
                "lower": b.lower,
                "upper": b.upper,
                "count": b.count,
                "ratio": b.ratio,
            }
            for b in summary.raw_score_distribution
        ],
        "synthetic": summary.synthetic,
        "completeness": summary.completeness,
        "applicability_status": summary.applicability_status,
        "operational_alerts_allowed": summary.operational_alerts_allowed,
        "experimental_warning": summary.experimental_warning,
    }


@router.post("/heatmaps", response_model=HeatmapMetadataModel, summary="Generate an image-space relative heat map")
def generate_heatmap(
    session_id: str,
    body: HeatmapGenerateRequest,
    db: Session = Depends(get_db),
    artifact_store: ArtifactStore = Depends(get_artifact_store),
) -> HeatmapMetadataModel:
    session = _get_session_or_404(session_id, db)

    obs_records = list(
        db.scalars(
            select(ObservationRecord)
            .where(ObservationRecord.session_id == session_id)
            .order_by(ObservationRecord.frame_index.asc())
        )
    )

    zsv = db.scalar(select(ZoneSetVersionRecord).where(ZoneSetVersionRecord.id == session.zone_set_version_id))
    zone_set: ZoneSet | None = None
    if zsv:
        from crowdsight.service.domain.zones import Point2D, ZoneDefinition, ZonePolygon

        zone_defs: list[ZoneDefinition] = []
        for zd in zsv.polygon_data.get("zones", []):
            poly_verts = tuple(Point2D(x=p[0], y=p[1]) for p in zd["vertices"])
            blind_polys = tuple(
                ZonePolygon(vertices=tuple(Point2D(x=p[0], y=p[1]) for p in b))
                for b in zd.get("blind_regions", [])
            )
            zone_defs.append(
                ZoneDefinition(
                    zone_id=zd["zone_id"],
                    name=zd["name"],
                    polygon=ZonePolygon(vertices=poly_verts),
                    blind_regions=blind_polys,
                )
            )
        zone_set = ZoneSet(
            zone_set_id=zsv.zone_set_id,
            version=zsv.version,
            name="Session Zone Set",
            image_width=zsv.image_width,
            image_height=zsv.image_height,
            zones=tuple(zone_defs),
        )

    w = session.media_asset.width if session.media_asset else 1920
    h = session.media_asset.height if session.media_asset else 1080

    obs_dicts = [
        {
            "media_time_s": o.media_time_s,
            "quality": o.quality,
            "fully_observed_zones": o.payload_v1.get("fully_observed_zones", []),
            "detections": o.payload_v1.get("detections", []),
        }
        for o in obs_records
    ]

    res = ImageSpaceHeatmapGenerator.generate(
        observations=obs_dicts,
        image_width=w,
        image_height=h,
        zone_set=zone_set,
        window_from_t=body.window_from_t,
        window_to_t=body.window_to_t,
        normalization_method=body.normalization_method,
    )

    art_id, relpath, digest = artifact_store.save_bytes(
        res.png_bytes,
        kind="IMAGE_SPACE",
        suffix=".png",
        session_id=session_id,
    )

    art_rec = ArtifactRecord(
        id=art_id,
        session_id=session_id,
        kind="IMAGE_SPACE",
        relpath=relpath,
        sha256=digest,
    )
    db.add(art_rec)
    db.commit()

    return HeatmapMetadataModel(
        artifact_id=art_id,
        kind="IMAGE_SPACE",
        image_width=res.metadata.image_width,
        image_height=res.metadata.image_height,
        window_from_t=res.metadata.window_from_t,
        window_to_t=res.metadata.window_to_t,
        frames_used=res.metadata.frames_used,
        frames_discarded=res.metadata.frames_discarded,
        normalization_method=res.metadata.normalization_method,
        colormap=res.metadata.colormap,
        sha256=digest,
        disclaimer=res.metadata.disclaimer,
    )


@router.get("/heatmaps/{artifact_id}", summary="Download heat map image or metadata")
def get_heatmap_artifact(
    session_id: str,
    artifact_id: str,
    db: Session = Depends(get_db),
    artifact_store: ArtifactStore = Depends(get_artifact_store),
) -> FastApiResponse:
    art = db.scalar(
        select(ArtifactRecord).where(
            ArtifactRecord.id == artifact_id,
            ArtifactRecord.session_id == session_id,
        )
    )
    if not art:
        raise APIProblemException(
            status_code=404,
            title="Artifact Not Found",
            detail=f"Heatmap artifact '{artifact_id}' not found.",
            code="ARTIFACT_NOT_FOUND",
        )

    file_bytes = artifact_store.get_path(art.relpath).read_bytes()
    return FastApiResponse(
        content=file_bytes,
        media_type="image/png",
        headers={
            "X-CrowdSight-Kind": "IMAGE_SPACE",
            "X-CrowdSight-SHA256": art.sha256,
        },
    )


@router.get("/notes", response_model=list[NoteResponseModel], summary="List operator notes for session")
def list_notes(
    session_id: str,
    db: Session = Depends(get_db),
) -> list[NoteResponseModel]:
    _get_session_or_404(session_id, db)
    notes = list(
        db.scalars(
            select(NoteRecord)
            .where(NoteRecord.session_id == session_id)
            .order_by(NoteRecord.media_time_s.asc())
        )
    )
    return [
        NoteResponseModel(
            id=n.id,
            session_id=n.session_id,
            media_time_s=n.media_time_s,
            zone_id=n.zone_id,
            text=n.text,
            author=n.author,
            created_at=n.created_at.isoformat(),
        )
        for n in notes
    ]


@router.post("/notes", response_model=NoteResponseModel, summary="Create an operator note")
def create_note(
    session_id: str,
    body: NoteCreateModel,
    db: Session = Depends(get_db),
) -> NoteResponseModel:
    _get_session_or_404(session_id, db)
    note = NoteRecord(
        session_id=session_id,
        media_time_s=body.media_time_s,
        zone_id=body.zone_id,
        text=body.text,
        author=body.author,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    return NoteResponseModel(
        id=note.id,
        session_id=note.session_id,
        media_time_s=note.media_time_s,
        zone_id=note.zone_id,
        text=note.text,
        author=note.author,
        created_at=note.created_at.isoformat(),
    )


@router.delete("/notes/{note_id}", status_code=204, summary="Delete an operator note")
def delete_note(
    session_id: str,
    note_id: str,
    db: Session = Depends(get_db),
) -> Response:
    rec = db.scalar(
        select(NoteRecord).where(
            NoteRecord.id == note_id,
            NoteRecord.session_id == session_id,
        )
    )
    if not rec:
        raise APIProblemException(
            status_code=404,
            title="Note Not Found",
            detail=f"Note '{note_id}' not found.",
            code="NOTE_NOT_FOUND",
        )
    db.delete(rec)
    db.commit()
    return Response(status_code=204)


@router.get("/export", summary="Export session observation archive or CSV counts")
def export_session(
    session_id: str,
    format: Literal["jsonl", "csv"] = Query("jsonl", description="Export format"),
    db: Session = Depends(get_db),
) -> FastApiResponse:
    session = _get_session_or_404(session_id, db)

    session_info = {
        "id": session.id,
        "model_profile_id": session.model_profile_id,
        "model_profile_sha256": session.model_profile_sha256,
        "checkpoint_sha256": session.checkpoint_sha256,
        "tracker_config_sha256": session.tracker_config_sha256,
        "synthetic": session.synthetic,
        "applicability_snapshot": session.applicability_snapshot,
    }

    zone_results = list(
        db.scalars(
            select(ZoneResultRecord)
            .where(ZoneResultRecord.session_id == session_id)
            .order_by(ZoneResultRecord.frame_index.asc())
        )
    )
    zone_dicts = [
        {
            "frame_index": zr.frame_index,
            "media_time_s": zr.media_time_s,
            "zone_id": zr.zone_id,
            "availability": zr.availability,
            "visible_count": zr.visible_count,
        }
        for zr in zone_results
    ]

    if format == "csv":
        csv_text = DataExporter.export_csv(session_info, zone_dicts)
        return FastApiResponse(
            content=csv_text,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="crowdsight_session_{session_id[:8]}_counts.csv"',
                "X-CrowdSight-Disclaimer": "EXPERIMENTAL_NO_APPROVAL",
            },
        )

    # format == "jsonl"
    obs_records = list(
        db.scalars(
            select(ObservationRecord)
            .where(ObservationRecord.session_id == session_id)
            .order_by(ObservationRecord.frame_index.asc())
        )
    )
    obs_dicts = [
        {
            "frame_index": o.frame_index,
            "media_time_s": o.media_time_s,
            "quality": o.quality,
            "payload_v1": o.payload_v1,
        }
        for o in obs_records
    ]

    generator = DataExporter.export_jsonl(session_info, obs_dicts, zone_dicts)
    return StreamingResponse(
        generator,
        media_type="application/x-ndjson; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="crowdsight_session_{session_id[:8]}_archive.jsonl"',
            "X-CrowdSight-Disclaimer": "EXPERIMENTAL_NO_APPROVAL",
        },
    )
