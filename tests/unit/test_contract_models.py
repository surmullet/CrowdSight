"""Tests verifying that Pydantic v2 models faithfully represent all 6 contract fixtures."""
from __future__ import annotations

from typing import Any

import pytest
from jsonschema.validators import Draft202012Validator
from pydantic import ValidationError

from crowdsight.service.domain.models import (
    CrowdFrameObservationV1,
    QualityState,
)


def test_schema_itself_is_valid_draft202012(schema_dict: dict[str, Any]) -> None:
    """Check that the v1 schema itself is valid Draft 2020-12."""
    Draft202012Validator.check_schema(schema_dict)


def test_all_six_fixtures_pass_jsonschema(
    schema_dict: dict[str, Any],
    all_six_fixtures: list[tuple[str, dict[str, Any]]],
) -> None:
    """Check that all 6 fixtures validate against the JSON Schema."""
    validator = Draft202012Validator(schema_dict)
    for name, fixture in all_six_fixtures:
        errors = list(validator.iter_errors(fixture))
        assert not errors, f"Fixture {name} failed JSON Schema validation: {errors}"


def test_all_six_fixtures_parse_into_pydantic_model(
    all_six_fixtures: list[tuple[str, dict[str, Any]]],
) -> None:
    """Check that all 6 fixtures parse cleanly into CrowdFrameObservationV1."""
    for _name, fixture in all_six_fixtures:
        model = CrowdFrameObservationV1.model_validate(fixture)
        assert model.session_id == fixture["session_id"]
        assert model.quality.value == fixture["quality"]
        assert model.observation_valid == fixture["observation_valid"]
        assert model.confidence_semantics == "RAW_MODEL_SCORE"


def test_valid_fixture_details(fixture_valid: dict[str, Any]) -> None:
    model = CrowdFrameObservationV1.model_validate(fixture_valid)
    assert model.quality == QualityState.VALID
    assert model.observation_valid is True
    assert model.fully_observed_zones == ("north-gate",)
    assert len(model.detections) == 1
    d = model.detections[0]
    assert d.track_id is None
    assert d.confidence == 0.87
    assert d.x == 0.51
    assert d.y == 0.72


def test_zero_fixture_details(fixture_zero: dict[str, Any]) -> None:
    model = CrowdFrameObservationV1.model_validate(fixture_zero)
    assert model.quality == QualityState.VALID
    assert model.observation_valid is True
    assert model.fully_observed_zones == ("north-gate",)
    assert len(model.detections) == 0


def test_partial_fixture_details(fixture_partial: dict[str, Any]) -> None:
    model = CrowdFrameObservationV1.model_validate(fixture_partial)
    assert model.quality == QualityState.PARTIAL
    assert model.observation_valid is True
    assert model.fully_observed_zones == ("north-gate",)
    assert len(model.detections) == 1


def test_unknown_fixture_details(fixture_unknown: dict[str, Any]) -> None:
    model = CrowdFrameObservationV1.model_validate(fixture_unknown)
    assert model.quality == QualityState.UNKNOWN
    assert model.observation_valid is False
    assert model.fully_observed_zones == ()
    assert len(model.detections) == 0


def test_stale_fixture_details(fixture_stale: dict[str, Any]) -> None:
    model = CrowdFrameObservationV1.model_validate(fixture_stale)
    assert model.quality == QualityState.STALE
    assert model.observation_valid is False
    assert model.fully_observed_zones == ()
    assert len(model.detections) == 0


def test_tracked_fixture_details(fixture_tracked: dict[str, Any]) -> None:
    model = CrowdFrameObservationV1.model_validate(fixture_tracked)
    assert model.quality == QualityState.VALID
    assert model.tracker_config_sha256 is not None
    assert len(model.detections) == 1
    assert model.detections[0].track_id == 17


def test_tracked_detections_require_tracker_hash(fixture_tracked: dict[str, Any]) -> None:
    bad_data = dict(fixture_tracked)
    bad_data["tracker_config_sha256"] = None
    with pytest.raises(ValidationError, match="require non-null tracker_config_sha256"):
        CrowdFrameObservationV1.model_validate(bad_data)


def test_unknown_quality_must_have_empty_detections(fixture_valid: dict[str, Any]) -> None:
    bad_data = dict(fixture_valid)
    bad_data["quality"] = "UNKNOWN"
    bad_data["observation_valid"] = False
    bad_data["fully_observed_zones"] = []
    # Keeps detections -> must fail!
    with pytest.raises(ValidationError, match="must have empty detections list"):
        CrowdFrameObservationV1.model_validate(bad_data)


def test_valid_quality_requires_observation_valid_true(fixture_valid: dict[str, Any]) -> None:
    bad_data = dict(fixture_valid)
    bad_data["observation_valid"] = False
    with pytest.raises(ValidationError, match="requires observation_valid=True"):
        CrowdFrameObservationV1.model_validate(bad_data)


def test_invalid_sha256_format(fixture_valid: dict[str, Any]) -> None:
    bad_data = dict(fixture_valid)
    bad_data["checkpoint_sha256"] = "too-short"
    with pytest.raises(ValidationError, match="Value must be a 64-character hex"):
        CrowdFrameObservationV1.model_validate(bad_data)


def test_bbox_anchor_mismatch_fails(fixture_valid: dict[str, Any]) -> None:
    bad_data = dict(fixture_valid)
    bad_detections = list(bad_data["detections"])
    bad_detections[0] = dict(bad_detections[0])
    # Modify x anchor to disagree with bbox bottom-centre
    bad_detections[0]["x"] = 0.99
    bad_data["detections"] = bad_detections
    with pytest.raises(ValidationError, match="does not match bbox bottom-centre"):
        CrowdFrameObservationV1.model_validate(bad_data)
