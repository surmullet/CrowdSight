"""Build the private image manifest from the frozen DroneCrowd selection.

The script hashes selected source frames and verifies their mapping to the
locked sequence/frame IDs. It reads no annotations and runs no model.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
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


def _read_json(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} root must be an object")
    return value


def _permission(record_path: Path) -> dict[str, Any]:
    record = _read_json(record_path, "Permission record")
    status = record.get("status")
    uses = record.get("permitted_uses")
    evidence_ref = record.get("evidence_ref")
    evidence_sha256 = record.get("evidence_sha256")
    evidence_file = record.get("evidence_file")
    reviewer_id = record.get("reviewer_id")
    if (
        status != "approved" or not isinstance(uses, list)
        or any(not isinstance(item, str) or not item.strip() for item in uses)
        or len(uses) != len(set(uses))
        or not {"model_evaluation", "annotation_transformation"}.issubset(uses)
    ):
        raise ValueError("Permission record must approve model_evaluation and annotation_transformation")
    if not isinstance(evidence_ref, str) or not evidence_ref.strip():
        raise ValueError("Permission record evidence_ref must be nonempty")
    if not isinstance(evidence_sha256, str) or len(evidence_sha256) != 64 or any(
        char not in "0123456789abcdefABCDEF" for char in evidence_sha256
    ):
        raise ValueError("Permission record evidence_sha256 must be a SHA-256")
    if not isinstance(reviewer_id, str) or not reviewer_id.strip():
        raise ValueError("Permission record reviewer_id must be nonempty")
    if not isinstance(evidence_file, str) or not evidence_file.strip():
        raise ValueError("Permission record must name the local evidence_file to hash")
    resolved_evidence = Path(evidence_file).expanduser().resolve()
    if not resolved_evidence.is_file():
        raise FileNotFoundError(f"Permission evidence file not found: {resolved_evidence}")
    actual_sha = sha256_file(resolved_evidence)
    if actual_sha.lower() != evidence_sha256.lower():
        raise ValueError("Permission evidence file hash does not match the permission record")
    return {
        "status": status,
        "permitted_uses": uses,
        "evidence_ref": evidence_ref,
        "evidence_sha256": actual_sha,
        "reviewer_id": reviewer_id,
        "review_state": "METADATA_ONLY_REVIEWER_MUST_AUTHENTICATE_SOURCE_TERMS",
    }


def prepare_manifest(
    *, selection_path: Path, images_root: Path, source_archive: Path,
    permission_record_path: Path, output_path: Path,
) -> dict[str, Any]:
    """Validate selection, archive, permission evidence, and frame bytes."""
    selection_path = selection_path.expanduser().resolve()
    images_root = images_root.expanduser().resolve()
    source_archive = source_archive.expanduser().resolve()
    permission_record_path = permission_record_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    if output_path.is_relative_to(ROOT):
        raise ValueError("Private evaluation manifests must be written outside the Git repository")
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite manifest: {output_path}")
    if not images_root.is_dir():
        raise NotADirectoryError(f"Extracted images root not found: {images_root}")
    if not source_archive.is_file():
        raise FileNotFoundError(f"Source archive not found: {source_archive}")

    selection = _read_json(selection_path, "Selection")
    if selection.get("schema_version") != 1 or selection.get("status") != "SELECTION_LOCKED_PENDING_PERMISSION_AND_SCORER":
        raise ValueError("Selection must be the locked, pending DroneCrowd candidate record")
    source = selection.get("source")
    sampling = selection.get("sampling")
    selected = selection.get("selected_sequence_ids")
    if not isinstance(source, dict) or not isinstance(sampling, dict):
        raise ValueError("Selection source and sampling objects are required")
    if not isinstance(selected, list) or not selected or any(
        not isinstance(item, str) or len(item) != 5 or not item.isdigit() for item in selected
    ):
        raise ValueError("Selection must contain selected_sequence_ids")
    if len(set(selected)) != len(selected):
        raise ValueError("Selection sequence IDs must be unique")
    independence = selection.get("independence")
    if not isinstance(independence, dict):
        raise ValueError("Selection independence record is required")
    excluded = independence.get("prior_comparison_excluded_sequence_ids", [])
    if (
        not isinstance(excluded, list)
        or any(not isinstance(item, str) for item in excluded)
        or set(selected).intersection(excluded)
    ):
        raise ValueError("Selection includes a sequence used in the prior comparison")
    sequence_count = sampling.get("selected_sequence_count")
    frames_per_sequence = sampling.get("frames_per_sequence")
    expected_count = sampling.get("expected_frame_count")
    if sequence_count != len(selected) or type(frames_per_sequence) is not int or frames_per_sequence != 30:
        raise ValueError("Selection sampling counts are inconsistent")
    if expected_count != sequence_count * frames_per_sequence:
        raise ValueError("Selection expected_frame_count is inconsistent")
    if sampling.get("frame_rule") != "All 30 labeled frame IDs, 1 through 30, in each selected sequence.":
        raise ValueError("Selection frame_rule does not match the frozen DroneCrowd sampling rule")
    if sampling.get("prediction_generated") is not False:
        raise ValueError("Selection record says predictions already exist; prepare a new reviewed manifest instead")

    expected_size = source.get("local_archive_bytes")
    expected_archive_sha = source.get("local_archive_sha256")
    if type(expected_size) is not int or source_archive.stat().st_size != expected_size:
        raise ValueError("Source archive byte size does not match the locked selection record")
    archive_sha = sha256_file(source_archive)
    if not isinstance(expected_archive_sha, str) or archive_sha.lower() != expected_archive_sha.lower():
        raise ValueError("Source archive SHA-256 does not match the locked selection record")
    permission = _permission(permission_record_path)

    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV is required to inspect source image dimensions") from exc

    samples = []
    image_width = image_height = None
    for sequence_id in selected:
        for frame_id in range(1, frames_per_sequence + 1):
            relative_path = Path("sequences") / sequence_id / f"{frame_id:05d}.jpg"
            image_path = (images_root / relative_path).resolve()
            if not image_path.is_relative_to(images_root):
                raise ValueError("Selected image path resolves outside images_root")
            if not image_path.is_file():
                raise FileNotFoundError(f"Selected source frame is missing: {image_path}")
            image_sha = sha256_file(image_path)
            image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError(f"Selected source frame cannot be decoded: {image_path}")
            height, width = image.shape[:2]
            if image_width is None:
                image_width, image_height = width, height
            elif (width, height) != (image_width, image_height):
                raise ValueError("Selected source images do not have consistent dimensions")
            samples.append({
                "sequence_id": sequence_id,
                "frame_id": frame_id,
                "image_path": relative_path.as_posix(),
                "image_sha256": image_sha,
                "stratum": "unstratified",
            })
    if len(samples) != expected_count:
        raise ValueError(f"Prepared {len(samples)} samples; expected {expected_count}")

    manifest = {
        "schema_version": 1,
        "dataset_id": selection["selection_id"],
        "split": "test",
        "source_id": "visdrone-dronecrowd-2020-cc",
        "source_sha256": archive_sha,
        "source_archive_bytes": source_archive.stat().st_size,
        "source_archive_sha256": archive_sha,
        "selection_id": selection["selection_id"],
        "selection_sha256": sha256_file(selection_path),
        "manifest_preparation_script_sha256": sha256_file(Path(__file__).resolve()),
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_protocol": {
            "split_unit": "sequence",
            "test_partition_id": selection["selection_id"],
            "selection_locked_before_predictions": True,
            "sample_count": expected_count,
        },
        "data_permission": permission,
        "width": image_width,
        "height": image_height,
        "samples": samples,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--images-root", type=Path, required=True)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--permission-record", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare_manifest(
        selection_path=args.selection,
        images_root=args.images_root,
        source_archive=args.source_archive,
        permission_record_path=args.permission_record,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
