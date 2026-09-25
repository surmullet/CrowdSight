"""Evaluate raw detector-score calibration against reviewed person boxes.

This tool evaluates probabilities implied by raw scores; it does not fit a
calibrator or change model output semantics. See the evaluation format guide.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from evaluate_crowd_boxes import _box, _match_pairs, evaluate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _metric_rows(scores: list[float], outcomes: list[int], bins: int) -> dict[str, Any]:
    if len(scores) != len(outcomes):
        raise ValueError("Scores and outcomes must have matching lengths")
    count = len(scores)
    if not count:
        return {"n": 0, "status": "UNAVAILABLE_NO_SCORABLE_DETECTIONS"}
    eps = 1e-15
    brier = sum((score - outcome) ** 2 for score, outcome in zip(scores, outcomes)) / count
    nll = -sum(
        outcome * math.log(max(eps, score))
        + (1 - outcome) * math.log(max(eps, 1 - score))
        for score, outcome in zip(scores, outcomes)
    ) / count
    bin_rows = []
    ece = 0.0
    for index in range(bins):
        lower = index / bins
        upper = (index + 1) / bins
        selected = [
            position for position, score in enumerate(scores)
            if lower <= score < upper or (index == bins - 1 and score == 1.0)
        ]
        if not selected:
            bin_rows.append({"index": index, "lower_inclusive": lower, "upper_exclusive": upper, "n": 0,
                             "mean_score": None, "observed_accuracy": None})
            continue
        mean_score = sum(scores[position] for position in selected) / len(selected)
        accuracy = sum(outcomes[position] for position in selected) / len(selected)
        ece += len(selected) / count * abs(mean_score - accuracy)
        bin_rows.append({"index": index, "lower_inclusive": lower, "upper_exclusive": upper,
                         "n": len(selected), "mean_score": mean_score,
                         "observed_accuracy": accuracy})
    return {
        "n": count,
        "status": "DESCRIPTIVE_RAW_SCORE_CALIBRATION",
        "brier_score": brier,
        "negative_log_likelihood": nll,
        "expected_calibration_error": ece,
        "binning": {"method": "equal_width", "bin_count": bins, "interval": "[lower, upper), final bin includes 1.0"},
        "bins": bin_rows,
        "limitations": [
            "Scores are evaluated only for detections emitted at the configured confidence threshold.",
            "These metrics do not fit or authorize a probability calibrator.",
            "Interpretation requires enough independent reviewed examples and condition-stratified review.",
        ],
    }


def evaluate_calibration(
    manifest: dict[str, Any], labels: dict[str, Any], predictions: dict[str, Any],
    iou_threshold: float = 0.5, bins: int = 10,
) -> dict[str, Any]:
    """Score emitted detection confidences using the box evaluator's match rule."""
    if type(bins) is not int or not 2 <= bins <= 100:
        raise ValueError("bins must be an integer from 2 through 100")
    if not math.isfinite(iou_threshold) or not 0.0 < iou_threshold <= 1.0:
        raise ValueError("iou_threshold must be in (0, 1]")
    # Reuse the strict schema, lineage, permission, frame-completeness, and
    # coordinate checks from the primary evaluator before computing calibration.
    base_report = evaluate(manifest, labels, predictions, iou_threshold)
    width, height = manifest["width"], manifest["height"]
    samples = {row["frame_index"]: row for row in manifest["samples"]}
    label_frames = {row["frame_index"]: row for row in labels["frames"]}
    output: dict[str, Any] = {
        "schema_version": 1,
        "evaluation_kind": "raw_detection_score_calibration",
        "dataset_id": manifest["dataset_id"],
        "split": manifest.get("split"),
        "iou_threshold": iou_threshold,
        "confidence_semantics": "RAW_MODEL_SCORE",
        "calibrator_fit": False,
        "release_approval": False,
        "models": {},
    }
    for model_id, model in predictions["models"].items():
        if model_id not in base_report["models"]:
            raise ValueError(f"Primary evaluator did not produce model result for {model_id}")
        frame_predictions = {row["frame_index"]: row for row in model["frames"]}
        groups: dict[str, tuple[list[float], list[int], list[int]]] = {}
        ignored_uncertain_total = 0
        for frame_index, sample in samples.items():
            prediction = frame_predictions[frame_index]
            if not prediction["valid"]:
                continue
            legacy_boxes = prediction["boxes"]
            scored = prediction.get("scored_boxes")
            if not isinstance(scored, list) or len(scored) != len(legacy_boxes):
                raise ValueError(
                    f"Model {model_id}, frame {frame_index} requires one scored_boxes entry per boxes entry; rerun inference"
                )
            boxes = [_box(box, width, height, "predicted box") for box in legacy_boxes]
            scores: list[float] = []
            for index, item in enumerate(scored):
                if not isinstance(item, dict) or item.get("bbox_xyxy") != legacy_boxes[index]:
                    raise ValueError("scored_boxes must preserve the exact ordered boxes coordinates")
                score = item.get("raw_score")
                if type(score) not in (int, float) or not math.isfinite(score) or not 0.0 <= score <= 1.0:
                    raise ValueError("Each raw_score must be a finite number in [0, 1]")
                scores.append(float(score))
            truth = label_frames[frame_index]
            certain = [_box(row["bbox_xyxy"], width, height, "certain label")
                       for row in truth["boxes"] if not row["uncertain"]]
            uncertain = [_box(row["bbox_xyxy"], width, height, "uncertain label")
                         for row in truth["boxes"] if row["uncertain"]]
            matched = _match_pairs(boxes, certain, iou_threshold)
            matched_predictions = {pred for pred, _ in matched}
            unmatched = [box for index, box in enumerate(boxes) if index not in matched_predictions]
            ignored_pairs = _match_pairs(unmatched, uncertain, iou_threshold)
            ignored_uncertain_total += len(ignored_pairs)
            unmatched_indices = [index for index in range(len(boxes)) if index not in matched_predictions]
            ignored_indices = {unmatched_indices[pred] for pred, _ in ignored_pairs}
            key = str(sample.get("stratum", "unstratified"))
            values = groups.setdefault(key, ([], [], []))
            for index, score in enumerate(scores):
                if index in ignored_indices:
                    continue
                values[0].append(score)
                values[1].append(1 if index in matched_predictions else 0)
                values[2].append(frame_index)
        model_groups = {
            "all": _metric_rows(
                [score for scores, _, _ in groups.values() for score in scores],
                [outcome for _, outcomes, _ in groups.values() for outcome in outcomes], bins,
            )
        }
        for stratum, (scores, outcomes, _) in sorted(groups.items()):
            model_groups[f"stratum:{stratum}"] = _metric_rows(scores, outcomes, bins)
        model_groups["all"]["ignored_predictions_overlapping_uncertain_annotations"] = ignored_uncertain_total
        output["models"][model_id] = {
            "profile_id": model["profile_id"],
            "profile_sha256": model["profile_sha256"],
            "checkpoint_sha256": model["checkpoint_sha256"],
            "evaluation_scope": base_report["models"][model_id]["evaluation_scope"],
            "training_overlap_status": base_report["models"][model_id]["training_overlap_status"],
            "groups": model_groups,
        }
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--iou", type=float, default=0.5)
    parser.add_argument("--bins", type=int, default=10)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    labels = json.loads(args.labels.read_text(encoding="utf-8-sig"))
    predictions = json.loads(args.predictions.read_text(encoding="utf-8"))
    report = evaluate_calibration(manifest, labels, predictions, args.iou, args.bins)
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
