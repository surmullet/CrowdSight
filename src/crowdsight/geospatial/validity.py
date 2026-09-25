"""Validity gate for converting visible counts into metric density."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Optional

from crowdsight.common.observations import QualityState


class DensityStatus(str, Enum):
    VALID = "VALID"
    UNAVAILABLE_OBSERVATION = "UNAVAILABLE_OBSERVATION"
    UNAVAILABLE_PARTIAL_COVERAGE = "UNAVAILABLE_PARTIAL_COVERAGE"
    UNAVAILABLE_REGISTRATION = "UNAVAILABLE_REGISTRATION"
    UNAVAILABLE_CALIBRATION = "UNAVAILABLE_CALIBRATION"
    UNAVAILABLE_AREA = "UNAVAILABLE_AREA"
    UNAVAILABLE_CALIBRATION_RESIDUAL = "UNAVAILABLE_CALIBRATION_RESIDUAL"
    UNAVAILABLE_CALIBRATION_EVIDENCE = "UNAVAILABLE_CALIBRATION_EVIDENCE"
    UNAVAILABLE_INDEPENDENCE_EVIDENCE = "UNAVAILABLE_INDEPENDENCE_EVIDENCE"
    UNAVAILABLE_SITE_POLICY = "UNAVAILABLE_SITE_POLICY"
    UNAVAILABLE_DENSITY_NUMERIC_RANGE = "UNAVAILABLE_DENSITY_NUMERIC_RANGE"


@dataclass(frozen=True, slots=True)
class DensityValidity:
    status: DensityStatus
    people_per_m2: Optional[float]


def assess_density_validity(
    *,
    people_estimate: float,
    quality: QualityState,
    fully_observed: bool,
    registration_valid: bool,
    calibration_id: Optional[str],
    usable_area_m2: Optional[float],
    heldout_residual_m: Optional[float],
    site_approved_max_residual_m: Optional[float],
    calibration_evidence_ref: Optional[str] = None,
    calibration_evidence_sha256: Optional[str] = None,
    independence_verified: bool = False,
    independence_review_ref: Optional[str] = None,
    independence_review_sha256: Optional[str] = None,
    site_policy_approved: bool = False,
    site_policy_approval_ref: Optional[str] = None,
    site_policy_approval_sha256: Optional[str] = None,
) -> DensityValidity:
    """Return density only when evidence and site policy support it.

    ``site_approved_max_residual_m`` is an explicitly approved calibration
    criterion, not a universal default. Image-space data alone cannot pass.
    Evidence references and hashes are recorded and format-checked here, not
    dereferenced. The caller must verify each artifact's content hash and
    authorization before setting the corresponding verification/approval flag.
    """
    if type(people_estimate) not in (int, float) or not math.isfinite(people_estimate) or people_estimate < 0:
        raise ValueError("people_estimate must be finite and nonnegative")
    if not isinstance(quality, QualityState):
        raise ValueError("quality must be a QualityState")
    if type(fully_observed) is not bool or type(registration_valid) is not bool:
        raise ValueError("coverage and registration validity must be booleans")
    if quality in (QualityState.UNKNOWN, QualityState.STALE):
        return DensityValidity(DensityStatus.UNAVAILABLE_OBSERVATION, None)
    if not fully_observed or quality is QualityState.PARTIAL:
        return DensityValidity(DensityStatus.UNAVAILABLE_PARTIAL_COVERAGE, None)
    if not registration_valid:
        return DensityValidity(DensityStatus.UNAVAILABLE_REGISTRATION, None)
    if not isinstance(calibration_id, str) or not calibration_id.strip():
        return DensityValidity(DensityStatus.UNAVAILABLE_CALIBRATION, None)
    if (
        usable_area_m2 is None
        or type(usable_area_m2) not in (int, float)
        or not math.isfinite(usable_area_m2)
        or usable_area_m2 <= 0
    ):
        return DensityValidity(DensityStatus.UNAVAILABLE_AREA, None)
    if (
        heldout_residual_m is None
        or site_approved_max_residual_m is None
        or type(heldout_residual_m) not in (int, float)
        or type(site_approved_max_residual_m) not in (int, float)
        or not math.isfinite(heldout_residual_m)
        or not math.isfinite(site_approved_max_residual_m)
        or heldout_residual_m < 0
        or site_approved_max_residual_m < 0
        or heldout_residual_m > site_approved_max_residual_m
    ):
        return DensityValidity(DensityStatus.UNAVAILABLE_CALIBRATION_RESIDUAL, None)
    if (
        not isinstance(calibration_evidence_ref, str)
        or not calibration_evidence_ref.strip()
        or not isinstance(calibration_evidence_sha256, str)
        or len(calibration_evidence_sha256) != 64
        or any(char not in "0123456789abcdefABCDEF" for char in calibration_evidence_sha256)
    ):
        return DensityValidity(DensityStatus.UNAVAILABLE_CALIBRATION_EVIDENCE, None)
    if (
        type(independence_verified) is not bool
        or not independence_verified
        or not isinstance(independence_review_ref, str)
        or not independence_review_ref.strip()
        or not isinstance(independence_review_sha256, str)
        or len(independence_review_sha256) != 64
        or any(char not in "0123456789abcdefABCDEF" for char in independence_review_sha256)
    ):
        return DensityValidity(DensityStatus.UNAVAILABLE_INDEPENDENCE_EVIDENCE, None)
    if (
        type(site_policy_approved) is not bool
        or not site_policy_approved
        or not isinstance(site_policy_approval_ref, str)
        or not site_policy_approval_ref.strip()
        or not isinstance(site_policy_approval_sha256, str)
        or len(site_policy_approval_sha256) != 64
        or any(char not in "0123456789abcdefABCDEF" for char in site_policy_approval_sha256)
    ):
        return DensityValidity(DensityStatus.UNAVAILABLE_SITE_POLICY, None)
    density = people_estimate / usable_area_m2
    if not math.isfinite(density) or (people_estimate > 0 and density == 0.0):
        return DensityValidity(DensityStatus.UNAVAILABLE_DENSITY_NUMERIC_RANGE, None)
    return DensityValidity(
        DensityStatus.VALID,
        density,
    )
