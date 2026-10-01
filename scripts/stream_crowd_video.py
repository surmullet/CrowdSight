"""Emit one CrowdSight v1 observation per video frame as flushed JSON Lines.

Standard output contains observations only. Progress and errors go to stderr.
The caller can consume each line immediately or redirect stdout to a .jsonl file.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from crowdsight.common.observations import FrameObservation, QualityState
from crowdsight.detection import UltralyticsPersonDetector, load_person_detector_profile

def _route_ultralytics_logs_to_stderr() -> None:
    """Reserve stdout for JSONL even when Ultralytics emits warnings."""
    try:
        from ultralytics.utils import LOGGER
    except ImportError:
        return

    for handler in LOGGER.handlers:
        if isinstance(handler, logging.StreamHandler) and handler.stream is sys.stdout:
            handler.setStream(sys.stderr)


def stream_video(
    video_path: Path,
    profile_path: Path,
    source_id: str,
    session_id: str,
    checkpoint_path: Path | None = None,
    device: str | None = None,
    fully_observed_zones: tuple[str, ...] = (),
) -> int:
    """Process frames in order and flush each observation before decoding the next."""
    if (
        not fully_observed_zones
        or any(not isinstance(zone, str) or not zone.strip() for zone in fully_observed_zones)
        or len(fully_observed_zones) != len(set(fully_observed_zones))
    ):
        raise ValueError(
            "Specify at least one unique fully observed zone; "
            "the video/application layer must establish its coverage"
        )
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV is required to decode video") from exc

    _route_ultralytics_logs_to_stderr()
    video_path = video_path.expanduser().resolve()
    if not video_path.is_file():
        raise FileNotFoundError(f"Video not found: {video_path}")
    profile = load_person_detector_profile(
        profile_path.expanduser().resolve(),
        checkpoint_path=checkpoint_path,
        device_override=device,
    )
    detector = UltralyticsPersonDetector(profile)
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    frame_index = 0
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("Video has no usable frame rate for media timestamps")
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            height, width = frame.shape[:2]
            media_time_s = frame_index / fps
            try:
                detections = tuple(detector.predict(frame))
                if detector.last_detection_limit_reached:
                    print(
                        f"Detection limit reached for frame {frame_index}: "
                        f"{profile.max_detections}; count is unavailable",
                        file=sys.stderr,
                        flush=True,
                    )
                    detections = ()
                    quality = QualityState.UNKNOWN
                    zones = ()
                else:
                    quality = QualityState.VALID
                    zones = fully_observed_zones
            except Exception as exc:
                print(
                    f"Inference failed for frame {frame_index}: {type(exc).__name__}: {exc}",
                    file=sys.stderr,
                    flush=True,
                )
                detections = ()
                quality = QualityState.UNKNOWN
                zones = ()

            observation = FrameObservation(
                source_id=source_id,
                session_id=session_id,
                model_profile_id=profile.profile_id,
                model_profile_sha256=profile.profile_sha256,
                checkpoint_sha256=profile.expected_sha256,
                tracker_config_sha256=None,
                frame_index=frame_index,
                media_time_s=media_time_s,
                image_width=width,
                image_height=height,
                detections=detections,
                fully_observed_zones=zones,
                quality=quality,
            )
            print(json.dumps(observation.to_contract_dict(), allow_nan=False), flush=True)
            frame_index += 1
    finally:
        capture.release()

    if frame_index == 0:
        raise RuntimeError("Video contained no decodable frames")
    print(f"Completed {frame_index} frames", file=sys.stderr, flush=True)
    return frame_index


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument(
        "--checkpoint", type=Path,
        help="Local model artifact; otherwise use the profile environment variable",
    )
    parser.add_argument("--device", help="Optional device override, for example cpu or cuda:0")
    parser.add_argument(
        "--fully-observed-zone", action="append", default=[], metavar="ZONE_ID",
        help="Zone whose full coverage is established by the caller; repeat for multiple zones",
    )
    args = parser.parse_args()
    stream_video(
        args.video,
        args.profile,
        args.source_id,
        args.session_id,
        args.checkpoint,
        args.device,
        tuple(args.fully_observed_zone),
    )


if __name__ == "__main__":
    main()
