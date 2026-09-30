"""Tests for deterministic SyntheticDetector."""
from __future__ import annotations

import math

import numpy as np

from crowdsight.service.pipeline.synthetic import (
    SYNTHETIC_CHECKPOINT_SHA256,
    SYNTHETIC_PROFILE_ID,
    SyntheticDetector,
)


def test_synthetic_detector_deterministic() -> None:
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    det1 = SyntheticDetector(num_persons=3, seed=100)
    det2 = SyntheticDetector(num_persons=3, seed=100)

    res1 = det1.predict(frame, frame_index=42)
    res2 = det2.predict(frame, frame_index=42)

    assert len(res1) == 3
    assert len(res2) == 3
    for p1, p2 in zip(res1, res2, strict=True):
        assert p1.x == p2.x
        assert p1.y == p2.y
        assert p1.confidence == p2.confidence
        assert p1.bbox_xyxy_px == p2.bbox_xyxy_px


def test_synthetic_detector_bottom_centre_invariant() -> None:
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    det = SyntheticDetector(num_persons=5, seed=42)
    detections = det.predict(frame, frame_index=10)

    width, height = 1920, 1080
    for d in detections:
        assert d.bbox_xyxy_px is not None
        x1, y1, x2, y2 = d.bbox_xyxy_px
        expected_x = ((x1 + x2) / 2.0) / width
        expected_y = y2 / height
        assert math.isclose(d.x, expected_x, abs_tol=1e-3)
        assert math.isclose(d.y, expected_y, abs_tol=1e-3)
        assert 0.0 <= d.confidence <= 1.0


def test_synthetic_detector_constants() -> None:
    assert SyntheticDetector.profile_id == SYNTHETIC_PROFILE_ID
    assert len(SyntheticDetector.checkpoint_sha256) == 64
    assert SyntheticDetector.checkpoint_sha256 == SYNTHETIC_CHECKPOINT_SHA256
