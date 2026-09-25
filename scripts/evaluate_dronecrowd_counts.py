"""Score frame counts against point-annotated DroneCrowd sequences.

This scorer reports count metrics only. Head-point annotations do not support
box-IoU detection precision/recall or person localization claims.
Input format is documented in docs/evaluation/dronecrowd-candidate-evaluation.md.
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


def _valid_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        char in "0123456789abcdefABCDEF" for char in value
    )


def _count(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")
    return value


def _frame_key(row: dict[str, Any], label: str) -> tuple[str, int]:
    sequence_id, frame_id = row.get("sequence_id"), row.get("frame_id")
    if not isinstance(sequence_id, str) or not sequence_id.strip():
        raise ValueError(f"{label}.sequence_id must be a nonempty string")
    if type(frame_id) is not int or frame_id < 1:
        raise ValueError(f"{label}.frame_id must be a positive one-based integer")
    return sequence_id, frame_id


def _metrics(errors: list[int]) -> dict[str, int | float] | None:
    if not errors:
        return None
    mse = sum(error * error for error in errors) / len(errors)
    return {
        "n": len(errors),
        "mae": sum(abs(error) for error in errors) / len(errors),
        "mse": mse,
        "rmse": math.sqrt(mse),
        "bias": sum(errors) / len(errors),
    }


def _permission_status(manifest: dict[str, Any]) -> dict[str, Any]:
    evidence = manifest.get("data_permission")
    if not isinstance(evidence, dict):
        raise ValueError("Manifest data_permission must be an object")
    status = evidence.get("status")
    uses = evidence.get("permitted_uses")
    ref, digest, reviewer = (
        evidence.get("evidence_ref"),
        evidence.get("evidence_sha256"),
        evidence.get("reviewer_id"),
    )
    if status not in ("approved", "pending", "denied", "unknown"):
        raise ValueError("Manifest data_permission.status is invalid")
    if not isinstance(uses, list) or any(not isinstance(item, str) for item in uses):
        raise ValueError("Manifest data_permission.permitted_uses must be an array")
    if status == "denied":
        raise ValueError("Scoring is prohibited by the manifest permission record")
    if status != "approved" or not {"model_evaluation", "annotation_transformation"}.issubset(uses):
        raise ValueError("Scoring requires approved model_evaluation and annotation_transformation permission")
    if not isinstance(ref, str) or not ref.strip() or not _valid_sha(digest):
        raise ValueError("Approved permission requires evidence_ref and evidence_sha256")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("Approved permission requires reviewer_id")
    return {
        "status": status,
        "permitted_uses": uses,
        "evidence_ref": ref,
        "evidence_sha256": digest.lower(),
        "reviewer_id": reviewer,
        "review_state": "METADATA_ONLY_REVIEWER_MUST_AUTHENTICATE_EVIDENCE",
    }


def evaluate(
    manifest: dict[str, Any], labels: dict[str, Any], predictions: dict[str, Any]
) -> dict[str, Any]:
    """Validate provenance-bound count inputs and compute official count metrics."""
    for document, name in ((manifest, "manifest"), (labels, "labels"), (predictions, "predictions")):
        if not isinstance(document, dict):
            raise ValueError(f"{name} root must be an object")
        if document.get("schema_version") != 1:
            raise ValueError(f"{name}.schema_version must be 1")

    dataset_id = manifest.get("dataset_id")
    source_sha = manifest.get("source_sha256")
    if not isinstance(dataset_id, str) or not dataset_id.strip():
        raise ValueError("Manifest dataset_id must be nonempty")
    if not _valid_sha(source_sha):
        raise ValueError("Manifest source_sha256 must be a 64-character SHA-256")
    if manifest.get("split") not in ("diagnostic", "test", "held_out"):
        raise ValueError("Manifest split must be diagnostic, test, or held_out")
    permission = _permission_status(manifest)

    protocol = manifest.get("evaluation_protocol")
    if not isinstance(protocol, dict):
        raise ValueError("Manifest evaluation_protocol must be an object")
    if protocol.get("split_unit") != "sequence":
        raise ValueError("DroneCrowd evaluation split_unit must be sequence")
    partition_id = protocol.get("test_partition_id")
    if not isinstance(partition_id, str) or not partition_id.strip():
        raise ValueError("Manifest test_partition_id must be nonempty")
    if protocol.get("selection_locked_before_predictions") is not True:
        raise ValueError("Manifest must lock frame selection before predictions")

    for document, name in ((labels, "labels"), (predictions, "predictions")):
        if document.get("dataset_id") != dataset_id:
            raise ValueError(f"{name}.dataset_id does not match the manifest")
        if not _valid_sha(document.get("source_sha256")) or document["source_sha256"].lower() != source_sha.lower():
            raise ValueError(f"{name}.source_sha256 does not match the manifest")

    samples = manifest.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("Manifest samples must be a nonempty array")
    sample_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError("Each manifest sample must be an object")
        key = _frame_key(sample, "manifest sample")
        if key in sample_by_key:
            raise ValueError("Manifest sequence/frame keys must be unique")
        stratum = sample.get("stratum", "unstratified")
        if not isinstance(stratum, str) or not stratum.strip():
            raise ValueError("Manifest sample stratum must be nonempty")
        image_sha = sample.get("image_sha256")
        if image_sha is not None and not _valid_sha(image_sha):
            raise ValueError("Manifest sample image_sha256 must be SHA-256 or omitted")
        sample_by_key[key] = sample

    def parse_rows(document: dict[str, Any], name: str, prediction: bool) -> dict[tuple[str, int], dict[str, Any]]:
        rows = document.get("frames")
        if not isinstance(rows, list):
            raise ValueError(f"{name}.frames must be an array")
        parsed: dict[tuple[str, int], dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"Each {name} frame must be an object")
            key = _frame_key(row, f"{name} frame")
            if key not in sample_by_key or key in parsed:
                raise ValueError(f"{name} contains an unknown or duplicate sequence/frame")
            if prediction:
                expected_image_sha = sample_by_key[key].get("image_sha256")
                image_sha = row.get("image_sha256")
                if not _valid_sha(expected_image_sha) or not _valid_sha(image_sha):
                    raise ValueError("Prediction and manifest must include each frame's image_sha256")
                if image_sha.lower() != expected_image_sha.lower():
                    raise ValueError("Prediction image_sha256 does not match the locked manifest sample")
                valid = row.get("valid")
                if type(valid) is not bool:
                    raise ValueError("Prediction valid must be boolean")
                if valid:
                    count = _count(row.get("count"), "Prediction count")
                else:
                    if row.get("count") is not None:
                        raise ValueError("Invalid prediction frames must set count to null")
                    count = None
            else:
                expected_image_sha = sample_by_key[key].get("image_sha256")
                image_sha = row.get("image_sha256")
                if not _valid_sha(expected_image_sha) or not _valid_sha(image_sha):
                    raise ValueError("Labels and manifest must include each frame's image_sha256")
                if image_sha.lower() != expected_image_sha.lower():
                    raise ValueError("Label image_sha256 does not match the locked manifest sample")
                if row.get("complete") is not True:
                    raise ValueError("Every scored label frame must be complete")
                reviewer = row.get("reviewer")
                if not isinstance(reviewer, str) or not reviewer.strip():
                    raise ValueError("Every scored label frame requires reviewer")
                valid, count = True, _count(row.get("person_count"), "Label person_count")
            parsed[key] = {"valid": valid, "count": count, "reviewer": row.get("reviewer")}
        if set(parsed) != set(sample_by_key):
            raise ValueError(f"{name} must include every manifest sample exactly once")
        return parsed

    label_rows = parse_rows(labels, "labels", prediction=False)
    prediction_rows = parse_rows(predictions, "predictions", prediction=True)

    model = predictions.get("model")
    if not isinstance(model, dict):
        raise ValueError("Predictions model must be an object")
    for name in ("profile_id",):
        if not isinstance(model.get(name), str) or not model[name].strip():
            raise ValueError(f"Predictions model.{name} must be nonempty")
    for name in ("profile_sha256", "checkpoint_sha256"):
        if not _valid_sha(model.get(name)):
            raise ValueError(f"Predictions model.{name} must be a SHA-256")
    run_metadata = predictions.get("run_metadata")
    if not isinstance(run_metadata, dict):
        raise ValueError("Predictions run_metadata must be an object from the versioned inference runner")
    for name in ("manifest_sha256", "source_archive_sha256", "profile_file_sha256", "inference_script_sha256"):
        if not _valid_sha(run_metadata.get(name)):
            raise ValueError(f"Predictions run_metadata.{name} must be a SHA-256")
    if run_metadata["source_archive_sha256"].lower() != source_sha.lower():
        raise ValueError("Predictions run_metadata.source_archive_sha256 does not match the manifest")
    if run_metadata["profile_file_sha256"].lower() != model["profile_sha256"].lower():
        raise ValueError("Predictions run_metadata.profile_file_sha256 does not match model.profile_sha256")
    if run_metadata.get("training_evidence_file_sha256") != model.get("training_evidence_file_sha256"):
        raise ValueError("Predictions training-evidence file hashes are inconsistent")

    overlap_status = model.get("training_overlap_status", "unknown_or_mixed")
    if overlap_status not in ("verified_disjoint", "verified_overlap", "overlap_possible", "unknown_or_mixed"):
        raise ValueError("training_overlap_status is invalid")
    training_hashes = model.get("training_source_sha256s", [])
    training_partitions = model.get("training_partition_ids", [])
    training_sequences = model.get("training_sequence_ids")
    if training_sequences is None:
        raise ValueError("training_sequence_ids must be present; use [] only when reviewed as complete")
    if not isinstance(training_hashes, list) or any(not _valid_sha(item) for item in training_hashes):
        raise ValueError("training_source_sha256s must contain SHA-256 values")
    if len({item.lower() for item in training_hashes}) != len(training_hashes):
        raise ValueError("training_source_sha256s contains duplicates")
    if not isinstance(training_partitions, list) or any(not isinstance(item, str) or not item.strip() for item in training_partitions):
        raise ValueError("training_partition_ids must contain nonempty strings")
    if len(set(training_partitions)) != len(training_partitions):
        raise ValueError("training_partition_ids contains duplicates")
    if not isinstance(training_sequences, list) or any(not isinstance(item, str) or not item.strip() for item in training_sequences):
        raise ValueError("training_sequence_ids must contain nonempty strings")
    if len(set(training_sequences)) != len(training_sequences):
        raise ValueError("training_sequence_ids contains duplicates")
    training_manifest_sha = model.get("training_manifest_sha256")
    training_evidence_file_sha = model.get("training_evidence_file_sha256")
    if training_manifest_sha is not None and not _valid_sha(training_manifest_sha):
        raise ValueError("training_manifest_sha256 must be a SHA-256 or null")
    if training_evidence_file_sha is not None and not _valid_sha(training_evidence_file_sha):
        raise ValueError("training_evidence_file_sha256 must be a SHA-256 or null")
    source_overlap = source_sha.lower() in {item.lower() for item in training_hashes}
    partition_overlap = partition_id in set(training_partitions)
    selected_sequences = {key[0] for key in sample_by_key}
    sequence_overlap_ids = sorted(selected_sequences.intersection(training_sequences))
    sequence_overlap = bool(sequence_overlap_ids)
    exact_overlap = source_overlap or partition_overlap or sequence_overlap
    inventory_complete = model.get("training_source_inventory_complete") is True
    sequence_inventory_complete = model.get("training_sequence_inventory_complete") is True
    independence_ref = model.get("independence_evidence_ref")
    independence_sha = model.get("independence_evidence_sha256")
    if independence_ref is not None and (
        not isinstance(independence_ref, str) or not independence_ref.strip()
    ):
        raise ValueError("independence_evidence_ref must be nonempty or null")
    independence_evidence = (
        isinstance(independence_ref, str) and bool(independence_ref.strip())
        and _valid_sha(independence_sha)
    )
    if overlap_status == "verified_disjoint" and (
        not inventory_complete or not sequence_inventory_complete
        or not training_hashes or not training_partitions
        or not _valid_sha(training_manifest_sha)
        or not _valid_sha(training_evidence_file_sha)
        or not independence_evidence or exact_overlap
    ):
        raise ValueError(
            "verified_disjoint requires complete nonempty hash-identified source and partition inventories, "
            "training manifest/evidence hashes, independence evidence, and no exact overlap"
        )
    if overlap_status == "verified_overlap" and not exact_overlap:
        raise ValueError("verified_overlap requires an exact source, partition, or sequence overlap")

    evaluation_scope = "EXPLORATORY"
    if exact_overlap or overlap_status == "verified_overlap":
        evaluation_scope = "TRAINING_FIT"
    elif (
        manifest["split"] in ("test", "held_out")
        and inventory_complete
        and sequence_inventory_complete
        and bool(training_hashes)
        and bool(training_partitions)
        and _valid_sha(training_manifest_sha)
        and _valid_sha(training_evidence_file_sha)
        and not exact_overlap
        and overlap_status == "verified_disjoint"
        and independence_evidence
    ):
        evaluation_scope = "HELD_OUT_CANDIDATE_REQUIRES_MANUAL_EVIDENCE_REVIEW"

    rows_by_stratum: dict[str, list[int]] = {}
    rows_by_sequence: dict[str, list[int]] = {}
    errors: list[int] = []
    unknown_frames = []
    per_frame = []
    for key, sample in sample_by_key.items():
        label = label_rows[key]
        prediction = prediction_rows[key]
        if not prediction["valid"]:
            unknown_frames.append({"sequence_id": key[0], "frame_id": key[1]})
            error = None
        else:
            error = prediction["count"] - label["count"]
            errors.append(error)
            rows_by_stratum.setdefault(sample.get("stratum", "unstratified"), []).append(error)
            rows_by_sequence.setdefault(key[0], []).append(error)
        per_frame.append({
            "sequence_id": key[0], "frame_id": key[1],
            "ground_truth_count": label["count"],
            "predicted_count": prediction["count"],
            "count_error": error,
            "stratum": sample.get("stratum", "unstratified"),
        })

    if not errors:
        raise ValueError("No valid prediction frames are available for count scoring")
    return {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "source_sha256": source_sha.lower(),
        "split": manifest["split"],
        "test_partition_id": partition_id,
        "evaluation_scope": evaluation_scope,
        "metrics_semantics": "DroneCrowd point-label count evaluation; no box-IoU localization metrics",
        "sample_count": len(samples),
        "valid_prediction_frames": len(errors),
        "unknown_prediction_frames": len(unknown_frames),
        "unknown_prediction_rate": len(unknown_frames) / len(samples),
        "count_metrics": _metrics(errors),
        "count_metrics_by_stratum": {key: _metrics(value) for key, value in sorted(rows_by_stratum.items())},
        "count_metrics_by_sequence": {key: _metrics(value) for key, value in sorted(rows_by_sequence.items())},
        "data_permission": permission,
        "lineage": {
            "training_overlap_status": overlap_status,
            "training_manifest_sha256": training_manifest_sha.lower() if _valid_sha(training_manifest_sha) else None,
            "training_evidence_file_sha256": training_evidence_file_sha.lower() if _valid_sha(training_evidence_file_sha) else None,
            "training_source_inventory_complete": inventory_complete,
            "training_source_sha256s": [item.lower() for item in training_hashes],
            "training_sequence_inventory_complete": sequence_inventory_complete,
            "training_sequence_ids": training_sequences,
            "training_partition_ids": training_partitions,
            "training_source_overlap": source_overlap,
            "training_partition_overlap": partition_overlap,
            "training_sequence_overlap_ids": sequence_overlap_ids,
            "independence_evidence_ref": independence_ref,
            "independence_evidence_sha256": independence_sha.lower() if _valid_sha(independence_sha) else None,
            "manual_review_required": evaluation_scope == "HELD_OUT_CANDIDATE_REQUIRES_MANUAL_EVIDENCE_REVIEW",
        },
        "model": {
            "profile_id": model["profile_id"],
            "profile_sha256": model["profile_sha256"].lower(),
            "checkpoint_sha256": model["checkpoint_sha256"].lower(),
            "runtime": model.get("runtime"),
        },
        "inference_run_metadata": {
            name: run_metadata.get(name)
            for name in (
                "manifest_sha256",
                "source_archive_sha256",
                "profile_file_sha256",
                "training_evidence_file_sha256",
                "inference_script_sha256",
            )
        },
        "input_sha256": {
            "manifest": None,
            "labels": None,
            "predictions": None,
        },
        "unknown_frames": unknown_frames,
        "per_frame": per_frame,
        "limitations": [
            "Point labels support counts; they do not provide person boxes or validate box-IoU detection metrics.",
            "This scorer checks evidence metadata and does not authenticate permission or independence artifacts.",
            "A held-out candidate still requires a named reviewer to verify source permission and complete training-lineage evidence.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = [args.manifest, args.labels, args.predictions]
    documents = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    report = evaluate(*documents)
    report["input_sha256"] = {
        "manifest": _sha256(args.manifest),
        "labels": _sha256(args.labels),
        "predictions": _sha256(args.predictions),
    }
    if report["inference_run_metadata"]["manifest_sha256"].lower() != report["input_sha256"]["manifest"].lower():
        raise ValueError("Inference manifest hash does not match the manifest supplied to the scorer")
    report["evaluator_sha256"] = _sha256(Path(__file__).resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
