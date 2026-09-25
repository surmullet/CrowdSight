"""Parking-space outputs kept separate from crowd/person observations."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import math
from typing import Optional

from crowdsight.common.observations import QualityState


class ParkingState(str, Enum):
    OCCUPIED = "OCCUPIED"
    AVAILABLE = "AVAILABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ParkingSpaceResult:
    """One configured site stall's state for one observation time."""

    space_id: str
    state: ParkingState
    confidence: Optional[float]
    evidence_time_s: float

    def __post_init__(self) -> None:
        if not isinstance(self.space_id, str) or not self.space_id.strip():
            raise ValueError("space_id must be a nonempty string")
        if not isinstance(self.state, ParkingState):
            raise ValueError("state must be a ParkingState")
        if type(self.evidence_time_s) not in (int, float) or not math.isfinite(self.evidence_time_s) or self.evidence_time_s < 0:
            raise ValueError("evidence_time_s must be finite and nonnegative")
        if self.confidence is not None:
            if (
                type(self.confidence) not in (int, float)
                or not math.isfinite(self.confidence)
                or not 0.0 <= self.confidence <= 1.0
            ):
                raise ValueError("confidence must be in [0, 1] or null")
        if self.state is ParkingState.UNKNOWN and self.confidence is not None:
            raise ValueError("UNKNOWN state must not carry model confidence")


@dataclass(frozen=True, slots=True)
class ParkingFrameObservation:
    """Namespaced frame result for the parking model/API contract."""

    site_id: str
    camera_view_id: str
    space_layout_version: str
    source_id: str
    session_id: str
    frame_index: int
    media_time_s: float
    model_profile_id: str
    model_profile_sha256: str
    checkpoint_sha256: str
    quality: QualityState
    spaces: tuple[ParkingSpaceResult, ...]
    captured_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        for name in ("site_id", "camera_view_id", "space_layout_version", "source_id", "session_id", "model_profile_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty string")
        if not isinstance(self.quality, QualityState):
            raise ValueError("quality must be a QualityState")
        if not isinstance(self.checkpoint_sha256, str) or len(self.checkpoint_sha256) != 64 or any(
            char not in "0123456789abcdefABCDEF" for char in self.checkpoint_sha256
        ):
            raise ValueError("checkpoint_sha256 must be a 64-character hex digest")
        if not isinstance(self.model_profile_sha256, str) or len(self.model_profile_sha256) != 64 or any(
            char not in "0123456789abcdefABCDEF" for char in self.model_profile_sha256
        ):
            raise ValueError("model_profile_sha256 must be a 64-character hex digest")
        if type(self.frame_index) is not int or self.frame_index < 0:
            raise ValueError("frame_index must be a nonnegative integer")
        if type(self.media_time_s) not in (int, float) or not math.isfinite(self.media_time_s) or self.media_time_s < 0:
            raise ValueError("frame index and media time must be valid")
        if self.captured_at is not None and (
            not isinstance(self.captured_at, datetime) or self.captured_at.utcoffset() is None
        ):
            raise ValueError("captured_at must be timezone-aware")
        if not isinstance(self.spaces, tuple) or not self.spaces or any(
            not isinstance(result, ParkingSpaceResult) for result in self.spaces
        ):
            raise ValueError("spaces must be a nonempty tuple of ParkingSpaceResult values")
        if self.quality in (QualityState.UNKNOWN, QualityState.STALE) and any(
            result.state is not ParkingState.UNKNOWN for result in self.spaces
        ):
            raise ValueError("UNKNOWN/STALE frames may contain only UNKNOWN spaces")
        space_ids = [result.space_id for result in self.spaces]
        if len(space_ids) != len(set(space_ids)):
            raise ValueError("space_id values must be unique within a frame")

    def to_contract_dict(self) -> dict[str, object]:
        return {
            "site_id": self.site_id,
            "camera_view_id": self.camera_view_id,
            "space_layout_version": self.space_layout_version,
            "source_id": self.source_id,
            "session_id": self.session_id,
            "frame_index": self.frame_index,
            "media_time_s": self.media_time_s,
            "captured_at": self.captured_at.isoformat() if self.captured_at else None,
            "model_profile_id": self.model_profile_id,
            "model_profile_sha256": self.model_profile_sha256.lower(),
            "checkpoint_sha256": self.checkpoint_sha256.lower(),
            "confidence_semantics": "RAW_MODEL_SCORE",
            "quality": self.quality.value,
            "spaces": [
                {
                    "space_id": item.space_id,
                    "state": item.state.value,
                    "confidence": item.confidence,
                    "evidence_time_s": item.evidence_time_s,
                }
                for item in self.spaces
            ],
        }
