"""Unit tests for ImageSpaceHeatmapGenerator and perceptual transparency."""
from __future__ import annotations

import cv2
import numpy as np

from crowdsight.service.analytics.heatmaps import ImageSpaceHeatmapGenerator


def test_heatmap_generates_valid_rgba_png_matching_image_dimensions() -> None:
    width = 640
    height = 480
    obs = [
        {
            "media_time_s": 0.0,
            "quality": "VALID",
            "detections": [
                {"x": 0.5, "y": 0.5, "confidence": 0.8},
                {"x": 0.52, "y": 0.51, "confidence": 0.85},
            ],
        },
        {
            "media_time_s": 0.5,
            "quality": "VALID",
            "detections": [
                {"x": 0.51, "y": 0.49, "confidence": 0.9},
            ],
        },
    ]

    res = ImageSpaceHeatmapGenerator.generate(
        observations=obs,
        image_width=width,
        image_height=height,
    )

    assert res.metadata.kind == "IMAGE_SPACE"
    assert res.metadata.image_width == width
    assert res.metadata.image_height == height
    assert res.metadata.frames_used == 2
    assert res.metadata.frames_discarded == 0
    assert len(res.metadata.sha256) == 64

    # Decode PNG
    nparr = np.frombuffer(res.png_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
    assert img is not None
    assert img.shape == (height, width, 4)

    # Corner pixel (empty) should have alpha == 0
    assert img[0, 0, 3] == 0
    # Centre pixel (around 0.5, 0.5) should have alpha > 0
    centre_y = int(0.5 * height)
    centre_x = int(0.5 * width)
    assert img[centre_y, centre_x, 3] > 0


def test_heatmap_quality_weighting_discards_unknown() -> None:
    width = 100
    height = 100
    obs = [
        {
            "media_time_s": 0.0,
            "quality": "UNKNOWN",
            "detections": [{"x": 0.5, "y": 0.5, "confidence": 0.9}],
        },
        {
            "media_time_s": 1.0,
            "quality": "STALE",
            "detections": [{"x": 0.5, "y": 0.5, "confidence": 0.9}],
        },
    ]

    res = ImageSpaceHeatmapGenerator.generate(
        observations=obs,
        image_width=width,
        image_height=height,
    )
    assert res.metadata.frames_used == 0
    assert res.metadata.frames_discarded == 2

    # Entire image should have alpha == 0
    nparr = np.frombuffer(res.png_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
    assert img is not None
    assert np.all(img[:, :, 3] == 0)
