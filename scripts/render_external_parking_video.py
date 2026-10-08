"""Full-rate diagnostic replay with fresh ~1 Hz inference and explicit cache age.

Fixed-view crop model; ORB drift rejection is heuristic, not an occlusion detector.
Only inference-update records are exported as current frame observations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from crowdsight.parking.crop_classifier import ParkingCropClassifier, sha256
from evaluate_external_parking_videos import metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--evaluation", required=True, type=Path, help="Frozen model/source evaluation directory")
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--review-layouts", required=True, type=Path)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output, repo = args.output.resolve(), Path(__file__).resolve().parents[1]
    if output == repo or repo in output.parents:
        raise ValueError("Use external artifact storage")
    output.mkdir(parents=True, exist_ok=False)
    import cv2
    import numpy as np
    import torch
    torch.set_num_threads(4)
    selection = json.loads(args.selection.read_bytes())
    video = args.selection.parent / selection["video"]
    if sha256(video) != selection["source_sha256"]:
        raise ValueError("Video hash mismatch")
    source = selection["source_id"]
    review = json.loads(args.review_layouts.read_bytes())["videos"][source]
    truth = json.loads(args.labels.read_bytes())["videos"][source]
    model = ParkingCropClassifier(args.evaluation / "runtime-profile.yaml", checkpoint_path=args.checkpoint,
                                  layout_path=args.evaluation / "layout.json", batch_size=24)
    visible = [sid for sid in model.space_ids if sid not in review["unavailable_space_ids"]]
    sampled_indices = set(selection["frame_indices"])
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if abs(fps - selection["fps"]) > .001:
        raise ValueError("Video FPS differs from locked selection")
    stride = max(1, round(fps))
    writer = cv2.VideoWriter(str(output / "annotated.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), fps, (model.width, model.height))
    if not cap.isOpened() or not writer.isOpened():
        raise RuntimeError("Video decoder/encoder unavailable")
    orb = cv2.ORB_create(nfeatures=1800)
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    reference_points = reference_desc = None
    corners = np.float32([[0,0],[model.width-1,0],[model.width-1,model.height-1],[0,model.height-1]]).reshape(-1,1,2)
    observations, registration, samples = [], [], []
    last = None
    index = 0
    started = time.perf_counter()
    with (output / "display-records.jsonl").open("x", encoding="utf-8") as display:
        try:
            while True:
                ok, original = cap.read()
                if not ok:
                    break
                frame = cv2.resize(original, (model.width, model.height), interpolation=cv2.INTER_AREA)
                update = index % stride == 0 or index in sampled_indices
                if update:
                    points, desc = orb.detectAndCompute(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), None)
                    valid, inliers, drift = False, 0, None
                    if index == 0:
                        reference_points, reference_desc = points, desc
                        valid, inliers, drift = desc is not None, len(points), 0.0
                    elif desc is not None and reference_desc is not None:
                        pairs = matcher.knnMatch(reference_desc, desc, k=2)
                        good = [pair[0] for pair in pairs if len(pair) == 2 and pair[0].distance < .7 * pair[1].distance]
                        if len(good) >= 30:
                            a = np.float32([reference_points[m.queryIdx].pt for m in good]).reshape(-1,1,2)
                            b = np.float32([points[m.trainIdx].pt for m in good]).reshape(-1,1,2)
                            transform, mask = cv2.findHomography(a, b, cv2.RANSAC, 2.5)
                            if transform is not None and mask is not None and np.isfinite(transform).all():
                                inliers = int(mask.sum())
                                mapped = cv2.perspectiveTransform(corners, transform)
                                drift = float(np.max(np.linalg.norm(mapped - corners, axis=2)))
                                valid = bool(np.isfinite(drift) and inliers >= 30 and inliers / len(good) >= .6 and drift <= 3)
                    last = model.observe(frame, site_id=model.profile.site_id, camera_view_id=model.profile.camera_view_id,
                                         space_layout_version=model.profile.space_layout_version, source_id=source,
                                         session_id=source + "-full-replay", frame_index=index, media_time_s=index/fps,
                                         visible_space_ids=visible, registration_valid=valid).to_contract_dict()
                    observations.append(last)
                    registration.append({"frame_index": index, "accepted": valid, "inliers": inliers, "max_corner_drift_px": drift})
                    if index in sampled_indices:
                        samples.append(last)
                    print(f"{source}: source frame {index}, quality {last['quality']}", flush=True)
                age = index/fps - last["media_time_s"]
                for result in last["spaces"]:
                    x0, y0, x1, y1 = model.boxes[result["space_id"]]
                    color = {"OCCUPIED": (30,30,230), "AVAILABLE": (30,200,30), "UNKNOWN": (150,150,150)}[result["state"]]
                    cv2.rectangle(frame, (x0,y0), (x1,y1), color, 2)
                    cv2.putText(frame, result["space_id"] + ":" + result["state"][0], (x0,y0-4), cv2.FONT_HERSHEY_SIMPLEX, .45, color, 1)
                cv2.rectangle(frame, (0,0), (model.width,76), (0,0,0), -1)
                lines = [f"{source} | Model C | threshold {model.threshold} | source t={index/fps:.2f}s",
                         f"{'FRESH INFERENCE' if update else 'CACHED DISPLAY'} | evidence age {age:.2f}s | selected stalls only",
                         "Diagnostic replay; static visibility assumed between reviewed samples; no live-latency claim"]
                for n, text in enumerate(lines):
                    cv2.putText(frame, text, (10,21+n*23), cv2.FONT_HERSHEY_SIMPLEX, .5, (255,255,255), 1)
                writer.write(frame)
                display.write(json.dumps({"frame_index": index, "media_time_s": index/fps, "cached": not update,
                                          "evidence_frame_index": last["frame_index"], "evidence_age_s": age}) + "\n")
                index += 1
        finally:
            cap.release()
            writer.release()
    elapsed = time.perf_counter() - started
    if index != selection["frame_count"]:
        raise ValueError("Source decode was incomplete")
    check = cv2.VideoCapture(str(output / "annotated.mp4"))
    decoded = 0
    while check.read()[0]:
        decoded += 1
    check.release()
    if decoded != index:
        raise ValueError("Output decode was incomplete")
    report = {"status": "COMPLETED", "source_sha256": selection["source_sha256"], "source_frames": index,
              "output_decoded_frames": decoded, "fresh_inference_updates": len(observations),
              "registration_rejections": sum(not r["accepted"] for r in registration),
              "sampled_metrics": metrics(samples, truth), "label_status": "AI_REVIEWED_PROVISIONAL",
              "profile_sha256": model.profile.profile_sha256, "checkpoint_sha256": model.profile.expected_sha256,
              "layout_sha256": model.layout_sha256, "labels_sha256": sha256(args.labels),
              "review_layouts_sha256": sha256(args.review_layouts), "selection_sha256": sha256(args.selection),
              "script_sha256": sha256(Path(__file__)), "output_sha256": sha256(output / "annotated.mp4"),
              "processing_wall_s": elapsed, "processing_fps": index/elapsed,
              "timing_scope": "decode+registration+inference+render+encode; excludes load/hash and output verification",
              "limitations": ["Per-frame visibility outside six inspected frames is an assumption, not verified labels.",
                              "ORB drift rejection does not establish occlusion/registration accuracy.",
                              "Cached display is not a new observation; age is shown and recorded."]}
    for name, value in (("run.json", report), ("observations.json", observations), ("registration.json", registration)):
        with (output / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
    print(json.dumps({"status": "COMPLETED", "frames": index, "accuracy_on_reviewed_samples": report["sampled_metrics"]["accuracy"]}))


if __name__ == "__main__":
    main()
