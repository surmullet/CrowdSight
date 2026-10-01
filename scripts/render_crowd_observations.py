"""Replay detection observations over the source video as an annotated mp4.

Reads the JSON Lines produced by stream_crowd_video.py and draws each
detection's pixel bounding box plus a count/status HUD. Frames without a
VALID observation are labeled "count unavailable" rather than shown as zero.
Progress goes to stderr; the final JSON summary goes to stdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

BOX_COLOR = (70, 200, 70)  # BGR green
HUD_FOREGROUND = (255, 255, 255)  # BGR white
HUD_WARNING = (70, 70, 230)  # BGR red
FONT_SCALE_PRIMARY = 0.8
FONT_SCALE_SECONDARY = 0.6
FONT_THICKNESS = 2
HUD_LINE_HEIGHT = 30
HUD_PADDING = 12


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_observations(observations_path: Path) -> dict[int, dict[str, Any]]:
    """Index observations by frame_index; duplicates or bad rows are rejected."""
    observations: dict[int, dict[str, Any]] = {}
    with observations_path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"Observation line {line_number} is not a JSON object")
            frame_index = row.get("frame_index")
            if type(frame_index) is not int or frame_index < 0:
                raise ValueError(f"Observation line {line_number} has an invalid frame_index")
            if frame_index in observations:
                raise ValueError(f"Duplicate observation for frame {frame_index}")
            observations[frame_index] = row
    if not observations:
        raise ValueError("Observation file contained no frames")
    return observations


def _clip(value: float, low: int, high: int) -> int:
    return min(max(int(round(value)), low), high)


def draw_detections(frame: Any, detections: list[dict[str, Any]], width: int, height: int) -> int:
    """Draw pixel boxes; returns how many detections had a drawable box."""
    import cv2

    drawn = 0
    for detection in detections:
        box = detection.get("bbox_xyxy")
        if not box:
            continue
        x1 = _clip(box[0], 0, width - 1)
        y1 = _clip(box[1], 0, height - 1)
        x2 = _clip(box[2], 0, width - 1)
        y2 = _clip(box[3], 0, height - 1)
        if x2 <= x1 or y2 <= y1:
            continue
        cv2.rectangle(frame, (x1, y1), (x2, y2), BOX_COLOR, FONT_THICKNESS)
        drawn += 1
    return drawn


def draw_hud(frame: Any, lines: list[tuple[str, tuple[int, int, int]]], width: int) -> None:
    """Draw a semi-transparent status panel at the top-left of the frame."""
    import cv2

    panel_width = 0
    for text, _color in lines:
        (text_width, _height), _baseline = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE_SECONDARY, 1
        )
        panel_width = max(panel_width, text_width)
    panel_width += 2 * HUD_PADDING
    panel_height = len(lines) * HUD_LINE_HEIGHT + 2 * HUD_PADDING
    panel_width = min(panel_width, width)

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (panel_width, panel_height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    for index, (text, color) in enumerate(lines):
        scale = FONT_SCALE_PRIMARY if index == 0 else FONT_SCALE_SECONDARY
        origin = (HUD_PADDING, HUD_PADDING + (index + 1) * HUD_LINE_HEIGHT - 8)
        cv2.putText(
            frame, text, origin, cv2.FONT_HERSHEY_SIMPLEX, scale, color, FONT_THICKNESS, cv2.LINE_AA
        )


def render(video_path: Path, observations_path: Path, output_path: Path) -> dict[str, Any]:
    """Overlay observation boxes/HUD on every decoded frame and write mp4."""
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV is required to decode and write video") from exc

    video_path = video_path.expanduser().resolve()
    observations_path = observations_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    if not video_path.is_file():
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not observations_path.is_file():
        raise FileNotFoundError(f"Observations not found: {observations_path}")
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {output_path}")

    observations = load_observations(observations_path)
    profile_id = str(next(iter(observations.values())).get("model_profile_id", "unknown-profile"))

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if not math.isfinite(fps) or fps <= 0 or width <= 0 or height <= 0:
        capture.release()
        raise RuntimeError("Video has no usable frame rate or dimensions")

    observed_sizes = {
        (int(row["image_width"]), int(row["image_height"])) for row in observations.values()
    }
    if observed_sizes != {(width, height)}:
        capture.release()
        raise ValueError(
            f"Observation frame sizes {sorted(observed_sizes)} do not match video {width}x{height}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )
    if not writer.isOpened():
        capture.release()
        raise RuntimeError(f"Could not open output video for writing: {output_path}")

    frames_written = 0
    unavailable_frames = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            observation = observations.get(frames_written)
            usable = (
                observation is not None
                and observation.get("quality") == "VALID"
                and observation.get("observation_valid", True) is not False
            )
            if usable:
                detections = observation.get("detections") or []
                draw_detections(frame, detections, width, height)
                media_time = observation.get("media_time_s", frames_written / fps)
                status_lines = [
                    (f"count: {len(detections)}", HUD_FOREGROUND),
                    (f"frame {frames_written}  t={media_time:0.2f}s", HUD_FOREGROUND),
                    (profile_id, HUD_FOREGROUND),
                ]
            else:
                unavailable_frames += 1
                status_lines = [
                    ("count: unavailable", HUD_WARNING),
                    (f"frame {frames_written}  t={frames_written / fps:0.2f}s", HUD_FOREGROUND),
                    (profile_id, HUD_FOREGROUND),
                ]
            draw_hud(frame, status_lines, width)
            writer.write(frame)
            frames_written += 1
            if frames_written % 50 == 0:
                print(f"Rendered {frames_written} frames", file=sys.stderr, flush=True)
    finally:
        capture.release()
        writer.release()

    if frames_written == 0:
        raise RuntimeError("Video contained no decodable frames")
    beyond = max(observations) >= frames_written
    if beyond:
        print(
            f"Warning: observations reference frames past the decoded video "
            f"(max frame_index {max(observations)}, frames decoded {frames_written})",
            file=sys.stderr,
            flush=True,
        )
    print(f"Completed {frames_written} frames", file=sys.stderr, flush=True)
    return {
        "frames_written": frames_written,
        "unavailable_frames": unavailable_frames,
        "output": str(output_path),
        "output_sha256": sha256_file(output_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path, help="Source video to annotate")
    parser.add_argument(
        "--observations", required=True, type=Path, help="JSONL from stream_crowd_video.py"
    )
    parser.add_argument("--output", required=True, type=Path, help="Annotated mp4 destination")
    args = parser.parse_args()
    summary = render(args.video, args.observations, args.output)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
