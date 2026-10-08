"""Filter pinned crowd detections to publisher QUT camera ROIs before count scoring.

The filter uses source-frame bbox bottom-centre anchors, as in the CrowdSight
observation contract. The publisher supplies person-location dots rather than
boxes, so this transformation supports counts only and is not an IoU scorer.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from prepare_qut_count_diagnostic import in_polygon, sha256_file


def filter_predictions(manifest_path: Path, predictions_path: Path, output_path: Path) -> dict[str, object]:
    manifest_path, predictions_path, output_path = (
        manifest_path.resolve(), predictions_path.resolve(), output_path.resolve()
    )
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite ROI predictions: {output_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    predictions = json.loads(predictions_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or predictions.get("schema_version") != 1:
        raise ValueError("Expected v1 manifest and predictions")
    if predictions.get("dataset_id") != manifest.get("dataset_id") or predictions.get("source_sha256") != manifest.get("source_sha256"):
        raise ValueError("Prediction dataset/source does not match the locked manifest")
    if predictions.get("run_metadata", {}).get("manifest_sha256") != sha256_file(manifest_path):
        raise ValueError("Inference used a different manifest")
    samples, frames = manifest.get("samples"), predictions.get("frames")
    if not isinstance(samples, list) or not isinstance(frames, list) or len(samples) != len(frames):
        raise ValueError("Prediction frames must match every manifest sample")
    roi_map = manifest.get("roi_by_sequence_id")
    if not isinstance(roi_map, dict) or set(roi_map) != {"QUT-A", "QUT-B", "QUT-C"}:
        raise ValueError("Missing locked QUT camera ROI polygons")
    width, height = manifest.get("width"), manifest.get("height")
    if (width, height) != (704, 576):
        raise ValueError("Unexpected QUT frame dimensions")

    filtered_frames = []
    kept_by_camera = dict.fromkeys(roi_map, 0)
    raw_by_camera = dict.fromkeys(roi_map, 0)
    for sample, frame in zip(samples, frames, strict=True):
        sequence, frame_id = sample.get("sequence_id"), sample.get("frame_id")
        if (frame.get("sequence_id"), frame.get("frame_id"), frame.get("image_sha256")) != (
            sequence, frame_id, sample.get("image_sha256")
        ):
            raise ValueError("Prediction and locked sample identity/order disagree")
        if sequence not in roi_map:
            raise ValueError("Prediction sequence has no ROI")
        vertices = tuple(tuple(point) for point in roi_map[sequence]["vertices_xy"])
        if len(vertices) < 3 or any(len(point) != 2 for point in vertices):
            raise ValueError("Malformed locked ROI polygon")
        if frame.get("valid") is False:
            if frame.get("count") is not None:
                raise ValueError("Invalid frame must have null count")
            filtered_frames.append(dict(frame))
            continue
        if frame.get("valid") is not True:
            raise ValueError("Frame valid flag must be true or false")
        boxes, scored_boxes = frame.get("boxes"), frame.get("scored_boxes")
        if not isinstance(boxes, list) or not isinstance(scored_boxes, list) or frame.get("count") != len(boxes) or len(boxes) != len(scored_boxes):
            raise ValueError("Valid frame count/boxes/scores mismatch")
        kept_boxes, kept_scores = [], []
        raw_by_camera[sequence] += len(boxes)
        for box, scored in zip(boxes, scored_boxes, strict=True):
            if not isinstance(box, list) or len(box) != 4 or scored.get("bbox_xyxy") != box:
                raise ValueError("Prediction box and scored box disagree")
            if any(type(value) not in (int, float) or not math.isfinite(value) for value in box):
                raise ValueError("Prediction box must contain finite coordinates")
            x1, y1, x2, y2 = box
            if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
                raise ValueError("Prediction box lies outside source frame")
            x = min((x1 + x2) / 2, width - 1e-6)
            y = min(y2, height - 1e-6)
            if in_polygon(x, y, vertices):
                kept_boxes.append(box)
                kept_scores.append(scored)
        kept_by_camera[sequence] += len(kept_boxes)
        filtered_frames.append({**frame, "unfiltered_count": len(boxes), "count": len(kept_boxes),
                                "boxes": kept_boxes, "scored_boxes": kept_scores})

    result = {**predictions, "frames": filtered_frames,
        "run_metadata": {**predictions["run_metadata"],
            "roi_filter_script_sha256": sha256_file(Path(__file__).resolve()),
            "unfiltered_predictions_sha256": sha256_file(predictions_path)},
        "roi_transformation": {"source": "publisher QUT roi.xml polygons locked in the manifest",
            "anchor": "source-frame bbox bottom centre; clamp exclusive edge to last in-image position",
            "boundary_inclusive": True, "raw_detections_by_camera": raw_by_camera,
            "roi_detections_by_camera": kept_by_camera}}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return {"frames": len(filtered_frames), "raw_detections_by_camera": raw_by_camera,
            "roi_detections_by_camera": kept_by_camera,
            "output_sha256": sha256_file(output_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(filter_predictions(args.manifest, args.predictions, args.output), indent=2))


if __name__ == "__main__":
    main()
