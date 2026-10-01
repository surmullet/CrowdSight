"""Unit tests for ModelBoundaryService and checkpoint integrity checking."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from crowdsight.service.pipeline.model_boundary import (
    ModelBoundaryService,
    ModelCheckpointHashMismatchError,
    ModelCheckpointMissingError,
)


def test_model_boundary_missing_checkpoint(tmp_path: Path) -> None:
    cfg = {
        "profile_id": "test_profile_v1",
        "model_family": "yolo11s_finetuned",
        "checkpoint_sha256": "1" * 64,
        "checkpoint_env": "TEST_CHECKPOINT_MISSING_ENV",
        "source_artifact": "non_existent_best.pt",
    }
    cfg_file = tmp_path / "model.yaml"
    cfg_file.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    service = ModelBoundaryService(default_config_path=cfg_file)
    res = service.verify_model(config_path=cfg_file)

    assert not res.checkpoint_available
    assert not res.is_checkpoint_valid
    assert res.error_code == "MODEL_CHECKPOINT_MISSING"

    # Creating live detector should raise ModelCheckpointMissingError
    with pytest.raises(ModelCheckpointMissingError):
        service.create_detector(synthetic=False, config_path=cfg_file)


def test_model_boundary_hash_mismatch(tmp_path: Path) -> None:
    fake_weights = tmp_path / "fake_best.pt"
    fake_weights.write_bytes(b"dummy model weights data")

    expected_sha256 = "2" * 64
    cfg = {
        "profile_id": "test_profile_v1",
        "model_family": "yolo11s_finetuned",
        "checkpoint_sha256": expected_sha256,
        "source_artifact": fake_weights.name,
    }
    cfg_file = tmp_path / "model.yaml"
    cfg_file.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    service = ModelBoundaryService(default_config_path=cfg_file)
    res = service.verify_model(config_path=cfg_file, checkpoint_override=fake_weights)

    assert res.checkpoint_available
    assert not res.is_checkpoint_valid
    assert res.error_code == "MODEL_CHECKPOINT_HASH_MISMATCH"

    with pytest.raises(ModelCheckpointHashMismatchError):
        service.create_detector(
            synthetic=False,
            config_path=cfg_file,
            checkpoint_override=fake_weights,
        )


def test_model_boundary_synthetic_mode_succeeds_without_weights(tmp_path: Path) -> None:
    cfg = {
        "profile_id": "test_profile_v1",
        "checkpoint_sha256": "3" * 64,
        "source_artifact": "absent.pt",
    }
    cfg_file = tmp_path / "model.yaml"
    cfg_file.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    service = ModelBoundaryService(default_config_path=cfg_file)
    detector, provenance = service.create_detector(synthetic=True, config_path=cfg_file)

    assert provenance["synthetic"] is True
    assert provenance["profile_id"] == "synthetic_crowd_v1"
    assert provenance["checkpoint_sha256"] == "0" * 64
    assert hasattr(detector, "predict")
