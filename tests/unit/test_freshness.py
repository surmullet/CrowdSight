"""Tests for freshness assessment and observation degradation."""
from __future__ import annotations

from typing import Any

import pytest

from crowdsight.service.domain.freshness import (
    FreshnessPolicy,
    apply_freshness_to_observation,
    assess_freshness,
)
from crowdsight.service.domain.models import CrowdFrameObservationV1, QualityState


def test_assess_freshness_within_gap() -> None:
    policy = FreshnessPolicy(max_gap_s=2.0)
    res = assess_freshness(query_time_s=10.0, observation_time_s=11.5, policy=policy)
    assert res.is_fresh is True
    assert res.gap_s == 1.5
    assert res.status == "FRESH"


def test_assess_freshness_exceeds_gap() -> None:
    policy = FreshnessPolicy(max_gap_s=2.0)
    res = assess_freshness(query_time_s=10.0, observation_time_s=12.1, policy=policy)
    assert res.is_fresh is False
    assert res.gap_s == pytest.approx(2.1)
    assert res.status == "STALE"


def test_assess_freshness_boundary() -> None:
    policy = FreshnessPolicy(max_gap_s=2.0)
    res = assess_freshness(query_time_s=10.0, observation_time_s=12.0, policy=policy)
    assert res.is_fresh is True
    assert res.gap_s == 2.0


def test_apply_freshness_downgrades_to_stale(fixture_valid: dict[str, Any]) -> None:
    obs = CrowdFrameObservationV1.model_validate(fixture_valid)
    # media_time_s is 1.4 in fixture_valid
    policy = FreshnessPolicy(max_gap_s=2.0)

    # Query at 1.4 + 5.0 = 6.4s -> gap is 5.0s > 2.0s -> STALE
    stale_obs = apply_freshness_to_observation(obs, query_time_s=6.4, policy=policy)
    assert stale_obs.quality == QualityState.STALE
    assert stale_obs.observation_valid is False
    assert len(stale_obs.detections) == 0
    assert len(stale_obs.fully_observed_zones) == 0


def test_apply_freshness_preserves_fresh_observation(fixture_valid: dict[str, Any]) -> None:
    obs = CrowdFrameObservationV1.model_validate(fixture_valid)
    policy = FreshnessPolicy(max_gap_s=2.0)

    # Query at 1.4 + 0.5 = 1.9s -> gap is 0.5s <= 2.0s -> FRESH
    fresh_obs = apply_freshness_to_observation(obs, query_time_s=1.9, policy=policy)
    assert fresh_obs.quality == QualityState.VALID
    assert fresh_obs.observation_valid is True
    assert len(fresh_obs.detections) == 1
