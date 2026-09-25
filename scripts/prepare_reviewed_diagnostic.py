"""Prepare CrowdSight-format diagnostic inputs from a reviewed frame export.

This conversion preserves the source video and reference annotations in place.
It selects only complete reviewed frames and explicitly marks the dataset as
diagnostic, never as held-out test evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare(review_manifest_path: Path, reviewed_labels_path: Path, video_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Convert complete one-based review frames to zero-based video indices."""
    review_manifest = json.loads(review_manifest_path.read_text(encoding="utf-8"))
    reviewed_labels = json.loads(reviewed_labels_path.read_text(encoding="utf-8-sig"))
    video_sha256 = _sha256(video_path)
    if video_sha256.lower() != str(reviewed_labels.get("source_sha256", "")).lower():
        raise ValueError("Source-video SHA-256 does not match reviewed labels")
    if review_manifest.get("dataset_id") != reviewed_labels.get("dataset_id"):
        raise ValueError("Review manifest and labels dataset_id do not match")
    if review_manifest.get("source_sha256", "").lower() != video_sha256.lower():
        raise ValueError("Review manifest source SHA-256 does not match the video")
    if int(review_manifest["width"]) <= 0 or int(review_manifest["height"]) <= 0:
        raise ValueError("Review manifest dimensions must be positive")

    manifest_rows = {row["frame"]: row for row in review_manifest.get("samples", [])}
    if len(manifest_rows) != len(review_manifest.get("samples", [])):
        raise ValueError("Review manifest has duplicate frame IDs")
    complete_labels = [row for row in reviewed_labels.get("frames", []) if row.get("complete") is True]
    label_rows = {row.get("frame"): row for row in complete_labels}
    if len(label_rows) != len(complete_labels):
        raise ValueError("Reviewed label export has duplicate completed frame IDs")
    if not complete_labels:
        raise ValueError("Reviewed label export contains no complete frames")

    samples = []
    frames = []
    for label_frame in sorted(label_rows):
        if type(label_frame) is not int or label_frame <= 0:
            raise ValueError("Review frame IDs must be positive one-based integers")
        source_row = manifest_rows.get(label_frame)
        if source_row is None:
            raise ValueError(f"Completed frame {label_frame} is absent from the review manifest")
        frame_index = label_frame - 1
        if source_row.get("source_frame_index") is None:
            raise ValueError(f"Review frame {label_frame} has no decoded source-frame mapping")
        samples.append({
            "frame_index": frame_index,
            "media_time_s": float(source_row["time_seconds"]),
            "stratum": str(source_row.get("stratum", "unstratified")),
        })
        frames.append({
            "frame_index": frame_index,
            "complete": True,
            "reviewer": str(label_rows[label_frame].get("reviewer", "")),
            "boxes": label_rows[label_frame].get("boxes", []),
        })

    dataset_id = str(reviewed_labels["dataset_id"])
    crowd_manifest = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "split": "diagnostic",
        "evaluation_protocol": {
            "split_unit": "video",
            "test_partition_id": f"{dataset_id}-diagnostic",
            "selection_locked_before_predictions": False,
        },
        "source_id": "reviewed-video-diagnostic",
        "source_sha256": video_sha256,
        "width": int(review_manifest["width"]),
        "height": int(review_manifest["height"]),
        "zone_polygons_normalized": {},
        "samples": samples,
    }
    crowd_labels = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "source_sha256": video_sha256,
        "frames": frames,
    }
    return crowd_manifest, crowd_labels


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-manifest", required=True, type=Path)
    parser.add_argument("--reviewed-labels", required=True, type=Path)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    manifest, labels = prepare(
        args.review_manifest.resolve(), args.reviewed_labels.resolve(), args.video.resolve()
    )
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, data in (("manifest.json", manifest), ("labels.json", labels)):
        with (output_dir / name).open("x", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, allow_nan=False)
            stream.write("\n")
    print(json.dumps({
        "status": "DIAGNOSTIC_INPUTS_PREPARED",
        "dataset_id": manifest["dataset_id"],
        "complete_frames": len(manifest["samples"]),
        "source_sha256": manifest["source_sha256"],
        "output_dir": str(output_dir),
        "split": manifest["split"],
    }, indent=2))


if __name__ == "__main__":
    main()
