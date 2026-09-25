"""Score person boxes/counts against reviewed diagnostic or test manifests.

Input schemas are documented in docs/evaluation/crowd-evaluation-format.md.
Metrics are descriptive evidence; this script does not set acceptance limits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdefABCDEF" for char in value)
    )


def _permission_evidence(manifest: dict[str, Any]) -> dict[str, Any]:
    """Read permission-review metadata without authenticating its artifact."""
    evidence = manifest.get("data_permission")
    if evidence is None:
        evidence = {}
    if not isinstance(evidence, dict):
        raise ValueError("Manifest data_permission must be an object")
    status = evidence.get("status", "unknown")
    if status not in ("approved", "pending", "denied", "unknown"):
        raise ValueError("Manifest data_permission.status is invalid")
    uses = evidence.get("permitted_uses", [])
    if not isinstance(uses, list) or any(not isinstance(use, str) or not use.strip() for use in uses):
        raise ValueError("Manifest data_permission.permitted_uses must be an array of nonempty strings")
    if len(uses) != len(set(uses)):
        raise ValueError("Manifest data_permission.permitted_uses contains duplicates")
    ref, digest, reviewer = (
        evidence.get("evidence_ref"),
        evidence.get("evidence_sha256"),
        evidence.get("reviewer_id"),
    )
    if ref is not None and (not isinstance(ref, str) or not ref.strip()):
        raise ValueError("Manifest data_permission.evidence_ref must be nonempty or null")
    if digest is not None and not _is_sha256(digest):
        raise ValueError("Manifest data_permission.evidence_sha256 is invalid")
    if reviewer is not None and (not isinstance(reviewer, str) or not reviewer.strip()):
        raise ValueError("Manifest data_permission.reviewer_id must be nonempty or null")
    eligible = (
        status == "approved" and "model_evaluation" in uses
        and isinstance(ref, str) and bool(ref.strip())
        and _is_sha256(digest)
        and isinstance(reviewer, str) and bool(reviewer.strip())
    )
    return {
        "status": status,
        "permitted_uses": uses,
        "evidence_ref": ref,
        "evidence_sha256": digest.lower() if _is_sha256(digest) else None,
        "reviewer_id": reviewer,
        "metadata_eligible": eligible,
        "review_state": "NOT_VERIFIED_BY_EVALUATOR_REVIEW_REQUIRED" if eligible else "NOT_ESTABLISHED",
    }


def _box(value: Any, width: int, height: int, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(f"{label} must be a four-value bbox_xyxy list")
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in value):
        raise ValueError(f"{label} must contain finite numeric coordinates")
    x1, y1, x2, y2 = (float(v) for v in value)
    if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
        raise ValueError(f"{label} lies outside image bounds or has zero area")
    return [x1, y1, x2, y2]


def _iou(a: list[float], b: list[float]) -> float:
    overlap = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(
        0.0, min(a[3], b[3]) - max(a[1], b[1])
    )
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return overlap / (area_a + area_b - overlap)


def _match_pairs(
    predicted: list[list[float]], truth: list[list[float]], threshold: float
) -> list[tuple[int, int]]:
    """Maximum-cardinality prediction/truth pairs under the requested IoU rule."""
    edges = [
        sorted(
            (j for j, box in enumerate(truth) if _iou(candidate, box) >= threshold),
            key=lambda j: _iou(candidate, truth[j]),
            reverse=True,
        )
        for candidate in predicted
    ]
    owners: dict[int, int] = {}

    def augment(pred_index: int, visited: set[int]) -> bool:
        for truth_index in edges[pred_index]:
            if truth_index in visited:
                continue
            visited.add(truth_index)
            if truth_index not in owners or augment(owners[truth_index], visited):
                owners[truth_index] = pred_index
                return True
        return False

    for index in range(len(predicted)):
        augment(index, set())
    return [(prediction_index, truth_index) for truth_index, prediction_index in owners.items()]


def _match_count(predicted: list[list[float]], truth: list[list[float]], threshold: float) -> int:
    """Maximum-cardinality bipartite match count under the requested IoU rule."""
    return len(_match_pairs(predicted, truth, threshold))


def _inside(point: tuple[float, float], polygon: list[list[float]]) -> bool:
    x, y = point
    inside = False
    for (ax, ay), (bx, by) in zip(polygon, polygon[1:] + polygon[:1]):
        cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax)
        if (
            abs(cross) < 1e-9
            and min(ax, bx) <= x <= max(ax, bx)
            and min(ay, by) <= y <= max(ay, by)
        ):
            return True
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            inside = not inside
    return inside


def _count_metrics(errors: list[int]) -> dict[str, float | int]:
    if not errors:
        raise ValueError("No valid labelled predictions available for count metrics")
    return {
        "n": len(errors),
        "mae": sum(abs(error) for error in errors) / len(errors),
        "rmse": math.sqrt(sum(error * error for error in errors) / len(errors)),
        "bias": sum(errors) / len(errors),
    }


def _detection_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tp = sum(row["tp"] for row in rows)
    fp = sum(row["fp"] for row in rows)
    fn = sum(row["fn"] for row in rows)
    errors = [row["count_error"] for row in rows if row["count_error"] is not None]
    return {
        "frames": len(rows),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "count": _count_metrics(errors) if errors else None,
        "frames_eligible_for_count_metrics": len(errors),
        "ignored_uncertain_region_predictions": sum(
            row["ignored_uncertain_region_predictions"] for row in rows
        ),
    }


def evaluate(manifest: dict[str, Any], labels: dict[str, Any], predictions: dict[str, Any], iou_threshold: float = 0.5) -> dict[str, Any]:
    """Validate matching data lineage and calculate full-frame/zone metrics."""
    for document, name in ((manifest, "manifest"), (labels, "labels"), (predictions, "predictions")):
        if not isinstance(document, dict):
            raise ValueError(f"{name} root must be an object")
    if manifest.get("schema_version") != 1:
        raise ValueError("Manifest schema_version must be 1")
    if manifest.get("split") not in ("diagnostic", "test", "held_out"):
        raise ValueError("Evaluation manifest split must be 'diagnostic', 'test', or 'held_out'")
    for name in ("dataset_id", "source_id"):
        if not isinstance(manifest.get(name), str) or not manifest[name].strip():
            raise ValueError(f"Manifest {name} must be a nonempty string")
    if not _is_sha256(manifest.get("source_sha256")):
        raise ValueError("Manifest source_sha256 must be a 64-character hex digest")
    permission_evidence = _permission_evidence(manifest)
    if not 0.0 < iou_threshold <= 1.0:
        raise ValueError("IoU threshold must be in (0, 1]")
    for document, name in ((labels, "labels"), (predictions, "predictions")):
        if document.get("schema_version") != 1:
            raise ValueError(f"{name} schema_version must be 1")
        if document.get("dataset_id") != manifest.get("dataset_id"):
            raise ValueError(f"{name} dataset_id does not match manifest")
        if not isinstance(document.get("source_sha256"), str) or document["source_sha256"].lower() != manifest["source_sha256"].lower():
            raise ValueError(f"{name} source_sha256 does not match manifest")
    width, height = manifest.get("width"), manifest.get("height")
    if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
        raise ValueError("Manifest image dimensions must be positive")
    samples = manifest.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("Manifest must contain selected samples")
    protocol = manifest.get("evaluation_protocol", {})
    if not isinstance(protocol, dict):
        raise ValueError("Manifest evaluation_protocol must be an object")
    split_unit = protocol.get("split_unit")
    partition_id = protocol.get("test_partition_id")
    selection_locked = protocol.get("selection_locked_before_predictions") is True
    if split_unit not in ("video", "site", "flight", "camera_date"):
        raise ValueError("Manifest evaluation_protocol.split_unit must name a video/site/flight/camera_date partition")
    if not isinstance(partition_id, str) or not partition_id.strip():
        raise ValueError("Manifest evaluation_protocol.test_partition_id must be nonempty")
    sample_by_frame = {}
    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError("Each manifest sample must be an object")
        frame_index = sample.get("frame_index")
        media_time_s = sample.get("media_time_s")
        stratum = sample.get("stratum", "unstratified")
        if type(frame_index) is not int or frame_index < 0:
            raise ValueError("Sample frame_index must be a nonnegative integer")
        if type(media_time_s) not in (int, float) or not math.isfinite(media_time_s) or media_time_s < 0:
            raise ValueError("Sample media_time_s must be finite and nonnegative")
        if not isinstance(stratum, str) or not stratum.strip():
            raise ValueError("Sample stratum must be a nonempty string")
        sample_by_frame[frame_index] = sample
    if len(sample_by_frame) != len(samples):
        raise ValueError("Manifest frame indices must be unique")

    label_rows: dict[int, dict[str, Any]] = {}
    label_frames = labels.get("frames")
    if not isinstance(label_frames, list):
        raise ValueError("Labels must contain a frames array")
    for row in label_frames:
        if not isinstance(row, dict):
            raise ValueError("Each label frame must be an object")
        frame_index = row.get("frame_index")
        if type(frame_index) is not int or frame_index not in sample_by_frame or frame_index in label_rows:
            raise ValueError("Labels contain an unknown or duplicate frame")
        if row.get("complete") is not True or not str(row.get("reviewer", "")).strip():
            raise ValueError("Every scored frame must have a complete manual review and reviewer")
        boxes = row.get("boxes")
        if not isinstance(boxes, list):
            raise ValueError("Each reviewed frame requires a boxes list; empty means reviewed zero")
        normalized = []
        uncertain_boxes = []
        for item in boxes:
            if not isinstance(item, dict) or type(item.get("uncertain")) is not bool:
                raise ValueError("Each manual box must include a boolean uncertain field")
            normalized_box = _box(item.get("bbox_xyxy"), width, height, "manual box")
            (uncertain_boxes if item["uncertain"] else normalized).append(normalized_box)
        label_rows[frame_index] = {"boxes": normalized, "uncertain_boxes": uncertain_boxes}
    if set(label_rows) != set(sample_by_frame):
        raise ValueError("Label export must include every selected frame and review status")

    zone_polygons = manifest.get("zone_polygons_normalized", {})
    if not isinstance(zone_polygons, dict):
        raise ValueError("zone_polygons_normalized must be an object")
    for zone_id, polygon in zone_polygons.items():
        if not isinstance(polygon, list) or len(polygon) < 3:
            raise ValueError(f"Zone {zone_id} must contain at least three vertices")
        for point in polygon:
            if (
                not isinstance(point, list)
                or len(point) != 2
                or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in point)
            ):
                raise ValueError(f"Zone {zone_id} has invalid normalized coordinates")

    models = predictions.get("models")
    if not isinstance(models, dict) or not models:
        raise ValueError("Predictions must contain at least one named model")
    output: dict[str, Any] = {
        "scope": "MANUAL_LABEL_EVALUATION",
        "dataset_id": manifest["dataset_id"],
        "source_sha256": manifest["source_sha256"],
        "split": manifest["split"],
        "data_permission": permission_evidence,
        "evaluation_protocol": {
            "split_unit": split_unit,
            "test_partition_id": partition_id,
            "selection_locked_before_predictions": selection_locked,
        },
        "iou_threshold": iou_threshold,
        "matching": "maximum_cardinality_bipartite",
        "zone_anchor": "bbox_bottom_center_normalized; boundary_inside",
        "inference_script_sha256": predictions.get("inference_script_sha256"),
        "reviewed_frames": len(samples),
        "models": {},
    }

    for model_id, model in models.items():
        if not isinstance(model_id, str) or not model_id.strip() or not isinstance(model, dict):
            raise ValueError("Each prediction model must have a nonempty name and object value")
        if (
            model.get("profile_id") is None
            or model.get("profile_sha256") is None
            or model.get("checkpoint_sha256") is None
        ):
            raise ValueError(
                f"Model {model_id} must record profile_id, profile_sha256, and checkpoint_sha256"
            )
        profile_sha = str(model["profile_sha256"])
        if not _is_sha256(profile_sha):
            raise ValueError(f"Model {model_id} profile_sha256 is invalid")
        checkpoint_sha = str(model["checkpoint_sha256"])
        if not _is_sha256(checkpoint_sha):
            raise ValueError(f"Model {model_id} checkpoint_sha256 is invalid")
        overlap_status = model.get("training_overlap_status", "unknown_or_mixed")
        if overlap_status not in ("verified_disjoint", "verified_overlap", "overlap_possible", "unknown_or_mixed"):
            raise ValueError(f"Model {model_id} training_overlap_status is invalid")
        independence_evidence = model.get("independence_evidence_ref")
        independence_evidence_sha = model.get("independence_evidence_sha256")
        if independence_evidence_sha is not None and not _is_sha256(independence_evidence_sha):
            raise ValueError(f"Model {model_id} independence_evidence_sha256 is invalid")
        training_hashes = model.get("training_source_sha256s")
        training_partitions = model.get("training_partition_ids")
        training_inventory_complete = model.get("training_source_inventory_complete") is True
        training_manifest_sha = model.get("training_manifest_sha256")
        valid_training_hashes = (
            isinstance(training_hashes, list)
            and all(
                isinstance(value, str)
                and len(value) == 64
                and all(char in "0123456789abcdefABCDEF" for char in value)
                for value in training_hashes
            )
        )
        valid_training_partitions = (
            isinstance(training_partitions, list)
            and all(isinstance(value, str) and value.strip() for value in training_partitions)
        )
        valid_training_manifest_hash = (
            isinstance(training_manifest_sha, str)
            and len(training_manifest_sha) == 64
            and all(char in "0123456789abcdefABCDEF" for char in training_manifest_sha)
        )
        if training_hashes is not None and not valid_training_hashes:
            raise ValueError(f"Model {model_id} training_source_sha256s must contain only SHA-256 digests")
        if training_partitions is not None and not valid_training_partitions:
            raise ValueError(f"Model {model_id} training_partition_ids must contain nonempty strings")
        if training_manifest_sha is not None and not valid_training_manifest_hash:
            raise ValueError(f"Model {model_id} training_manifest_sha256 is invalid")
        if valid_training_hashes and len({value.lower() for value in training_hashes}) != len(training_hashes):
            raise ValueError(f"Model {model_id} training_source_sha256s contains duplicate hashes")
        if valid_training_partitions and len(set(training_partitions)) != len(training_partitions):
            raise ValueError(f"Model {model_id} training_partition_ids contains duplicates")
        training_evidence_file_sha = model.get("training_evidence_file_sha256")
        if training_evidence_file_sha is not None and not _is_sha256(training_evidence_file_sha):
            raise ValueError(f"Model {model_id} training_evidence_file_sha256 is invalid")
        valid_training_evidence_file_hash = _is_sha256(training_evidence_file_sha)
        source_overlap = (
            valid_training_hashes
            and manifest["source_sha256"].lower()
            in {value.lower() for value in training_hashes}
        )
        partition_overlap = (
            valid_training_partitions and partition_id in training_partitions
        )
        if overlap_status == "verified_disjoint" and (source_overlap or partition_overlap):
            raise ValueError(f"Model {model_id} claims disjoint data but overlaps the evaluation source/partition")
        if overlap_status == "verified_overlap" and not (source_overlap or partition_overlap):
            raise ValueError(f"Model {model_id} claims confirmed overlap but no source/partition overlap is recorded")
        held_out_candidate = (
            manifest.get("split") in ("test", "held_out")
            and
            selection_locked
            and overlap_status == "verified_disjoint"
            and isinstance(independence_evidence, str)
            and bool(independence_evidence.strip())
            and _is_sha256(independence_evidence_sha)
            and training_inventory_complete
            and valid_training_hashes
            and valid_training_partitions
            and bool(training_hashes)
            and bool(training_partitions)
            and valid_training_manifest_hash
            and valid_training_evidence_file_hash
            and not source_overlap
            and not partition_overlap
            and permission_evidence["metadata_eligible"]
        )
        frame_predictions = {}
        model_frames = model.get("frames")
        if not isinstance(model_frames, list):
            raise ValueError(f"Model {model_id} must contain a frames array")
        for row in model_frames:
            if not isinstance(row, dict):
                raise ValueError(f"Model {model_id} frame predictions must be objects")
            frame_index = row.get("frame_index")
            if type(frame_index) is not int or frame_index not in sample_by_frame or frame_index in frame_predictions:
                raise ValueError(f"Model {model_id} has unknown or duplicate prediction frame")
            valid = row.get("valid")
            if type(valid) is not bool:
                raise ValueError("Prediction frames must explicitly declare valid true/false")
            boxes = row.get("boxes")
            if not isinstance(boxes, list) or (not valid and boxes):
                raise ValueError("Invalid predictions must contain no boxes")
            frame_predictions[frame_index] = {
                "valid": valid,
                "boxes": [_box(box, width, height, "predicted box") for box in boxes],
            }
        if set(frame_predictions) != set(sample_by_frame):
            raise ValueError(f"Model {model_id} must account for every selected frame")

        scored_rows = []
        frames_with_uncertainty = []
        count_excluded_frames = []
        for frame_index, sample in sample_by_frame.items():
            truth_row = label_rows[frame_index]
            certain_truth = truth_row["boxes"]
            uncertain_truth = truth_row["uncertain_boxes"]
            if uncertain_truth:
                frames_with_uncertainty.append(frame_index)
                count_excluded_frames.append(frame_index)
            prediction = frame_predictions[frame_index]
            if not prediction["valid"]:
                continue
            predicted_boxes = prediction["boxes"]
            matched_certain = _match_pairs(predicted_boxes, certain_truth, iou_threshold)
            matched_prediction_indices = {prediction_index for prediction_index, _ in matched_certain}
            unmatched_predictions = [
                box for index, box in enumerate(predicted_boxes)
                if index not in matched_prediction_indices
            ]
            ignored_uncertain = _match_count(unmatched_predictions, uncertain_truth, iou_threshold)
            tp = len(matched_certain)
            count_metrics_eligible = not uncertain_truth
            row = {
                "frame_index": frame_index,
                "stratum": sample.get("stratum", "unstratified"),
                "tp": tp,
                "fp": len(predicted_boxes) - tp - ignored_uncertain,
                "fn": len(certain_truth) - tp,
                "predicted_count": len(predicted_boxes),
                "certain_truth_count": len(certain_truth),
                "uncertain_annotation_count": len(uncertain_truth),
                "ignored_uncertain_region_predictions": ignored_uncertain,
                "count_metrics_eligible": count_metrics_eligible,
                "count_error": (
                    len(predicted_boxes) - len(certain_truth)
                    if count_metrics_eligible else None
                ),
            }
            for zone_id, polygon in zone_polygons.items():
                truth_n = sum(
                    _inside(((box[0] + box[2]) / (2 * width), box[3] / height), polygon)
                    for box in certain_truth
                )
                predicted_n = sum(
                    _inside(((box[0] + box[2]) / (2 * width), box[3] / height), polygon)
                    for box in predicted_boxes
                )
                row[f"{zone_id}_truth"] = truth_n if count_metrics_eligible else None
                row[f"{zone_id}_predicted"] = predicted_n
                row[f"{zone_id}_error"] = (
                    predicted_n - truth_n if count_metrics_eligible else None
                )
            scored_rows.append(row)

        strata = sorted({row["stratum"] for row in scored_rows})
        groups = {"all": _detection_metrics(scored_rows)} if scored_rows else {}
        for stratum in strata:
            groups[f"stratum:{stratum}"] = _detection_metrics(
                [row for row in scored_rows if row["stratum"] == stratum]
            )
        zone_metrics = {}
        for zone_id in zone_polygons:
            errors = [
                row[f"{zone_id}_error"] for row in scored_rows
                if row[f"{zone_id}_error"] is not None
            ]
            zone_metrics[zone_id] = _count_metrics(errors) if errors else None
        output["models"][model_id] = {
            "profile_id": model["profile_id"],
            "profile_sha256": profile_sha.lower(),
            "checkpoint_sha256": checkpoint_sha.lower(),
            "evaluation_scope": (
                "TRAINING_FIT_MANUAL_LABEL_EVALUATION_OVERLAP_CONFIRMED"
                if source_overlap or partition_overlap
                else "HELD_OUT_CANDIDATE_REQUIRES_MANUAL_EVIDENCE_REVIEW"
                if held_out_candidate
                else "EXPLORATORY_MANUAL_LABEL_EVALUATION_OVERLAP_UNVERIFIED"
            ),
            "training_overlap_status": (
                "verified_overlap" if source_overlap or partition_overlap else overlap_status
            ),
            "source_overlap_detected": bool(source_overlap),
            "partition_overlap_detected": bool(partition_overlap),
            "independence_evidence_ref": independence_evidence,
            "independence_evidence_sha256": (
                independence_evidence_sha.lower()
                if _is_sha256(independence_evidence_sha) else None
            ),
            "independence_evidence_review_state": (
                "NOT_VERIFIED_BY_EVALUATOR_REVIEW_REQUIRED"
                if held_out_candidate else "NOT_ESTABLISHED"
            ),
            "release_approval": False,
            "training_manifest_sha256": training_manifest_sha.lower() if valid_training_manifest_hash else None,
            "training_evidence_file_sha256": training_evidence_file_sha.lower() if training_evidence_file_sha else None,
            "training_source_inventory_complete": training_inventory_complete,
            "training_source_sha256s": [value.lower() for value in training_hashes] if valid_training_hashes else [],
            "training_partition_ids": training_partitions if valid_training_partitions else [],
            "runtime": model.get("runtime"),
            "valid_prediction_frames": sum(frame["valid"] for frame in frame_predictions.values()),
            "unknown_prediction_frames": sum(not frame["valid"] for frame in frame_predictions.values()),
            "unknown_rate": sum(not frame["valid"] for frame in frame_predictions.values()) / len(samples),
            "frames_with_uncertain_annotations": frames_with_uncertainty,
            "frames_excluded_from_count_metrics": count_excluded_frames,
            "scored_frames": len(scored_rows),
            "groups": groups,
            "zone_count": zone_metrics,
            "per_frame": scored_rows,
            "tracking_and_crossing_accuracy": "NOT_EVALUATED_BY_THIS_BOX_METRIC",
        }
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--iou", type=float, default=0.5)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    labels = json.loads(args.labels.read_text(encoding="utf-8-sig"))
    predictions = json.loads(args.predictions.read_text(encoding="utf-8"))
    report = evaluate(manifest, labels, predictions, args.iou)
    report["inputs_sha256"] = {
        "manifest": _sha256(args.manifest),
        "labels": _sha256(args.labels),
        "predictions": _sha256(args.predictions),
    }
    report["evaluator_script_sha256"] = _sha256(Path(__file__).resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "EVALUATED", "report": str(args.output)}))


if __name__ == "__main__":
    main()
