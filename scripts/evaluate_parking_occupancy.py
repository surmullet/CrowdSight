"""Evaluate per-space parking occupancy against reviewed frame labels.

The input format is documented in docs/evaluation/parking-evaluation-format.md.
This reports descriptive metrics and never makes a deployment decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

STATES = ("OCCUPIED", "AVAILABLE")
ALL_STATES = (*STATES, "UNKNOWN")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _valid_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        char in "0123456789abcdefABCDEF" for char in value
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
    if digest is not None and not _valid_hash(digest):
        raise ValueError("Manifest data_permission.evidence_sha256 is invalid")
    if reviewer is not None and (not isinstance(reviewer, str) or not reviewer.strip()):
        raise ValueError("Manifest data_permission.reviewer_id must be nonempty or null")
    eligible = (
        status == "approved" and "model_evaluation" in uses
        and isinstance(ref, str) and bool(ref.strip())
        and _valid_hash(digest)
        and isinstance(reviewer, str) and bool(reviewer.strip())
    )
    return {
        "status": status,
        "permitted_uses": uses,
        "evidence_ref": ref,
        "evidence_sha256": digest.lower() if _valid_hash(digest) else None,
        "reviewer_id": reviewer,
        "metadata_eligible": eligible,
        "review_state": "NOT_VERIFIED_BY_EVALUATOR_REVIEW_REQUIRED" if eligible else "NOT_ESTABLISHED",
    }


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def evaluate(manifest: Any, labels: Any, predictions: Any) -> dict[str, Any]:
    for value, name in ((manifest, "manifest"), (labels, "labels"), (predictions, "predictions")):
        if not isinstance(value, dict):
            raise ValueError(f"{name} root must be an object")
    if manifest.get("schema_version") != 1 or labels.get("schema_version") != 1 or predictions.get("schema_version") != 1:
        raise ValueError("All input schema_version values must be 1")
    if manifest.get("split") not in ("diagnostic", "test", "held_out"):
        raise ValueError("Manifest split must be diagnostic, test, or held_out")
    for key in ("dataset_id", "site_id", "camera_view_id", "space_layout_version", "partition_id"):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            raise ValueError(f"Manifest {key} must be a nonempty string")
    source_hash = manifest.get("source_sha256")
    if not _valid_hash(source_hash):
        raise ValueError("Manifest source_sha256 must be a SHA-256 digest")
    permission_evidence = _permission_evidence(manifest)
    protocol = manifest.get("evaluation_protocol")
    if not isinstance(protocol, dict):
        raise ValueError("Manifest evaluation_protocol must be an object")
    if protocol.get("split_unit") not in ("date", "site", "camera", "camera_date"):
        raise ValueError("Parking evaluation must be partitioned by date/site/camera/camera_date")
    locked = protocol.get("selection_locked_before_predictions") is True
    for document, name in ((labels, "labels"), (predictions, "predictions")):
        if document.get("dataset_id") != manifest["dataset_id"]:
            raise ValueError(f"{name} dataset_id does not match manifest")
        if document.get("site_id") != manifest["site_id"]:
            raise ValueError(f"{name} site_id does not match manifest")
        if not _valid_hash(document.get("source_sha256")) or document["source_sha256"].lower() != source_hash.lower():
            raise ValueError(f"{name} source_sha256 does not match manifest")
        if document.get("space_layout_version") != manifest["space_layout_version"]:
            raise ValueError(f"{name} space_layout_version does not match manifest")

    samples = manifest.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("Manifest samples must be a nonempty array")
    by_frame: dict[int, dict[str, Any]] = {}
    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError("Each sample must be an object")
        index = sample.get("frame_index")
        time_s = sample.get("media_time_s")
        if type(index) is not int or index < 0 or index in by_frame:
            raise ValueError("Sample frame_index values must be unique nonnegative integers")
        if type(time_s) not in (int, float) or not math.isfinite(time_s) or time_s < 0:
            raise ValueError("Sample media_time_s must be finite and nonnegative")
        by_frame[index] = sample

    configured_spaces = manifest.get("space_ids")
    if not isinstance(configured_spaces, list) or not configured_spaces or any(
        not isinstance(value, str) or not value.strip() for value in configured_spaces
    ) or len(configured_spaces) != len(set(configured_spaces)):
        raise ValueError("Manifest space_ids must be a nonempty unique string array")
    expected_spaces = set(configured_spaces)

    def index_rows(document: dict[str, Any], field: str, kind: str) -> dict[int, dict[str, Any]]:
        rows = document.get(field)
        if not isinstance(rows, list):
            raise ValueError(f"{kind} must contain a {field} array")
        indexed: dict[int, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"Each {kind} frame must be an object")
            index = row.get("frame_index")
            if type(index) is not int or index not in by_frame or index in indexed:
                raise ValueError(f"{kind} contains an unknown or duplicate frame")
            indexed[index] = row
        if set(indexed) != set(by_frame):
            raise ValueError(f"{kind} must include every sampled frame exactly once")
        return indexed

    label_frames = index_rows(labels, "frames", "Labels")
    prediction_frames = index_rows(predictions, "frames", "Predictions")
    normalized_labels: dict[int, dict[str, str]] = {}
    normalized_predictions: dict[int, dict[str, str]] = {}
    for index, row in label_frames.items():
        if row.get("complete") is not True or not isinstance(row.get("reviewer"), str) or not row["reviewer"].strip():
            raise ValueError("Every label frame needs complete=true and a reviewer")
        spaces = row.get("spaces")
        if not isinstance(spaces, list):
            raise ValueError("Each label frame needs a spaces array")
        states = {}
        for item in spaces:
            if not isinstance(item, dict) or not isinstance(item.get("space_id"), str):
                raise ValueError("Each labelled space needs a space_id")
            space_id, state = item["space_id"], item.get("state")
            if space_id in states or space_id not in expected_spaces or state not in ALL_STATES:
                raise ValueError("Labels contain duplicate/unknown space IDs or invalid state")
            states[space_id] = state
        if set(states) != expected_spaces:
            raise ValueError("Every frame label must cover every configured space")
        normalized_labels[index] = states

    for index, row in prediction_frames.items():
        time_s = row.get("media_time_s")
        if type(time_s) not in (int, float) or not math.isfinite(time_s) or time_s != by_frame[index]["media_time_s"]:
            raise ValueError("Prediction media_time_s must match the sampled frame")
        spaces = row.get("spaces")
        if not isinstance(spaces, list):
            raise ValueError("Each prediction frame needs a spaces array")
        states = {}
        for item in spaces:
            if not isinstance(item, dict) or not isinstance(item.get("space_id"), str):
                raise ValueError("Each predicted space needs a space_id")
            space_id, state = item["space_id"], item.get("state")
            if space_id in states or space_id not in expected_spaces or state not in ALL_STATES:
                raise ValueError("Predictions contain duplicate/unknown space IDs or invalid state")
            confidence = item.get("confidence")
            if confidence is not None and (
                type(confidence) not in (int, float) or not math.isfinite(confidence) or not 0 <= confidence <= 1
            ):
                raise ValueError("Prediction confidence must be null or a finite value in [0,1]")
            if state == "UNKNOWN" and confidence is not None:
                raise ValueError("UNKNOWN predictions must have null confidence")
            evidence_time_s = item.get("evidence_time_s")
            if (
                type(evidence_time_s) not in (int, float)
                or not math.isfinite(evidence_time_s)
                or evidence_time_s != time_s
            ):
                raise ValueError("Each parking-space evidence_time_s must match its frame media_time_s")
            states[space_id] = state
        if set(states) != expected_spaces:
            raise ValueError("Every prediction frame must cover every configured space")
        normalized_predictions[index] = states

    # Unknown manual labels are excluded above; keep truth rows to the two
    # evaluable states while retaining UNKNOWN as a prediction/abstention column.
    confusion = {truth: {pred: 0 for pred in ALL_STATES} for truth in STATES}
    evaluated = 0
    unknown_truth = 0
    abstentions = 0
    per_space: dict[str, dict[str, int]] = {
        space_id: {"correct": 0, "known_truth": 0, "unknown_truth": 0, "abstained": 0}
        for space_id in configured_spaces
    }
    count_errors: list[int] = []
    count_truths: list[int] = []
    available_truths: list[int] = []
    excluded_count_frames: list[int] = []
    for index in by_frame:
        truths = normalized_labels[index]
        preds = normalized_predictions[index]
        for space_id in configured_spaces:
            truth, pred = truths[space_id], preds[space_id]
            if truth == "UNKNOWN":
                unknown_truth += 1
                per_space[space_id]["unknown_truth"] += 1
                continue
            per_space[space_id]["known_truth"] += 1
            confusion[truth][pred] += 1
            evaluated += 1
            if pred == "UNKNOWN":
                abstentions += 1
                per_space[space_id]["abstained"] += 1
            elif pred == truth:
                per_space[space_id]["correct"] += 1
        if all(truths[sid] != "UNKNOWN" and preds[sid] != "UNKNOWN" for sid in configured_spaces):
            truth_count = sum(truths[sid] == "OCCUPIED" for sid in configured_spaces)
            pred_count = sum(preds[sid] == "OCCUPIED" for sid in configured_spaces)
            count_errors.append(pred_count - truth_count)
            count_truths.append(truth_count)
            available_truths.append(len(configured_spaces) - truth_count)
        else:
            excluded_count_frames.append(index)

    class_metrics = {}
    for state in STATES:
        tp = confusion[state][state]
        fp = sum(confusion[other][state] for other in STATES if other != state)
        fn = sum(confusion[state][other] for other in ALL_STATES if other != state)
        precision, recall = _ratio(tp, tp + fp), _ratio(tp, tp + fn)
        class_metrics[state] = {
            "precision": precision,
            "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None,
        }
    training = predictions.get("training_evidence", {})
    if not isinstance(training, dict):
        raise ValueError("training_evidence must be an object")
    training_hashes = training.get("source_sha256s", [])
    training_partitions = training.get("partition_ids", [])
    inventory_hash = training.get("manifest_sha256")
    complete_inventory = training.get("source_inventory_complete") is True
    if inventory_hash is not None and not _valid_hash(inventory_hash):
        raise ValueError("training_evidence.manifest_sha256 must be a SHA-256 digest")
    if not isinstance(training_hashes, list) or any(not _valid_hash(item) for item in training_hashes):
        raise ValueError("training_evidence.source_sha256s must be SHA-256 digests")
    if not isinstance(training_partitions, list) or any(not isinstance(item, str) or not item.strip() for item in training_partitions):
        raise ValueError("training_evidence.partition_ids must be nonempty strings")
    if len({item.lower() for item in training_hashes}) != len(training_hashes):
        raise ValueError("training_evidence.source_sha256s contains duplicate hashes")
    if len(set(training_partitions)) != len(training_partitions):
        raise ValueError("training_evidence.partition_ids contains duplicates")
    hash_overlap = source_hash.lower() in {item.lower() for item in training_hashes}
    partition_overlap = manifest["partition_id"] in training_partitions
    overlap_status = training.get("overlap_status", "unknown_or_mixed")
    if overlap_status not in ("verified_disjoint", "verified_overlap", "overlap_possible", "unknown_or_mixed"):
        raise ValueError("Invalid training overlap status")
    evidence_ref = training.get("independence_evidence_ref")
    evidence_sha = training.get("independence_evidence_sha256")
    if evidence_ref is not None and (not isinstance(evidence_ref, str) or not evidence_ref.strip()):
        raise ValueError("training_evidence.independence_evidence_ref must be nonempty or null")
    if evidence_sha is not None and not _valid_hash(evidence_sha):
        raise ValueError("training_evidence.independence_evidence_sha256 must be a SHA-256 digest")
    if overlap_status == "verified_disjoint" and (
        not complete_inventory or not training_hashes or not training_partitions
        or not _valid_hash(inventory_hash)
        or not isinstance(evidence_ref, str) or not evidence_ref.strip()
        or not _valid_hash(evidence_sha)
        or hash_overlap or partition_overlap
    ):
        raise ValueError(
            "verified_disjoint requires a complete nonempty hash-identified source/partition inventory, "
            "training-manifest and independence-evidence hashes, and no exact test overlap"
        )
    if overlap_status == "verified_overlap" and not (hash_overlap or partition_overlap):
        raise ValueError("Training evidence claims confirmed overlap but no source/partition overlap is recorded")
    model = predictions.get("model")
    if not isinstance(model, dict) or not isinstance(model.get("profile_id"), str) or not model["profile_id"].strip():
        raise ValueError("Predictions must identify a model profile")
    for key in ("site_id", "camera_view_id", "space_layout_version"):
        if model.get(key) != manifest[key]:
            raise ValueError(f"Predictions model {key} does not match manifest")
    for key in ("profile_sha256", "checkpoint_sha256"):
        if not _valid_hash(model.get(key)):
            raise ValueError(f"Predictions model.{key} must be a SHA-256 digest")
    held_out_candidate = (
        manifest["split"] in ("test", "held_out") and locked
        and overlap_status == "verified_disjoint" and not hash_overlap and not partition_overlap
        and complete_inventory and _valid_hash(inventory_hash)
        and bool(training_hashes) and bool(training_partitions)
        and isinstance(evidence_ref, str) and bool(evidence_ref.strip())
        and _valid_hash(evidence_sha)
        and permission_evidence["metadata_eligible"]
    )
    count_mae = sum(abs(error) for error in count_errors) / len(count_errors) if count_errors else None
    count_bias = sum(count_errors) / len(count_errors) if count_errors else None
    count_rmse = math.sqrt(sum(error * error for error in count_errors) / len(count_errors)) if count_errors else None
    percentage_errors = [abs(error) / truth for error, truth in zip(count_errors, count_truths) if truth > 0]
    count_mape = sum(percentage_errors) / len(percentage_errors) if percentage_errors else None
    available_percentage_errors = [
        abs(error) / available
        for error, available in zip(count_errors, available_truths)
        if available > 0
    ]
    return {
        "scope": (
            "TRAINING_FIT_PARKING_EVALUATION_OVERLAP_CONFIRMED"
            if overlap_status == "verified_overlap" or hash_overlap or partition_overlap
            else "HELD_OUT_CANDIDATE_REQUIRES_MANUAL_EVIDENCE_REVIEW"
            if held_out_candidate
            else "EXPLORATORY_PARKING_EVALUATION_DISJOINTNESS_RECORDED"
            if overlap_status == "verified_disjoint"
            else "EXPLORATORY_PARKING_EVALUATION_OVERLAP_UNVERIFIED"
        ),
        "dataset_id": manifest["dataset_id"],
        "split": manifest["split"],
        "site_id": manifest["site_id"],
        "space_layout_version": manifest["space_layout_version"],
        "partition_id": manifest["partition_id"],
        "source_sha256": source_hash.lower(),
        "data_permission": permission_evidence,
        "evaluation_protocol": {
            "split_unit": protocol["split_unit"],
            "selection_locked_before_predictions": locked,
        },
        "training_overlap_status": (
            "verified_overlap" if overlap_status == "verified_overlap" or hash_overlap or partition_overlap else overlap_status
        ),
        "training_manifest_sha256": inventory_hash.lower() if _valid_hash(inventory_hash) else None,
        "training_source_inventory_complete": complete_inventory,
        "training_source_sha256s": [item.lower() for item in training_hashes],
        "training_partition_ids": list(training_partitions),
        "source_overlap_detected": bool(hash_overlap),
        "partition_overlap_detected": bool(partition_overlap),
        "independence_evidence_ref": evidence_ref,
        "independence_evidence_sha256": evidence_sha.lower() if _valid_hash(evidence_sha) else None,
        "independence_evidence_review_state": (
            "NOT_VERIFIED_BY_EVALUATOR_REVIEW_REQUIRED" if held_out_candidate else "NOT_ESTABLISHED"
        ),
        "release_approval": False,
        "frames": len(by_frame),
        "configured_spaces": len(expected_spaces),
        "known_label_space_observations": evaluated,
        "unknown_label_space_observations": unknown_truth,
        "prediction_abstentions": abstentions,
        "prediction_abstention_rate_on_known_labels": _ratio(abstentions, evaluated),
        "known_prediction_coverage_on_known_labels": _ratio(evaluated - abstentions, evaluated),
        "confusion_matrix": confusion,
        "per_class": class_metrics,
        "per_space": {
            space_id: {
                **counts,
                "accuracy_on_non_unknown_labels": _ratio(counts["correct"], counts["known_truth"] - counts["abstained"]),
                "abstention_rate": _ratio(counts["abstained"], counts["known_truth"]),
            }
            for space_id, counts in per_space.items()
        },
        "occupied_space_count_error": {
            "frames": len(count_errors),
            "excluded_frame_indices": excluded_count_frames,
            "mae": count_mae,
            "rmse": count_rmse,
            "bias": count_bias,
            "mape_nonzero_truth_only": count_mape,
            "frames_with_zero_occupied_truth_excluded_from_mape": sum(truth == 0 for truth in count_truths),
        },
        "available_space_count_error": {
            "frames": len(count_errors),
            "mae": count_mae,
            "rmse": count_rmse,
            "bias": -count_bias if count_bias is not None else None,
            "mape_nonzero_truth_only": (
                sum(available_percentage_errors) / len(available_percentage_errors)
                if available_percentage_errors else None
            ),
            "frames_with_zero_available_truth_excluded_from_mape": sum(
                available == 0 for available in available_truths
            ),
        },
        "model": model,
        "runtime": predictions.get("runtime"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    inputs = [args.manifest, args.labels, args.predictions]
    values = [json.loads(path.read_text(encoding="utf-8")) for path in inputs]
    report = evaluate(*values)
    report["input_sha256"] = {path.stem: _sha256(path) for path in inputs}
    report["evaluator_script_sha256"] = _sha256(Path(__file__).resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "EVALUATED", "report": str(args.output)}))


if __name__ == "__main__":
    main()
