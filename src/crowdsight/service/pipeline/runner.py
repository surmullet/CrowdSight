"""Video pipeline orchestrator: decoding, inference, zone aggregation, and persistence."""
from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

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
        detector: Any,  # Supports predict(frame_bgr, frame_index)
        db_manager: DatabaseManager,
        is_synthetic: bool = False,
        max_consecutive_unknown: int = 30,
        max_unknown_rate: float = 0.5,
    ) -> None:
        self.session_id = session_id
        self.video_path = video_path
        self.zone_set = zone_set
        self.detector = detector
        self.db_manager = db_manager
        self.is_synthetic = is_synthetic
        self.max_consecutive_unknown = max_consecutive_unknown
        self.max_unknown_rate = max_unknown_rate

    def run(self, cancellation_check: Callable[[], bool] | None = None) -> str:
        """Run the pipeline to completion, cancellation, or failure.

        Returns final session status string.
        """
        decoder = VideoDecoder(self.video_path)

        with self.db_manager.get_session() as session:
            sess_record = session.get(SessionRecord, self.session_id)
            if not sess_record:
                raise ValueError(f"Session {self.session_id} not found")
            sess_record.status = "RUNNING"
            total_frames = sess_record.total_frames or 100

        processed = 0
        unknown_count = 0
        consecutive_unknown = 0

        for frame in decoder.iter_frames():
            # Check cooperative cancellation
            if cancellation_check and cancellation_check():
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

            # Write batch/single frame result
            with self.db_manager.get_session() as session:
                obs_rec = ObservationRecord(
                    session_id=self.session_id,
                    frame_index=observation.frame_index,
                    media_time_s=observation.media_time_s,
                    quality=observation.quality.value,
                    reason_code=frame.reason_code,
                    payload_v1=observation.model_dump(mode="json"),
                )
                session.add(obs_rec)

                for z_res in agg_result.zones:
                    zr_rec = ZoneResultRecord(
                        session_id=self.session_id,
                        frame_index=observation.frame_index,
                        media_time_s=observation.media_time_s,
                        zone_id=z_res.zone_id,
                        availability=z_res.availability.value,
                        visible_count=z_res.visible_count,
                    )
                    session.add(zr_rec)

                processed += 1
                sess_record = session.get(SessionRecord, self.session_id)
                if sess_record:
                    sess_record.processed_frames = processed
                    sess_record.progress = min(round(processed / max(total_frames, 1), 3), 1.0)

            # Failure rate threshold check
            if consecutive_unknown >= self.max_consecutive_unknown:
                with self.db_manager.get_session() as session:
                    sess_record = session.get(SessionRecord, self.session_id)
                    if sess_record:
                        sess_record.status = "FAILED"
                        sess_record.error_code = "INFERENCE_FAILURE_RATE_EXCEEDED"
                        sess_record.user_action_hint = "Too many consecutive unreadable or failed frames"
                raise PipelineInferenceError("Exceeded maximum consecutive UNKNOWN frames")

        # Mark completed
        with self.db_manager.get_session() as session:
            sess_record = session.get(SessionRecord, self.session_id)
            if sess_record:
                sess_record.status = "COMPLETED"
                sess_record.progress = 1.0
                sess_record.completeness = "FULL"

        return "COMPLETED"

    def _process_frame(self, frame: DecodedFrame) -> CrowdFrameObservationV1:
        profile_id = getattr(self.detector, "profile_id", "crowd_best_local_v2")
        profile_sha256 = getattr(self.detector, "profile_sha256", "a" * 64)
        checkpoint_sha256 = getattr(self.detector, "checkpoint_sha256", "b" * 64)

        if not frame.is_usable or frame.image_bgr is None:
            return CrowdFrameObservationV1(
                source_id="camera-stream",
                session_id=self.session_id,
                model_profile_id=profile_id,
                model_profile_sha256=profile_sha256,
                checkpoint_sha256=checkpoint_sha256,
                tracker_config_sha256=None,
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

        # Run detector
        predict_fn = self.detector.predict
        try:
            # Check if predict accepts frame_index
            import inspect
            sig = inspect.signature(predict_fn)
            if "frame_index" in sig.parameters:
                raw_detections = predict_fn(frame.image_bgr, frame_index=frame.frame_index)
            else:
                raw_detections = predict_fn(frame.image_bgr)
        except Exception as exc:
            logger.warning("Inference error on frame %d: %s", frame.frame_index, exc)
            return CrowdFrameObservationV1(
                source_id="camera-stream",
                session_id=self.session_id,
                model_profile_id=profile_id,
                model_profile_sha256=profile_sha256,
                checkpoint_sha256=checkpoint_sha256,
                tracker_config_sha256=None,
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
            detection_models.append(
                DetectionV1(
                    track_id=d.track_id,
                    x=d.x,
                    y=d.y,
                    confidence=d.confidence,
                    bbox_xyxy=d.bbox_xyxy_px,
                )
            )

        return CrowdFrameObservationV1(
            source_id="camera-stream",
            session_id=self.session_id,
            model_profile_id=profile_id,
            model_profile_sha256=profile_sha256,
            checkpoint_sha256=checkpoint_sha256,
            tracker_config_sha256=None,
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
