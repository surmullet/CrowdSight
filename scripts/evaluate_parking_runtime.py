"""Bounded validation-crop inference using the product classifier on A3 and C.

Deterministic chronological frame selection; no tuning and no test crop reads.
This checks crop-runtime behavior, not full-frame fixed-layout accuracy.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import platform
import sys
import time
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crowdsight.parking.crop_classifier import ParkingCropClassifier, sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", required=True, type=Path)
    parser.add_argument("--prepared", required=True, type=Path, help="Completed prepare_parking_product output")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--frames-per-unit", type=int, default=1)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    if args.frames_per_unit < 1 or args.threads < 1:
        raise ValueError("Frame and thread counts must be positive")
    repo, output = Path(__file__).resolve().parents[1], args.output.resolve()
    if output == repo or repo in output.parents:
        raise ValueError("Write generated results outside the source repository")
    output.mkdir(parents=True, exist_ok=False)
    prepared = json.loads((args.prepared / "comparison.json").read_bytes())
    if prepared["scope"] != "MATCHED_VALIDATION_DIAGNOSTIC":
        raise ValueError("Expected a completed validation preparation")
    crops_zip = args.handoff / "pklot-a6-crops.zip"
    crops_hash = sha256(crops_zip)
    if crops_hash != "296246db46170094b36b67d7c53ee146e08dc3a8aecbb5a221d9da089db10805":
        raise ValueError("Crop archive hash mismatch")
    import numpy as np
    import torch
    import torchvision
    from PIL import Image
    torch.set_num_threads(args.threads)
    results = {}
    with zipfile.ZipFile(crops_zip) as archive:
        csv_bytes, split_bytes = archive.read("crops.csv"), archive.read("split-manifest.json")
        split = json.loads(split_bytes)
        if hashlib.sha256(split_bytes).hexdigest() != prepared["split_manifest_sha256"]:
            raise ValueError("Crop split differs from prepared comparison")
        rows_by_unit = {}
        for row in csv.DictReader(io.StringIO(csv_bytes.decode("utf-8"))):
            if row["partition"] != "validation":
                continue
            unit = row["camera"].lower() + "-" + row["era"]
            site = "pucpr" if row["camera"] == "PUCPR" else "ufpr"
            if row["date"] not in split["groups"]["validation"][site]:
                raise ValueError("Crop row contains a non-validation date")
            rows_by_unit.setdefault(unit, []).append(row)
        selected = {}
        for unit, rows in sorted(rows_by_unit.items()):
            stems = sorted({row["stem"] for row in rows})
            # Uniform chronological sampling chosen before model loading.
            count = min(args.frames_per_unit, len(stems))
            chosen = {stems[i * len(stems) // count] for i in range(count)}
            selected[unit] = sorted((row for row in rows if row["stem"] in chosen),
                                    key=lambda row: (row["stem"], int(row["space_id"])))
        selection_path = output / "selection.json"
        selection_path.write_text(json.dumps(selected, indent=2), encoding="utf-8")
        for tag, record in prepared["models"].items():
            results[tag] = {}
            for unit, rows in selected.items():
                profile_dir = args.prepared / tag / unit
                model = ParkingCropClassifier(profile_dir / "runtime-profile.yaml",
                                              checkpoint_path=Path(record["checkpoint_path"]),
                                              layout_path=profile_dir / "layout.json",
                                              device=args.device, batch_size=args.batch_size)
                for key, data in (("crops_csv_sha256", csv_bytes), ("split_manifest_sha256", split_bytes)):
                    if model.checkpoint_metadata.get(key) != hashlib.sha256(data).hexdigest():
                        raise ValueError(f"{tag}: checkpoint/data {key} mismatch")
                crops, crop_hashes = [], []
                for row in rows:
                    raw = archive.read(row["crop"])
                    crop_hashes.append(hashlib.sha256(raw).hexdigest())
                    with Image.open(io.BytesIO(raw)) as image:
                        crops.append(np.array(image.convert("RGB")))
                start = time.perf_counter()
                scores = model.score_rgb_crops(crops)
                seconds = time.perf_counter() - start
                confusion = {truth: {pred: 0 for pred in ("AVAILABLE", "OCCUPIED", "UNKNOWN")}
                             for truth in ("AVAILABLE", "OCCUPIED")}
                predictions = []
                for row, score, digest in zip(rows, scores, crop_hashes):
                    if not np.isfinite(score) or abs(score - model.threshold) < model.margin:
                        state = "UNKNOWN"
                    else:
                        state = "OCCUPIED" if score >= model.threshold else "AVAILABLE"
                    truth = "OCCUPIED" if row["state"] == "occupied" else "AVAILABLE"
                    confusion[truth][state] += 1
                    predictions.append({"crop": row["crop"], "sha256": digest, "truth": truth,
                                        "state": state, "occupied_raw_score": score if np.isfinite(score) else None})
                correct = sum(confusion[s][s] for s in confusion)
                results[tag][unit] = {"crops": len(rows), "accuracy": correct / len(rows),
                                      "confusion": confusion, "seconds": seconds,
                                      "timing_scope": "preprocessing+forward+device transfer; first call included; excludes decoding",
                                      "profile_sha256": model.profile.profile_sha256,
                                      "checkpoint_sha256": model.profile.expected_sha256,
                                      "predictions": predictions}
                print(f"{tag}/{unit}: {correct}/{len(rows)} correct, {seconds:.3f}s", flush=True)
                del model
    report = {"scope": "BOUNDED_VALIDATION_CROP_RUNTIME_DIAGNOSTIC", "test_accessed": False,
              "release_approval": False, "results": results, "crop_archive_sha256": crops_hash,
              "selection_sha256": sha256(selection_path), "script_sha256": sha256(Path(__file__)),
              "adapter_sha256": sha256(Path(sys.modules[ParkingCropClassifier.__module__].__file__)),
              "prepared_comparison_sha256": sha256(args.prepared / "comparison.json"),
              "runtime": {"python": platform.python_version(), "torch": torch.__version__, "torchvision": torchvision.__version__,
                          "platform": platform.platform(), "processor": platform.processor(), "device": args.device,
                          "device_name": torch.cuda.get_device_name(args.device) if args.device.startswith("cuda") else platform.processor(),
                          "threads": args.threads, "batch_size": args.batch_size}}
    with (output / "report.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
