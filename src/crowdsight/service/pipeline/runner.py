"""Video pipeline orchestrator: decoding, inference, zone aggregation, and persistence."""
from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from crowdsight.service.artifacts.store import ArtifactStore
from crowdsight.service.domain.aggregation import aggregate_frame
from crowdsight.service.domain.models import (
    CrowdFrameObservationV1,
    DetectionV1,
    QualityState,
)
from crowdsight.service.domain.zones import ZoneSet
from crowdsight.service.pipeline.decoder import DecodedFrame, VideoDecoder
from crowdsight.service.storage.database import DatabaseManager
from crowdsight.service.storage.models import (
    ArtifactRecord,
    ObservationRecord,
    SessionRecord,
    ZoneResultRecord,
)

logger = logging.getLogger("crowdsight.pipeline")


class PipelineInferenceError(RuntimeError):
    """Raised when pipeline fails due to excessive errors or unrecoverable state."""


class SessionPipeline:
    """Executes frame-by-frame processing for one video monitoring session."""

    def __init__(
        self,
        *,
        session_id: str,
        video_path: Path,
        zone_set: ZoneSet,
        detector: Any,  # Supports track(frame_bgr) or predict(frame_bgr)
        db_manager: DatabaseManager,
        artifact_store: ArtifactStore | None = None,
        is_synthetic: bool = False,
        max_consecutive_unknown: int = 30,
        max_unknown_rate: float = 0.5,
        frame_stride: int = 1,
        db_batch_size: int = 30,
    ) -> None:
        self.session_id = session_id
        self.video_path = video_path
        self.zone_set = zone_set
        self.detector = detector
        self.db_manager = db_manager
        if artifact_store is None:
            self.artifact_store = ArtifactStore(Path("data/artifacts"))
        else:
            self.artifact_store = artifact_store
        self.is_synthetic = is_synthetic
        self.max_consecutive_unknown = max_consecutive_unknown
        self.max_unknown_rate = max_unknown_rate
        self.frame_stride = max(1, frame_stride)
        self.db_batch_size = max(1, db_batch_size)

    def run(self, cancellation_check: Callable[[], bool] | None = None) -> str:
        """Run the pipeline to completion, cancellation, or failure.

        Returns final session status string.
        """
        decoder = VideoDecoder(self.video_path, frame_stride=self.frame_stride)

        with self.db_manager.get_session() as session:
            sess_record = session.get(SessionRecord, self.session_id)
            if not sess_record:
                raise ValueError(f"Session {self.session_id} not found")
            sess_record.status = "RUNNING"
            raw_total = sess_record.total_frames or 100
            total_frames = max(1, (raw_total + self.frame_stride - 1) // self.frame_stride) if self.frame_stride > 1 else raw_total
            sess_record.total_frames = total_frames

        processed = 0
        unknown_count = 0
        consecutive_unknown = 0
        exported_frames: list[dict[str, Any]] = []
        zone_names = {z.zone_id: z.name for z in self.zone_set.zones}
        frame_width = 1280
        frame_height = 720

        # Buffer DB writes to eliminate per-frame remote round-trip latency
        batch_obs: list[ObservationRecord] = []
        batch_zr: list[ZoneResultRecord] = []
        last_flush_time = time.time()

        def _flush_db(final: bool = False) -> None:
            nonlocal batch_obs, batch_zr, last_flush_time
            if not batch_obs and not batch_zr and not final:
                return
            with self.db_manager.get_session() as session:
                if batch_obs:
                    session.add_all(batch_obs)
                if batch_zr:
                    session.add_all(batch_zr)
                sess_record = session.get(SessionRecord, self.session_id)
                if sess_record:
                    sess_record.processed_frames = processed
                    sess_record.progress = min(round(processed / max(total_frames, 1), 3), 1.0)
            batch_obs.clear()
            batch_zr.clear()
            last_flush_time = time.time()

        for frame in decoder.iter_frames():
            frame_width = frame.width
            frame_height = frame.height

            # Check cooperative cancellation
            if cancellation_check and cancellation_check():
                _flush_db(final=True)
                with self.db_manager.get_session() as session:
                    sess_record = session.get(SessionRecord, self.session_id)
                    if sess_record:
                        sess_record.status = "PARTIAL_CANCELLED"
                        sess_record.completeness = "PARTIAL"
                return "PARTIAL_CANCELLED"

            # Process frame
            observation = self._process_frame(frame)
            agg_result = aggregate_frame(observation, self.zone_set)

            if observation.quality == QualityState.UNKNOWN:
                unknown_count += 1
                consecutive_unknown += 1
            else:
                consecutive_unknown = 0

            # Buffer frame result
            obs_rec = ObservationRecord(
                session_id=self.session_id,
                frame_index=observation.frame_index,
                media_time_s=observation.media_time_s,
                quality=observation.quality.value,
                reason_code=frame.reason_code,
                payload_v1=observation.model_dump(mode="json"),
            )
            batch_obs.append(obs_rec)

            for z_res in agg_result.zones:
                zr_rec = ZoneResultRecord(
                    session_id=self.session_id,
                    frame_index=observation.frame_index,
                    media_time_s=observation.media_time_s,
                    zone_id=z_res.zone_id,
                    availability=z_res.availability.value,
                    visible_count=z_res.visible_count,
                )
                batch_zr.append(zr_rec)

            processed += 1

            # Flush periodically (every batch_size frames or >= 1.0s) to keep SSE progress lively
            now = time.time()
            if len(batch_obs) >= self.db_batch_size or (now - last_flush_time >= 1.0):
                _flush_db()

            # Accumulate frame data for export artifact
            frame_export = {
                "frame_index": observation.frame_index,
                "media_time_s": round(observation.media_time_s, 3),
                "quality": observation.quality.value,
                "fully_observed_zones": list(self.zone_set.zone_ids),
                "detections": [
                    {
                        "track_id": d.track_id,
                        "x": round(d.x, 4),
                        "y": round(d.y, 4),
                        "confidence": round(d.confidence, 3),
                        "bbox_xyxy": [round(c, 1) for c in d.bbox_xyxy] if d.bbox_xyxy else None,
                    }
                    for d in observation.detections
                ],
                "zone_readings": [
                    {
                        "status": z_res.availability.value,
                        "count": z_res.visible_count if z_res.availability.value == "COUNTED" else 0,
                        "zoneId": z_res.zone_id,
                        "zoneName": zone_names.get(z_res.zone_id, z_res.zone_id),
                    }
                    for z_res in agg_result.zones
                ],
            }
            exported_frames.append(frame_export)

            # Failure rate threshold check
            if consecutive_unknown >= self.max_consecutive_unknown:
                _flush_db(final=True)
                with self.db_manager.get_session() as session:
                    sess_record = session.get(SessionRecord, self.session_id)
                    if sess_record:
                        sess_record.status = "FAILED"
                        sess_record.error_code = "INFERENCE_FAILURE_RATE_EXCEEDED"
                        sess_record.user_action_hint = "Too many consecutive unreadable or failed frames"
                raise PipelineInferenceError("Exceeded maximum consecutive UNKNOWN frames")

        # Ensure all buffered frames are committed to database
        _flush_db(final=True)

        # Generate artifacts and finalize session
        palette = ["#0072B2", "#009E73", "#D55E00", "#CC79A7", "#F0E442"]
        zone_list = [
            {
                "zone_id": z.zone_id,
                "name": z.name,
                "color": palette[i % len(palette)],
                "vertices": [[round(p.x, 1), round(p.y, 1)] for p in z.polygon.vertices],
            }
            for i, z in enumerate(self.zone_set.zones)
        ]
        v_fps = float(getattr(decoder, "fps", 25.0) or 25.0)
        v_raw_total = int(getattr(decoder, "total_raw_frames", 0) or 0)
        duration_s = (
            round(v_raw_total / v_fps, 2)
            if v_raw_total > 0
            else (round(processed * self.frame_stride / v_fps, 2) if processed > 0 else 0.0)
        )
        dataset_dict = {
            "metadata": {
                "sessionId": self.session_id,
                "sourceId": self.video_path.name,
                "mediaName": self.video_path.name,
                "duration": duration_s,
                "fps": v_fps,
                "width": frame_width,
                "height": frame_height,
                "totalFrames": processed,
                "model": getattr(self.detector, "profile_id", "models/best.pt"),
                "confidence": round(float(getattr(getattr(self.detector, "_profile", None), "confidence", 0.18)), 2),
                "tracker": "BoT-SORT",
            },
            "zones": zone_list,
            "frames": exported_frames,
        }

        # 1. Save DATASET_EXPORT JSON artifact
        try:
            json_bytes = json.dumps(dataset_dict).encode("utf-8")
            art_id, relpath, digest = self.artifact_store.save_bytes(
                json_bytes,
                kind="DATASET_EXPORT",
                suffix=".json",
                session_id=self.session_id,
            )
            with self.db_manager.get_session() as session:
                art_rec = ArtifactRecord(
                    id=art_id,
                    session_id=self.session_id,
                    kind="DATASET_EXPORT",
                    relpath=relpath,
                    sha256=digest,
                )
                session.add(art_rec)
        except Exception as exc:
            logger.warning("Failed to save dataset export artifact: %s", exc)

        # 2. Save HEATMAP PNG artifact
        try:
            from crowdsight.service.analytics.heatmaps import ImageSpaceHeatmapGenerator
            hm_result = ImageSpaceHeatmapGenerator.generate(
                observations=exported_frames,
                image_width=frame_width,
                image_height=frame_height,
                zone_set=self.zone_set,
            )
            hm_art_id, hm_relpath, hm_digest = self.artifact_store.save_bytes(
                hm_result.png_bytes,
                kind="HEATMAP",
                suffix=".png",
                session_id=self.session_id,
            )
            with self.db_manager.get_session() as session:
                hm_art_rec = ArtifactRecord(
                    id=hm_art_id,
                    session_id=self.session_id,
                    kind="HEATMAP",
                    relpath=hm_relpath,
                    sha256=hm_digest,
                )
                session.add(hm_art_rec)
        except Exception as exc:
            logger.warning("Failed to generate heatmap artifact: %s", exc)

        # Mark completed
        with self.db_manager.get_session() as session:
            sess_record = session.get(SessionRecord, self.session_id)
            if sess_record:
                sess_record.status = "COMPLETED"
                sess_record.progress = 1.0
                sess_record.completeness = "FULL"
                sess_record.processed_frames = processed

        return "COMPLETED"

    def _process_frame(self, frame: DecodedFrame) -> CrowdFrameObservationV1:
        profile_id = getattr(self.detector, "profile_id", "crowd_best_local_v2")
        profile_sha256 = getattr(self.detector, "profile_sha256", "a" * 64)
        checkpoint_sha256 = getattr(self.detector, "checkpoint_sha256", "b" * 64)
        tracker_sha256 = getattr(self.detector, "tracker_config_sha256", None)

        if not frame.is_usable or frame.image_bgr is None:
            return CrowdFrameObservationV1(
                source_id="camera-stream",
                session_id=self.session_id,
                model_profile_id=profile_id,
                model_profile_sha256=profile_sha256,
                checkpoint_sha256=checkpoint_sha256,
                tracker_config_sha256=tracker_sha256,
                frame_index=frame.frame_index,
                media_time_s=frame.media_time_s,
                captured_at=None,
                image_width=frame.width,
                image_height=frame.height,
                observation_valid=False,
                registration_valid=False,
                fully_observed_zones=(),
                confidence_semantics="RAW_MODEL_SCORE",
                quality=QualityState.UNKNOWN,
                detections=(),
            )

        # Run tracker or detector
        infer_fn = getattr(self.detector, "track", None) or self.detector.predict
        try:
            import inspect
            sig = inspect.signature(infer_fn)
            if "frame_index" in sig.parameters:
                raw_detections = infer_fn(frame.image_bgr, frame_index=frame.frame_index)
            else:
                raw_detections = infer_fn(frame.image_bgr)
        except Exception as exc:
            logger.warning("Inference error on frame %d: %s", frame.frame_index, exc)
            return CrowdFrameObservationV1(
                source_id="camera-stream",
                session_id=self.session_id,
                model_profile_id=profile_id,
                model_profile_sha256=profile_sha256,
                checkpoint_sha256=checkpoint_sha256,
                tracker_config_sha256=tracker_sha256,
                frame_index=frame.frame_index,
                media_time_s=frame.media_time_s,
                captured_at=None,
                image_width=frame.width,
                image_height=frame.height,
                observation_valid=False,
                registration_valid=False,
                fully_observed_zones=(),
                confidence_semantics="RAW_MODEL_SCORE",
                quality=QualityState.UNKNOWN,
                detections=(),
            )

        # Map to DetectionV1
        detection_models: list[DetectionV1] = []
        for d in raw_detections:
            track_id = int(d.track_id) if getattr(d, "track_id", None) is not None else None
            bbox_raw = getattr(d, "bbox_xyxy_px", None) or getattr(d, "bbox_xyxy", None)
            bbox: tuple[float, float, float, float] | None = None
            if bbox_raw is not None and len(bbox_raw) == 4:
                bbox = (float(bbox_raw[0]), float(bbox_raw[1]), float(bbox_raw[2]), float(bbox_raw[3]))
            detection_models.append(
                DetectionV1(
                    track_id=track_id,
                    x=min(max(float(d.x), 0.0), 1.0),
                    y=min(max(float(d.y), 0.0), 1.0),
                    confidence=min(max(float(d.confidence), 0.0), 1.0),
                    bbox_xyxy=bbox,
                )
            )

        return CrowdFrameObservationV1(
            source_id="camera-stream",
            session_id=self.session_id,
            model_profile_id=profile_id,
            model_profile_sha256=profile_sha256,
            checkpoint_sha256=checkpoint_sha256,
            tracker_config_sha256=tracker_sha256,
            frame_index=frame.frame_index,
            media_time_s=frame.media_time_s,
            captured_at=None,
            image_width=frame.width,
            image_height=frame.height,
            observation_valid=True,
            registration_valid=False,
            fully_observed_zones=tuple(sorted(self.zone_set.zone_ids)),
            confidence_semantics="RAW_MODEL_SCORE",
            quality=QualityState.VALID,
            detections=tuple(detection_models),
        )
