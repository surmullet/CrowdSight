"""Promote previously scored videos to development and freeze a new threshold.

These reused labels cannot subsequently be called confirmation/test evidence.
The frozen candidate must be evaluated on a new video.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_external_parking_videos import metrics, retreshold, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous-run", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--goal", type=float, default=.7)
    args = parser.parse_args()
    from crowdsight.parking.crop_classifier import sha256
    previous = json.loads((args.previous_run / "workflow.json").read_bytes())
    labels = json.loads(args.labels.read_bytes())
    tag = previous["candidate"]["model"]
    archives = {source: json.loads((args.previous_run / tag / source / "observations.json").read_bytes())
                for source in previous["reports"]}
    observations = {source: archive["frames"] for source, archive in archives.items()}
    attempts = []
    for threshold in (.5, .6, .7, .8, .9, .95, .97, .98, .99):
        reports = {source: metrics(retreshold(obs, threshold), labels["videos"][source]) for source, obs in observations.items()}
        eligible = all(r["accuracy"] >= args.goal and r["known_label_coverage"] >= .9
                       and (r["balanced_accuracy"] is None or r["balanced_accuracy"] >= args.goal) for r in reports.values())
        attempts.append({"threshold": threshold, "eligible": eligible, "reports": reports})
    eligible = [a for a in attempts if a["eligible"]]
    if not eligible:
        raise ValueError("Threshold adjustment did not reach the development target; new training data needed")
    winner = max(eligible, key=lambda a: (min(r["accuracy"] for r in a["reports"].values()),
                                         min(r["balanced_accuracy"] for r in a["reports"].values() if r["balanced_accuracy"] is not None),
                                         -a["threshold"]))
    write(args.output, {"schema_version": 1, "model": tag, "threshold": winner["threshold"],
                        "scope": "REUSED_FAILURES_PROMOTED_TO_DEVELOPMENT_NOT_TEST",
                        "goal": args.goal, "development_videos": list(observations),
                        "development_source_sha256s": [archive["source_sha256"] for archive in archives.values()],
                        "previous_workflow_sha256": sha256(args.previous_run / "workflow.json"),
                        "labels_sha256": sha256(args.labels), "script_sha256": sha256(Path(__file__)),
                        "attempts": attempts, "requires_new_confirmation_video": True})
    print(json.dumps({"model": tag, "threshold": winner["threshold"],
                      "development_accuracy": {key:r["accuracy"] for key,r in winner["reports"].items()}}))


if __name__ == "__main__":
    main()
