"""Tests for VideoDecoder anomaly detection: blank and frozen frames."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from crowdsight.service.pipeline.decoder import VideoDecoder


def test_decoder_blank_frame_detection(tmp_path: Path) -> None:
    video_path = tmp_path / "blank_test.mp4"
    fourcc = int(cv2.VideoWriter_fourcc(*"mp4v"))  # type: ignore[attr-defined]
    writer = cv2.VideoWriter(str(video_path), fourcc, 10.0, (100, 100))

    # Frame 0: normal texture
    writer.write(np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8))
    # Frame 1: pure black (blank)
    writer.write(np.zeros((100, 100, 3), dtype=np.uint8))
    # Frame 2: normal texture
    writer.write(np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8))
    writer.release()

    decoder = VideoDecoder(video_path)
    frames = list(decoder.iter_frames())

    assert len(frames) == 3
    assert frames[0].is_usable is True
    assert frames[1].is_usable is False
    assert frames[1].reason_code == "FRAME_BLANK"
    assert frames[2].is_usable is True


def test_decoder_frozen_frame_detection(tmp_path: Path) -> None:
    video_path = tmp_path / "frozen_test.mp4"
    fourcc = int(cv2.VideoWriter_fourcc(*"mp4v"))  # type: ignore[attr-defined]
    writer = cv2.VideoWriter(str(video_path), fourcc, 10.0, (100, 100))

    static_pattern = np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8)
    # Write 8 identical frames (exceeds default max_frozen_consecutive=5)
    for _ in range(8):
        writer.write(static_pattern)
    writer.release()

    decoder = VideoDecoder(video_path, max_frozen_consecutive=4)
    frames = list(decoder.iter_frames())

    # The later frames should be flagged as FRAME_FROZEN
    frozen_frames = [f for f in frames if f.reason_code == "FRAME_FROZEN"]
    assert len(frozen_frames) > 0
    assert any(not f.is_usable for f in frozen_frames)
