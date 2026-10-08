"""Verify A3/C handoff, rescore matched validation packs, export runtime profiles.

Reads returned predictions, not test images. Outputs belong outside the repository.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import platform
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml

from crowdsight.parking.crop_classifier import PREPROCESSING, sha256
from evaluate_parking_occupancy import evaluate

MODELS = {
    "modelA3": {"folder": "model_a3", "arch": "tinycnn",
                "checkpoint": "2294c41aa2cf9ee513038e0fcf786d71d10e696e95ffcf8692d066115413e40d"},
    "modelC": {"folder": "modelC", "arch": "vit_b16",
               "checkpoint": "06d7b96351868f9d7a712b0851af0bb01b7c292847eff9e68375c18cbbd0ccbf"},
}
UNITS = ("pucpr-main", "ufpr04-era-a", "ufpr04-era-b", "ufpr05-main")
A3_ARCHIVE_SHA = "f2812c370845e170cbeb8b1769463f8e60644a45b349c40bd940a9b910b418e8"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def summarize(report: dict) -> dict:
    confusion = report["confusion_matrix"]
    correct = sum(confusion[state][state] for state in ("OCCUPIED", "AVAILABLE"))
    n = report["known_label_space_observations"]
    return {
        "frames": report["frames"], "known_labels": n,
        "accuracy_on_known_labels": correct / n if n else None,
        "unknown_labels": report["unknown_label_space_observations"],
        "abstention_rate": report["prediction_abstention_rate_on_known_labels"],
        "false_available": confusion["OCCUPIED"]["AVAILABLE"],
        "false_occupied": confusion["AVAILABLE"]["OCCUPIED"],
        "per_class": report["per_class"],
        "occupied_count": report["occupied_space_count_error"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", required=True, type=Path, help="T2-parking-data directory")
    parser.add_argument("--layout-root", required=True, type=Path, help="PKLot layouts and split-manifest.json")
    parser.add_argument("--output", required=True, type=Path, help="New private artifact directory")
    parser.add_argument("--inventory", type=Path, help="Optional PKLot inventory.csv for weather strata")
    args = parser.parse_args()
    root, layouts, output = args.handoff.resolve(), args.layout_root.resolve(), args.output.resolve()
    repo = Path(__file__).resolve().parents[1]
    if output == repo or repo in output.parents:
        raise ValueError("Generated artifacts must be outside the source repository")
    output.mkdir(parents=True, exist_ok=False)
    split_path = layouts / "split-manifest.json"
    split = json.loads(split_path.read_bytes())
    split_hash = sha256(split_path)
    weather_by_frame = {}
    inventory_hash = sha256(args.inventory) if args.inventory else None
    if args.inventory:
        with args.inventory.open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                if row["kind"] == "frame" and row["partition"] == "validation":
                    key = (row["camera"].lower(), Path(row["image_id"]).stem)
                    if key in weather_by_frame:
                        raise ValueError("Duplicate validation frame in weather inventory")
                    weather_by_frame[key] = row["weather"]
    archive_path = root / "model_a3/modelA3-validation-artifacts.zip"
    if sha256(archive_path) != A3_ARCHIVE_SHA:
        raise ValueError("A3 validation archive hash mismatch")
    results, identity, inventory = {}, {}, {}
    scorer_hash = sha256(Path(__file__).with_name("evaluate_parking_occupancy.py"))
    with zipfile.ZipFile(archive_path) as archive:
        member_hashes = {}
        for line in archive.read("MANIFEST.sha256").decode().splitlines():
            digest, name = line.split("  ", 1)
            member_hashes[name] = digest

        for tag, model in MODELS.items():
            folder = root / model["folder"]
            checkpoint = folder / f"checkpoint-{tag}.pt"
            run_path, calibration_path = folder / f"run-{tag}.json", folder / f"calibration-{tag}.json"
            run, calibration = json.loads(run_path.read_bytes()), json.loads(calibration_path.read_bytes())
            checkpoint_hash, calibration_hash = sha256(checkpoint), sha256(calibration_path)
            if checkpoint_hash != model["checkpoint"] or run["checkpoint_sha256"] != checkpoint_hash:
                raise ValueError(f"{tag}: checkpoint hash mismatch")
            if run["calibration_sha256"] != calibration_hash or calibration["checkpoint_sha256"] != checkpoint_hash:
                raise ValueError(f"{tag}: calibration hash/binding mismatch")
            if sha256(folder / run["script"]) != run["script_sha256"]:
                raise ValueError(f"{tag}: training script hash mismatch")
            inventory[tag] = {"checkpoint_sha256": checkpoint_hash, "checkpoint_path": str(checkpoint),
                              "calibration_sha256": calibration_hash, "run_sha256": sha256(run_path),
                              "architecture": model["arch"], "training_runtime": {k: run[k] for k in ("python", "torch", "device")}}
            results[tag] = {}
            for unit in UNITS:
                def read_pack(name: str) -> bytes:
                    if tag == "modelA3":
                        member = f"evals/modelA3/validation/{unit}/{name}"
                        raw = archive.read(member)
                        if hashlib.sha256(raw).hexdigest() != member_hashes.get(member):
                            raise ValueError(f"Archive member hash mismatch: {member}")
                        return raw
                    return (folder / "validation-scored" / unit / name).read_bytes()

                raw = {key: read_pack(f"{key}.json") for key in ("manifest", "labels", "predictions", "frame-selection")}
                documents = {key: json.loads(value) for key, value in raw.items()}
                manifest, labels, predictions, selection = (documents[k] for k in raw)
                if manifest["split"] != "diagnostic" or not manifest["partition_id"].endswith("|validation"):
                    raise ValueError("Only validation diagnostic packs are supported")
                if hashlib.sha256(raw["frame-selection"]).hexdigest() != manifest["source_sha256"]:
                    raise ValueError("Selection hash differs from pack source identity")
                if len(selection) != len(manifest["samples"]):
                    raise ValueError("Selection and sample lengths differ")
                site = "pucpr" if unit == "pucpr-main" else "ufpr"
                validation_dates = set(split["groups"]["validation"][site])
                if any(item["frame"][:10] not in validation_dates for item in selection):
                    raise ValueError("Selection contains a non-validation date")
                if predictions["training_evidence"]["manifest_sha256"] != split_hash:
                    raise ValueError("Split manifest hash differs from training evidence")
                profile_bytes = read_pack(predictions["model"]["profile_id"] + ".yaml")
                old_profile = yaml.safe_load(profile_bytes)
                profile_hash = hashlib.sha256(profile_bytes).hexdigest()
                recorded_profile_hash = predictions["model"]["profile_sha256"]
                profile_binding = "EXACT_BYTES"
                if profile_hash != recorded_profile_hash:
                    normalized_hash = hashlib.sha256(profile_bytes.replace(b"\r\n", b"\n")).hexdigest()
                    if tag != "modelA3" or normalized_hash != recorded_profile_hash:
                        raise ValueError("Prediction profile hash mismatch")
                    profile_binding = "LEGACY_A3_LF_NORMALIZED_ONLY_NOT_EXACT_BYTES"
                if predictions["model"]["checkpoint_sha256"] != checkpoint_hash or old_profile["checkpoint_sha256"] != checkpoint_hash:
                    raise ValueError("Prediction/profile checkpoint mismatch")
                for field in ("profile_id", "site_id", "camera_view_id", "space_layout_version"):
                    if old_profile[field] != predictions["model"][field]:
                        raise ValueError(f"Profile metadata mismatch: {field}")
                threshold = calibration["thresholds"].get(unit, {}).get("threshold", 0.5)
                if predictions["runtime"]["decision_threshold"] != threshold:
                    raise ValueError("Prediction threshold differs from frozen calibration")
                current_identity = {"selection": selection, "samples": manifest["samples"],
                                    "spaces": manifest["space_ids"], "labels": labels["frames"],
                                    "site": manifest["site_id"], "camera": manifest["camera_view_id"],
                                    "layout": manifest["space_layout_version"]}
                if unit in identity and current_identity != identity[unit]:
                    raise ValueError(f"{unit}: A3/C frames or labels are not matched")
                identity[unit] = current_identity
                report = evaluate(manifest, labels, predictions)
                report["input_sha256"] = {key: hashlib.sha256(value).hexdigest() for key, value in raw.items()}
                report["evaluator_script_sha256"] = scorer_hash
                report["evaluation_stage"] = "RESCORED_RETURNED_VALIDATION_PREDICTIONS"
                report["historical_profile_binding"] = {
                    "status": profile_binding, "actual_sha256": profile_hash,
                    "prediction_recorded_sha256": recorded_profile_hash,
                }
                target = output / tag / unit
                write_json(target / "report.json", report)
                results[tag][unit] = summarize(report)
                if args.inventory:
                    weather_indices = {}
                    for sample, item in zip(manifest["samples"], selection):
                        weather = weather_by_frame[(manifest["camera_view_id"], item["frame"])]
                        weather_indices.setdefault(weather, set()).add(sample["frame_index"])
                    results[tag][unit]["weather"] = {}
                    for weather, indices in sorted(weather_indices.items()):
                        subset_manifest = {**manifest, "samples": [r for r in manifest["samples"] if r["frame_index"] in indices],
                                           "evaluation_protocol": {**manifest["evaluation_protocol"], "selection_locked_before_predictions": False}}
                        subset_labels = {**labels, "frames": [r for r in labels["frames"] if r["frame_index"] in indices]}
                        subset_predictions = {**predictions, "frames": [r for r in predictions["frames"] if r["frame_index"] in indices]}
                        weather_report = evaluate(subset_manifest, subset_labels, subset_predictions)
                        weather_report["stratum"] = weather
                        weather_report["selection_scope"] = "POST_INFERENCE_WEATHER_SLICE"
                        weather_report["parent_input_sha256"] = report["input_sha256"]
                        weather_report["inventory_sha256"] = inventory_hash
                        weather_report["evaluator_script_sha256"] = scorer_hash
                        write_json(target / f"weather-{weather}.json", weather_report)
                        results[tag][unit]["weather"][weather] = summarize(weather_report)
                with (target / "errors.csv").open("x", newline="", encoding="utf-8") as stream:
                    writer = csv.writer(stream)
                    writer.writerow(("frame_index", "source_frame", "space_id", "truth", "prediction", "raw_score"))
                    truths = {row["frame_index"]: {s["space_id"]: s["state"] for s in row["spaces"]} for row in labels["frames"]}
                    stems = {row["frame_index"]: item["frame"] for row, item in zip(manifest["samples"], selection)}
                    for frame in predictions["frames"]:
                        index = frame["frame_index"]
                        for space in frame["spaces"]:
                            truth = truths[index][space["space_id"]]
                            if truth != "UNKNOWN" and truth != space["state"]:
                                writer.writerow((index, stems[index], space["space_id"], truth, space["state"], space["confidence"]))
                layout_path = layouts / f"{manifest['space_layout_version']}.layout.json"
                layout_bytes = layout_path.read_bytes()
                layout = json.loads(layout_bytes)
                for field in ("site_id", "camera_view_id", "space_layout_version"):
                    if layout[field] != manifest[field]:
                        raise ValueError(f"Layout {field} mismatch")
                if [s["space_id"] for s in layout["spaces"]] != manifest["space_ids"]:
                    raise ValueError("Layout space order differs from evaluation")
                with (target / "layout.json").open("xb") as stream:
                    stream.write(layout_bytes)
                profile = {**old_profile, "profile_id": old_profile["profile_id"] + "_runtime_v1",
                           "status": "trained_candidate", "release_approval": False,
                           "runtime": {"adapter_version": "parking_crop_v1", "architecture": model["arch"],
                                       "preprocessing": PREPROCESSING, "classes": {"0": "AVAILABLE", "1": "OCCUPIED"},
                                       "layout_sha256": hashlib.sha256(layout_bytes).hexdigest(),
                                       "decision_threshold": threshold, "abstention_margin": 0.0,
                                       "calibration_sha256": calibration_hash,
                                       "threshold_source": "train_site_date_carve" if unit in calibration["thresholds"] else "fixed_0.5_uncalibrated",
                                       "precision": "float32", "coverage_source": "caller_per_frame"}}
                with (target / "runtime-profile.yaml").open("x", encoding="utf-8") as stream:
                    yaml.safe_dump(profile, stream, sort_keys=False)
                print(f"Scored {tag}/{unit}: {results[tag][unit]['accuracy_on_known_labels']:.6f}", flush=True)
    summary = {"schema_version": 1, "scope": "MATCHED_VALIDATION_DIAGNOSTIC",
               "release_approval": False, "test_accessed": False, "inference_rerun": False,
               "models": inventory, "results": results, "split_manifest_sha256": split_hash,
               "a3_archive_sha256": A3_ARCHIVE_SHA, "scorer_sha256": scorer_hash,
               "pipeline_sha256": sha256(Path(__file__)),
               "inventory_sha256": inventory_hash,
               "runtime": {"python": platform.python_version(), "platform": platform.platform()},
               "limitations": ["Publisher XML-derived crop labels; not independently reviewed target-site labels.",
                               "A3 historical profile hashes bind LF-normalized content, not archived CRLF bytes; both recorded per report.",
                               "Validation predictions use per-frame XML crops; fixed-layout runtime needs separate evaluation.",
                               "Historical test reuse prevents a new clean one-shot claim.",
                               "Raw scores; threshold fitting is not probability calibration.",
                               "No night, Vietnam-site, motorbike or camera-movement acceptance evidence."]}
    write_json(output / "comparison.json", summary)
    lines = ["# Parking model comparison", "", "Matched validation diagnostics; returned predictions rescored.", "",
             "| View | A3 accuracy | C accuracy | A3 count MAE | C count MAE |", "|---|---:|---:|---:|---:|"]
    for unit in UNITS:
        a, c = results["modelA3"][unit], results["modelC"][unit]
        lines.append(f"| {unit} | {a['accuracy_on_known_labels']:.4%} | {c['accuracy_on_known_labels']:.4%} | {a['occupied_count']['mae']:.4f} | {c['occupied_count']['mae']:.4f} |")
    lines += ["", *[f"- {item}" for item in summary["limitations"]]]
    (output / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Completed: {output / 'comparison.json'}")


if __name__ == "__main__":
    main()
