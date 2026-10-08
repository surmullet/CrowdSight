"""Development-only model/threshold selection, then frozen external-video scoring.

AI-reviewed labels yield provisional diagnostics, never human-verified accuracy.
All sampled frames are evaluated; abstentions reduce known-label accuracy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crowdsight.parking.crop_classifier import ParkingCropClassifier, sha256

STATES = {"O": "OCCUPIED", "A": "AVAILABLE", "U": "UNKNOWN"}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def metrics(observations, labels):
    confusion = {truth: {pred: 0 for pred in STATES.values()} for truth in ("OCCUPIED", "AVAILABLE")}
    truth_by_frame = {row["frame_index"]: row for row in labels["frames"]}
    if (len(truth_by_frame) != len(labels["frames"]) or len(observations) != len(truth_by_frame)
            or set(truth_by_frame) != {o["frame_index"] for o in observations}):
        raise ValueError("Label/prediction frame coverage differs")
    if len(set(labels["space_ids"])) != len(labels["space_ids"]):
        raise ValueError("Duplicate label IDs")
    unknown_truth, errors, per_space, count_errors = 0, [], {}, []
    for observation in observations:
        row = truth_by_frame[observation["frame_index"]]
        if len(row["states"]) != len(labels["space_ids"]):
            raise ValueError("Incomplete label row")
        truths = dict(zip(labels["space_ids"], [STATES[s] for s in row["states"]]))
        if [s["space_id"] for s in observation["spaces"]] != labels["space_ids"]:
            raise ValueError("Label/prediction stall identity differs")
        for space in observation["spaces"]:
            sid, pred = space["space_id"], space["state"]
            truth = truths[sid]
            if truth == "UNKNOWN":
                unknown_truth += 1
                continue
            confusion[truth][pred] += 1
            counts = per_space.setdefault(sid, {"correct": 0, "known_labels": 0})
            counts["known_labels"] += 1
            counts["correct"] += pred == truth
            if pred != truth:
                errors.append({"frame_index": observation["frame_index"], "space_id": sid, "truth": truth, "prediction": pred})
        if all(v != "UNKNOWN" for v in truths.values()) and all(s["state"] != "UNKNOWN" for s in observation["spaces"]):
            count_errors.append(sum(s["state"] == "OCCUPIED" for s in observation["spaces"]) - sum(v == "OCCUPIED" for v in truths.values()))
    total = sum(sum(row.values()) for row in confusion.values())
    correct = sum(confusion[s][s] for s in confusion)
    abstained = sum(row["UNKNOWN"] for row in confusion.values())
    recalls = {s: confusion[s][s] / sum(confusion[s].values()) if sum(confusion[s].values()) else None for s in confusion}
    return {"accuracy": correct / total if total else None,
            "balanced_accuracy": sum(recalls.values()) / 2 if all(v is not None for v in recalls.values()) else None,
            "known_label_coverage": (total - abstained) / total if total else None,
            "known_labels": total, "unknown_labels": unknown_truth, "correct": correct,
            "per_class_recall": recalls, "confusion_matrix": confusion,
            "per_space": per_space, "errors": errors,
            "count_mae": sum(abs(e) for e in count_errors) / len(count_errors) if count_errors else None,
            "count_evaluable_frames": len(count_errors), "count_scope": "selected configured stalls only"}


def retreshold(observations, threshold):
    copied = json.loads(json.dumps(observations))
    for obs in copied:
        for space in obs["spaces"]:
            if space["state"] == "UNKNOWN":
                continue
            p = space["confidence"] if space["state"] == "OCCUPIED" else 1 - space["confidence"]
            space["state"] = "OCCUPIED" if p >= threshold else "AVAILABLE"
            space["confidence"] = p if p >= threshold else 1 - p
    return copied


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", required=True, type=Path)
    parser.add_argument("--layouts", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--prepared", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--goal", type=float, default=.7)
    parser.add_argument("--candidate", type=Path, help="Previously frozen development-only candidate; confirmation-only mode")
    args = parser.parse_args()
    if not 0 < args.goal <= 1:
        raise ValueError("Goal must be in (0,1]")
    repo, output = Path(__file__).resolve().parents[1], args.output.resolve()
    if output == repo or repo in output.parents:
        raise ValueError("Use external artifact storage")
    output.mkdir(parents=True, exist_ok=False)
    import cv2
    import numpy as np
    import torch
    import yaml
    torch.set_num_threads(4)
    layouts = json.loads(args.layouts.read_bytes())
    labels = json.loads(args.labels.read_bytes())
    prepared = json.loads((args.prepared / "comparison.json").read_bytes())
    development = [key for key, spec in layouts["videos"].items() if spec["role"] == "development"]
    confirmation = [key for key, spec in layouts["videos"].items() if spec["role"] == "confirmation"]
    if (args.candidate is None and len(development) != 1) or not confirmation:
        raise ValueError("Require one development video and separate confirmation videos")
    if set(layouts["videos"]) != set(labels["videos"]):
        raise ValueError("Layout/label video coverage differs")
    freeze = {"goal": args.goal, "coverage_minimum": .9, "layouts_sha256": sha256(args.layouts),
              "labels_sha256": sha256(args.labels), "script_sha256": sha256(Path(__file__)),
              "prepared_comparison_sha256": sha256(args.prepared / "comparison.json"),
              "development": development, "confirmation": confirmation,
              "selection_rule": ("Evaluate the pre-frozen candidate once on new confirmation videos." if args.candidate else
                                 "Try both models at 0.5 on development only. If neither meets goal, scan thresholds 0.1..0.9. Freeze best balanced accuracy before confirmation."),
              "label_status": labels["status"], "human_review_completed": labels["human_review_completed"]}
    write(output / "protocol-locked.json", freeze)

    frozen = json.loads(args.candidate.read_bytes()) if args.candidate else None
    if frozen:
        if development or set(confirmation) & set(frozen["development_videos"]):
            raise ValueError("Frozen-candidate confirmation cannot reuse development videos")
        write(output / "candidate-frozen.json", {**frozen, "candidate_file_sha256": sha256(args.candidate)})

    def infer(source, tag, threshold):
        spec = layouts["videos"][source]
        selection_path = args.intake / source / "frames.json"
        selection = json.loads(selection_path.read_bytes())
        if sha256(args.intake / source / selection["video"]) != selection["source_sha256"]:
            raise ValueError("Video identity mismatch")
        if frozen and selection["source_sha256"] in frozen.get("development_source_sha256s", []):
            raise ValueError("Confirmation source bytes were already used for development")
        if spec["role"] != selection["role"]:
            raise ValueError("Video role mismatch")
        target = output / tag / source
        target.mkdir(parents=True, exist_ok=False)
        layout = {"site_id": source, "camera_view_id": source + "-fixed-v1", "space_layout_version": source + "-review-v1",
                  "image_size": dict(zip(("width", "height"), layouts["reference_size"])), "spaces": []}
        for space in spec["spaces"]:
            x0, y0, x1, y1 = space["box"]
            layout["spaces"].append({"space_id": space["id"], "polygon": [{"x":x0,"y":y0},{"x":x1,"y":y0},{"x":x1,"y":y1},{"x":x0,"y":y1}]})
        write(target / "layout.json", layout)
        profile = yaml.safe_load((args.prepared / tag / "pucpr-main/runtime-profile.yaml").read_bytes())
        profile.update({key: layout[key] for key in ("site_id", "camera_view_id", "space_layout_version")})
        profile["profile_id"] = source + "-" + tag + "-external-v1"
        profile["runtime"].update({"layout_sha256": sha256(target / "layout.json"), "decision_threshold": threshold,
                                    "threshold_source": "fixed_0.5_new_camera" if threshold == .5 else "external_development_only",
                                    "calibration_sha256": None, "abstention_margin": 0.0})
        with (target / "runtime-profile.yaml").open("x", encoding="utf-8") as stream:
            yaml.safe_dump(profile, stream, sort_keys=False)
        model = ParkingCropClassifier(target / "runtime-profile.yaml",
                                      checkpoint_path=Path(prepared["models"][tag]["checkpoint_path"]),
                                      layout_path=target / "layout.json", batch_size=16)
        observations, frames = [], []
        for row in selection["frames"]:
            raw = (args.intake / source / row["path"]).read_bytes()
            if hashlib.sha256(raw).hexdigest() != row["sha256"]:
                raise ValueError("Source frame hash mismatch")
            frame = cv2.resize(cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR),
                               tuple(layouts["reference_size"]), interpolation=cv2.INTER_AREA)
            visible = [s["id"] for s in spec["spaces"] if s["id"] not in spec["unavailable_space_ids"]]
            obs = model.observe(frame, **{key: layout[key] for key in ("site_id", "camera_view_id", "space_layout_version")},
                                source_id=source, session_id=source + "-external-eval", frame_index=row["frame_index"],
                                media_time_s=row["media_time_s"], visible_space_ids=visible,
                                registration_valid=row["frame_index"] not in spec.get("invalid_frame_indices", []))
            observations.append(obs.to_contract_dict())
            frames.append(frame)
        report = metrics(observations, labels["videos"][source])
        write(target / "observations.json", {"source_sha256": selection["source_sha256"],
                                            "selection_sha256": sha256(selection_path), "frames": observations})
        write(target / "report.json", report)
        writer = cv2.VideoWriter(str(target / "sampled-inference.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 1, tuple(layouts["reference_size"]))
        if not writer.isOpened():
            raise RuntimeError("Cannot create review video")
        for frame, observation in zip(frames, observations):
            for space, result in zip(spec["spaces"], observation["spaces"]):
                x0, y0, x1, y1 = space["box"]
                color = {"OCCUPIED": (30, 30, 230), "AVAILABLE": (30, 200, 30), "UNKNOWN": (140, 140, 140)}[result["state"]]
                cv2.rectangle(frame, (x0, y0), (x1, y1), color, 2)
                cv2.putText(frame, space["id"] + ":" + result["state"][0], (x0, y0 - 3), cv2.FONT_HERSHEY_SIMPLEX, .45, color, 1)
            cv2.rectangle(frame, (0, 0), (1280, 60), (0, 0, 0), -1)
            cv2.putText(frame, f"{source} {tag} | SAMPLED REVIEW, not real-time | source t={observation['media_time_s']:.2f}s", (12, 24), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
            cv2.putText(frame, "Selected stalls only | AI-reviewed labels: provisional | red occupied / green available / gray unknown", (12, 47), cv2.FONT_HERSHEY_SIMPLEX, .5, (255,255,255), 1)
            writer.write(frame)
        writer.release()
        check = cv2.VideoCapture(str(target / "sampled-inference.mp4"))
        readable = 0
        while check.read()[0]:
            readable += 1
        check.release()
        if readable != len(frames):
            raise RuntimeError("Review-video decode count mismatch")
        print(f"{tag}/{source}: accuracy={report['accuracy']:.4f}, balanced={report['balanced_accuracy']}", flush=True)
        return observations, report

    if frozen:
        reports = {}
        for source in confirmation:
            _, reports[source] = infer(source, frozen["model"], frozen["threshold"])
        met = all(r["accuracy"] is not None and r["accuracy"] >= args.goal
                  and r["balanced_accuracy"] is not None and r["balanced_accuracy"] >= args.goal
                  and r["known_label_coverage"] >= .9 for r in reports.values())
        write(output / "workflow.json", {"status": "PROVISIONAL_AI_REVIEW_TARGET_MET" if met else "CONFIRMATION_TARGET_NOT_MET",
                                         "human_verified_goal_met": False, "goal": args.goal,
                                         "candidate": {"model": frozen["model"], "threshold": frozen["threshold"]},
                                         "candidate_sha256": sha256(args.candidate), "reports": reports,
                                         "protocol_sha256": sha256(output / "protocol-locked.json"),
                                         "label_status": labels["status"],
                                         "limitations": ["AI-reviewed labels require human confirmation.",
                                                         "Selected stalls and correlated video samples; not whole-lot or general accuracy."]})
        return

    dev = development[0]
    baseline, candidates = {}, []
    for tag in prepared["models"]:
        obs, report = infer(dev, tag, .5)
        baseline[tag] = obs
        candidates.append({"model": tag, "threshold": .5, "metrics": report})

    def meets(report):
        return (report["accuracy"] is not None and report["accuracy"] >= args.goal
                and report["balanced_accuracy"] is not None and report["balanced_accuracy"] >= args.goal
                and report["known_label_coverage"] >= .9)

    if not any(meets(c["metrics"]) for c in candidates):
        for tag, obs in baseline.items():
            for threshold in (.1, .2, .3, .4, .6, .7, .8, .9):
                candidates.append({"model": tag, "threshold": threshold,
                                   "metrics": metrics(retreshold(obs, threshold), labels["videos"][dev])})
    eligible = [c for c in candidates if meets(c["metrics"])]
    if not eligible:
        write(output / "workflow.json", {"status": "DEVELOPMENT_TARGET_NOT_MET", "candidates": candidates,
                                         "next_action": "Collect separate development footage/labels for domain adaptation; confirmation remains unscored."})
        return
    winner = max(eligible, key=lambda c: (c["metrics"]["balanced_accuracy"], c["metrics"]["accuracy"], -abs(c["threshold"]-.5)))
    write(output / "candidate-frozen.json", winner)
    reports = {dev: winner["metrics"]}
    for source in confirmation:
        _, reports[source] = infer(source, winner["model"], winner["threshold"])
    evaluable = [r for key, r in reports.items() if key in confirmation and r["balanced_accuracy"] is not None]
    provisional_met = bool(evaluable) and all(meets(r) for r in evaluable) and all(r["accuracy"] >= args.goal for r in reports.values())
    write(output / "workflow.json", {"status": "PROVISIONAL_AI_REVIEW_TARGET_MET" if provisional_met else "CONFIRMATION_TARGET_NOT_MET",
                                     "human_verified_goal_met": False, "goal": args.goal,
                                     "candidate": {"model": winner["model"], "threshold": winner["threshold"]},
                                     "development_candidates": candidates, "reports": reports,
                                     "confirmation_two_class_videos": len(evaluable),
                                     "limitations": ["AI visual labels need human review.", "Selected 12-region subsets, not whole-lot inventories.",
                                                     "Adjacent samples within clips are correlated; no state transitions in reviewed subset.",
                                                     "One camera has only known occupied examples; balanced accuracy unavailable.",
                                                     "No claim of independent upstream training-source exclusion or site release approval."],
                                     "protocol_sha256": sha256(output / "protocol-locked.json"),
                                     "runtime": {"torch": torch.__version__, "opencv": cv2.__version__, "device": "cpu", "threads": 4}})


if __name__ == "__main__":
    main()
