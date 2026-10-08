"""Process 150.mp4 with real YOLO11 detection and generate observations JSON and heatmap."""
import json
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

video_path = Path("data/media/150.mp4")
output_json = Path("web/public/media_150_observations.json")
output_heatmap = Path("web/public/media_150_heatmap.png")

if not video_path.is_file():
    print(f"Error: {video_path} not found")
    exit(1)

print(f"Processing {video_path}...")
cap = cv2.VideoCapture(str(video_path))
fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
duration = total_frames / fps
print(f"Specs: {width}x{height}, {fps} FPS, {total_frames} frames, duration: {duration:.2f}s")

model = YOLO("yolo11n.pt")

# Default zones for 150.mp4
# Zone A (Left/Center area) and Zone B (Right area)
zone_a_poly = np.array([
    [int(width * 0.1), int(height * 0.3)],
    [int(width * 0.55), int(height * 0.3)],
    [int(width * 0.5), int(height * 0.95)],
    [int(width * 0.05), int(height * 0.95)],
], dtype=np.int32)

zone_b_poly = np.array([
    [int(width * 0.55), int(height * 0.25)],
    [int(width * 0.95), int(height * 0.25)],
    [int(width * 0.95), int(height * 0.95)],
    [int(width * 0.50), int(height * 0.95)],
], dtype=np.int32)

def point_in_polygon(px: float, py: float, polygon: np.ndarray) -> bool:
    return cv2.pointPolygonTest(polygon, (float(px), float(py)), False) >= 0

frame_observations = {}
accumulator = np.zeros((height, width), dtype=np.float32)

frame_idx = 0
while True:
    ret, frame = cap.read()
    if not ret or frame is None:
        break

    media_time_s = round(frame_idx / fps, 2)

    results = model.track(
        source=frame,
        persist=True,
        classes=[0],
        conf=0.25,
        verbose=False,
    )

    boxes = results[0].boxes
    detections = []
    zone_a_count = 0
    zone_b_count = 0

    if boxes is not None and len(boxes) > 0:
        for box in boxes:
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
            conf = float(box.conf[0])
            track_id = int(box.id[0]) if (box.id is not None and len(box.id) > 0) else None

            anchor_px_x = (x1 + x2) / 2.0
            anchor_px_y = y2
            norm_x = round(anchor_px_x / width, 4)
            norm_y = round(anchor_px_y / height, 4)

            # Accumulate for heatmap
            px = int(round(min(max(anchor_px_x, 0.0), float(width - 1))))
            py = int(round(min(max(anchor_px_y, 0.0), float(height - 1))))
            accumulator[py, px] += 1.0

            in_a = point_in_polygon(anchor_px_x, anchor_px_y, zone_a_poly)
            in_b = point_in_polygon(anchor_px_x, anchor_px_y, zone_b_poly)

            if in_a:
                zone_a_count += 1
            if in_b:
                zone_b_count += 1

            detections.append({
                "track_id": track_id or 1,
                "x": norm_x,
                "y": norm_y,
                "confidence": round(conf, 3),
                "bbox_xyxy": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
            })

    frame_observations[frame_idx] = {
        "source_id": "150.mp4",
        "session_id": "session-150-real",
        "model_profile_id": "yolo11n_person",
        "model_profile_sha256": "yolo11n_official_weights",
        "checkpoint_sha256": "yolo11n_ultralytics_v840",
        "frame_index": frame_idx,
        "media_time_s": media_time_s,
        "image_width": width,
        "image_height": height,
        "observation_valid": True,
        "registration_valid": False,
        "fully_observed_zones": ["zone-a", "zone-b"],
        "confidence_semantics": "RAW_MODEL_SCORE",
        "quality": "VALID",
        "detections": detections,
        "zone_readings": [
            {
                "zoneId": "zone-a",
                "zoneName": "Khu vực Giám sát A (Bên trái)",
                "count": zone_a_count,
                "status": "COUNTED",
            },
            {
                "zoneId": "zone-b",
                "zoneName": "Khu vực Giám sát B (Bên phải)",
                "count": zone_b_count,
                "status": "COUNTED",
            },
        ],
    }

    frame_idx += 1
    if frame_idx % 150 == 0:
        print(f"Processed {frame_idx}/{total_frames} frames ({frame_idx/total_frames*100:.1f}%)")

cap.release()

# Generate Heatmap image
sigma = max(int(0.02 * width), 5)
blurred = cv2.GaussianBlur(accumulator, (0, 0), sigmaX=sigma, sigmaY=sigma)
max_val = float(np.max(blurred))
if max_val > 0:
    normalized = blurred / max_val
else:
    normalized = blurred

lut_input = (normalized * 255.0).astype(np.uint8)
colored_bgr = cv2.applyColorMap(lut_input, cv2.COLORMAP_VIRIDIS)
alpha_channel = (normalized * 210.0).astype(np.uint8)
colored_bgra = cv2.cvtColor(colored_bgr, cv2.COLOR_BGR2BGRA)
colored_bgra[:, :, 3] = alpha_channel

cv2.imwrite(str(output_heatmap), colored_bgra)
print(f"Saved heatmap to {output_heatmap}")

dataset = {
    "metadata": {
        "videoId": "150.mp4",
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
            "zone_id": "zone-a",
            "name": "Khu vực Giám sát A (Bên trái)",
            "color": "#0072B2",
            "vertices": zone_a_poly.tolist(),
        },
        {
            "zone_id": "zone-b",
            "name": "Khu vực Giám sát B (Bên phải)",
            "color": "#009E73",
            "vertices": zone_b_poly.tolist(),
        },
    ],
    "frames": frame_observations,
}

with output_json.open("w", encoding="utf-8") as f:
    json.dump(dataset, f)

print(f"Successfully processed 150.mp4: {total_frames} frames saved to {output_json}!")
