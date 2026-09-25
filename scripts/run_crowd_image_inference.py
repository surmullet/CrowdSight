"""Run the pinned CrowdSight detector on a locked manifest of source images.

This runner is for ordered image-sequence datasets such as DroneCrowd. It does
not load labels, and it refuses to infer unless model-evaluation permission is
present in the manifest. Keep images and output JSON in private artifact storage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from crowdsight.detection import UltralyticsPersonDetector, load_person_detector_profile


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_authorized_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema_version") != 1:
        raise ValueError("Manifest schema_version must be 1")
    if manifest.get("split") not in ("diagnostic", "test", "held_out"):
        raise ValueError("Manifest split must be diagnostic, test, or held_out")
    protocol = manifest.get("evaluation_protocol")
    if not isinstance(protocol, dict):
        raise ValueError("Manifest evaluation_protocol must be an object")
    if protocol.get("split_unit") != "sequence":
        raise ValueError("Image-sequence evaluation requires split_unit: sequence")
    if protocol.get("selection_locked_before_predictions") is not True:
        raise ValueError("Image-sequence inference requires selection locked before predictions")
    partition_id = protocol.get("test_partition_id")
    if not isinstance(partition_id, str) or not partition_id.strip():
        raise ValueError("Manifest test_partition_id must be nonempty")
    permission = manifest.get("data_permission")
    if not isinstance(permission, dict) or permission.get("status") != "approved":
        raise ValueError("Inference requires approved data_permission metadata")
    uses = permission.get("permitted_uses")
    ref, digest, reviewer = (
        permission.get("evidence_ref"),
        permission.get("evidence_sha256"),
        permission.get("reviewer_id"),
    )
    if (
        not isinstance(uses, list) or "model_evaluation" not in uses
        or not isinstance(ref, str) or not ref.strip()
        or not isinstance(digest, str) or len(digest) != 64
        or any(char not in "0123456789abcdefABCDEF" for char in digest)
        or not isinstance(reviewer, str) or not reviewer.strip()
    ):
        raise ValueError(
            "Inference requires approved model_evaluation permission with evidence reference, SHA-256, and reviewer ID"
        )


def _training_evidence(path: Path | None) -> dict[str, Any]:
    evidence = {
        "training_overlap_status": "unknown_or_mixed",
        "independence_evidence_ref": None,
        "independence_evidence_sha256": None,
        "training_manifest_sha256": None,
        "training_source_inventory_complete": False,
        "training_source_sha256s": [],
        "training_sequence_inventory_complete": False,
        "training_sequence_ids": [],
        "training_partition_ids": [],
        "training_evidence_file_sha256": None,
    }
    if path is None:
        return evidence
    resolved = path.expanduser().resolve()
    loaded = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("Training evidence root must be an object")
    extra = set(loaded) - set(evidence)
    if extra:
        raise ValueError(f"Training evidence has unsupported fields: {sorted(extra)}")
    evidence.update(loaded)
    evidence["training_evidence_file_sha256"] = sha256_file(resolved)
    return evidence


def run_inference(
    *,
    images_root: Path,
    source_archive: Path,
    manifest_path: Path,
    profile_path: Path,
    output_path: Path,
    checkpoint_path: Path | None = None,
    device_override: str | None = None,
    training_evidence_path: Path | None = None,
) -> dict[str, Any]:
    """Infer all locked frames after validating source, rights, and model hashes."""
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV is required to decode evaluation images") from exc

    manifest_path = manifest_path.expanduser().resolve()
    images_root = images_root.expanduser().resolve()
    source_archive = source_archive.expanduser().resolve()
    profile_path = profile_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing predictions: {output_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Manifest root must be an object")
    _require_authorized_manifest(manifest)
    if not source_archive.is_file():
        raise FileNotFoundError(f"Source archive not found: {source_archive}")
    if not images_root.is_dir():
        raise NotADirectoryError(f"Images root not found: {images_root}")
    archive_sha = sha256_file(source_archive)
    expected_archive_sha = manifest.get("source_sha256")
    if not isinstance(expected_archive_sha, str) or archive_sha.lower() != expected_archive_sha.lower():
        raise ValueError("Source archive SHA-256 does not match the manifest")
    training = _training_evidence(training_evidence_path)

    samples = manifest.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("Manifest must contain a nonempty samples array")
    width, height = manifest.get("width"), manifest.get("height")
    if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
        raise ValueError("Manifest width and height must be positive integers")
    seen_keys: set[tuple[str, int]] = set()
    resolved_samples = []
    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError("Each manifest sample must be an object")
        sequence_id, frame_id = sample.get("sequence_id"), sample.get("frame_id")
        if not isinstance(sequence_id, str) or not sequence_id.strip() or type(frame_id) is not int or frame_id < 1:
            raise ValueError("Each sample requires a nonempty sequence_id and positive one-based frame_id")
        key = (sequence_id, frame_id)
        if key in seen_keys:
            raise ValueError("Manifest sequence/frame keys must be unique")
        seen_keys.add(key)
        relative_path = sample.get("image_path")
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("Each sample requires image_path relative to images_root")
        image_path = (images_root / relative_path).resolve()
        if not image_path.is_relative_to(images_root):
            raise ValueError("Manifest image_path resolves outside images_root")
        image_sha = sample.get("image_sha256")
        if not isinstance(image_sha, str) or len(image_sha) != 64 or any(
            char not in "0123456789abcdefABCDEF" for char in image_sha
        ):
            raise ValueError("Each sample requires a 64-character image_sha256")
        resolved_samples.append((sample, image_path, image_sha.lower()))

    profile = load_person_detector_profile(
        profile_path,
        checkpoint_path=checkpoint_path,
        device_override=device_override,
    )
    detector = UltralyticsPersonDetector(profile)
    predictions = []
    for sample, image_path, expected_sha in resolved_samples:
        if not image_path.is_file():
            predictions.append({
                "sequence_id": sample["sequence_id"],
                "frame_id": sample["frame_id"],
                "image_sha256": expected_sha,
                "valid": False,
                "count": None,
                "unavailable_reason": "SOURCE_IMAGE_MISSING",
            })
            continue
        image_sha = sha256_file(image_path)
        if image_sha.lower() != expected_sha:
            raise ValueError(f"Image SHA-256 does not match manifest: {image_path}")
        frame = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if frame is None:
            predictions.append({
                "sequence_id": sample["sequence_id"],
                "frame_id": sample["frame_id"],
                "image_sha256": image_sha,
                "valid": False,
                "count": None,
                "unavailable_reason": "SOURCE_IMAGE_DECODE_FAILED",
            })
            continue
        frame_height, frame_width = frame.shape[:2]
        if (frame_width, frame_height) != (width, height):
            raise ValueError(
                f"Decoded image dimensions {(frame_width, frame_height)} do not match manifest {(width, height)}"
            )
        detections = detector.predict(frame)
        boxes = [
            [float(value) for value in detection.bbox_xyxy_px]
            for detection in detections if detection.bbox_xyxy_px is not None
        ]
        scored_boxes = [
            {"bbox_xyxy": [float(value) for value in detection.bbox_xyxy_px], "raw_score": float(detection.confidence)}
            for detection in detections if detection.bbox_xyxy_px is not None
        ]
        if len(boxes) != len(detections):
            raise RuntimeError("Detector returned a person without a pixel box; cannot produce a reproducible count")
        predictions.append({
            "sequence_id": sample["sequence_id"],
            "frame_id": sample["frame_id"],
            "image_sha256": image_sha,
            "valid": True,
            "count": len(detections),
            "boxes": boxes,
            "scored_boxes": scored_boxes,
        })

    result = {
        "schema_version": 1,
        "dataset_id": manifest.get("dataset_id"),
        "source_sha256": archive_sha,
        "model": {
            "profile_id": profile.profile_id,
            "profile_sha256": profile.profile_sha256,
            "checkpoint_sha256": detector.checkpoint_sha256,
            **training,
            "runtime": detector.runtime_metadata,
        },
        "frames": predictions,
        "run_metadata": {
            "manifest_sha256": sha256_file(manifest_path),
            "source_archive_sha256": archive_sha,
            "profile_file_sha256": sha256_file(profile_path),
            "training_evidence_file_sha256": training["training_evidence_file_sha256"],
            "inference_script_sha256": sha256_file(Path(__file__).resolve()),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images-root", type=Path, required=True)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--training-evidence", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--device", help="Optional device override, for example cpu or cuda:0")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_inference(
        images_root=args.images_root,
        source_archive=args.source_archive,
        manifest_path=args.manifest,
        profile_path=args.profile,
        training_evidence_path=args.training_evidence,
        checkpoint_path=args.checkpoint,
        device_override=args.device,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
