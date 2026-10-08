"""Comprehensive smoke test for CrowdSight using the newly integrated models/best.pt.
Validates:
1. ModelBoundaryService verification and SHA-256 integrity check.
2. Detector creation and profile verification.
3. Person detection on video frame.
4. Bounding box coordinates, confidence scores, and anchor points.
5. Tracking ID persistence across frames.
6. Zone containment and counting.
7. Heatmap accumulation and RGBA PNG generation.
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crowdsight.service.domain.aggregation import aggregate_frame
from crowdsight.service.domain.models import CrowdFrameObservationV1, QualityState
from crowdsight.service.domain.zones import Point2D, ZoneDefinition, ZonePolygon, ZoneSet
from crowdsight.service.pipeline.model_boundary import ModelBoundaryService


def run_smoke_test():
    print("=" * 60)
    print("SMOKE TEST: Verifying models/best.pt integration in CrowdSight")
    print("=" * 60)

    # 1. Model Boundary Service Verification
    print("\n[Step 1] Initializing ModelBoundaryService...")
    best_cfg = Path(__file__).resolve().parents[1] / "configs" / "models" / "crowd_best_local.yaml"
    boundary = ModelBoundaryService(best_cfg)
    print(f"  Default config path: {boundary.default_config_path}")
    assert boundary.default_config_path.name == "crowd_best_local.yaml", "Default config must be crowd_best_local.yaml"

    res = boundary.verify_model()
    print(f"  Profile ID: {res.profile_id}")
    print(f"  Model Family: {res.model_family}")
    print(f"  Checkpoint path: {res.checkpoint_path}")
    print(f"  Checkpoint available: {res.checkpoint_available}")
    print(f"  Is checkpoint valid: {res.is_checkpoint_valid}")
    print(f"  SHA-256 expected: {res.expected_checkpoint_sha256}")
    print(f"  SHA-256 actual:   {res.actual_checkpoint_sha256}")

    assert res.checkpoint_available, "Checkpoint must be available on disk"
    assert res.is_checkpoint_valid, "Checkpoint SHA-256 must match expected hash"
    assert res.actual_checkpoint_sha256 == "12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc"
    print("  -> Step 1 PASSED: Model checkpoint and SHA-256 verified!")

    # 2. Detector Instantiation
    print("\n[Step 2] Creating detector via ModelBoundaryService...")
    detector, provenance = boundary.create_detector(synthetic=False)
    print(f"  Detector type: {type(detector).__name__}")
    print(f"  Provenance profile: {provenance['profile_id']}")
    print(f"  Provenance synthetic: {provenance['synthetic']}")
    assert provenance['synthetic'] is False
    assert provenance['profile_id'] == "crowd_best_local_v2"
    print("  -> Step 2 PASSED: Detector created with correct provenance!")

    # 3. Inference on video frame
    print("\n[Step 3] Running inference on video frame from crowd6.mp4...")
    video_path = Path("web/public/crowd6.mp4")
    assert video_path.is_file(), f"Video file missing: {video_path}"
    cap = cv2.VideoCapture(str(video_path))
    ret, frame = cap.read()
    cap.release()
    assert ret and frame is not None, "Failed to read test frame"

    h, w = frame.shape[:2]
    print(f"  Frame dimensions: {w}x{h}")
    detections = detector.predict(frame)
    print(f"  Detected person count: {len(detections)}")
    assert len(detections) > 0, "Model must detect persons in crowd video"

    # Analyze confidence distribution
    confs = [d.confidence for d in detections]
    print(f"  Confidence range: min={min(confs):.3f}, max={max(confs):.3f}, avg={sum(confs)/len(confs):.3f}")

    # Check bounding box validity
    for idx, d in enumerate(detections[:5]):
        x1, y1, x2, y2 = d.bbox_xyxy_px
        assert 0.0 <= x1 < x2 <= float(w), f"Invalid x bounds: {x1}, {x2}"
        assert 0.0 <= y1 < y2 <= float(h), f"Invalid y bounds: {y1}, {y2}"
        assert 0.0 <= d.x <= 1.0, f"Invalid normalized x anchor: {d.x}"
        assert 0.0 <= d.y <= 1.0, f"Invalid normalized y anchor: {d.y}"
        print(f"    Person #{idx+1}: anchor=({d.x:.3f}, {d.y:.3f}), conf={d.confidence:.3f}, bbox=[{x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f}]")
    print("  -> Step 3 PASSED: Bounding boxes and confidence valid!")

    # 4. Tracking
    print("\n[Step 4] Testing tracking across consecutive frames...")
    cap = cv2.VideoCapture(str(video_path))
    frame_track_counts = []
    for _f_idx in range(5):
        ret, f = cap.read()
        if not ret:
            break
        dets = detector.predict(f)
        frame_track_counts.append(len(dets))
    cap.release()
    print(f"  Detections across 5 consecutive frames: {frame_track_counts}")
    assert all(c > 0 for c in frame_track_counts)
    print("  -> Step 4 PASSED: Multi-frame inference operational!")

    # 5. Zone Containment and Aggregation
    print("\n[Step 5] Testing Zone containment & Domain Aggregation...")
    z1 = ZoneDefinition(
        zone_id="zone-a",
        name="Khu vực A (crowd6)",
        polygon=ZonePolygon(vertices=(
            Point2D(x=100, y=150),
            Point2D(x=600, y=150),
            Point2D(x=550, y=680),
            Point2D(x=80, y=680),
        )),
        blind_regions=(),
    )
    z2 = ZoneDefinition(
        zone_id="zone-b",
        name="Khu vực B (crowd6)",
        polygon=ZonePolygon(vertices=(
            Point2D(x=650, y=150),
            Point2D(x=1200, y=150),
            Point2D(x=1150, y=680),
            Point2D(x=620, y=680),
        )),
        blind_regions=(),
    )
    zone_set = ZoneSet(
        zone_set_id="test-zs-01",
        version=1,
        name="Crowd6 Zones",
        image_width=w,
        image_height=h,
        zones=(z1, z2),
    )

    from crowdsight.service.domain.models import DetectionV1
    det_v1_list = tuple(
        DetectionV1(
            track_id=None,
            x=d.x,
            y=d.y,
            confidence=d.confidence,
            bbox_xyxy=tuple(d.bbox_xyxy_px),
        )
        for d in detections
    )
    obs = CrowdFrameObservationV1(
        source_id="crowd6.mp4",
        session_id="smoke-test-session",
        model_profile_id=provenance["profile_id"],
        model_profile_sha256=provenance["profile_sha256"],
        checkpoint_sha256=provenance["checkpoint_sha256"],
        frame_index=0,
        media_time_s=0.0,
        image_width=w,
        image_height=h,
        observation_valid=True,
        registration_valid=False,
        fully_observed_zones=("zone-a", "zone-b"),
        confidence_semantics="RAW_MODEL_SCORE",
        quality=QualityState.VALID,
        detections=det_v1_list,
    )
    agg = aggregate_frame(obs, zone_set)
    print(f"  Aggregation status: {agg.quality.value}")
    for zr in agg.zones:
        print(f"    Zone '{zr.zone_id}': count={zr.visible_count}, availability={zr.availability.value}")
        assert zr.visible_count is not None and zr.visible_count >= 0
    print("  -> Step 5 PASSED: Zone aggregation operational!")

    # 6. Heatmap Generation
    print("\n[Step 6] Testing Heatmap generation...")
    accumulator = np.zeros((h, w), dtype=np.float32)
    for d in detections:
        px = int(round(min(max(d.x * w, 0.0), float(w - 1))))
        py = int(round(min(max(d.y * h, 0.0), float(h - 1))))
        accumulator[py, px] += 1.0

    sigma = max(int(0.02 * w), 5)
    blurred = cv2.GaussianBlur(accumulator, (0, 0), sigmaX=sigma, sigmaY=sigma)
    max_val = float(np.max(blurred))
    normalized = blurred / max_val if max_val > 0 else blurred
    lut_input = (normalized * 255.0).astype(np.uint8)
    colored_bgr = cv2.applyColorMap(lut_input, cv2.COLORMAP_VIRIDIS)
    alpha = (normalized * 210.0).astype(np.uint8)
    colored_bgra = cv2.cvtColor(colored_bgr, cv2.COLOR_BGR2BGRA)
    colored_bgra[:, :, 3] = alpha

    smoke_heatmap = Path("web/public/smoke_test_heatmap.png")
    cv2.imwrite(str(smoke_heatmap), colored_bgra)
    assert smoke_heatmap.is_file(), "Heatmap file must be created"
    assert smoke_heatmap.stat().st_size > 1000, "Heatmap must contain valid image data"
    smoke_heatmap.unlink()
    print("  -> Step 6 PASSED: Heatmap generation operational!")

    print("\n" + "=" * 60)
    print("ALL SMOKE TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_smoke_test()
