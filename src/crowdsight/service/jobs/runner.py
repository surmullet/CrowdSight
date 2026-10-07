"""Job orchestration, cancellation tracking, and crash recovery."""
from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import select

from crowdsight.service.artifacts.store import ArtifactStore
from crowdsight.service.domain.zones import Point2D, ZoneDefinition, ZonePolygon, ZoneSet
from crowdsight.service.pipeline.runner import SessionPipeline
from crowdsight.service.storage.database import DatabaseManager
from crowdsight.service.storage.media_registry import MediaRegistry
from crowdsight.service.storage.models import (
    AuditLogRecord,
    SessionRecord,
    ZoneSetVersionRecord,
)

logger = logging.getLogger("crowdsight.jobs")


class JobManager:
    """Manages session processing jobs, cancellation flags, and worker recovery."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        media_registry: MediaRegistry,
        artifact_store: ArtifactStore | None = None,
    ) -> None:
        self.db_manager = db_manager
        self.media_registry = media_registry
        self.artifact_store = artifact_store
        self._cancellation_requests: set[str] = set()

    def recover_orphaned_jobs(self) -> int:
        """Find jobs left in RUNNING on startup and mark as FAILED."""
        recovered = 0
        with self.db_manager.get_session() as session:
            stmt = select(SessionRecord).where(SessionRecord.status.in_(["RUNNING", "CANCELLING"]))
            orphaned = list(session.scalars(stmt))
            for job in orphaned:
                job.status = "FAILED"
                job.error_code = "WORKER_CRASH_RECOVERED"
                job.user_action_hint = "The processing worker was restarted while this job was running. Please retry the analysis."
                recovered += 1

                audit = AuditLogRecord(
                    action="JOB_RECOVERED_FROM_CRASH",
                    entity_type="session",
                    entity_id=job.id,
                    details={"previous_status": job.status},
                )
                session.add(audit)
        return recovered

    def request_cancellation(self, session_id: str) -> bool:
        """Cooperatively request cancellation of an active session."""
        self._cancellation_requests.add(session_id)
        with self.db_manager.get_session() as session:
            job = session.get(SessionRecord, session_id)
            if job and job.status in ("QUEUED", "RUNNING"):
                job.status = "CANCELLING"
                return True
        return False

    def is_cancelled(self, session_id: str) -> bool:
        return session_id in self._cancellation_requests

    def clear_cancellation(self, session_id: str) -> None:
        self._cancellation_requests.discard(session_id)

    def run_session_job(
        self,
        session_id: str,
        detector: object | None = None,
    ) -> str:
        """Execute a session pipeline synchronously."""
        with self.db_manager.get_session() as session:
            job = session.get(SessionRecord, session_id)
            if not job:
                raise ValueError(f"Session not found: {session_id}")

            job.status = "RUNNING"
            session.commit()

            zone_version = session.get(ZoneSetVersionRecord, job.zone_set_version_id)
            if not zone_version:
                raise ValueError(f"Zone set version {job.zone_set_version_id} not found")

            # Reconstruct domain ZoneSet
            zone_defs: list[ZoneDefinition] = []
            for z_data in zone_version.polygon_data.get("zones", []):
                poly_verts = tuple(Point2D(x=p[0], y=p[1]) for p in z_data["vertices"])
                blind_polys = tuple(
                    ZonePolygon(vertices=tuple(Point2D(x=p[0], y=p[1]) for p in b))
                    for b in z_data.get("blind_regions", [])
                )
                zone_defs.append(
                    ZoneDefinition(
                        zone_id=z_data["zone_id"],
                        name=z_data["name"],
                        polygon=ZonePolygon(vertices=poly_verts),
                        blind_regions=blind_polys,
                    )
                )

            zone_set = ZoneSet(
                zone_set_id=zone_version.zone_set_id,
                version=zone_version.version,
                name="Session Zone Set",
                image_width=zone_version.image_width,
                image_height=zone_version.image_height,
                zones=tuple(zone_defs),
            )

        video_path = self.media_registry.get_media_path(job.media_asset_id)

        if detector is None:
            from crowdsight.service.pipeline.model_boundary import (
                ModelBoundaryError,
                ModelBoundaryService,
            )

            try:
                boundary = ModelBoundaryService()
                conf_override = None
                imgsz_override = None
                if job.options:
                    if "confidence" in job.options:
                        try:
                            conf_override = float(job.options["confidence"])
                        except (ValueError, TypeError):
                            conf_override = None
                    if "image_size" in job.options:
                        try:
                            imgsz_override = int(job.options["image_size"])
                        except (ValueError, TypeError):
                            imgsz_override = None

                target_cfg = None
                model_opt = job.options.get("model_profile") if job.options else None
                if model_opt in ("crowd_best", "crowd_best_local_v2"):
                    target_cfg = Path("configs/models/crowd_best_local.yaml").resolve()
                elif model_opt in ("yolo11n", "yolo11n_local"):
                    target_cfg = Path("configs/models/yolo11n_local.yaml").resolve()

                detector, _ = boundary.create_detector(
                    config_path=target_cfg,
                    synthetic=job.synthetic,
                    enable_tracker=bool(job.options.get("enable_tracker", not job.synthetic)),
                    confidence_override=conf_override,
                    image_size_override=imgsz_override,
                )
            except ModelBoundaryError as mbe:
                with self.db_manager.get_session() as session:
                    sess_rec = session.get(SessionRecord, session_id)
                    if sess_rec:
                        sess_rec.status = "FAILED"
                        sess_rec.error_code = mbe.code
                        sess_rec.user_action_hint = mbe.message
                    session.commit()
                return "FAILED"
            except Exception as exc:
                with self.db_manager.get_session() as session:
                    sess_rec = session.get(SessionRecord, session_id)
                    if sess_rec:
                        sess_rec.status = "FAILED"
                        sess_rec.error_code = "DETECTOR_INITIALIZATION_FAILED"
                        sess_rec.user_action_hint = f"Failed to initialize detector: {exc}"
                    session.commit()
                return "FAILED"

        stride = int(job.options.get("frame_stride", 1)) if job.options else 1
        db_batch = int(job.options.get("db_batch_size", 30)) if job.options else 30
        pipeline = SessionPipeline(
            session_id=session_id,
            video_path=video_path,
            zone_set=zone_set,
            detector=detector,
            db_manager=self.db_manager,
            artifact_store=self.artifact_store,
            is_synthetic=job.synthetic,
            frame_stride=stride,
            db_batch_size=db_batch,
        )

        try:
            status = pipeline.run(cancellation_check=lambda: self.is_cancelled(session_id))
            return status
        except Exception as exc:
            logger.exception("Pipeline run failed for session %s: %s", session_id, exc)
            with self.db_manager.get_session() as session:
                sess_rec = session.get(SessionRecord, session_id)
                if sess_rec:
                    sess_rec.status = "FAILED"
                    sess_rec.error_code = "INFERENCE_PIPELINE_ERROR"
                    sess_rec.user_action_hint = str(exc)
            return "FAILED"
        finally:
            self.clear_cancellation(session_id)
