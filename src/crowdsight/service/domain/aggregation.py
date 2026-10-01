"""Zone-level aggregation and availability computation.

Enforces invariants:
- visible_count IS NOT NULL <=> availability == 'COUNTED'
- VALID frames: all configured zones counted (genuine 0 if no detections)
- PARTIAL frames: only zones in fully_observed_zones counted; others NOT_FULLY_OBSERVED with visible_count=None
- UNKNOWN frames: all zones UNKNOWN with visible_count=None (never 0)
- STALE frames: all zones STALE with visible_count=None
- density_people_per_m2 is always null; density_status is 'UNAVAILABLE_NO_CALIBRATION'
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from crowdsight.service.domain.models import (
    CrowdFrameObservationV1,
    QualityState,
)
from crowdsight.service.domain.zones import ZoneSet


class ZoneAvailability(str, Enum):
    COUNTED = "COUNTED"
    NOT_FULLY_OBSERVED = "NOT_FULLY_OBSERVED"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"


class ZoneResult(BaseModel):
    """Aggregate counting result for one zone in one frame."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    zone_id: str = Field(min_length=1)
    availability: ZoneAvailability
    visible_count: int | None = Field(
        default=None,
        ge=0,
        description="Number of visible detected persons in this observed zone. NULL when unavailable.",
    )
    density_people_per_m2: float | None = Field(
        default=None,
        description="Always null until metric calibration is approved.",
    )
    density_status: str = Field(
        default="UNAVAILABLE_NO_CALIBRATION",
        description="Explains why density is unavailable.",
    )

    @model_validator(mode="after")
    def validate_count_availability_invariant(self) -> ZoneResult:
        # Invariant: visible_count is not None <=> availability == COUNTED
        if self.availability == ZoneAvailability.COUNTED:
            if self.visible_count is None:
                raise ValueError("visible_count cannot be None when availability is COUNTED")
        else:
            if self.visible_count is not None:
                raise ValueError(
                    f"visible_count must be None when availability is {self.availability.value}, got {self.visible_count}"
                )

        # Invariant: density_people_per_m2 must be None
        if self.density_people_per_m2 is not None:
            raise ValueError("density_people_per_m2 must be None for uncalibrated camera views")

        return self


class FrameAggregationResult(BaseModel):
    """Aggregated zone results for one source frame."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str
    frame_index: int
    media_time_s: float
    quality: QualityState
    zones: tuple[ZoneResult, ...]


def aggregate_frame(
    observation: CrowdFrameObservationV1,
    zone_set: ZoneSet,
) -> FrameAggregationResult:
    """Pure domain function aggregating a validated observation into per-zone counts.

    Does not perform I/O.
    """
    quality = observation.quality
    configured_zones = {z.zone_id: z for z in zone_set.zones}
    results: list[ZoneResult] = []

    if quality in (QualityState.UNKNOWN, QualityState.STALE):
        mapped_availability = (
            ZoneAvailability.UNKNOWN
            if quality == QualityState.UNKNOWN
            else ZoneAvailability.STALE
        )
        for zone_id in sorted(configured_zones.keys()):
            results.append(
                ZoneResult(
                    zone_id=zone_id,
                    availability=mapped_availability,
                    visible_count=None,
                )
            )
        return FrameAggregationResult(
            session_id=observation.session_id,
            frame_index=observation.frame_index,
            media_time_s=observation.media_time_s,
            quality=quality,
            zones=tuple(results),
        )

    # For VALID or PARTIAL:
    fully_observed_ids = set(observation.fully_observed_zones)

    # Compute person anchor pixel coordinates: (x * width, y * height)
    # Bottom-centre anchor represents ground-contact position
    detections_px: list[tuple[float, float]] = [
        (d.x * observation.image_width, d.y * observation.image_height)
        for d in observation.detections
    ]

    for zone_id in sorted(configured_zones.keys()):
        zone_def = configured_zones[zone_id]

        if quality == QualityState.VALID or zone_id in fully_observed_ids:
            # Count persons whose bottom-centre anchor falls inside or on boundary of zone
            count = sum(
                1 for px, py in detections_px if zone_def.contains_point(px, py)
            )
            results.append(
                ZoneResult(
                    zone_id=zone_id,
                    availability=ZoneAvailability.COUNTED,
                    visible_count=count,
                )
            )
        else:
            # PARTIAL frame and this zone was not fully observed
            results.append(
                ZoneResult(
                    zone_id=zone_id,
                    availability=ZoneAvailability.NOT_FULLY_OBSERVED,
                    visible_count=None,
                )
            )

    return FrameAggregationResult(
        session_id=observation.session_id,
        frame_index=observation.frame_index,
        media_time_s=observation.media_time_s,
        quality=quality,
        zones=tuple(results),
    )
