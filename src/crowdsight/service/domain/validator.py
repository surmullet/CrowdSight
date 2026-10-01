"""Two-stage validator for crowd-frame observations.

Stage 1: Fast structural validation using JSON Schema (Draft 2020-12).
Stage 2: Semantic cross-validation (geometric bounds, bottom-centre alignment,
         tracker hash pairing, zone-set coverage consistency).
"""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from jsonschema.validators import Draft202012Validator

from crowdsight.service.domain.models import (
    CrowdFrameObservationV1,
    QualityState,
)


class ObservationValidationError(ValueError):
    """Raised when an observation fails structural or semantic validation."""

    def __init__(self, message: str, *, code: str = "OBSERVATION_INVALID", errors: Sequence[str] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.errors = list(errors or [])


class TwoStageObservationValidator:
    """Validates observation dictionaries against schema v1 and domain rules."""

    def __init__(self, schema_path: Path | None = None) -> None:
        if schema_path is None:
            # Default to contracts/v1/crowd-frame-observation.schema.json in repo
            repo_root = Path(__file__).resolve().parents[4]
            schema_path = repo_root / "contracts" / "v1" / "crowd-frame-observation.schema.json"

        if not schema_path.is_file():
            raise FileNotFoundError(f"Schema file not found at {schema_path}")

        schema_dict = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema_dict)
        self._json_validator = Draft202012Validator(schema_dict)

    def validate_dict(
        self,
        payload: Mapping[str, Any],
        *,
        configured_zone_ids: set[str] | None = None,
    ) -> CrowdFrameObservationV1:
        """Run two-stage validation on raw dictionary.

        Args:
            payload: Dict to validate against v1 schema.
            configured_zone_ids: Set of active zone IDs to check coverage against.

        Returns:
            Validated CrowdFrameObservationV1 instance.

        Raises:
            ObservationValidationError: On any structural or semantic violation.
        """
        # Stage 1: JSON Schema structural validation
        schema_errors = sorted(self._json_validator.iter_errors(payload), key=lambda e: e.path)
        if schema_errors:
            error_details = [
                f"{'/'.join(str(p) for p in err.path) or 'root'}: {err.message}"
                for err in schema_errors
            ]
            raise ObservationValidationError(
                f"Observation failed JSON Schema validation ({len(schema_errors)} errors)",
                code="SCHEMA_VALIDATION_FAILED",
                errors=error_details,
            )

        # Stage 2: Pydantic parsing & model invariant validation
        try:
            observation = CrowdFrameObservationV1.model_validate(payload)
        except Exception as exc:
            raise ObservationValidationError(
                f"Observation failed model validation: {exc}",
                code="MODEL_VALIDATION_FAILED",
                errors=[str(exc)],
            ) from exc

        # Stage 2b: Coverage verification against configured zone set
        if configured_zone_ids is not None:
            observed_set = set(observation.fully_observed_zones)
            if observation.quality == QualityState.VALID:
                if observed_set != configured_zone_ids:
                    raise ObservationValidationError(
                        f"VALID observation must cover exactly all configured zones. "
                        f"Expected {sorted(configured_zone_ids)}, got {sorted(observed_set)}",
                        code="COVERAGE_MISMATCH_VALID",
                    )
            elif observation.quality == QualityState.PARTIAL:
                if not observed_set.issubset(configured_zone_ids):
                    unknown_zones = observed_set - configured_zone_ids
                    raise ObservationValidationError(
                        f"PARTIAL observation contains zones not in configured set: {sorted(unknown_zones)}",
                        code="COVERAGE_UNKNOWN_ZONES",
                    )
                if observed_set == configured_zone_ids:
                    raise ObservationValidationError(
                        "PARTIAL observation cannot cover all configured zones; should be VALID",
                        code="COVERAGE_SHOULD_BE_VALID",
                    )
                if len(observed_set) == 0:
                    raise ObservationValidationError(
                        "PARTIAL observation must contain at least one fully observed zone",
                        code="COVERAGE_EMPTY_PARTIAL",
                    )

        return observation
