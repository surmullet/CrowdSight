"""Fail-closed site/view applicability decision for crowd model results.

Frame quality describes available visual evidence. This decision describes
whether one exact model and camera view may drive operational alerts.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CrowdUseStatus(str, Enum):
    EXPERIMENTAL_NO_APPROVAL = "EXPERIMENTAL_NO_APPROVAL"
    EXPERIMENTAL_MODEL_OR_VIEW_MISMATCH = "EXPERIMENTAL_MODEL_OR_VIEW_MISMATCH"
    EXPERIMENTAL_EVALUATION_UNVERIFIED = "EXPERIMENTAL_EVALUATION_UNVERIFIED"
    EXPERIMENTAL_SITE_POLICY_UNAPPROVED = "EXPERIMENTAL_SITE_POLICY_UNAPPROVED"
    APPROVED_FOR_VIEW = "APPROVED_FOR_VIEW"


@dataclass(frozen=True, slots=True)
class CrowdUseDecision:
    status: CrowdUseStatus
    operational_alerts_allowed: bool


@dataclass(frozen=True, slots=True)
class CrowdViewApproval:
    """Evidence-bound approval supplied by a trusted site-policy service.

    The service must verify the referenced files, their SHA-256 digests, the
    independent evaluation decision, and the approver's authority. This
    dataclass records those decisions; it cannot authenticate them.
    """

    site_id: str
    camera_view_id: str
    model_profile_id: str
    model_profile_sha256: str
    checkpoint_sha256: str
    evaluation_ref: str
    evaluation_sha256: str
    independence_verified: bool
    site_acceptance_passed: bool
    site_policy_approved: bool
    site_approval_ref: str
    site_approval_sha256: str


def _valid_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdefABCDEF" for character in value
    )


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def assess_crowd_operating_use(
    *,
    site_id: str,
    camera_view_id: str,
    model_profile_id: str,
    model_profile_sha256: str,
    checkpoint_sha256: str,
    approval: Optional[CrowdViewApproval] = None,
) -> CrowdUseDecision:
    """Return an alert decision for one exact model and versioned camera view.

    An absent or incomplete approval permits an experimental display only.
    Observation quality, including ``VALID``, never overrides this decision.
    """
    if not all(_nonempty(value) for value in (site_id, camera_view_id, model_profile_id)):
        raise ValueError("site, camera view, and model profile IDs must be nonempty")
    if not _valid_sha256(model_profile_sha256) or not _valid_sha256(checkpoint_sha256):
        raise ValueError("model profile and checkpoint hashes must be SHA-256 digests")
    if approval is None:
        return CrowdUseDecision(CrowdUseStatus.EXPERIMENTAL_NO_APPROVAL, False)
    if not isinstance(approval, CrowdViewApproval):
        raise TypeError("approval must be a CrowdViewApproval or null")
    if (
        approval.site_id != site_id
        or approval.camera_view_id != camera_view_id
        or approval.model_profile_id != model_profile_id
        or not _valid_sha256(approval.model_profile_sha256)
        or not _valid_sha256(approval.checkpoint_sha256)
        or approval.model_profile_sha256.lower() != model_profile_sha256.lower()
        or approval.checkpoint_sha256.lower() != checkpoint_sha256.lower()
    ):
        return CrowdUseDecision(CrowdUseStatus.EXPERIMENTAL_MODEL_OR_VIEW_MISMATCH, False)
    if (
        not _nonempty(approval.evaluation_ref)
        or not _valid_sha256(approval.evaluation_sha256)
        or approval.independence_verified is not True
        or approval.site_acceptance_passed is not True
    ):
        return CrowdUseDecision(CrowdUseStatus.EXPERIMENTAL_EVALUATION_UNVERIFIED, False)
    if (
        approval.site_policy_approved is not True
        or not _nonempty(approval.site_approval_ref)
        or not _valid_sha256(approval.site_approval_sha256)
    ):
        return CrowdUseDecision(CrowdUseStatus.EXPERIMENTAL_SITE_POLICY_UNAPPROVED, False)
    return CrowdUseDecision(CrowdUseStatus.APPROVED_FOR_VIEW, True)
