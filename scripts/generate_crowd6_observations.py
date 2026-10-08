"""Regenerate media_crowd6_observations.json using models/best.pt with BoT-SORT tracking.

Configuration:
- Model: models/best.pt
- Confidence: 0.25
- Input size (imgsz): 1280
- Tracker: BoT-SORT (persist=True)
- Classes: [0] (person)
- Output: web/public/media_crowd6_observations.json
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


def main():
    video_path = Path("web/public/crowd6.mp4")
    if not video_path.exists():
        video_path = Path("data/media/crowd6.mp4")
    output_json = Path("web/public/media_crowd6_observations.json")
    output_heatmap = Path("web/public/media_crowd6_heatmap.png")

    print(f"Loading video: {video_path}")
    cap = cv2.VideoCapture(str(video_path))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = round(total_frames / fps, 2)
    print(f"Video specs: {width}x{height}, {fps} FPS, {total_frames} frames, duration: {duration}s")

    model_path = Path("models/best.pt").resolve()
    print(f"Loading model: {model_path}")
    model = YOLO(str(model_path))

    # Existing zones for crowd6.mp4
    zone_a_poly = np.array([
        [100, 150],
        [600, 150],
        [550, 680],
        [80, 680],
    ], dtype=np.int32)

    zone_b_poly = np.array([
        [650, 150],
        [1200, 150],
        [1150, 680],
        [620, 680],
    ], dtype=np.int32)

    def point_in_poly(pt_x: float, pt_y: float, poly: np.ndarray) -> bool:
        return cv2.pointPolygonTest(poly, (float(pt_x), float(pt_y)), False) >= 0

    zones_metadata = [
        {
            "zone_id": "zone-a",
            "name": "Khu vực A (crowd6)",
            "color": "#0072B2",
            "vertices": zone_a_poly.tolist(),
        },
        {
            "zone_id": "zone-b",
            "name": "Khu vực B (crowd6)",
            "color": "#009E73",
            "vertices": zone_b_poly.tolist(),
        },
    ]

    frames_list = []
    accumulator = np.zeros((height, width), dtype=np.float32)

    print("Starting BoT-SORT tracking inference at imgsz=1280, conf=0.25...")
    start_time = time.time()
    frame_idx = 0

    while True:
        ret, frame_bgr = cap.read()
        if not ret or frame_bgr is None:
            break

        media_time_s = round(frame_idx / fps, 2)

        results = model.track(
            source=frame_bgr,
            persist=True,
            tracker="botsort.yaml",
            conf=0.25,
            imgsz=1280,
            classes=[0],
            verbose=False,
        )

        boxes = results[0].boxes
        detections = []
        count_zone_a = 0
        count_zone_b = 0

        if boxes is not None and len(boxes) > 0:
            coords = boxes.xyxy.detach().cpu().numpy()
            scores = boxes.conf.detach().cpu().numpy()
            track_ids = boxes.id.detach().cpu().numpy() if boxes.id is not None else None

            for i, box in enumerate(coords):
                x1, y1, x2, y2 = [float(v) for v in box]
                conf = float(scores[i])
                track_id = int(track_ids[i]) if (track_ids is not None and i < len(track_ids)) else None

                # Clamping
                x1 = min(max(x1, 0.0), float(width))
                x2 = min(max(x2, 0.0), float(width))
                y1 = min(max(y1, 0.0), float(height))
                y2 = min(max(y2, 0.0), float(height))
                if x2 <= x1 or y2 <= y1:
                    continue

                anchor_px_x = (x1 + x2) / 2.0
                anchor_px_y = y2
                norm_x = round(anchor_px_x / width, 4)
                norm_y = round(anchor_px_y / height, 4)

                # Heatmap accumulator
                px = int(round(min(max(anchor_px_x, 0.0), float(width - 1))))
                py = int(round(min(max(anchor_px_y, 0.0), float(height - 1))))
                accumulator[py, px] += 1.0

                # Zone membership
                in_a = point_in_poly(anchor_px_x, anchor_px_y, zone_a_poly)
                in_b = point_in_poly(anchor_px_x, anchor_px_y, zone_b_poly)
                if in_a:
                    count_zone_a += 1
                elif in_b:
                    count_zone_b += 1

                detections.append({
                    "track_id": track_id,
                    "x": norm_x,
                    "y": norm_y,
                    "confidence": round(conf, 3),
                    "bbox_xyxy": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                })

        frame_payload = {
            "frame_index": frame_idx,
            "media_time_s": media_time_s,
            "detections": detections,
            "zone_readings": [
                {
                    "status": "COUNTED",
                    "count": count_zone_a,
                    "zoneId": "zone-a",
                    "zoneName": "Khu vực A (crowd6)",
                },
                {
                    "status": "COUNTED",
                    "count": count_zone_b,
                    "zoneId": "zone-b",
                    "zoneName": "Khu vực B (crowd6)",
                },
            ],
        }
        frames_list.append(frame_payload)

        frame_idx += 1
        if frame_idx % 25 == 0 or frame_idx == total_frames:
            elapsed = time.time() - start_time
            fps_proc = frame_idx / elapsed if elapsed > 0 else 0
            eta = (total_frames - frame_idx) / fps_proc if fps_proc > 0 else 0
            curr_dets = len(detections)
            print(
                f"[{frame_idx:03d}/{total_frames}] "
                f"Detections: {curr_dets:3d} (Zone A: {count_zone_a:3d}, Zone B: {count_zone_b:3d}) | "
                f"{fps_proc:.1f} fps | ETA: {eta:.0f}s"
            )

    cap.release()
    total_elapsed = time.time() - start_time
    print(f"\nInference completed in {total_elapsed:.1f}s ({frame_idx} frames processed).")

    # Save observations JSON
    final_dataset = {
        "metadata": {
            "sourceId": "crowd6.mp4",
            "mediaName": "crowd6.mp4",
            "duration": duration,
            "fps": fps,
            "width": width,
            "height": height,
            "totalFrames": len(frames_list),
            "model": "models/best.pt (YOLO11s Finetuned)",
            "confidence": 0.25,
            "tracker": "BoT-SORT",
        },
        "zones": zones_metadata,
        "frames": frames_list,
    }

    print(f"Writing updated JSON to {output_json}...")
    with output_json.open("w", encoding="utf-8") as f:
        json.dump(final_dataset, f, ensure_ascii=False)
    print(f"Successfully saved {output_json.stat().st_size / 1024 / 1024:.2f} MB")

    # Generate Heatmap
    if accumulator.max() > 0:
        norm_acc = accumulator / accumulator.max()
        blurred = cv2.GaussianBlur(norm_acc, (31, 31), 0)
        blurred_norm = (blurred / (blurred.max() + 1e-6) * 255).astype(np.uint8)
        heatmap_colored = cv2.applyColorMap(blurred_norm, cv2.COLORMAP_JET)
        cv2.imwrite(str(output_heatmap), heatmap_colored)
        print(f"Saved crowd6 heatmap to {output_heatmap}")

    # Summary verification
    f0 = frames_list[0]
    f1 = frames_list[1]
    f2 = frames_list[2]
    print("\nVerification:")
    print(f"  Frame 0 detections: {len(f0['detections'])} (Zone A: {f0['zone_readings'][0]['count']}, Zone B: {f0['zone_readings'][1]['count']})")
    print(f"  Frame 1 detections: {len(f1['detections'])} (Zone A: {f1['zone_readings'][0]['count']}, Zone B: {f1['zone_readings'][1]['count']})")
    print(f"  Frame 2 detections: {len(f2['detections'])} (Zone A: {f2['zone_readings'][0]['count']}, Zone B: {f2['zone_readings'][1]['count']})")


if __name__ == "__main__":
    main()
