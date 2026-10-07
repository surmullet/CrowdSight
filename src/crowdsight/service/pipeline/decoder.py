"""Sequential video frame decoding with degradation and anomaly detection."""
from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True, slots=True)
class DecodedFrame:
    frame_index: int
    media_time_s: float
    width: int
    height: int
    image_bgr: np.ndarray[Any, Any] | None
    is_usable: bool
    reason_code: str | None = None


class VideoDecoder:
    """Decodes video files sequentially with anomaly detection and single-frame retry."""

    def __init__(
        self,
        video_path: Path,
        *,
        frame_stride: int = 1,
        blank_threshold_std: float = 3.0,
        freeze_mse_threshold: float = 0.5,
        max_frozen_consecutive: int = 5,
    ) -> None:
        self.video_path = Path(video_path).resolve()
        if not self.video_path.is_file():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")

        self.frame_stride = max(1, frame_stride)
        self.blank_threshold_std = blank_threshold_std
        self.freeze_mse_threshold = freeze_mse_threshold
        self.max_frozen_consecutive = max_frozen_consecutive

    def iter_frames(self) -> Generator[DecodedFrame, None, None]:
        cap = cv2.VideoCapture(str(self.video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open video: {self.video_path}")

        fps = float(cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0 or not (1.0 <= fps <= 120.0):
            fps = 25.0

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = fps
        self.width = width
        self.height = height
        self.total_raw_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        prev_frame_gray: np.ndarray[Any, Any] | None = None
        consecutive_frozen = 0
        raw_frame_idx = 0

        try:
            while True:
                # Handle frame stride
                if self.frame_stride > 1 and raw_frame_idx % self.frame_stride != 0:
                    success = cap.grab()
                    if not success:
                        break
                    raw_frame_idx += 1
                    continue

                success, frame = cap.read()
                if not success:
                    # Retry once before terminating or declaring decode failure
                    success, frame = cap.read()
                    if not success:
                        break

                current_frame_idx = raw_frame_idx
                media_time_s = round(current_frame_idx / fps, 3)
                raw_frame_idx += 1

                if frame is None or frame.ndim != 3:
                    yield DecodedFrame(
                        frame_index=current_frame_idx,
                        media_time_s=media_time_s,
                        width=width,
                        height=height,
                        image_bgr=None,
                        is_usable=False,
                        reason_code="DECODE_FAILED",
                    )
                    continue

                # Check for blank / blackout / whiteout frame
                # Subsample high-resolution frames for quality checks to avoid computing over millions of pixels on CPU
                sample = frame[::4, ::4] if (width > 240 and height > 240) else frame
                std_dev = float(sample.std())
                mean_val = float(sample.mean())
                if std_dev < self.blank_threshold_std and (mean_val < 15.0 or mean_val > 240.0):
                    yield DecodedFrame(
                        frame_index=current_frame_idx,
                        media_time_s=media_time_s,
                        width=width,
                        height=height,
                        image_bgr=frame,
                        is_usable=False,
                        reason_code="FRAME_BLANK",
                    )
                    continue

                # Check for frozen frames
                gray = cv2.cvtColor(sample, cv2.COLOR_BGR2GRAY)
                if prev_frame_gray is not None and prev_frame_gray.shape == gray.shape:
                    mse = float(np.mean((prev_frame_gray.astype(np.float32) - gray.astype(np.float32)) ** 2))
                    if mse < self.freeze_mse_threshold:
                        consecutive_frozen += 1
                    else:
                        consecutive_frozen = 0
                else:
                    consecutive_frozen = 0

                prev_frame_gray = gray

                if consecutive_frozen >= self.max_frozen_consecutive:
                    yield DecodedFrame(
                        frame_index=current_frame_idx,
                        media_time_s=media_time_s,
                        width=width,
                        height=height,
                        image_bgr=frame,
                        is_usable=False,
                        reason_code="FRAME_FROZEN",
                    )
                    continue

                # Usable valid frame
                yield DecodedFrame(
                    frame_index=current_frame_idx,
                    media_time_s=media_time_s,
                    width=width,
                    height=height,
                    image_bgr=frame,
                    is_usable=True,
                    reason_code=None,
                )
        finally:
            cap.release()
