"""Load a versioned person-detector YAML profile and verify required fields."""
from __future__ import annotations

import os
import hashlib
from pathlib import Path
from typing import Optional

from crowdsight.detection.adapter import PersonDetectorProfile, PersonTracker


def load_person_detector_profile(
    profile_path: Path,
    *,
    checkpoint_path: Optional[Path] = None,
    device_override: Optional[str] = None,
) -> PersonDetectorProfile:
    """Create a runtime profile from the product YAML and external weight path.

    Checkpoint files are never resolved from an untrusted API request. The
    default checkpoint comes from the profile's named environment variable;
    local callers may inject a trusted path explicitly.
    """
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read model profiles") from exc
    config_path = Path(profile_path).expanduser().resolve()
    if not config_path.is_file():
        raise FileNotFoundError(f"Model profile not found: {config_path}")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError(f"Model profile must contain a YAML mapping: {config_path}")
    if config.get("task") not in ("person_detection", "person_detection_and_tracking"):
        raise ValueError("Model profile task must identify a person-detection model")
    profile_id = config.get("profile_id")
    if not isinstance(profile_id, str) or not profile_id.strip():
        raise ValueError("Model profile profile_id must be a nonempty string")
    checkpoint_env = config.get("checkpoint_env")
    resolved_checkpoint = checkpoint_path
    if resolved_checkpoint is None and isinstance(checkpoint_env, str):
        env_path = os.environ.get(checkpoint_env)
        if env_path:
            resolved_checkpoint = Path(env_path).expanduser()
    if resolved_checkpoint is None:
        raise ValueError(
            f"Supply checkpoint_path or set profile variable {checkpoint_env!r}; "
            "model weights are stored outside the source repository"
        )
    mapping = config.get("class_mapping")
    preprocessing = config.get("preprocessing")
    inference = config.get("inference")
    if not all(isinstance(section, dict) for section in (mapping, preprocessing, inference)):
        raise ValueError(f"Person-detector sections must be mappings: {config_path}")
    person_class_id = mapping.get("person")
    expected_sha256 = config.get("checkpoint_sha256")
    image_size = preprocessing.get("image_size")
    confidence = inference.get("confidence")
    if type(person_class_id) is not int or person_class_id < 0:
        raise ValueError("class_mapping.person must be a nonnegative integer")
    if not isinstance(expected_sha256, str):
        raise ValueError("checkpoint_sha256 must be a 64-character hex string")
    if type(image_size) is not int or image_size <= 0:
        raise ValueError("preprocessing.image_size must be a positive integer")
    if type(confidence) not in (int, float):
        raise ValueError("inference.confidence must be a number")
    if preprocessing.get("color_order") != "BGR":
        raise ValueError("The current adapter accepts BGR images; profile must declare BGR")
    device = inference.get("device", "auto")
    if not isinstance(device, str) or not device.strip():
        raise ValueError("inference.device must be a nonempty string")
    selected_device = device if device_override is None else device_override
    return PersonDetectorProfile(
        profile_id=profile_id,
        checkpoint_path=Path(resolved_checkpoint),
        expected_sha256=expected_sha256,
        profile_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
        person_class_id=person_class_id,
        confidence=confidence,
        image_size=image_size,
        device=selected_device,
    )


def load_person_tracker(
    profile_path: Path,
    *,
    checkpoint_path: Optional[Path] = None,
    tracker_config_path: Optional[Path] = None,
    device_override: Optional[str] = None,
) -> PersonTracker:
    """Load the profile-paired tracker after verifying both artifact hashes.

    A trusted tracker path can be supplied directly or through the named
    ``tracker_config_env`` profile setting. Relative ``config_source`` paths
    resolve from the CrowdSight repository root.
    """
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read model profiles") from exc
    config_path = Path(profile_path).expanduser().resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or not isinstance(config.get("tracker"), dict):
        raise ValueError(f"Model profile has no tracker mapping: {config_path}")
    tracker = config["tracker"]
    tracker_path = tracker_config_path
    tracker_env = tracker.get("config_env")
    if tracker_path is None and isinstance(tracker_env, str) and os.environ.get(tracker_env):
        tracker_path = Path(os.environ[tracker_env]).expanduser()
    if tracker_path is None:
        source = tracker.get("config_source")
        if not isinstance(source, str):
            raise ValueError("Tracker profile must define config_source or config_env")
        repository_root = config_path.parents[2]
        tracker_path = (repository_root / source).resolve()
    expected_tracker_sha256 = tracker.get("config_sha256")
    if not isinstance(expected_tracker_sha256, str):
        raise ValueError("Tracker profile must pin config_sha256")
    from crowdsight.detection.adapter import UltralyticsPersonTracker

    return UltralyticsPersonTracker(
        load_person_detector_profile(
            config_path,
            checkpoint_path=checkpoint_path,
            device_override=device_override,
        ),
        tracker_config=Path(tracker_path),
        expected_tracker_sha256=expected_tracker_sha256,
    )
