"""Run YOLO person detection on web/public/sample.mp4 and print results."""
from pathlib import Path

import cv2
from ultralytics import YOLO

video_path = Path("web/public/sample.mp4")
if not video_path.is_file():
    print(f"File not found: {video_path}")
    exit(1)

cap = cv2.VideoCapture(str(video_path))
fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
duration = total_frames / fps

print(f"Video: {video_path.name}")
print(f"Dimensions: {width}x{height}, FPS: {fps}, Total Frames: {total_frames}, Duration: {duration:.2f}s")

model = YOLO("yolo11n.pt")

# Test on 5 sample frames
sample_indices = [0, int(total_frames * 0.25), int(total_frames * 0.5), int(total_frames * 0.75), total_frames - 1]
for idx in sample_indices:
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ret, frame = cap.read()
    if not ret or frame is None:
        continue
    results = model.predict(frame, classes=[0], conf=0.25, verbose=False)
    boxes = results[0].boxes
    print(f"\nFrame {idx} (time: {idx/fps:.2f}s): {len(boxes)} person(s) detected")
    for box in boxes:
        xyxy = [round(float(v), 1) for v in box.xyxy[0].tolist()]
        conf = round(float(box.conf[0]), 2)
        print(f"  Person bbox: {xyxy}, conf: {conf}")

cap.release()
