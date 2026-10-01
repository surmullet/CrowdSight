"""Tests for TwoStageObservationValidator."""
from __future__ import annotations

from typing import Any

import pytest

from crowdsight.service.domain.models import QualityState
from crowdsight.service.domain.validator import (
    ObservationValidationError,
    TwoStageObservationValidator,
)


@pytest.fixture
def validator() -> TwoStageObservationValidator:
    return TwoStageObservationValidator()


def test_validator_accepts_valid_fixture(
    validator: TwoStageObservationValidator, fixture_valid: dict[str, Any]
) -> None:
    obs = validator.validate_dict(fixture_valid, configured_zone_ids={"north-gate"})
    assert obs.quality == QualityState.VALID


def test_validator_rejects_missing_required_property(
    validator: TwoStageObservationValidator, fixture_valid: dict[str, Any]
) -> None:
    bad_data = dict(fixture_valid)
    del bad_data["source_id"]
    with pytest.raises(ObservationValidationError) as exc_info:
        validator.validate_dict(bad_data)
    assert exc_info.value.code == "SCHEMA_VALIDATION_FAILED"


def test_validator_rejects_coverage_mismatch_for_valid_frame(
    validator: TwoStageObservationValidator, fixture_valid: dict[str, Any]
) -> None:
    # Configured zones include north-gate and south-gate, but frame only has north-gate
    with pytest.raises(ObservationValidationError) as exc_info:
        validator.validate_dict(fixture_valid, configured_zone_ids={"north-gate", "south-gate"})
    assert exc_info.value.code == "COVERAGE_MISMATCH_VALID"


def test_validator_accepts_partial_fixture_with_subset_coverage(
    validator: TwoStageObservationValidator, fixture_partial: dict[str, Any]
) -> None:
    # Partial has north-gate, configured has north-gate and south-gate -> proper subset!
    obs = validator.validate_dict(fixture_partial, configured_zone_ids={"north-gate", "south-gate"})
    assert obs.quality == QualityState.PARTIAL


def test_validator_rejects_partial_fixture_covering_all_configured_zones(
    validator: TwoStageObservationValidator, fixture_partial: dict[str, Any]
) -> None:
    # If it covers all zones, it should have been marked VALID
    with pytest.raises(ObservationValidationError) as exc_info:
        validator.validate_dict(fixture_partial, configured_zone_ids={"north-gate"})
    assert exc_info.value.code == "COVERAGE_SHOULD_BE_VALID"


def test_validator_rejects_partial_with_unknown_zones(
    validator: TwoStageObservationValidator, fixture_partial: dict[str, Any]
) -> None:
    with pytest.raises(ObservationValidationError) as exc_info:
        validator.validate_dict(fixture_partial, configured_zone_ids={"south-gate"})
    assert exc_info.value.code == "COVERAGE_UNKNOWN_ZONES"
