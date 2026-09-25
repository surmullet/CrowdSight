"""Run a pinned detector profile on manifest-selected diagnostic/test frames."""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from crowdsight.detection import UltralyticsPersonDetector, load_person_detector_profile

logger = logging.getLogger("crowdsight.inference")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_locked_test_authorization(manifest: dict[str, Any]) -> None:
    """Refuse test inference until selection and permission metadata are recorded.

    This checks manifest fields only. A named reviewer must still authenticate
    the referenced evidence before results can be described as approved.
    """
    if manifest.get("split") not in ("test", "held_out"):
        return
    protocol = manifest.get("evaluation_protocol")
    if not isinstance(protocol, dict):
        raise ValueError("Test inference requires an evaluation_protocol object")
    if protocol.get("selection_locked_before_predictions") is not True:
        raise ValueError(
            "Test inference requires selection_locked_before_predictions: true"
        )
    if protocol.get("split_unit") not in ("video", "site", "flight", "camera_date"):
        raise ValueError("Test inference requires a video/site/flight/camera_date split_unit")
    partition_id = protocol.get("test_partition_id")
    if not isinstance(partition_id, str) or not partition_id.strip():
        raise ValueError("Test inference requires a nonempty test_partition_id")

    evidence = manifest.get("data_permission")
    if not isinstance(evidence, dict):
        raise ValueError("Test inference requires a data_permission review record")
    uses = evidence.get("permitted_uses")
    digest = evidence.get("evidence_sha256")
    if (
        evidence.get("status") != "approved"
        or not isinstance(uses, list)
        or "model_evaluation" not in uses
        or not isinstance(evidence.get("evidence_ref"), str)
        or not evidence["evidence_ref"].strip()
        or not isinstance(digest, str)
        or len(digest) != 64
        or any(char not in "0123456789abcdefABCDEF" for char in digest)
        or not isinstance(evidence.get("reviewer_id"), str)
        or not evidence["reviewer_id"].strip()
    ):
        raise ValueError(
            "Test inference requires approved model_evaluation permission with evidence reference, SHA-256, and reviewer_id"
        )


def run_inference(
    video_path: Path,
    manifest_path: Path,
    profile_path: Path,
    output_path: Path,
    checkpoint_path: Path | None = None,
    device_override: str | None = None,
    training_evidence_path: Path | None = None,
) -> dict[str, Any]:
    """Infer selected manifest frames; unavailable frames remain explicit."""
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV is required to decode evaluation video") from exc
    video_path = video_path.expanduser().resolve()
    manifest_path = manifest_path.expanduser().resolve()
    profile_path = profile_path.expanduser().resolve()
    training_evidence = {
        "training_overlap_status": "unknown_or_mixed",
        "independence_evidence_ref": None,
        "independence_evidence_sha256": None,
        "training_manifest_sha256": None,
        "training_source_inventory_complete": False,
        "training_source_sha256s": [],
        "training_partition_ids": [],
        "training_evidence_file_sha256": None,
    }
    if training_evidence_path is not None:
        evidence_path = training_evidence_path.expanduser().resolve()
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        if not isinstance(evidence, dict):
            raise ValueError("Training evidence root must be an object")
        allowed = set(training_evidence)
        if set(evidence) - allowed:
            raise ValueError(f"Training evidence has unsupported fields: {sorted(set(evidence) - allowed)}")
        training_evidence.update(evidence)
        training_evidence["training_evidence_file_sha256"] = sha256_file(evidence_path)
    if not video_path.is_file():
        raise FileNotFoundError(f"Evaluation video not found: {video_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("split") not in ("diagnostic", "test", "held_out"):
        raise ValueError("Inference manifest split must be diagnostic/test/held_out")
    _require_locked_test_authorization(manifest)
    video_sha256 = sha256_file(video_path)
    if video_sha256.lower() != str(manifest.get("source_sha256", "")).lower():
        raise ValueError("Evaluation video SHA-256 does not match the manifest")
    width, height = int(manifest["width"]), int(manifest["height"])
    samples = manifest.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("Manifest must define at least one selected frame")
    selected = [sample["frame_index"] for sample in samples]
    if any(type(index) is not int or index < 0 for index in selected):
        raise ValueError("Manifest frame_index values must be nonnegative integers")
    if len(set(selected)) != len(selected):
        raise ValueError("Manifest frame_index values must be unique")
    selected_set = set(selected)

    profile = load_person_detector_profile(
        profile_path,
        checkpoint_path=checkpoint_path,
        device_override=device_override,
    )
    detector = UltralyticsPersonDetector(profile)
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open evaluation video: {video_path}")
    frame_predictions = []
    current_index = 0
    remaining = set(selected_set)
    try:
        while remaining:
            ok, frame = capture.read()
            if not ok:
                break
            if frame.shape[1] != width or frame.shape[0] != height:
                raise ValueError("Decoded frame dimensions do not match evaluation manifest")
            if current_index in selected_set:
                try:
                    detections = detector.predict(frame)
                    boxes = [
                        list(detection.bbox_xyxy_px)
                        for detection in detections
                        if detection.bbox_xyxy_px is not None
                    ]
                    frame_predictions.append(
                        {"frame_index": current_index, "valid": True, "boxes": boxes}
                    )
                    remaining.remove(current_index)
                except Exception as exc:
                    logger.exception("Inference failed for selected frame %d", current_index)
                    frame_predictions.append(
                        {
                            "frame_index": current_index,
                            "valid": False,
                            "boxes": [],
                            "failure_type": type(exc).__name__,
                        }
                    )
                    remaining.remove(current_index)
            current_index += 1
    finally:
        capture.release()

    produced = {row["frame_index"] for row in frame_predictions}
    missing = selected_set - produced
    if missing:
        raise ValueError(f"Video ended before manifest frames were decoded: {sorted(missing)}")
    frame_predictions.sort(key=lambda item: item["frame_index"])
    result = {
        "schema_version": 1,
        "dataset_id": manifest["dataset_id"],
        "source_sha256": video_sha256,
        "inference_script_sha256": sha256_file(Path(__file__).resolve()),
        "models": {
            profile.profile_id: {
                "profile_id": profile.profile_id,
                "profile_sha256": profile.profile_sha256.lower(),
                "checkpoint_sha256": profile.expected_sha256.lower(),
                **training_evidence,
                "runtime": {
                    **detector.runtime_metadata,
                    "opencv_version": cv2.__version__,
                },
                "frames": frame_predictions,
            }
        },
    }
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    return {
        "profile_id": profile.profile_id,
        "selected_frames": len(selected),
        "valid_frames": sum(row["valid"] for row in frame_predictions),
        "unknown_frames": sum(not row["valid"] for row in frame_predictions),
        "prediction_file": str(output_path),
        "video_sha256": video_sha256,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--checkpoint", type=Path, help="Trusted local artifact path; otherwise use the profile environment variable")
    parser.add_argument("--device", help="Optional device override, for example cpu or cuda:0")
    parser.add_argument(
        "--training-evidence",
        type=Path,
        help="JSON record of training sources/partitions and reviewed independence evidence; omit to label overlap unknown",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    summary = run_inference(
        args.video,
        args.manifest,
        args.profile,
        args.output,
        args.checkpoint,
        args.device,
        args.training_evidence,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
