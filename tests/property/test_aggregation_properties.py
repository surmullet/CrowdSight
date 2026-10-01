"""Hypothesis property-based tests for domain invariants."""
from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from crowdsight.service.domain.aggregation import (
    ZoneAvailability,
    aggregate_frame,
)
from crowdsight.service.domain.models import (
    CrowdFrameObservationV1,
    DetectionV1,
    QualityState,
)
from crowdsight.service.domain.zones import (
    Point2D,
    ZoneDefinition,
    ZonePolygon,
    ZoneSet,
)

# Strategies for property tests
detection_strategy = st.builds(
    DetectionV1,
    x=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    y=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    track_id=st.none(),
    bbox_xyxy=st.none(),
)

dummy_sha256 = "a" * 64


def build_two_zone_set() -> ZoneSet:
    z1 = ZoneDefinition(
        zone_id="zone-a",
        name="Zone A",
        polygon=ZonePolygon(
            vertices=(
                Point2D(x=0, y=0),
                Point2D(x=500, y=0),
                Point2D(x=500, y=500),
                Point2D(x=0, y=500),
            )
        ),
    )
    z2 = ZoneDefinition(
        zone_id="zone-b",
        name="Zone B",
        polygon=ZonePolygon(
            vertices=(
                Point2D(x=500, y=500),
                Point2D(x=1000, y=500),
                Point2D(x=1000, y=1000),
                Point2D(x=500, y=1000),
            )
        ),
    )
    return ZoneSet(
        zone_set_id="zs-prop",
        version=1,
        name="Property Test Set",
        image_width=1000,
        image_height=1000,
        zones=(z1, z2),
    )


@given(detections=st.lists(detection_strategy, max_size=20))
def test_valid_frame_invariants(detections: list[DetectionV1]) -> None:
    """Property: VALID frame always counts all configured zones, counts are >= 0."""
    zs = build_two_zone_set()
    obs = CrowdFrameObservationV1(
        source_id="src-prop",
        session_id="sess-prop",
        model_profile_id="crowd_best_local_v2",
        model_profile_sha256=dummy_sha256,
        checkpoint_sha256=dummy_sha256,
        tracker_config_sha256=None,
        frame_index=0,
        media_time_s=0.0,
        image_width=1000,
        image_height=1000,
        observation_valid=True,
        registration_valid=False,
        fully_observed_zones=("zone-a", "zone-b"),
        confidence_semantics="RAW_MODEL_SCORE",
        quality=QualityState.VALID,
        detections=tuple(detections),
    )
    res = aggregate_frame(obs, zs)

    assert res.quality == QualityState.VALID
    for z in res.zones:
        # Invariant 1: all zones are COUNTED
        assert z.availability == ZoneAvailability.COUNTED
        # Invariant 2: visible_count is not None and >= 0
        assert z.visible_count is not None
        assert z.visible_count >= 0
        # Invariant 3: density is ALWAYS None
        assert z.density_people_per_m2 is None


@given(detections=st.lists(detection_strategy, max_size=20))
def test_partial_frame_invariants(detections: list[DetectionV1]) -> None:
    """Property: PARTIAL frame only counts observed zones; unobserved is NOT_FULLY_OBSERVED and None."""
    zs = build_two_zone_set()
    obs = CrowdFrameObservationV1(
        source_id="src-prop",
        session_id="sess-prop",
        model_profile_id="crowd_best_local_v2",
        model_profile_sha256=dummy_sha256,
        checkpoint_sha256=dummy_sha256,
        tracker_config_sha256=None,
        frame_index=0,
        media_time_s=0.0,
        image_width=1000,
        image_height=1000,
        observation_valid=True,
        registration_valid=False,
        fully_observed_zones=("zone-a",),  # Only zone-a is fully observed
        confidence_semantics="RAW_MODEL_SCORE",
        quality=QualityState.PARTIAL,
        detections=tuple(detections),
    )
    res = aggregate_frame(obs, zs)

    assert res.quality == QualityState.PARTIAL
    zone_map = {z.zone_id: z for z in res.zones}

    assert zone_map["zone-a"].availability == ZoneAvailability.COUNTED
    assert zone_map["zone-a"].visible_count is not None

    assert zone_map["zone-b"].availability == ZoneAvailability.NOT_FULLY_OBSERVED
    assert zone_map["zone-b"].visible_count is None  # NEVER 0!


@given(quality=st.sampled_from([QualityState.UNKNOWN, QualityState.STALE]))
def test_unknown_and_stale_never_have_counts(quality: QualityState) -> None:
    """Property: UNKNOWN and STALE never produce a count."""
    zs = build_two_zone_set()
    obs = CrowdFrameObservationV1(
        source_id="src-prop",
        session_id="sess-prop",
        model_profile_id="crowd_best_local_v2",
        model_profile_sha256=dummy_sha256,
        checkpoint_sha256=dummy_sha256,
        tracker_config_sha256=None,
        frame_index=0,
        media_time_s=0.0,
        image_width=1000,
        image_height=1000,
        observation_valid=False,
        registration_valid=False,
        fully_observed_zones=(),
        confidence_semantics="RAW_MODEL_SCORE",
        quality=quality,
        detections=(),
    )
    res = aggregate_frame(obs, zs)

    expected_avail = (
        ZoneAvailability.UNKNOWN
        if quality == QualityState.UNKNOWN
        else ZoneAvailability.STALE
    )
    for z in res.zones:
        assert z.availability == expected_avail
        assert z.visible_count is None
        assert z.density_people_per_m2 is None
