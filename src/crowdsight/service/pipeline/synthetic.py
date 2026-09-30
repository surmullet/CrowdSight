"""Deterministic synthetic person detector for zero-weight development, testing, and CI."""
from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import numpy as np

from crowdsight.common.observations import PersonDetection

SYNTHETIC_PROFILE_ID = "crowd_best_local_v2"
SYNTHETIC_PROFILE_SHA256 = "a" * 64
SYNTHETIC_CHECKPOINT_SHA256 = "b" * 64


class SyntheticDetector:
    """Deterministic synthetic person detector producing contract-compliant anchors.

    Simulates realistic person bounding boxes moving predictably over time.
    """

    profile_id: str = SYNTHETIC_PROFILE_ID
    profile_sha256: str = SYNTHETIC_PROFILE_SHA256
    checkpoint_sha256: str = SYNTHETIC_CHECKPOINT_SHA256

    def __init__(
        self,
        *,
        num_persons: int = 3,
        seed: int = 42,
        speed_factor: float = 0.05,
    ) -> None:
        self.num_persons = num_persons
        self.seed = seed
        self.speed_factor = speed_factor

    def predict(
        self,
        frame_bgr: np.ndarray[Any, Any],
        frame_index: int = 0,
    ) -> Sequence[PersonDetection]:
        """Generate deterministic person detections for a given frame."""
        height, width = frame_bgr.shape[:2]
        if height <= 0 or width <= 0:
            raise ValueError("Frame dimensions must be positive")

        if self.num_persons == 0:
            return ()

        detections: list[PersonDetection] = []
        rng = np.random.default_rng(self.seed + frame_index * 17)

        box_width = max(width * 0.05, 30.0)
        box_height = max(height * 0.12, 60.0)

        for i in range(self.num_persons):
            # Deterministic moving base positions
            base_x = (0.2 + 0.6 * (i / max(self.num_persons - 1, 1))) * width
            base_y = (0.3 + 0.4 * math.sin(frame_index * self.speed_factor + i)) * height

            # Jitter
            offset_x = float(rng.uniform(-10.0, 10.0))
            offset_y = float(rng.uniform(-10.0, 10.0))

            cx = min(max(base_x + offset_x, box_width), width - box_width)
            cy = min(max(base_y + offset_y, box_height), height - 10.0)

            x1 = cx - box_width / 2.0
            x2 = cx + box_width / 2.0
            y1 = cy - box_height
            y2 = cy

            # Normalized bottom-centre anchor
            anchor_x = ((x1 + x2) / 2.0) / width
            anchor_y = y2 / height

            confidence = round(float(rng.uniform(0.65, 0.95)), 3)

            detections.append(
                PersonDetection(
                    x=anchor_x,
                    y=anchor_y,
                    confidence=confidence,
                    track_id=None,
                    bbox_xyxy_px=(round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)),
                )
            )

        return tuple(detections)
