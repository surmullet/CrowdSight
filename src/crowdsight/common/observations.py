"""Validated observation data and quality-state semantics."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import math
from typing import Optional


class QualityState(str, Enum):
    VALID = "VALID"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"


class UnavailableReason(str, Enum):
    """Machine-readable cause for an unusable observation.

    Producer-side reasons describe why one frame's result is `UNKNOWN`.
    `FRESHNESS_LIMIT_EXCEEDED` belongs to `STALE` and is assigned by the
    consuming service's freshness policy, never by the frame producer.
    """

    INFERENCE_FAILURE = "INFERENCE_FAILURE"
    NMS_TIME_LIMIT_EXCEEDED = "NMS_TIME_LIMIT_EXCEEDED"
    DETECTION_LIMIT_REACHED = "DETECTION_LIMIT_REACHED"
    NO_FULLY_OBSERVED_ZONE = "NO_FULLY_OBSERVED_ZONE"
    FRESHNESS_LIMIT_EXCEEDED = "FRESHNESS_LIMIT_EXCEEDED"


PRODUCER_UNAVAILABLE_REASONS = frozenset(
    (
        UnavailableReason.INFERENCE_FAILURE,
        UnavailableReason.NMS_TIME_LIMIT_EXCEEDED,
        UnavailableReason.DETECTION_LIMIT_REACHED,
        UnavailableReason.NO_FULLY_OBSERVED_ZONE,
    )
)


@dataclass(frozen=True, slots=True)
class PersonDetection:
    """One observed person anchor, normalized to the source frame.

    Coordinates identify the bottom-centre/approximate ground-contact point,
    not the box centre. Track IDs are anonymous and local to one video run.
    Pixel boxes use source-frame coordinates with exclusive right/bottom edges.
    They are serialized for annotated replay; normalized anchors remain the
    stable geometry for zone membership.
    """

    x: float
    y: float
    confidence: float
    track_id: Optional[int] = None
    bbox_xyxy_px: Optional[tuple[float, float, float, float]] = None

    def __post_init__(self) -> None:
        for name in ("x", "y", "confidence"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if not 0.0 <= self.x <= 1.0 or not 0.0 <= self.y <= 1.0:
            raise ValueError("normalized anchor x and y must be in [0, 1]")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        if self.track_id is not None and (type(self.track_id) is not int or self.track_id < 0):
            raise ValueError("track_id must be nonnegative or null")
        if self.bbox_xyxy_px is not None:
            if (
                not isinstance(self.bbox_xyxy_px, tuple)
                or len(self.bbox_xyxy_px) != 4
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in self.bbox_xyxy_px)
            ):
                raise ValueError("bbox_xyxy_px must be a tuple of four finite values")
            x1, y1, x2, y2 = self.bbox_xyxy_px
            if x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1:
                raise ValueError("bbox_xyxy_px must have nonnegative coordinates and positive area")

    def to_contract_dict(self) -> dict[str, object]:
        """Serialize only fields in the proposed shared detection contract."""
        return {
            "track_id": self.track_id,
            "x": self.x,
            "y": self.y,
            "confidence": self.confidence,
            "bbox_xyxy": list(self.bbox_xyxy_px) if self.bbox_xyxy_px is not None else None,
        }


@dataclass(frozen=True, slots=True)
class FrameObservation:
    """AI output associated with one source frame.

    Producers must explicitly supply zone coverage. An empty tuple is a
    deliberate statement that no configured zone is fully observable.
    `unavailable_reason` is null for usable frames, carries the producer
    cause on UNKNOWN frames, and carries FRESHNESS_LIMIT_EXCEEDED when the
    consuming service marks the observation STALE.
    """

    source_id: str
    session_id: str
    model_profile_id: str
    model_profile_sha256: str
    checkpoint_sha256: str
    tracker_config_sha256: Optional[str]
    frame_index: int
    media_time_s: float
    image_width: int
    image_height: int
    detections: tuple[PersonDetection, ...]
    fully_observed_zones: tuple[str, ...]
    quality: QualityState = QualityState.VALID
    captured_at: Optional[datetime] = None
    registration_valid: bool = False
    unavailable_reason: Optional[UnavailableReason] = None

    def __post_init__(self) -> None:
        for name in ("source_id", "session_id", "model_profile_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty string")
        if not isinstance(self.quality, QualityState):
            raise ValueError("quality must be a QualityState")
        if not isinstance(self.model_profile_sha256, str) or len(self.model_profile_sha256) != 64 or any(
            char not in "0123456789abcdefABCDEF" for char in self.model_profile_sha256
        ):
            raise ValueError("model_profile_sha256 must be a 64-character hex digest")
        if not isinstance(self.checkpoint_sha256, str) or len(self.checkpoint_sha256) != 64 or any(
            char not in "0123456789abcdefABCDEF" for char in self.checkpoint_sha256
        ):
            raise ValueError("checkpoint_sha256 must be a 64-character hex digest")
        if not isinstance(self.registration_valid, bool):
            raise ValueError("registration_valid must be a boolean")
        if not isinstance(self.detections, tuple) or any(
            not isinstance(detection, PersonDetection) for detection in self.detections
        ):
            raise ValueError("detections must be a tuple of PersonDetection values")
        if (
            not isinstance(self.fully_observed_zones, tuple)
            or any(not isinstance(zone_id, str) or not zone_id.strip() for zone_id in self.fully_observed_zones)
            or len(self.fully_observed_zones) != len(set(self.fully_observed_zones))
        ):
            raise ValueError("fully_observed_zones must be a tuple of unique nonempty zone IDs")
        if self.tracker_config_sha256 is not None and (
            not isinstance(self.tracker_config_sha256, str)
            or len(self.tracker_config_sha256) != 64
            or any(char not in "0123456789abcdefABCDEF" for char in self.tracker_config_sha256)
        ):
            raise ValueError("tracker_config_sha256 must be a 64-character hex digest or null")
        if self.tracker_config_sha256 is None and any(
            detection.track_id is not None for detection in self.detections
        ):
            raise ValueError("tracked detections require tracker_config_sha256")
        if type(self.frame_index) is not int or self.frame_index < 0:
            raise ValueError("frame_index must be nonnegative")
        if type(self.media_time_s) not in (int, float) or not math.isfinite(self.media_time_s) or self.media_time_s < 0:
            raise ValueError("media_time_s must be finite and nonnegative")
        if type(self.image_width) is not int or type(self.image_height) is not int or self.image_width <= 0 or self.image_height <= 0:
            raise ValueError("image dimensions must be positive")
        for detection in self.detections:
            if detection.bbox_xyxy_px is not None:
                x1, y1, x2, y2 = detection.bbox_xyxy_px
                if x2 > self.image_width or y2 > self.image_height:
                    raise ValueError("detection bbox_xyxy_px must lie within the source frame")
                expected_x = ((x1 + x2) / 2.0) / self.image_width
                expected_y = y2 / self.image_height
                if not math.isclose(detection.x, expected_x, rel_tol=0.0, abs_tol=1e-9) or not math.isclose(
                    detection.y, expected_y, rel_tol=0.0, abs_tol=1e-9
                ):
                    raise ValueError("normalized detection anchor must match the bbox bottom-centre")
        if self.captured_at is not None and (
            not isinstance(self.captured_at, datetime) or self.captured_at.utcoffset() is None
        ):
            raise ValueError("captured_at must be timezone-aware")
        if self.quality in (QualityState.VALID, QualityState.PARTIAL) and not self.fully_observed_zones:
            raise ValueError("VALID/PARTIAL observations require at least one fully observed zone; use UNKNOWN when none are usable")
        if self.quality in (QualityState.UNKNOWN, QualityState.STALE) and (
            self.detections or self.fully_observed_zones
        ):
            raise ValueError("UNKNOWN/STALE observations must not carry detections or fully observed zones")
        if self.unavailable_reason is not None and not isinstance(self.unavailable_reason, UnavailableReason):
            raise ValueError("unavailable_reason must be an UnavailableReason or null")
        if self.quality in (QualityState.VALID, QualityState.PARTIAL) and self.unavailable_reason is not None:
            raise ValueError("VALID/PARTIAL observations must not carry unavailable_reason")
        if self.quality is QualityState.UNKNOWN and self.unavailable_reason not in PRODUCER_UNAVAILABLE_REASONS:
            raise ValueError(
                "UNKNOWN observations require a producer unavailable_reason; "
                "freshness-based reasons belong to STALE and are assigned downstream"
            )
        if self.quality is QualityState.STALE and self.unavailable_reason is not UnavailableReason.FRESHNESS_LIMIT_EXCEEDED:
            raise ValueError(
                "STALE observations require unavailable_reason FRESHNESS_LIMIT_EXCEEDED, "
                "assigned by the consuming service freshness policy"
            )

    def to_contract_dict(self) -> dict[str, object]:
        """Serialize the proposed shared frame-observation schema."""
        return {
            "source_id": self.source_id,
            "session_id": self.session_id,
            "model_profile_id": self.model_profile_id,
            "model_profile_sha256": self.model_profile_sha256.lower(),
            "checkpoint_sha256": self.checkpoint_sha256.lower(),
            "tracker_config_sha256": (
                self.tracker_config_sha256.lower()
                if self.tracker_config_sha256 is not None
                else None
            ),
            "frame_index": self.frame_index,
            "media_time_s": self.media_time_s,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
            "image_width": self.image_width,
            "image_height": self.image_height,
            "observation_valid": self.quality not in (
                QualityState.UNKNOWN,
                QualityState.STALE,
            ),
            "registration_valid": self.registration_valid,
            "unavailable_reason": (
                self.unavailable_reason.value
                if self.unavailable_reason is not None
                else None
            ),
            "fully_observed_zones": list(self.fully_observed_zones),
            "confidence_semantics": "RAW_MODEL_SCORE",
            "quality": self.quality.value,
            "detections": [d.to_contract_dict() for d in self.detections],
        }
