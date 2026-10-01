"""Pydantic v2 models representing the AI/ML v1 Crowd Frame Observation contract.

These models strictly adhere to contracts/v1/crowd-frame-observation.schema.json.
"""
from __future__ import annotations

import math
import re
from collections.abc import Sequence
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SHA256_REGEX = re.compile(r"^[A-Fa-f0-9]{64}$")


class QualityState(str, Enum):
    """Visual evidence quality state defined by the AI/ML contract."""
    VALID = "VALID"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"


ConfidenceSemantics = Literal["RAW_MODEL_SCORE"]


class DetectionV1(BaseModel):
    """Single person detection matching v1 contract detection item."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    track_id: int | None = Field(
        default=None,
        ge=0,
        description="Anonymous track ID, local to one video session. Null for detector-only output.",
    )
    x: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized x coordinate [0, 1] locating the bounding box bottom centre.",
    )
    y: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized y coordinate [0, 1] locating the bounding box bottom centre.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Uncalibrated raw detector score in [0, 1]. Never formatted as a percentage.",
    )
    bbox_xyxy: tuple[float, float, float, float] | None = Field(
        default=None,
        description="Pixel box [x1, y1, x2, y2] in original source-frame coordinates (right/bottom exclusive).",
    )

    @field_validator("bbox_xyxy")
    @classmethod
    def validate_bbox_geometry(
        cls, v: tuple[float, float, float, float] | None
    ) -> tuple[float, float, float, float] | None:
        if v is None:
            return None
        if len(v) != 4:
            raise ValueError("bbox_xyxy must contain exactly 4 coordinates")
        x1, y1, x2, y2 = v
        for coord in (x1, y1, x2, y2):
            if not math.isfinite(coord) or coord < 0:
                raise ValueError("bbox_xyxy coordinates must be finite and non-negative")
        if x2 <= x1 or y2 <= y1:
            raise ValueError(f"bbox_xyxy must have positive width and height: got {v}")
        return v


class CrowdFrameObservationV1(BaseModel):
    """Pydantic representation of contracts/v1/crowd-frame-observation.schema.json."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1, description="Identifier of the source recorded video or camera.")
    session_id: str = Field(min_length=1, description="Processing run or session identifier.")
    model_profile_id: str = Field(min_length=1, description="Model profile identifier (e.g. crowd_best_local_v2).")
    model_profile_sha256: str = Field(description="SHA-256 digest of the model profile YAML configuration.")
    checkpoint_sha256: str = Field(description="SHA-256 digest of the model weight artifact.")
    tracker_config_sha256: str | None = Field(
        default=None,
        description="SHA-256 digest of the tracker configuration YAML, or null if tracking is disabled.",
    )
    frame_index: int = Field(ge=0, description="Zero-based index of the decoded frame in source order.")
    media_time_s: float = Field(ge=0.0, description="Elapsed time in seconds within the source recording.")
    captured_at: datetime | None = Field(
        default=None,
        description="Timestamp when the frame was captured, if known from source metadata.",
    )
    image_width: int = Field(ge=1, description="Original source image width in pixels.")
    image_height: int = Field(ge=1, description="Original source image height in pixels.")
    observation_valid: bool = Field(description="True if frame is VALID or PARTIAL, False if UNKNOWN or STALE.")
    registration_valid: bool = Field(
        default=False,
        description="True only if geographic registration is verified. Always false for image-space views.",
    )
    fully_observed_zones: tuple[str, ...] = Field(
        default=(),
        description="Zone IDs with complete observable coverage in this frame.",
    )
    confidence_semantics: ConfidenceSemantics = Field(
        default="RAW_MODEL_SCORE",
        description="Semantics of detection confidence scores.",
    )
    quality: QualityState = Field(description="Frame quality status (VALID, PARTIAL, UNKNOWN, STALE).")
    detections: tuple[DetectionV1, ...] = Field(
        default=(),
        description="List of detected persons in this frame.",
    )

    @field_validator("model_profile_sha256", "checkpoint_sha256")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        if not SHA256_REGEX.match(v):
            raise ValueError(f"Value must be a 64-character hex SHA-256 string, got {v!r}")
        return v.lower()

    @field_validator("tracker_config_sha256")
    @classmethod
    def validate_tracker_sha256(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not SHA256_REGEX.match(v):
            raise ValueError(f"tracker_config_sha256 must be a 64-character hex string, got {v!r}")
        return v.lower()

    @field_validator("fully_observed_zones")
    @classmethod
    def validate_unique_zones(cls, v: Sequence[str]) -> tuple[str, ...]:
        tuple_v = tuple(v)
        if len(tuple_v) != len(set(tuple_v)):
            raise ValueError("fully_observed_zones elements must be unique")
        for z in tuple_v:
            if not z.strip():
                raise ValueError("Zone ID in fully_observed_zones must be non-empty")
        return tuple_v

    @model_validator(mode="after")
    def validate_contract_invariants(self) -> CrowdFrameObservationV1:
        # Invariant 1: VALID and PARTIAL require observation_valid == True and at least 1 fully observed zone
        if self.quality in (QualityState.VALID, QualityState.PARTIAL):
            if not self.observation_valid:
                raise ValueError(f"quality={self.quality.value} requires observation_valid=True")
            if len(self.fully_observed_zones) == 0:
                raise ValueError(
                    f"quality={self.quality.value} requires at least one fully observed zone; "
                    "use UNKNOWN when none are usable"
                )

        # Invariant 2: UNKNOWN and STALE require observation_valid == False and empty zones and empty detections
        if self.quality in (QualityState.UNKNOWN, QualityState.STALE):
            if self.observation_valid:
                raise ValueError(f"quality={self.quality.value} requires observation_valid=False")
            if len(self.fully_observed_zones) > 0:
                raise ValueError(f"quality={self.quality.value} must have empty fully_observed_zones")
            if len(self.detections) > 0:
                raise ValueError(f"quality={self.quality.value} must have empty detections list")

        # Invariant 3: Tracking requirement
        has_tracked_detections = any(d.track_id is not None for d in self.detections)
        if has_tracked_detections and self.tracker_config_sha256 is None:
            raise ValueError("detections containing track_id require non-null tracker_config_sha256")

        # Invariant 4: Bounding box within image dimensions and anchor alignment
        for idx, d in enumerate(self.detections):
            if d.bbox_xyxy is not None:
                x1, y1, x2, y2 = d.bbox_xyxy
                if x2 > self.image_width or y2 > self.image_height:
                    raise ValueError(
                        f"Detection {idx} bbox [{x1}, {y1}, {x2}, {y2}] exceeds image dimensions "
                        f"{self.image_width}x{self.image_height}"
                    )
                expected_x = ((x1 + x2) / 2.0) / self.image_width
                expected_y = y2 / self.image_height
                if not math.isclose(d.x, expected_x, abs_tol=1e-3):
                    raise ValueError(
                        f"Detection {idx} anchor x={d.x} does not match bbox bottom-centre x={expected_x}"
                    )
                if not math.isclose(d.y, expected_y, abs_tol=1e-3):
                    raise ValueError(
                        f"Detection {idx} anchor y={d.y} does not match bbox bottom-centre y={expected_y}"
                    )

        return self
