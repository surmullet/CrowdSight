"""Tests for frame aggregation logic across all quality states."""
from __future__ import annotations

from typing import Any

import pytest

from crowdsight.service.domain.aggregation import (
    ZoneAvailability,
    ZoneResult,
    aggregate_frame,
)
from crowdsight.service.domain.models import CrowdFrameObservationV1, QualityState
from crowdsight.service.domain.zones import (
    Point2D,
    ZoneDefinition,
    ZonePolygon,
    ZoneSet,
)


def make_test_zone_set() -> ZoneSet:
    # North gate: x: 900..1100, y: 500..800
    # In fixture_valid: detection anchor is at x=0.51, y=0.72 -> px=979.2, py=777.6
    # This falls squarely inside north-gate!
    north_gate = ZoneDefinition(
        zone_id="north-gate",
        name="North Gate",
        polygon=ZonePolygon(
            vertices=(
                Point2D(x=900, y=500),
                Point2D(x=1100, y=500),
                Point2D(x=1100, y=800),
                Point2D(x=900, y=800),
            )
        ),
    )
    # South gate: x: 100..400, y: 100..400
    south_gate = ZoneDefinition(
        zone_id="south-gate",
        name="South Gate",
        polygon=ZonePolygon(
            vertices=(
                Point2D(x=100, y=100),
                Point2D(x=400, y=100),
                Point2D(x=400, y=400),
                Point2D(x=100, y=400),
            )
        ),
    )
    return ZoneSet(
        zone_set_id="zs-test",
        version=1,
        name="Test Zone Set",
        image_width=1920,
        image_height=1080,
        zones=(north_gate, south_gate),
    )


def test_aggregate_valid_fixture(fixture_valid: dict[str, Any]) -> None:
    # Update fixture to cover both zones so it is VALID for test zone set
    valid_data = dict(fixture_valid)
    valid_data["fully_observed_zones"] = ["north-gate", "south-gate"]
    obs = CrowdFrameObservationV1.model_validate(valid_data)
    zs = make_test_zone_set()

    res = aggregate_frame(obs, zs)
    assert res.quality == QualityState.VALID
    assert len(res.zones) == 2

    # Map by zone_id
    zone_map = {z.zone_id: z for z in res.zones}
    # north-gate contains the detection -> count = 1
    assert zone_map["north-gate"].availability == ZoneAvailability.COUNTED
    assert zone_map["north-gate"].visible_count == 1
    assert zone_map["north-gate"].density_people_per_m2 is None

    # south-gate is fully observed but has no detections -> count = 0 (genuine 0)
    assert zone_map["south-gate"].availability == ZoneAvailability.COUNTED
    assert zone_map["south-gate"].visible_count == 0


def test_aggregate_zero_fixture(fixture_zero: dict[str, Any]) -> None:
    zero_data = dict(fixture_zero)
    zero_data["fully_observed_zones"] = ["north-gate", "south-gate"]
    obs = CrowdFrameObservationV1.model_validate(zero_data)
    zs = make_test_zone_set()

    res = aggregate_frame(obs, zs)
    zone_map = {z.zone_id: z for z in res.zones}
    assert zone_map["north-gate"].availability == ZoneAvailability.COUNTED
    assert zone_map["north-gate"].visible_count == 0
    assert zone_map["south-gate"].availability == ZoneAvailability.COUNTED
    assert zone_map["south-gate"].visible_count == 0


def test_aggregate_partial_fixture(fixture_partial: dict[str, Any]) -> None:
    # fixture_partial has fully_observed_zones = ["north-gate"]
    obs = CrowdFrameObservationV1.model_validate(fixture_partial)
    zs = make_test_zone_set()

    res = aggregate_frame(obs, zs)
    zone_map = {z.zone_id: z for z in res.zones}

    # north-gate is observed -> COUNTED (1)
    assert zone_map["north-gate"].availability == ZoneAvailability.COUNTED
    assert zone_map["north-gate"].visible_count == 1

    # south-gate is not in fully_observed_zones -> NOT_FULLY_OBSERVED and visible_count=None (NEVER 0!)
    assert zone_map["south-gate"].availability == ZoneAvailability.NOT_FULLY_OBSERVED
    assert zone_map["south-gate"].visible_count is None


def test_aggregate_unknown_fixture(fixture_unknown: dict[str, Any]) -> None:
    obs = CrowdFrameObservationV1.model_validate(fixture_unknown)
    zs = make_test_zone_set()

    res = aggregate_frame(obs, zs)
    assert res.quality == QualityState.UNKNOWN
    for z in res.zones:
        assert z.availability == ZoneAvailability.UNKNOWN
        assert z.visible_count is None  # NEVER 0


def test_aggregate_stale_fixture(fixture_stale: dict[str, Any]) -> None:
    obs = CrowdFrameObservationV1.model_validate(fixture_stale)
    zs = make_test_zone_set()

    res = aggregate_frame(obs, zs)
    assert res.quality == QualityState.STALE
    for z in res.zones:
        assert z.availability == ZoneAvailability.STALE
        assert z.visible_count is None


def test_zone_result_invariant_enforcement() -> None:
    # Attempting to set visible_count on an unobserved zone must raise ValueError
    with pytest.raises(ValueError, match="visible_count must be None when availability is UNKNOWN"):
        ZoneResult(
            zone_id="test",
            availability=ZoneAvailability.UNKNOWN,
            visible_count=0,
        )

    # Attempting to leave visible_count None on COUNTED zone must raise ValueError
    with pytest.raises(ValueError, match="visible_count cannot be None when availability is COUNTED"):
        ZoneResult(
            zone_id="test",
            availability=ZoneAvailability.COUNTED,
            visible_count=None,
        )
