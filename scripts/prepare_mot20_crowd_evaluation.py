"""Prepare private CrowdSight manifests and box labels from MOT20 train data.

This utility does not download or copy the dataset. Lock the selected sequence
IDs before inference, provide an approved permission record, and write outputs
outside the Git repository. MOTChallenge frame IDs are one-based; this tool
assigns each selected sequence/frame pair a unique zero-based frame_index.
"""
from __future__ import annotations

import argparse
import configparser
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
from typing import Any
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MOT20_TRAIN_SEQUENCES = {"MOT20-01", "MOT20-02", "MOT20-03", "MOT20-05"}
MOT20_CLASS_IDS = set(range(1, 14))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _permission(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if path.is_relative_to(ROOT):
        raise ValueError("Private permission records must be stored outside the Git repository")
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError("Permission record must be a JSON object")
    uses = record.get("permitted_uses")
    evidence_file = record.get("evidence_file")
    evidence_sha = record.get("evidence_sha256")
    evidence_ref = record.get("evidence_ref")
    reviewer = record.get("reviewer_id")
    if (
        record.get("status") != "approved"
        or not isinstance(uses, list)
        or any(not isinstance(use, str) or not use.strip() for use in uses)
        or len(uses) != len(set(uses))
        or not {"model_evaluation", "annotation_transformation"}.issubset(uses)
        or not isinstance(evidence_file, str)
        or not evidence_file.strip()
        or not isinstance(evidence_ref, str)
        or not evidence_ref.strip()
        or not isinstance(reviewer, str)
        or not reviewer.strip()
        or not isinstance(evidence_sha, str)
        or len(evidence_sha) != 64
        or any(char not in "0123456789abcdefABCDEF" for char in evidence_sha)
    ):
        raise ValueError(
            "Permission record must approve model_evaluation and annotation_transformation "
            "and identify its evidence file, SHA-256, reference, and reviewer"
        )
    evidence_path = Path(evidence_file).expanduser()
    if not evidence_path.is_absolute():
        evidence_path = path.parent / evidence_path
    evidence_path = evidence_path.resolve()
    if evidence_path.is_relative_to(ROOT):
        raise ValueError("Private permission evidence must be stored outside the Git repository")
    if not evidence_path.is_file() or sha256_file(evidence_path).lower() != evidence_sha.lower():
        raise ValueError("Permission evidence file is missing or its SHA-256 does not match")
    return {
        "status": "approved",
        "permitted_uses": uses,
        "evidence_ref": evidence_ref,
        "evidence_sha256": evidence_sha.lower(),
        "reviewer_id": reviewer,
        "review_state": "METADATA_ONLY_REVIEWER_MUST_AUTHENTICATE_SOURCE_TERMS",
    }


def _read_sequence(sequence_dir: Path) -> tuple[int, int, int, float, list[Path]]:
    info_path = sequence_dir / "seqinfo.ini"
    image_dir = sequence_dir / "img1"
    if not info_path.is_file() or not image_dir.is_dir():
        raise FileNotFoundError(f"Expected seqinfo.ini and img1/ under {sequence_dir}")
    parser = configparser.ConfigParser()
    parser.read(info_path, encoding="utf-8")
    if "Sequence" not in parser:
        raise ValueError(f"Missing [Sequence] section in {info_path}")
    section = parser["Sequence"]
    try:
        width = int(section["imWidth"])
        height = int(section["imHeight"])
        length = int(section["seqLength"])
        fps = float(section["frameRate"])
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Invalid image size, frame rate, or sequence length in {info_path}") from exc
    if width <= 0 or height <= 0 or length <= 0 or not math.isfinite(fps) or fps <= 0:
        raise ValueError(f"Invalid sequence metadata in {info_path}")
    images = list(image_dir.glob("*.jpg"))
    for image in images:
        if not image.stem.isdigit():
            raise ValueError(f"Non-numeric image filename in {image_dir}: {image.name}")
    images.sort(key=lambda path: int(path.stem))
    expected_ids = list(range(1, length + 1))
    actual_ids = [int(image.stem) for image in images]
    if actual_ids != expected_ids:
        raise ValueError(f"Image IDs in {image_dir} are missing, duplicated, or outside seqLength")
    return width, height, length, fps, images


def _read_people(gt_path: Path, width: int, height: int) -> tuple[dict[int, list[list[float]]], int]:
    """Read marked pedestrian class 1; clip partially visible boxes to image bounds."""
    if not gt_path.is_file():
        raise FileNotFoundError(f"MOT20 ground-truth file not found: {gt_path}")
    people: dict[int, list[list[float]]] = {}
    clipped_count = 0
    with gt_path.open("r", encoding="utf-8-sig", newline="") as stream:
        for line_number, row in enumerate(csv.reader(stream), start=1):
            if not row or all(not value.strip() for value in row):
                continue
            if len(row) != 9:
                raise ValueError(f"Expected nine MOTChallenge GT fields at {gt_path}:{line_number}")
            try:
                frame_id = int(row[0].strip())
                track_id_value = float(row[1].strip())
                left, top, box_width, box_height = (float(row[i].strip()) for i in range(2, 6))
                mark_value = float(row[6].strip())
                class_value = float(row[7].strip())
                visibility = float(row[8].strip())
            except ValueError as exc:
                raise ValueError(f"Non-numeric MOTChallenge GT value at {gt_path}:{line_number}") from exc
            if (
                frame_id <= 0
                or not all(math.isfinite(value) for value in (
                    track_id_value, left, top, box_width, box_height,
                    mark_value, class_value, visibility,
                ))
                or not track_id_value.is_integer()
                or not mark_value.is_integer()
                or not class_value.is_integer()
                or not 0.0 <= visibility <= 1.0
            ):
                raise ValueError(f"Invalid frame or box value at {gt_path}:{line_number}")
            mark, class_id = int(mark_value), int(class_value)
            if class_id not in MOT20_CLASS_IDS:
                raise ValueError(f"Unknown MOT20 class ID {class_id} at {gt_path}:{line_number}")
            if class_id != 1 or mark == 0:
                continue
            right, bottom = left + box_width, top + box_height
            if right <= left or bottom <= top:
                raise ValueError(f"Degenerate marked pedestrian box at {gt_path}:{line_number}")
            clipped_box = [max(0.0, left), max(0.0, top), min(float(width), right), min(float(height), bottom)]
            if clipped_box[2] <= clipped_box[0] or clipped_box[3] <= clipped_box[1]:
                raise ValueError(f"Marked pedestrian box has no image intersection at {gt_path}:{line_number}")
            if clipped_box != [left, top, right, bottom]:
                clipped_count += 1
            people.setdefault(frame_id, []).append(clipped_box)
    return people, clipped_count


def _archive_member(archive: zipfile.ZipFile, suffix: tuple[str, ...]) -> str:
    matches = [
        name for name in archive.namelist()
        if tuple(PurePosixPath(name).parts[-len(suffix):]) == suffix
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one archive member ending in {'/'.join(suffix)}; found {len(matches)}")
    return matches[0]


def prepare(
    *, sequences_root: Path, source_archive: Path, labels_archive: Path, permission_record: Path,
    sequence_ids: list[str], sample_stride: int, output_dir: Path,
) -> dict[str, Any]:
    sequences_root = sequences_root.expanduser().resolve()
    source_archive = source_archive.expanduser().resolve()
    labels_archive = labels_archive.expanduser().resolve()
    permission_record = permission_record.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    if output_dir.is_relative_to(ROOT):
        raise ValueError("Private manifests and labels must be written outside the Git repository")
    if sequences_root.is_relative_to(ROOT) or source_archive.is_relative_to(ROOT) or labels_archive.is_relative_to(ROOT):
        raise ValueError("MOT20 media and archive must remain outside the Git repository")
    if not source_archive.is_file():
        raise FileNotFoundError(f"MOT20 source archive not found: {source_archive}")
    if not labels_archive.is_file():
        raise FileNotFoundError(f"MOT20 labels archive not found: {labels_archive}")
    if type(sample_stride) is not int or sample_stride <= 0:
        raise ValueError("sample_stride must be a positive integer")
    if not sequence_ids or len(set(sequence_ids)) != len(sequence_ids):
        raise ValueError("Provide a nonempty unique list of sequence IDs")
    if any(sequence_id not in MOT20_TRAIN_SEQUENCES for sequence_id in sequence_ids):
        raise ValueError("Only the four official annotated MOT20 training sequences can be selected")
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite an existing output directory: {output_dir}")

    permission = _permission(permission_record)
    archive_sha = sha256_file(source_archive)
    labels_archive_sha = sha256_file(labels_archive)
    try:
        video_zip = zipfile.ZipFile(source_archive)
        labels_zip = zipfile.ZipFile(labels_archive)
    except zipfile.BadZipFile as exc:
        raise ValueError("MOT20 source and annotation archives must be readable ZIP files") from exc
    selected = sorted(sequence_ids)
    partition_id = "MOT20-train-" + "-".join(selected)
    dataset_id = (
        "mot20-" + "-".join(sequence_id.lower() for sequence_id in selected)
        + f"-stride{sample_stride}-test-v4"
    )
    samples: list[dict[str, Any]] = []
    label_frames: list[dict[str, Any]] = []
    common_size: tuple[int, int] | None = None
    global_index = 0
    selected_frame_count = 0
    clipped_gt_box_count = 0
    for sequence_id in selected:
        sequence_dir = sequences_root / sequence_id
        width, height, length, fps, images = _read_sequence(sequence_dir)
        if common_size is None:
            common_size = (width, height)
        elif common_size != (width, height):
            raise ValueError("Selected MOT20 sequences have different dimensions; evaluate one size group per manifest")
        gt_by_frame, sequence_clipped_box_count = _read_people(sequence_dir / "gt" / "gt.txt", width, height)
        clipped_gt_box_count += sequence_clipped_box_count
        if any(frame_id > length for frame_id in gt_by_frame):
            raise ValueError(f"Ground-truth frame ID exceeds seqLength in {sequence_dir}")
        gt_path = sequence_dir / "gt" / "gt.txt"
        gt_member = _archive_member(labels_zip, (sequence_id, "gt", "gt.txt"))
        archived_gt = labels_zip.read(gt_member)
        if hashlib.sha256(archived_gt).hexdigest() != sha256_file(gt_path):
            raise ValueError(f"Extracted ground truth does not match labels archive: {sequence_id}")
        chosen_positions = set(range(0, len(images), sample_stride))
        if len(images) - 1 not in chosen_positions:
            chosen_positions.add(len(images) - 1)
        for position in sorted(chosen_positions):
            image = images[position]
            frame_id = int(image.stem)
            frame_index = global_index
            global_index += 1
            selected_frame_count += 1
            image_member = _archive_member(video_zip, (sequence_id, "img1", image.name))
            archived_image = video_zip.read(image_member)
            image_sha = sha256_file(image)
            if hashlib.sha256(archived_image).hexdigest() != image_sha:
                raise ValueError(f"Extracted image does not match source archive: {sequence_id}/{image.name}")
            samples.append({
                "frame_index": frame_index,
                "media_time_s": (frame_id - 1) / fps,
                "stratum": sequence_id,
                "sequence_id": sequence_id,
                "frame_id": frame_id,
                "image_path": f"{sequence_id}/img1/{image.name}",
                "image_sha256": image_sha,
            })
            label_frames.append({
                "frame_index": frame_index,
                "complete": True,
                "reviewer": "MOTChallenge-published-GT; source mapping not independently re-annotated",
                "boxes": [
                    {"bbox_xyxy": box, "uncertain": False}
                    for box in gt_by_frame.get(frame_id, [])
                ],
            })

    video_zip.close()
    labels_zip.close()

    if not samples or common_size is None:
        raise ValueError("No frames were selected")
    prepared_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    preparation_script_sha = sha256_file(Path(__file__).resolve())
    manifest = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "split": "test",
        "prepared_at_utc": prepared_at,
        "manifest_preparation_script_sha256": preparation_script_sha,
        "evaluation_protocol": {
            "split_unit": "sequence",
            "test_partition_id": partition_id,
            "selection_locked_before_predictions": True,
            "selection_locked_at_utc": prepared_at,
            "sequence_ids": selected,
            "sample_stride_frames": sample_stride,
            "sampling_method": "Zero-based positions at the fixed stride, plus the last frame if not already selected.",
            "annotation_mapping": "MOTChallenge GT class_id=1 with nonzero mark; track ID ignored for frame-level detection/count metrics; xywh converted to xyxy and partial boxes clipped to image bounds.",
            "clipped_gt_box_count_full_sequence": clipped_gt_box_count,
            "source_annotation_review": "Publisher annotation used without relabeling; verify source protocol and selected frame mapping before claims.",
        },
        "source_id": "motchallenge-mot20",
        "source_page": "https://motchallenge.net/data/MOT20/",
        "dataset_license_status": "UNVERIFIED; current official archive page omits license terms; historical CC BY-NC-SA 3.0 notice requires independent reviewer authentication",
        "historical_license_notice": "CC BY-NC-SA 3.0 (historical notice; not authenticated from current source)",
        "source_sha256": archive_sha,
        "source_archive_bytes": source_archive.stat().st_size,
        "source_archive_sha256": archive_sha,
        "annotation_archive_bytes": labels_archive.stat().st_size,
        "annotation_archive_sha256": labels_archive_sha,
        "data_permission": permission,
        "width": common_size[0],
        "height": common_size[1],
        "zone_polygons_normalized": {},
        "samples": samples,
    }
    labels = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "source_sha256": archive_sha,
        "annotation_archive_sha256": labels_archive_sha,
        "annotation_source_kind": "published_ground_truth",
        "annotation_source": "MOTChallenge MOT20 publisher ground truth",
        "annotation_mapping": "class_id=1 and mark!=0; xywh converted to xyxy; partial boxes clipped to image bounds; track IDs ignored",
        "clipped_gt_box_count_full_sequence": clipped_gt_box_count,
        "frames": label_frames,
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output_dir / "labels.json").write_text(json.dumps(labels, indent=2) + "\n", encoding="utf-8")
    return {
        "dataset_id": dataset_id,
        "partition_id": partition_id,
        "sequence_ids": selected,
        "sample_count": selected_frame_count,
        "source_archive_sha256": archive_sha,
        "annotation_archive_sha256": labels_archive_sha,
        "manifest_sha256": sha256_file(output_dir / "manifest.json"),
        "labels_sha256": sha256_file(output_dir / "labels.json"),
        "output_dir": str(output_dir),
        "note": "Review source license and sequence mapping independently; output is a candidate evaluation package, not a verified held-out report.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequences-root", type=Path, required=True, help="Extracted train directory containing MOT20-*/ folders")
    parser.add_argument("--source-archive", type=Path, required=True, help="Original official MOT20 archive whose SHA-256 identifies this dataset source")
    parser.add_argument("--labels-archive", type=Path, required=True, help="Original official MOT20Labels archive; its SHA-256 is recorded with the labels")
    parser.add_argument("--permission-record", type=Path, required=True, help="Privately reviewed permission JSON with evidence file and hash")
    parser.add_argument("--sequence-ids", nargs="+", required=True, choices=sorted(MOT20_TRAIN_SEQUENCES))
    parser.add_argument("--sample-stride", type=int, default=25, help="Sample every Nth frame (default: 25, about 1 Hz at 25 FPS)")
    parser.add_argument("--output-dir", type=Path, required=True, help="Private output directory outside this repository")
    args = parser.parse_args()
    print(json.dumps(prepare(
        sequences_root=args.sequences_root,
        source_archive=args.source_archive,
        labels_archive=args.labels_archive,
        permission_record=args.permission_record,
        sequence_ids=args.sequence_ids,
        sample_stride=args.sample_stride,
        output_dir=args.output_dir,
    ), indent=2))


if __name__ == "__main__":
    main()
