"""Freshness policy and staleness evaluation for recorded video playback queries."""
from __future__ import annotations

import math
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from crowdsight.service.domain.models import CrowdFrameObservationV1, QualityState


class FreshnessPolicy(BaseModel):
    """Configuration governing when a temporal observation gap becomes STALE."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    max_gap_s: float = Field(
        default=2.0,
        gt=0.0,
        description="Maximum allowed difference in seconds between query time and nearest observation.",
    )


@dataclass(frozen=True, slots=True)
class FreshnessAssessment:
    is_fresh: bool
    gap_s: float
    status: str


def assess_freshness(
    query_time_s: float,
    observation_time_s: float,
    policy: FreshnessPolicy,
) -> FreshnessAssessment:
    """Assess whether an observation at observation_time_s is fresh at query_time_s."""
    if not math.isfinite(query_time_s) or query_time_s < 0:
        raise ValueError("query_time_s must be non-negative and finite")
    if not math.isfinite(observation_time_s) or observation_time_s < 0:
        raise ValueError("observation_time_s must be non-negative and finite")

    gap_s = abs(query_time_s - observation_time_s)
    if gap_s <= policy.max_gap_s:
        return FreshnessAssessment(is_fresh=True, gap_s=gap_s, status="FRESH")
    return FreshnessAssessment(is_fresh=False, gap_s=gap_s, status="STALE")


def apply_freshness_to_observation(
    observation: CrowdFrameObservationV1,
    query_time_s: float,
    policy: FreshnessPolicy,
) -> CrowdFrameObservationV1:
    """Downgrade an observation to STALE if the time gap exceeds policy limit."""
    assessment = assess_freshness(query_time_s, observation.media_time_s, policy)
    if assessment.is_fresh:
        return observation

    # Stale: transform to explicit STALE quality
    return CrowdFrameObservationV1(
        source_id=observation.source_id,
        session_id=observation.session_id,
        model_profile_id=observation.model_profile_id,
        model_profile_sha256=observation.model_profile_sha256,
        checkpoint_sha256=observation.checkpoint_sha256,
        tracker_config_sha256=observation.tracker_config_sha256,
        frame_index=observation.frame_index,
        media_time_s=observation.media_time_s,
        captured_at=observation.captured_at,
        image_width=observation.image_width,
        image_height=observation.image_height,
        observation_valid=False,
        registration_valid=False,
        fully_observed_zones=(),
        confidence_semantics="RAW_MODEL_SCORE",
        quality=QualityState.STALE,
        detections=(),
    )
