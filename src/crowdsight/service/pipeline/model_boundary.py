"""Model boundary verification, checkpoint integrity checking, and detector factory."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from crowdsight.detection.adapter import (
    PersonDetector,
    PersonDetectorProfile,
    UltralyticsPersonDetector,
    UltralyticsPersonTracker,
)
from crowdsight.detection.applicability import CrowdUseDecision, assess_crowd_operating_use
from crowdsight.service.pipeline.synthetic import SyntheticDetector


class ModelBoundaryError(Exception):
    """Base exception for model boundary integrity errors."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ModelCheckpointMissingError(ModelBoundaryError):
    def __init__(self, path: Path) -> None:
        super().__init__(
            "MODEL_CHECKPOINT_MISSING",
            f"Required model checkpoint is missing at path: {path}",
        )


class ModelCheckpointHashMismatchError(ModelBoundaryError):
    def __init__(self, path: Path, expected: str, actual: str) -> None:
        super().__init__(
            "MODEL_CHECKPOINT_HASH_MISMATCH",
            f"Checkpoint SHA-256 mismatch for {path}: expected {expected}, got {actual}",
        )


class ModelProfileMismatchError(ModelBoundaryError):
    def __init__(self, expected_profile_id: str, actual_profile_id: str) -> None:
        super().__init__(
            "MODEL_PROFILE_MISMATCH",
            f"Model profile mismatch: expected {expected_profile_id}, got {actual_profile_id}",
        )


@dataclass(frozen=True, slots=True)
class ModelVerificationResult:
    profile_id: str
    model_family: str
    profile_path: Path
    profile_sha256: str
    checkpoint_path: Path | None
    checkpoint_available: bool
    expected_checkpoint_sha256: str
    actual_checkpoint_sha256: str | None
    is_checkpoint_valid: bool
    tracker_config_path: Path | None
    tracker_config_sha256: str | None
    applicability: CrowdUseDecision
    error_code: str | None = None
    error_message: str | None = None


def sha256_file(path: Path) -> str:
    """Return streaming hex digest of file without loading entire file into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


class ModelBoundaryService:
    """Enforces provenance, integrity hashes, and applicability at model boundary."""

    def __init__(self, default_config_path: Path | None = None) -> None:
        if default_config_path is None:
            repo_root = Path(__file__).resolve().parents[4]
            crowd_best = repo_root / "configs" / "models" / "crowd_best_local.yaml"
            local_yolo = repo_root / "configs" / "models" / "yolo11n_local.yaml"
            if (repo_root / "yolo11n.pt").is_file() and local_yolo.is_file():
                default_config_path = local_yolo
            elif (repo_root / "models" / "best.pt").is_file() and crowd_best.is_file():
                default_config_path = crowd_best
            else:
                default_config_path = local_yolo
        self.default_config_path = default_config_path

    def load_config(self, config_path: Path | None = None) -> dict[str, Any]:
        target_path = config_path or self.default_config_path
        if not target_path.is_file():
            raise FileNotFoundError(f"Model configuration file not found: {target_path}")
        content = target_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML content in {target_path}")
        return data

    def verify_model(
        self,
        config_path: Path | None = None,
        checkpoint_override: Path | None = None,
        tracker_config_override: Path | None = None,
    ) -> ModelVerificationResult:
        target_config = config_path or self.default_config_path
        config = self.load_config(target_config)

        profile_id = str(config.get("profile_id", "crowd_best_local_v2"))
        model_family = str(config.get("model_family", "yolo11s_finetuned"))
        expected_checkpoint_hash = str(
            config.get("checkpoint_sha256", "12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc")
        ).lower()
        checkpoint_env = str(config.get("checkpoint_env", "CROWDSIGHT_CROWD_CHECKPOINT"))

        profile_sha256 = sha256_file(target_config)

        # Locate checkpoint
        checkpoint_path: Path | None = None
        if checkpoint_override is not None:
            checkpoint_path = checkpoint_override
        else:
            env_val = os.environ.get(checkpoint_env)
            if env_val:
                checkpoint_path = Path(env_val)
            else:
                raw_src = config.get("source_artifact")
                if raw_src:
                    checkpoint_path = (target_config.parent / str(raw_src)).resolve()

        checkpoint_available = checkpoint_path is not None and checkpoint_path.is_file()
        actual_checkpoint_hash: str | None = None
        is_checkpoint_valid = False
        error_code: str | None = None
        error_message: str | None = None

        if not checkpoint_available:
            error_code = "MODEL_CHECKPOINT_MISSING"
            error_message = f"Model checkpoint not found (looked for env {checkpoint_env} or {checkpoint_path})"
        else:
            assert checkpoint_path is not None
            actual_checkpoint_hash = sha256_file(checkpoint_path)
            if actual_checkpoint_hash == expected_checkpoint_hash:
                is_checkpoint_valid = True
            else:
                error_code = "MODEL_CHECKPOINT_HASH_MISMATCH"
                error_message = (
                    f"Checkpoint hash mismatch: expected {expected_checkpoint_hash}, "
                    f"got {actual_checkpoint_hash}"
                )

        # Tracker config verification
        tracker_config_path: Path | None = None
        tracker_config_sha256: str | None = None
        tracker_section = config.get("tracker", {})
        if isinstance(tracker_section, dict):
            t_src = tracker_section.get("config_source")
            t_env = tracker_section.get("config_env", "CROWDSIGHT_TRACKER_CONFIG")
            if tracker_config_override is not None:
                tracker_config_path = tracker_config_override
            elif os.environ.get(t_env):
                tracker_config_path = Path(os.environ[t_env])
            elif t_src:
                tracker_config_path = (target_config.parent / str(t_src)).resolve()

            if tracker_config_path is not None and tracker_config_path.is_file():
                tracker_config_sha256 = sha256_file(tracker_config_path)

        # Assess applicability fail-closed
        applicability = assess_crowd_operating_use(
            site_id="default-site",
            camera_view_id="fixed-camera-01",
            model_profile_id=profile_id,
            model_profile_sha256=profile_sha256,
            checkpoint_sha256=actual_checkpoint_hash or expected_checkpoint_hash,
            approval=None,
        )

        return ModelVerificationResult(
            profile_id=profile_id,
            model_family=model_family,
            profile_path=target_config,
            profile_sha256=profile_sha256,
            checkpoint_path=checkpoint_path,
            checkpoint_available=checkpoint_available,
            expected_checkpoint_sha256=expected_checkpoint_hash,
            actual_checkpoint_sha256=actual_checkpoint_hash,
            is_checkpoint_valid=is_checkpoint_valid,
            tracker_config_path=tracker_config_path,
            tracker_config_sha256=tracker_config_sha256,
            applicability=applicability,
            error_code=error_code,
            error_message=error_message,
        )

    def create_detector(
        self,
        *,
        synthetic: bool = False,
        config_path: Path | None = None,
        checkpoint_override: Path | None = None,
        enable_tracker: bool = False,
        tracker_config_override: Path | None = None,
        seed: int = 42,
        confidence_override: float | None = None,
    ) -> tuple[PersonDetector, dict[str, Any]]:
        """Instantiate detector with integrity checks or fallback to deterministic synthetic."""
        target_config = config_path or self.default_config_path
        config = self.load_config(target_config)
        profile_id = str(config.get("profile_id", "crowd_best_local_v2"))
        profile_sha256 = sha256_file(target_config)

        if synthetic:
            detector = SyntheticDetector(seed=seed)
            provenance = {
                "profile_id": "synthetic_crowd_v1",
                "profile_sha256": "0" * 64,
                "checkpoint_sha256": "0" * 64,
                "tracker_config_sha256": None,
                "synthetic": True,
            }
            return detector, provenance

        verification = self.verify_model(
            config_path=target_config,
            checkpoint_override=checkpoint_override,
            tracker_config_override=tracker_config_override,
        )

        if not verification.checkpoint_available or verification.checkpoint_path is None:
            raise ModelCheckpointMissingError(
                verification.checkpoint_path or Path("unspecified_checkpoint")
            )

        if not verification.is_checkpoint_valid:
            assert verification.actual_checkpoint_sha256 is not None
            raise ModelCheckpointHashMismatchError(
                verification.checkpoint_path,
                verification.expected_checkpoint_sha256,
                verification.actual_checkpoint_sha256,
            )

        target_conf = (
            float(confidence_override)
            if confidence_override is not None
            else float(config.get("inference", {}).get("confidence", 0.18))
        )

        detector_profile = PersonDetectorProfile(
            profile_id=profile_id,
            checkpoint_path=verification.checkpoint_path,
            expected_sha256=verification.expected_checkpoint_sha256,
            profile_sha256=profile_sha256,
            person_class_id=int(config.get("class_mapping", {}).get("person", 0)),
            confidence=target_conf,
            image_size=int(config.get("preprocessing", {}).get("image_size", 1280)),
            device=str(config.get("inference", {}).get("device", "auto")),
        )

        if enable_tracker and verification.tracker_config_path is not None:
            expected_tracker_hash = str(config.get("tracker", {}).get("config_sha256", ""))
            tracker = UltralyticsPersonTracker(
                profile=detector_profile,
                tracker_config=verification.tracker_config_path,
                expected_tracker_sha256=expected_tracker_hash,
            )
            provenance = {
                "profile_id": profile_id,
                "profile_sha256": profile_sha256,
                "checkpoint_sha256": verification.actual_checkpoint_sha256,
                "tracker_config_sha256": verification.tracker_config_sha256,
                "synthetic": False,
            }
            return tracker, provenance

        live_detector: PersonDetector = UltralyticsPersonDetector(detector_profile)
        provenance = {
            "profile_id": profile_id,
            "profile_sha256": profile_sha256,
            "checkpoint_sha256": verification.actual_checkpoint_sha256,
            "tracker_config_sha256": None,
            "synthetic": False,
        }
        return live_detector, provenance
