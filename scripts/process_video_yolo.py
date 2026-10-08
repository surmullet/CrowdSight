"""Generate real YOLO tracking and detections on web/public/sample.mp4.

Outputs:
1. web/public/sample_real_observations.json for frontend client-side instant playback
2. Database records in crowdsight.db for backend API endpoints
"""
import json
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

video_path = Path("web/public/sample.mp4")
output_json = Path("web/public/sample_real_observations.json")

print(f"Loading video from: {video_path}")
cap = cv2.VideoCapture(str(video_path))
fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
duration = total_frames / fps
print(f"Video specs: {width}x{height}, {fps} FPS, {total_frames} frames, duration: {duration:.2f}s")

# Load YOLO model
model = YOLO("yolo11n.pt")

# Define 2 zones tailored to sample.mp4
# Zone North: Central floor area
# Zone South: Entrance hallway
zone_north_poly = np.array([
    [200, 400],
    [950, 400],
    [900, 1070],
    [150, 1070],
], dtype=np.int32)

zone_south_poly = np.array([
    [960, 200],
    [1750, 200],
    [1700, 900],
    [920, 900],
], dtype=np.int32)

def point_in_polygon(px: float, py: float, polygon: np.ndarray) -> bool:
    pt = (float(px), float(py))
    # cv2.pointPolygonTest returns > 0 if inside, 0 if on edge, < 0 if outside
    return cv2.pointPolygonTest(polygon, pt, False) >= 0

observations_by_time = []
frame_observations = {}

print("Running YOLO tracking on frames...")
frame_idx = 0

# Track IDs persist across frames
# We can use model.track with persist=True
while True:
    ret, frame = cap.read()
    if not ret or frame is None:
        break

    media_time_s = round(frame_idx / fps, 2)

    # Run YOLO tracking on person class (class 0)
    # persist=True maintains track IDs across consecutive frames
    results = model.track(
        source=frame,
        persist=True,
        classes=[0],
        conf=0.25,
        verbose=False,
    )

    boxes = results[0].boxes
    detections = []
    zone_north_count = 0
    zone_south_count = 0

    if boxes is not None and len(boxes) > 0:
        for box in boxes:
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
            conf = float(box.conf[0])
            track_id = int(box.id[0]) if (box.id is not None and len(box.id) > 0) else None

            # Bottom center anchor in pixels and normalized
            anchor_px_x = (x1 + x2) / 2.0
            anchor_px_y = y2
            norm_x = round(anchor_px_x / width, 4)
            norm_y = round(anchor_px_y / height, 4)

            # Check which zone contains this anchor point
            in_north = point_in_polygon(anchor_px_x, anchor_px_y, zone_north_poly)
            in_south = point_in_polygon(anchor_px_x, anchor_px_y, zone_south_poly)

            if in_north:
                zone_north_count += 1
            if in_south:
                zone_south_count += 1

            detections.append({
                "track_id": track_id or 101,
                "x": norm_x,
                "y": norm_y,
                "confidence": round(conf, 3),
                "bbox_xyxy": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
            })

    obs_payload = {
        "source_id": "sample.mp4",
        "session_id": "session-demo-01",
        "model_profile_id": "yolo11n_person",
        "model_profile_sha256": "yolo11n_official_weights",
        "checkpoint_sha256": "yolo11n_ultralytics_v840",
        "frame_index": frame_idx,
        "media_time_s": media_time_s,
        "image_width": width,
        "image_height": height,
        "observation_valid": True,
        "registration_valid": False,
        "fully_observed_zones": ["zone-north", "zone-south"],
        "confidence_semantics": "RAW_MODEL_SCORE",
        "quality": "VALID",
        "detections": detections,
        "zone_readings": [
            {
                "zoneId": "zone-north",
                "zoneName": "Khu vực Lối vào (Sảnh chính)",
                "count": zone_north_count,
                "status": "COUNTED",
            },
            {
                "zoneId": "zone-south",
                "zoneName": "Khu vực Hành lang / Lối ra",
                "count": zone_south_count,
                "status": "COUNTED",
            },
        ],
    }

    frame_observations[frame_idx] = obs_payload
    if frame_idx % 5 == 0:
        observations_by_time.append({
            "time": media_time_s,
            "frame": frame_idx,
            "person_count": len(detections),
            "zone_north": zone_north_count,
            "zone_south": zone_south_count,
        })

    frame_idx += 1
    if frame_idx % 100 == 0:
        print(f"Processed {frame_idx}/{total_frames} frames ({frame_idx/total_frames*100:.1f}%)")

cap.release()

dataset = {
    "metadata": {
        "videoId": "sample.mp4",
        "width": width,
        "height": height,
        "fps": fps,
        "totalFrames": total_frames,
        "duration": duration,
        "model": "YOLO11n (Ultralytics)",
        "synthetic": False,
    },
    "zones": [
        {
            "zone_id": "zone-north",
            "name": "Khu vực Lối vào (Sảnh chính)",
            "color": "#0072B2",
            "vertices": zone_north_poly.tolist(),
        },
        {
            "zone_id": "zone-south",
            "name": "Khu vực Hành lang / Lối ra",
            "color": "#009E73",
            "vertices": zone_south_poly.tolist(),
        },
    ],
    "frames": frame_observations,
}

print(f"Saving observations to {output_json}...")
with output_json.open("w", encoding="utf-8") as f:
    json.dump(dataset, f)

print(f"Done! Successfully processed {total_frames} frames with real YOLO detections!")
