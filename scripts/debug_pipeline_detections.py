"""Diagnostic script to trace detection counts across every stage of CrowdSight pipeline."""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from crowdsight.service.pipeline.model_boundary import ModelBoundaryService


def main():
    print("=" * 70)
    print("STARTING CROWDSIGHT PIPELINE DETECTION TRACE")
    print("=" * 70)

    # 1. Locate video and frame 0
    video_path = Path("web/public/crowd6.mp4")
    if not video_path.exists():
        video_path = Path("data/media/crowd6.mp4")
    print(f"Target video: {video_path.resolve()}")

    cap = cv2.VideoCapture(str(video_path))
    ret, frame_bgr = cap.read()
    cap.release()
    if not ret or frame_bgr is None:
        raise RuntimeError("Failed to read frame 0 from video")

    h, w = frame_bgr.shape[:2]
    print(f"Frame 0 resolution: {w}x{h} (w x h)")

    # 2. Stage 1: MODEL OUTPUT (models/best.pt)
    model_path = Path("models/best.pt").resolve()
    print(f"\n[STAGE 1: MODEL OUTPUT] Running raw YOLO from {model_path}...")
    model = YOLO(str(model_path))

    # Test with default max_det (300)
    res_default = model.predict(
        source=frame_bgr,
        conf=0.25,
        imgsz=1280,
        classes=[0],
        verbose=False,
    )[0]
    boxes_default = res_default.boxes

    # Test with max_det = 1000
    res_1000 = model.predict(
        source=frame_bgr,
        conf=0.25,
        imgsz=1280,
        max_det=1000,
        classes=[0],
        verbose=False,
    )[0]
    boxes_1000 = res_1000.boxes

    # Test with max_det = 3000
    res_3000 = model.predict(
        source=frame_bgr,
        conf=0.25,
        imgsz=1280,
        max_det=3000,
        classes=[0],
        verbose=False,
    )[0]
    boxes_3000 = res_3000.boxes

    # Test with very low conf (0.01) to see total potential detections
    res_lowconf = model.predict(
        source=frame_bgr,
        conf=0.01,
        imgsz=1280,
        max_det=3000,
        classes=[0],
        verbose=False,
    )[0]

    # Calculate stats on default (conf >= 0.25, max_det=300)
    confs_default = boxes_default.conf.detach().cpu().numpy()
    count_default = len(boxes_default)
    count_1000 = len(boxes_1000)
    count_3000 = len(boxes_3000)
    count_lowconf = len(res_lowconf.boxes)

    conf_min = float(confs_default.min()) if count_default > 0 else 0.0
    conf_max = float(confs_default.max()) if count_default > 0 else 0.0
    conf_mean = float(confs_default.mean()) if count_default > 0 else 0.0

    print(f"  - Total detections at conf>=0.01 (max_det=3000): {count_lowconf}")
    print(f"  - Total detections at conf>=0.25 (max_det=3000): {count_3000}")
    print(f"  - Total detections at conf>=0.25 (max_det=1000): {count_1000}")
    print(f"  - Total detections at conf>=0.25 (max_det=300, default): {count_default}")
    print(f"  - Confidence min: {conf_min:.4f}, max: {conf_max:.4f}, mean: {conf_mean:.4f}")

    # Save 01_raw_model.jpg
    img_raw = frame_bgr.copy()
    raw_coords = boxes_default.xyxy.detach().cpu().numpy()
    for box, _c in zip(raw_coords, confs_default, strict=False):
        x1, y1, x2, y2 = [int(v) for v in box]
        cv2.rectangle(img_raw, (x1, y1), (x2, y2), (0, 140, 255), 1)
        # small anchor
        cv2.circle(img_raw, ((x1 + x2) // 2, y2), 2, (0, 255, 255), -1)

    # Put count overlay
    cv2.rectangle(img_raw, (10, 10), (520, 70), (0, 0, 0), -1)
    cv2.putText(
        img_raw,
        "Stage 1: Raw YOLO best.pt (conf>=0.25, default max_det=300)",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
    )
    cv2.putText(
        img_raw,
        f"Total Detections: {count_default} (if max_det=1000: {count_1000})",
        (20, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2,
    )
    out_dir = Path("debug_output")
    out_dir.mkdir(exist_ok=True)
    cv2.imwrite(str(out_dir / "01_raw_model.jpg"), img_raw)
    print(f"  -> Saved {out_dir / '01_raw_model.jpg'}")

    # 3. Stage 2: AFTER DETECTOR (adapter.py)
    print("\n[STAGE 2: AFTER DETECTOR (adapter.py)]...")
    mb = ModelBoundaryService()
    detector, prov = mb.create_detector(enable_tracker=False)
    print(f"  - Detector type: {type(detector).__name__}")
    print(f"  - Profile: {detector._profile.profile_id}, conf={detector._profile.confidence}, imgsz={detector._profile.image_size}")

    adapter_detections = detector.predict(frame_bgr)
    count_adapter = len(adapter_detections)
    print(f"  - Raw YOLO detections: {count_default}")
    print(f"  - Adapter returned detections: {count_adapter}")
    dropped_in_adapter = count_default - count_adapter
    print(f"  - Detections dropped in adapter: {dropped_in_adapter}")

    # Save 02_after_adapter.jpg
    img_adapter = frame_bgr.copy()
    for d in adapter_detections:
        x1, y1, x2, y2 = [int(v) for v in d.bbox_xyxy_px]
        cv2.rectangle(img_adapter, (x1, y1), (x2, y2), (255, 180, 0), 1)
        # bottom center anchor
        cx = int(d.x * w)
        cy = int(d.y * h)
        cv2.circle(img_adapter, (cx, cy), 2, (0, 255, 0), -1)

    cv2.rectangle(img_adapter, (10, 10), (520, 70), (0, 0, 0), -1)
    cv2.putText(
        img_adapter,
        "Stage 2: After adapter.py (UltralyticsPersonDetector)",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
    )
    cv2.putText(
        img_adapter,
        f"Total Detections: {count_adapter} (Dropped by adapter: {dropped_in_adapter})",
        (20, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2,
    )
    cv2.imwrite(str(out_dir / "02_after_adapter.jpg"), img_adapter)
    print(f"  -> Saved {out_dir / '02_after_adapter.jpg'}")

    # 4. Stage 3: TRACKING (BoT-SORT / ByteTrack)
    print("\n[STAGE 3: TRACKING]...")
    # Find botsort config
    botsort_yaml = Path(".venv/Lib/site-packages/ultralytics/cfg/trackers/botsort.yaml").resolve()
    print(f"  - Testing with BoT-SORT config: {botsort_yaml}")

    # Run track on frame 0
    track_res = model.track(
        source=frame_bgr,
        persist=True,
        tracker=str(botsort_yaml),
        conf=0.25,
        imgsz=1280,
        classes=[0],
        verbose=False,
    )[0]

    track_boxes = track_res.boxes
    count_before_tracker = count_default
    track_ids = track_boxes.id.detach().cpu().numpy() if track_boxes.id is not None else None
    count_after_tracker = len(track_boxes) if track_boxes is not None else 0
    count_with_track_id = len(track_ids) if track_ids is not None else 0

    print(f"  - Detections before tracker: {count_before_tracker}")
    print(f"  - Boxes returned after tracker: {count_after_tracker}")
    print(f"  - Boxes with assigned track_id: {count_with_track_id}")
    dropped_in_tracker = count_before_tracker - count_after_tracker
    print(f"  - Dropped in tracker: {dropped_in_tracker}")

    # Save 03_after_tracker.jpg
    img_tracker = frame_bgr.copy()
    if track_boxes is not None:
        tr_coords = track_boxes.xyxy.detach().cpu().numpy()
        for idx, box in enumerate(tr_coords):
            x1, y1, x2, y2 = [int(v) for v in box]
            cv2.rectangle(img_tracker, (x1, y1), (x2, y2), (0, 220, 100), 1)
            tid_str = f"#{int(track_ids[idx])}" if track_ids is not None else "no-id"
            cv2.putText(
                img_tracker,
                tid_str,
                (x1, max(y1 - 2, 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                (0, 255, 128),
                1,
            )

    cv2.rectangle(img_tracker, (10, 10), (520, 70), (0, 0, 0), -1)
    cv2.putText(
        img_tracker,
        "Stage 3: After BoT-SORT Tracker (first frame)",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
    )
    cv2.putText(
        img_tracker,
        f"Total Tracks: {count_after_tracker} (with ID: {count_with_track_id})",
        (20, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (100, 255, 100),
        2,
    )
    cv2.imwrite(str(out_dir / "03_after_tracker.jpg"), img_tracker)
    print(f"  -> Saved {out_dir / '03_after_tracker.jpg'}")

    # 5. Stage 4: FILTERING & ZONE CHECKS
    print("\n[STAGE 4: FILTERING]")
    # Check zones from media_crowd6_observations.json
    obs_file = Path("web/public/media_crowd6_observations.json")
    with obs_file.open("r", encoding="utf-8") as f:
        obs_data = json.load(f)

    zones = obs_data.get("zones", [])
    print(f"  - Configured zones count: {len(zones)}")
    for z in zones:
        print(f"    * Zone '{z['name']}': {z['vertices']}")

    # Check how many adapter detections fall into Zone A and Zone B
    def is_point_in_poly(pt, poly):
        return cv2.pointPolygonTest(np.array(poly, dtype=np.int32), (float(pt[0]), float(pt[1])), False) >= 0

    zone_a_poly = zones[0]["vertices"] if len(zones) > 0 else []
    zone_b_poly = zones[1]["vertices"] if len(zones) > 1 else []

    count_in_zone_a = 0
    count_in_zone_b = 0
    count_outside_all_zones = 0

    for d in adapter_detections:
        px = d.x * w
        py = d.y * h
        in_a = is_point_in_poly((px, py), zone_a_poly) if zone_a_poly else False
        in_b = is_point_in_poly((px, py), zone_b_poly) if zone_b_poly else False
        if in_a:
            count_in_zone_a += 1
        elif in_b:
            count_in_zone_b += 1
        else:
            count_outside_all_zones += 1

    print(f"  - Points inside Zone A: {count_in_zone_a}")
    print(f"  - Points inside Zone B: {count_in_zone_b}")
    print(f"  - Points outside both zones: {count_outside_all_zones}")
    print(f"  - Sum inside zones: {count_in_zone_a + count_in_zone_b}")

    # 6. Stage 5: FRONTEND / API
    print("\n[STAGE 5: FRONTEND & API INVESTIGATION]")
    f0_obs = obs_data.get("frames", [])[0] if obs_data.get("frames") else {}
    f0_detections = f0_obs.get("detections", [])
    f0_readings = f0_obs.get("zone_readings", [])
    print(f"  - Current file 'web/public/media_crowd6_observations.json' Frame 0 detections count: {len(f0_detections)}")
    for i, d in enumerate(f0_detections):
        print(f"      Box {i+1}: {d}")
    print(f"  - Current file Frame 0 zone_readings: {f0_readings}")

    # Also check frame 2 and other frames
    f2_obs = obs_data.get("frames", [])[2] if len(obs_data.get("frames", [])) > 2 else {}
    print(f"  - Current file Frame 2 detections count: {len(f2_obs.get('detections', []))}")

    # Summary
    print("\n" + "=" * 70)
    print("STAGE COMPARISON SUMMARY")
    print("=" * 70)
    print("| Stage                               | Count |")
    print("|-------------------------------------|-------|")
    print(f"| YOLO raw (conf>=0.01, max_det=3000) | {count_lowconf:<5} |")
    print(f"| YOLO raw (conf>=0.25, max_det=3000) | {count_3000:<5} |")
    print(f"| YOLO raw (conf>=0.25, max_det=1000) | {count_1000:<5} |")
    print(f"| YOLO raw (conf>=0.25, max_det=300)  | {count_default:<5} |")
    print(f"| After adapter.py (clamped/valid)    | {count_adapter:<5} |")
    print(f"| After tracker (BoT-SORT)            | {count_after_tracker:<5} |")
    print(f"| Inside Zone A + B                   | {count_in_zone_a + count_in_zone_b:<5} |")
    print(f"| Old media_crowd6_observations.json  | {len(f0_detections):<5} (Frame 0 in frontend JSON) |")
    print("=" * 70)


if __name__ == "__main__":
    main()
