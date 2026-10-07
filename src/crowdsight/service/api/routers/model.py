"""Model profile metadata, provenance verification, and operational alert status."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from crowdsight.detection.applicability import assess_crowd_operating_use

router = APIRouter(prefix="/api/v1", tags=["Model & Governance"])

REPO_ROOT = Path(__file__).resolve().parents[5]
MODEL_CONFIG_PATH = REPO_ROOT / "configs" / "models" / "crowd_best_local.yaml"


class ModelProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    model_family: str
    checkpoint_env: str
    checkpoint_sha256: str
    checkpoint_available: bool
    image_size: int
    raw_confidence_threshold: float
    confidence_semantics: str = Field(
        default="RAW_MODEL_SCORE",
        description="Uncalibrated model score, not a probability.",
    )
    applicability_status: str
    operational_alerts_allowed: bool
    experimental_warning: str


class AlertStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operational_alerts_allowed: bool
    status: str
    reason: str


@router.get(
    "/model/profile",
    response_model=ModelProfileResponse,
    summary="Get active crowd model profile and applicability status",
)
def get_model_profile() -> ModelProfileResponse:
    profile_data: dict[str, Any] = {}
    if MODEL_CONFIG_PATH.is_file():
        profile_data = yaml.safe_load(MODEL_CONFIG_PATH.read_text(encoding="utf-8")) or {}

    profile_id = str(profile_data.get("profile_id", "crowd_best_local_v2"))
    expected_checkpoint_sha256 = str(profile_data.get("checkpoint_sha256", "12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc"))
    checkpoint_env = str(profile_data.get("checkpoint_env", "CROWDSIGHT_CROWD_CHECKPOINT"))

    # Check if checkpoint exists on server via env or relative path or models/best.pt
    checkpoint_path_str = os.environ.get(checkpoint_env)
    checkpoint_available = False
    if checkpoint_path_str and Path(checkpoint_path_str).is_file():
        checkpoint_available = True
    elif (REPO_ROOT / "models" / "best.pt").is_file():
        checkpoint_available = True
    else:
        raw_src = profile_data.get("source_artifact")
        if raw_src and (MODEL_CONFIG_PATH.parent / str(raw_src)).resolve().is_file():
            checkpoint_available = True

    # Applicability check defaults fail-closed
    decision = assess_crowd_operating_use(
        site_id="default-site",
        camera_view_id="fixed-camera-01",
        model_profile_id=profile_id,
        model_profile_sha256="a" * 64,
        checkpoint_sha256=expected_checkpoint_sha256,
        approval=None,
    )

    return ModelProfileResponse(
        profile_id=profile_id,
        model_family=str(profile_data.get("model_family", "yolo11s_finetuned")),
        checkpoint_env=checkpoint_env,
        checkpoint_sha256=expected_checkpoint_sha256,
        checkpoint_available=checkpoint_available,
        image_size=int(profile_data.get("preprocessing", {}).get("image_size", 1280)),
        raw_confidence_threshold=float(profile_data.get("inference", {}).get("confidence", 0.25)),
        applicability_status=decision.status.value,
        operational_alerts_allowed=decision.operational_alerts_allowed,
        experimental_warning="Thử nghiệm — mô hình chưa được duyệt cho vận hành thực tế. Có thể đếm thiếu ở cảnh đông.",
    )


@router.get(
    "/alerts/status",
    response_model=AlertStatusResponse,
    summary="Get operational alert gate status (always disabled for experimental views)",
)
def get_alerts_status() -> AlertStatusResponse:
    return AlertStatusResponse(
        operational_alerts_allowed=False,
        status="EXPERIMENTAL_NO_APPROVAL",
        reason="Operational alerts are strictly disabled. The current model profile is approved only for experimental recorded-video replay pending site-specific evaluation.",
    )
