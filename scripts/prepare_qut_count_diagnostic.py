"""Lock every annotated SAIVT-QUT frame and transform publisher dots to ROI counts.

The QUT cameras are external diagnostic units. Publisher dot positions support
count error, not box matching. Source images and generated records stay private.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import xml.etree.ElementTree as ET


ARCHIVE_SHA256 = "0ae3bad144917191445a1c390e5f2ec9a06884318e751661baa57c8091582d37"
ARCHIVE_BYTES = 977_933_533
CAMERAS = ("A", "B", "C")
ROOT = "SAIVT-QUTCrowdCountingDatabase/Datasets/QUT"
GT_PATTERN = re.compile(rf"^{re.escape(ROOT)}/([ABC])/gt/(\d{{8}})\.txt$")
IMAGE_PATTERN = re.compile(rf"^{re.escape(ROOT)}/([ABC])/img/(\d{{8}})\.jpg$")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def outside_git(path: Path) -> bool:
    return not any((parent / ".git").exists() for parent in (path, *path.parents))


def in_polygon(x: float, y: float, vertices: tuple[tuple[int, int], ...]) -> bool:
    """Include polygon edges; use the same rule for dots and detections."""
    inside = False
    for index, (x1, y1) in enumerate(vertices):
        x2, y2 = vertices[(index + 1) % len(vertices)]
        cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
        if abs(cross) < 1e-9 and min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2):
            return True
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def parse_roi(data: bytes, camera: str) -> tuple[int, int, tuple[tuple[int, int], ...]]:
    root = ET.fromstring(data)
    if root.tag != "ROI":
        raise ValueError(f"QUT {camera} ROI root is not ROI")
    width, height = int(root.attrib["image-width"]), int(root.attrib["image-height"])
    vertices = tuple((int(point.attrib["x"]), int(point.attrib["y"])) for point in root.findall("point"))
    if len(vertices) < 3 or len(vertices) != int(root.attrib["num-points"]):
        raise ValueError(f"QUT {camera} ROI vertex count mismatch")
    if any(x < 0 or y < 0 or x >= width or y >= height for x, y in vertices):
        raise ValueError(f"QUT {camera} ROI vertex outside image")
    return width, height, vertices


def parse_dots(data: bytes, name: str) -> tuple[tuple[int, int], ...]:
    points = []
    for number, line in enumerate(data.decode("ascii").splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"Unexpected dot annotation at {name}:{number}")
        points.append((int(parts[0]), int(parts[1])))
    return tuple(points)


def prepare(archive: Path, permission_record: Path, output_root: Path) -> dict[str, object]:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow is required to verify QUT images") from exc

    archive, permission_record, output_root = archive.resolve(), permission_record.resolve(), output_root.resolve()
    if output_root.exists() or not outside_git(output_root):
        raise ValueError("Output root must be new and outside every Git worktree")
    if not permission_record.is_file():
        raise FileNotFoundError(permission_record)
    if archive.stat().st_size != ARCHIVE_BYTES or sha256_file(archive) != ARCHIVE_SHA256:
        raise ValueError("Publisher archive size or SHA-256 does not match the reviewed source")

    gt: dict[tuple[str, int], bytes] = {}
    images: set[tuple[str, int]] = set()
    roi_bytes: dict[str, bytes] = {}
    with tarfile.open(archive, mode="r|gz") as package:
        for member in package:
            if not member.isfile():
                continue
            gt_match, image_match = GT_PATTERN.fullmatch(member.name), IMAGE_PATTERN.fullmatch(member.name)
            if gt_match:
                key = (gt_match[1], int(gt_match[2]))
                if key in gt:
                    raise ValueError(f"Duplicate GT member: {member.name}")
                gt[key] = package.extractfile(member).read()
            elif image_match:
                key = (image_match[1], int(image_match[2]))
                if key in images:
                    raise ValueError(f"Duplicate image member: {member.name}")
                images.add(key)
            elif member.name in {f"{ROOT}/{camera}/roi.xml" for camera in CAMERAS}:
                camera = member.name.split("/")[-2]
                if camera in roi_bytes:
                    raise ValueError(f"Duplicate ROI XML for QUT {camera}")
                roi_bytes[camera] = package.extractfile(member).read()

    if set(roi_bytes) != set(CAMERAS) or not gt or not set(gt).issubset(images):
        raise ValueError("Missing QUT camera ROI, annotation, or matching image")
    roi = {camera: parse_roi(roi_bytes[camera], camera) for camera in CAMERAS}
    if {dimensions[:2] for dimensions in roi.values()} != {(704, 576)}:
        raise ValueError("Unexpected QUT camera ROI dimensions")
    selected = sorted(gt, key=lambda key: (key[0], key[1]))
    if len(selected) != 153 or {camera: sum(key[0] == camera for key in selected) for camera in CAMERAS} != {"A": 53, "B": 50, "C": 50}:
        raise ValueError("QUT annotated-frame inventory differs from the reviewed archive")

    output_root.mkdir(parents=True)
    frames_root = output_root / "frames"
    for camera in CAMERAS:
        (frames_root / camera).mkdir(parents=True)
    selected_set = set(selected)
    image_sha: dict[tuple[str, int], str] = {}
    with tarfile.open(archive, mode="r|gz") as package:
        for member in package:
            match = IMAGE_PATTERN.fullmatch(member.name)
            if not match or not member.isfile():
                continue
            key = (match[1], int(match[2]))
            if key not in selected_set:
                continue
            data = package.extractfile(member).read()
            with Image.open(io.BytesIO(data)) as image:
                if image.size != roi[key[0]][:2]:
                    raise ValueError(f"Image and ROI dimensions disagree: {member.name}")
                image.verify()
            destination = frames_root / key[0] / f"{key[1]:08d}.jpg"
            destination.write_bytes(data)
            image_sha[key] = sha256_bytes(data)
    if set(image_sha) != selected_set:
        raise ValueError("Not every annotated QUT image was extracted")

    annotation_digest = hashlib.sha256()
    for key in selected:
        annotation_digest.update(f"{key[0]}/{key[1]:08d}.txt\0".encode("ascii"))
        annotation_digest.update(gt[key])
    for camera in CAMERAS:
        annotation_digest.update(f"{camera}/roi.xml\0".encode("ascii"))
        annotation_digest.update(roi_bytes[camera])
    selection_id = "qut-all-annotated-3-camera-v1"
    selected_at = datetime.now(timezone.utc).isoformat()
    permission_sha = sha256_file(permission_record)
    samples, labels, camera_summary = [], [], {}
    for camera in CAMERAS:
        camera_summary[camera] = {"annotated_frames": 0, "raw_dots": 0, "roi_dots": 0, "excluded_dots": 0}
    for camera, source_index in selected:
        _, _, vertices = roi[camera]
        dots = parse_dots(gt[camera, source_index], f"{camera}/{source_index:08d}.txt")
        included = tuple((x, y) for x, y in dots if in_polygon(x, y, vertices))
        summary = camera_summary[camera]
        summary["annotated_frames"] += 1
        summary["raw_dots"] += len(dots)
        summary["roi_dots"] += len(included)
        summary["excluded_dots"] += len(dots) - len(included)
        shared = {"sequence_id": f"QUT-{camera}", "frame_id": source_index + 1,
                  "source_frame_index": source_index, "image_sha256": image_sha[camera, source_index]}
        samples.append({**shared, "image_path": f"{camera}/{source_index:08d}.jpg", "stratum": f"qut_camera_{camera}"})
        labels.append({**shared, "complete": True, "reviewer": "QUT publisher dots filtered by publisher ROI; no independent human re-review", "person_count": len(included)})

    manifest = {
        "schema_version": 1, "dataset_id": selection_id, "source_id": "SAIVT-QUT-2012",
        "source_page": "https://researchdatafinder.qut.edu.au/individual/n1251",
        "source_sha256": ARCHIVE_SHA256, "source_archive_bytes": ARCHIVE_BYTES,
        "annotation_file_sha256": annotation_digest.hexdigest(), "split": "diagnostic",
        "width": 704, "height": 576,
        "evaluation_protocol": {"split_unit": "sequence", "test_partition_id": selection_id,
            "selection_locked_before_predictions": True,
            "selection_rule": "All publisher-annotated frames from QUT cameras A, B, and C; no model-based selection or threshold tuning; each camera remains intact."},
        "selection_locked_at_utc": selected_at,
        "data_permission": {"status": "approved", "permitted_uses": ["model_evaluation", "annotation_transformation"],
            "evidence_ref": str(permission_record), "evidence_sha256": permission_sha,
            "reviewer_id": "CrowdSight AI/ML lead — user-authorized private noncommercial evaluation"},
        "dataset_license_status": "CC_BY_SA_3_0_AUSTRALIA",
        "frame_timestamp_status": "publisher supplies source frame indices, not capture timestamps",
        "roi_by_sequence_id": {f"QUT-{camera}": {"vertices_xy": [list(point) for point in roi[camera][2]],
            "roi_xml_sha256": sha256_bytes(roi_bytes[camera])} for camera in CAMERAS},
        "samples": samples,
    }
    label_document = {
        "schema_version": 1, "dataset_id": selection_id, "source_sha256": ARCHIVE_SHA256,
        "label_semantics": "Publisher person-location dots inside camera ROI; count-only, no person boxes",
        "annotation_transformation": {"script_sha256": sha256_file(Path(__file__).resolve()),
            "publisher_annotation_and_roi_sha256": annotation_digest.hexdigest(),
            "roi_boundary_inclusive": True, "independent_human_review": False,
            "camera_summary": camera_summary},
        "frames": labels,
    }
    manifest_path, labels_path = output_root / "manifest.json", output_root / "labels.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    labels_path.write_text(json.dumps(label_document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"selected_frames": len(selected), "camera_summary": camera_summary,
        "manifest_sha256": sha256_file(manifest_path), "labels_sha256": sha256_file(labels_path),
        "source_sha256": ARCHIVE_SHA256, "output_root": str(output_root)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--permission-record", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.archive, args.permission_record, args.output_root), indent=2))


if __name__ == "__main__":
    main()
