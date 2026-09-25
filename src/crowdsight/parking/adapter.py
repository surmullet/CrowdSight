"""Model-independent contract for the planned parking-occupancy model.

No trained parking model is installed in this repository. The protocol allows
the backend to develop against a mock/fixture implementation while the
AI/ML lead collects permitted data, trains the model, and validates a concrete
adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
from typing import Protocol, Sequence

import numpy as np

from crowdsight.common.observations import QualityState
from crowdsight.common.parking import ParkingSpaceResult, ParkingState


@dataclass(frozen=True, slots=True)
class ParkingModelProfile:
    """Immutable identity and runtime settings for a trained parking model."""

    profile_id: str
    checkpoint_path: Path
    expected_sha256: str
    profile_sha256: str
    site_id: str
    camera_view_id: str
    space_layout_version: str

    def __post_init__(self) -> None:
        if not all(
            isinstance(value, str) and value.strip()
            for value in (self.profile_id, self.site_id, self.camera_view_id, self.space_layout_version)
        ):
            raise ValueError("profile, site, camera, and space layout IDs must be nonempty")
        if not isinstance(self.expected_sha256, str) or len(self.expected_sha256) != 64 or any(
            char not in "0123456789abcdefABCDEF" for char in self.expected_sha256
        ):
            raise ValueError("expected_sha256 must be a 64-character hex digest")
        if not isinstance(self.profile_sha256, str) or len(self.profile_sha256) != 64 or any(
            char not in "0123456789abcdefABCDEF" for char in self.profile_sha256
        ):
            raise ValueError("profile_sha256 must be a 64-character hex digest")


def load_parking_model_profile(
    profile_path: Path,
    *,
    checkpoint_path: Path | None = None,
) -> ParkingModelProfile:
    """Load a finalized parking profile and hash the exact YAML bytes.

    Weights are resolved only from an explicitly injected trusted path or the
    environment variable named in the profile. Pending template values fail
    dataclass validation and cannot be used for inference.
    """
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read parking model profiles") from exc
    config_path = Path(profile_path).expanduser().resolve()
    if not config_path.is_file():
        raise FileNotFoundError(f"Parking model profile not found: {config_path}")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError(f"Parking model profile must contain a YAML mapping: {config_path}")
    if config.get("task") != "parking_space_occupancy_classification":
        raise ValueError("Parking model profile task must be parking_space_occupancy_classification")
    profile_status = config.get("status")
    release_approval = config.get("release_approval")
    if profile_status not in ("trained_candidate", "release_approved"):
        raise ValueError(
            "Parking profile status must be trained_candidate or release_approved"
        )
    if (profile_status == "trained_candidate" and release_approval is not False) or (
        profile_status == "release_approved" and release_approval is not True
    ):
        raise ValueError("Parking profile status and release_approval flag are inconsistent")
    checkpoint = checkpoint_path
    checkpoint_env = config.get("checkpoint_env")
    if checkpoint is None and isinstance(checkpoint_env, str) and checkpoint_env.strip():
        env_value = os.environ.get(checkpoint_env)
        if env_value:
            checkpoint = Path(env_value).expanduser()
    if checkpoint is None:
        raise ValueError(
            f"Supply a trusted checkpoint_path or set the profile variable {checkpoint_env!r}; "
            "model weights are stored outside the source repository"
        )
    try:
        return ParkingModelProfile(
            profile_id=config["profile_id"],
            checkpoint_path=Path(checkpoint),
            expected_sha256=config["checkpoint_sha256"],
            profile_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
            site_id=config["site_id"],
            camera_view_id=config["camera_view_id"],
            space_layout_version=config["space_layout_version"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Incomplete parking model profile: {config_path}") from exc


def verify_parking_checkpoint(profile: ParkingModelProfile) -> Path:
    """Resolve the external checkpoint and verify it matches the profile hash."""
    if not isinstance(profile, ParkingModelProfile):
        raise TypeError("profile must be a ParkingModelProfile")
    checkpoint = profile.checkpoint_path.expanduser().resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(f"Parking checkpoint unavailable: {checkpoint}")
    digest = hashlib.sha256()
    with checkpoint.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    actual_sha256 = digest.hexdigest()
    if actual_sha256.lower() != profile.expected_sha256.lower():
        raise ValueError(
            f"Parking checkpoint SHA-256 mismatch: expected {profile.expected_sha256}, "
            f"got {actual_sha256}"
        )
    return checkpoint


class ParkingOccupancyModel(Protocol):
    """Inference boundary; physical parking control is deliberately excluded."""

    profile_id: str

    def classify_spaces(
        self,
        frame_bgr: np.ndarray,
        space_layout_version: str,
        space_ids: Sequence[str],
        evidence_time_s: float,
    ) -> Sequence[ParkingSpaceResult]:
        """Return one state per configured stall, including UNKNOWN as needed.

        The supplied space_layout_version must match the profile's supported
        layout. The implementation must not infer AVAILABLE from a missing
        vehicle detection alone. No gate/barrier/reservation control is part
        of this API.
        """


def validate_parking_predictions(
    *,
    profile: ParkingModelProfile,
    prediction_profile_id: str,
    site_id: str,
    camera_view_id: str,
    space_layout_version: str,
    space_ids: Sequence[str],
    evidence_time_s: float,
    quality: QualityState,
    predictions: Sequence[ParkingSpaceResult],
) -> tuple[ParkingSpaceResult, ...]:
    """Validate one model response against its configured frame and layout.

    Enforces exact one-result-per-space coverage, configured output ordering,
    frame-time provenance, and fail-closed frame quality. This function does
    not calibrate model scores or determine whether an occupancy decision is
    correct.
    """
    if space_layout_version != profile.space_layout_version:
        raise ValueError(
            "Requested space_layout_version does not match the parking model profile"
        )
    if prediction_profile_id != profile.profile_id:
        raise ValueError("Prediction model profile_id does not match the configured profile")
    if site_id != profile.site_id:
        raise ValueError("Requested site_id does not match the parking model profile")
    if camera_view_id != profile.camera_view_id:
        raise ValueError("Requested camera_view_id does not match the parking model profile")
    if (
        not isinstance(space_ids, Sequence)
        or isinstance(space_ids, (str, bytes))
        or not space_ids
        or any(not isinstance(space_id, str) or not space_id.strip() for space_id in space_ids)
        or len(space_ids) != len(set(space_ids))
    ):
        raise ValueError("space_ids must be a nonempty sequence of unique nonempty strings")
    if (
        type(evidence_time_s) not in (int, float)
        or not math.isfinite(evidence_time_s)
        or evidence_time_s < 0
    ):
        raise ValueError("evidence_time_s must be finite and nonnegative")
    if not isinstance(quality, QualityState):
        raise ValueError("quality must be a QualityState")
    if not isinstance(predictions, Sequence) or isinstance(predictions, (str, bytes)):
        raise ValueError("predictions must be a sequence of ParkingSpaceResult values")
    by_space: dict[str, ParkingSpaceResult] = {}
    for prediction in predictions:
        if not isinstance(prediction, ParkingSpaceResult):
            raise ValueError("Every prediction must be a ParkingSpaceResult")
        if prediction.space_id in by_space:
            raise ValueError(f"Duplicate prediction for parking space {prediction.space_id!r}")
        if prediction.space_id not in space_ids:
            raise ValueError(f"Prediction contains unconfigured parking space {prediction.space_id!r}")
        if prediction.evidence_time_s != evidence_time_s:
            raise ValueError(
                f"Prediction evidence time for {prediction.space_id!r} does not match frame media time"
            )
        if quality in (QualityState.UNKNOWN, QualityState.STALE) and prediction.state is not ParkingState.UNKNOWN:
            raise ValueError("UNKNOWN/STALE frame quality requires UNKNOWN for every parking space")
        by_space[prediction.space_id] = prediction
    missing = [space_id for space_id in space_ids if space_id not in by_space]
    if missing:
        raise ValueError(f"Model omitted configured parking spaces: {missing}")
    return tuple(by_space[space_id] for space_id in space_ids)
