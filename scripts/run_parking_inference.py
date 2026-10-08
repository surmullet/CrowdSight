"""Run a parking candidate on a manifest of decoded image frames.

Manifest fields: source_id, session_id, site_id, camera_view_id,
space_layout_version, frames [{path, sha256, frame_index, media_time_s,
visible_space_ids, registration_valid, stale}]. Coverage defaults to unknown.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crowdsight.parking.crop_classifier import ParkingCropClassifier, sha256


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--layout", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    output = args.output.resolve()
    repo = Path(__file__).resolve().parents[1]
    if output == repo or repo in output.parents:
        raise ValueError("Write inference artifacts outside the repository")
    output.mkdir(parents=True, exist_ok=False)
    manifest_bytes = args.manifest.read_bytes()
    manifest = json.loads(manifest_bytes)
    rows = manifest["frames"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("frames must be a nonempty array")
    indices = [row["frame_index"] for row in rows]
    if any(type(i) is not int or i < 0 for i in indices) or len(set(indices)) != len(indices):
        raise ValueError("Frame indices must be unique nonnegative integers")
    model = ParkingCropClassifier(args.profile, checkpoint_path=args.checkpoint,
                                  layout_path=args.layout, device=args.device, batch_size=args.batch_size)
    import cv2
    import numpy as np
    import torch
    import torchvision
    from PIL import __version__ as pillow_version

    elapsed, qualities = [], {}
    with (output / "observations.jsonl").open("x", encoding="utf-8") as stream:
        for row in rows:
            source_path = (args.manifest.parent / row["path"]).resolve()
            image_bytes = source_path.read_bytes()
            if hashlib.sha256(image_bytes).hexdigest() != row["sha256"]:
                raise ValueError(f"Frame hash mismatch: {source_path}")
            start = time.perf_counter()
            frame = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
            observation = model.observe(
                frame, **{key: manifest[key] for key in ("site_id", "camera_view_id", "space_layout_version", "source_id", "session_id")},
                frame_index=row["frame_index"], media_time_s=row["media_time_s"],
                visible_space_ids=row.get("visible_space_ids", []),
                registration_valid=row.get("registration_valid", False), stale=row.get("stale", False),
            )
            elapsed.append(time.perf_counter() - start)
            record = observation.to_contract_dict()
            qualities[record["quality"]] = qualities.get(record["quality"], 0) + 1
            stream.write(json.dumps(record, allow_nan=False) + "\n")
    run = {"status": "COMPLETED", "frames": len(rows), "quality_counts": qualities,
           "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
           "profile_sha256": model.profile.profile_sha256, "checkpoint_sha256": model.profile.expected_sha256,
           "layout_sha256": model.layout_sha256, "adapter_sha256": sha256(Path(sys.modules[ParkingCropClassifier.__module__].__file__)),
           "runner_sha256": sha256(Path(__file__)), "observations_sha256": sha256(output / "observations.jsonl"),
           "runtime": {"python": platform.python_version(), "platform": platform.platform(),
                       "processor": platform.processor(), "torch": torch.__version__, "torchvision": torchvision.__version__,
                       "opencv": cv2.__version__, "pillow": pillow_version, "numpy": np.__version__, "device": str(model.device),
                       "device_name": torch.cuda.get_device_name(model.device) if model.device.type == "cuda" else platform.processor(),
                       "batch_size": args.batch_size, "precision": "float32"},
           "timing": {"scope": "decode+preprocess+inference+observation; excludes load/hash/I/O; first call included",
                      "seconds": elapsed, "mean_seconds": sum(elapsed) / len(elapsed)},
           "release_approval": False}
    with (output / "run.json").open("x", encoding="utf-8") as stream:
        json.dump(run, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "COMPLETED", "frames": len(rows), "output": str(output)}))


if __name__ == "__main__":
    main()
