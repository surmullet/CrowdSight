"""Web proxy generation using FFmpeg for non-browser playable video codecs."""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

import cv2

logger = logging.getLogger(__name__)


class VideoProxyGenerator:
    """Creates browser-playable H.264 web proxies when source codec is incompatible."""

    @staticmethod
    def is_ffmpeg_available() -> bool:
        return shutil.which("ffmpeg") is not None

    @classmethod
    def generate_proxy(
        cls,
        source_path: Path,
        proxy_dir: Path,
        *,
        source_fps: float,
        source_duration_s: float,
    ) -> Path | None:
        if not cls.is_ffmpeg_available():
            logger.info("ffmpeg not available on system; web proxy generation skipped")
            return None

        proxy_dir.mkdir(parents=True, exist_ok=True)
        proxy_file = proxy_dir / f"{source_path.stem}_proxy.mp4"

        cmd = [
            "ffmpeg",
            "-y",  # Overwrite
            "-i",
            str(source_path),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(proxy_file),
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, timeout=120)
            if res.returncode != 0:
                logger.warning("FFmpeg proxy generation failed: %s", res.stderr.decode(errors="ignore"))
                return None

            # Verify generated proxy with OpenCV
            cap = cv2.VideoCapture(str(proxy_file))
            if not cap.isOpened():
                return None

            try:
                gen_fps = float(cap.get(cv2.CAP_PROP_FPS))
                gen_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                gen_duration = gen_frames / gen_fps if gen_fps > 0 else 0.0

                # Check duration drift tolerance (max 10% or 1s)
                if abs(gen_duration - source_duration_s) > max(1.0, source_duration_s * 0.1):
                    logger.warning("Proxy duration drift too high: source %s vs gen %s", source_duration_s, gen_duration)
                    return None

                return proxy_file
            finally:
                cap.release()

        except Exception as exc:
            logger.warning("Error generating web proxy for %s: %s", source_path, exc)
            return None
