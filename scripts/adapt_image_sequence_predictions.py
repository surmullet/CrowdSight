"""Adapt ordered-image runner output to the shared person-box evaluator format.

The adapter verifies dataset/archive identity and exact sequence/frame coverage,
then joins each prediction to the manifest's unique frame_index. It performs no
scoring and never changes detection boxes or confidence scores.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def adapt(manifest_path: Path, image_predictions_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    image_predictions_path = image_predictions_path.expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    image_predictions = json.loads(image_predictions_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(image_predictions, dict):
        raise ValueError("Manifest and image predictions must be JSON objects")
    if image_predictions.get("schema_version") != 1:
        raise ValueError("Image prediction schema_version must be 1")
    if image_predictions.get("dataset_id") != manifest.get("dataset_id"):
        raise ValueError("Image predictions dataset_id does not match manifest")
    source_sha = manifest.get("source_sha256")
    prediction_source_sha = image_predictions.get("source_sha256")
    if (
        not isinstance(source_sha, str)
        or not isinstance(prediction_source_sha, str)
        or prediction_source_sha.lower() != source_sha.lower()
    ):
        raise ValueError("Image predictions source archive hash does not match manifest")
    run_metadata = image_predictions.get("run_metadata")
    if not isinstance(run_metadata, dict):
        raise ValueError("Image prediction document has no run_metadata")
    inference_manifest_sha256 = run_metadata.get("manifest_sha256")
    if (
        not isinstance(inference_manifest_sha256, str)
        or inference_manifest_sha256.lower() != sha256_file(manifest_path).lower()
    ):
        raise ValueError("Image predictions were not generated from this exact manifest hash")
    model = image_predictions.get("model")
    if not isinstance(model, dict):
        raise ValueError("Image prediction document has no model metadata")
    model_id = model.get("profile_id")
    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError("Model profile_id must be a nonempty string")
    samples = manifest.get("samples")
    rows = image_predictions.get("frames")
    if not isinstance(samples, list) or not samples or not isinstance(rows, list):
        raise ValueError("Manifest samples and image prediction frames are required")
    key_to_index: dict[tuple[str, int], int] = {}
    expected_indices: set[int] = set()
    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError("Every manifest sample must be an object")
        sequence_id, frame_id, frame_index = (
            sample.get("sequence_id"), sample.get("frame_id"), sample.get("frame_index")
        )
        if (
            not isinstance(sequence_id, str) or not sequence_id.strip()
            or type(frame_id) is not int or frame_id < 1
            or type(frame_index) is not int or frame_index < 0
        ):
            raise ValueError("Each image sample requires sequence_id, positive frame_id, and unique frame_index")
        key = (sequence_id, frame_id)
        if key in key_to_index or frame_index in expected_indices:
            raise ValueError("Manifest sequence/frame keys and frame_index values must be unique")
        key_to_index[key] = frame_index
        expected_indices.add(frame_index)

    adapted_frames = []
    seen: set[tuple[str, int]] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each image prediction frame must be an object")
        key = (row.get("sequence_id"), row.get("frame_id"))
        if key not in key_to_index or key in seen:
            raise ValueError("Prediction contains an unknown or duplicate sequence/frame key")
        seen.add(key)
        if row.get("frame_index") != key_to_index[key]:
            raise ValueError("Prediction frame_index does not match manifest sequence/frame mapping")
        valid = row.get("valid")
        boxes = row.get("boxes", [])
        scored = row.get("scored_boxes", [])
        if type(valid) is not bool or not isinstance(boxes, list) or not isinstance(scored, list):
            raise ValueError("Prediction valid, boxes, and scored_boxes fields are malformed")
        if not valid and (boxes or scored):
            raise ValueError("Invalid image observations must not contain boxes or scores")
        adapted_frames.append({
            "frame_index": key_to_index[key],
            "valid": valid,
            "boxes": boxes,
            "scored_boxes": scored,
        })
    if seen != set(key_to_index):
        missing = sorted(set(key_to_index) - seen)
        raise ValueError(f"Image predictions do not cover every manifest sample: {missing[:10]}")
    adapted_frames.sort(key=lambda row: row["frame_index"])
    return {
        "schema_version": 1,
        "dataset_id": manifest["dataset_id"],
        "source_sha256": source_sha,
        "models": {
            model_id: {
                key: model.get(key) for key in (
                    "profile_id", "profile_sha256", "checkpoint_sha256",
                    "training_overlap_status", "independence_evidence_ref",
                    "independence_evidence_sha256", "training_manifest_sha256",
                    "training_source_inventory_complete", "training_source_sha256s",
                    "training_partition_ids", "training_evidence_file_sha256", "runtime",
                )
            } | {"frames": adapted_frames}
        },
        "image_prediction_sha256": sha256_file(image_predictions_path),
        "inference_script_sha256": run_metadata.get("inference_script_sha256"),
        "image_inference_script_sha256": run_metadata.get("inference_script_sha256"),
        "adapter_script_sha256": sha256_file(Path(__file__).resolve()),
        "manifest_sha256": sha256_file(manifest_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--image-predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if output.is_relative_to(ROOT):
        raise ValueError("Private predictions must be written outside the Git repository")
    adapted = adapt(args.manifest, args.image_predictions)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(adapted, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "PREDICTIONS_ADAPTED", "output": str(output), "sha256": sha256_file(output)}))


if __name__ == "__main__":
    main()
