"""Versioned PKLot crop runtime; model frameworks stay behind this boundary.

Coverage and camera registration are caller evidence, not classifier outputs.
No visible-space declaration means UNKNOWN for every space.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Sequence

import numpy as np

from crowdsight.common.observations import QualityState
from crowdsight.common.parking import ParkingFrameObservation, ParkingSpaceResult, ParkingState
from crowdsight.parking.adapter import load_parking_model_profile, verify_parking_checkpoint

PREPROCESSING = "pklot_bbox_area64_jpeg95_rgb_v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class ParkingCropClassifier:
    """TinyCNN A3 / ViT-B16 C inference using an immutable runtime profile."""

    def __init__(self, profile_path: Path, *, checkpoint_path: Path,
                 layout_path: Path, device: str = "cpu", batch_size: int = 32):
        import yaml

        self.profile = load_parking_model_profile(profile_path, checkpoint_path=checkpoint_path)
        raw = Path(profile_path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != self.profile.profile_sha256:
            raise ValueError("Profile changed during load")
        config = yaml.safe_load(raw)
        runtime = config.get("runtime", {})
        if runtime.get("adapter_version") != "parking_crop_v1" or runtime.get("preprocessing") != PREPROCESSING:
            raise ValueError("Unsupported parking adapter/preprocessing version")
        if runtime.get("precision") != "float32" or runtime.get("coverage_source") != "caller_per_frame":
            raise ValueError("Unsupported runtime precision/coverage policy")
        self.arch = runtime.get("architecture")
        if self.arch not in ("tinycnn", "vit_b16"):
            raise ValueError("Unsupported parking architecture")
        if runtime.get("classes") != {"0": "AVAILABLE", "1": "OCCUPIED"}:
            raise ValueError("Unsupported class mapping")
        self.threshold = runtime.get("decision_threshold")
        self.margin = runtime.get("abstention_margin")
        for name, value in (("decision_threshold", self.threshold), ("abstention_margin", self.margin)):
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if not 0 < self.threshold < 1 or not 0 <= self.margin < min(self.threshold, 1 - self.threshold):
            raise ValueError("Invalid threshold/abstention margin")
        if type(batch_size) is not int or batch_size < 1:
            raise ValueError("batch_size must be positive")
        self.batch_size = batch_size
        layout_bytes = Path(layout_path).read_bytes()
        self.layout_sha256 = hashlib.sha256(layout_bytes).hexdigest()
        if self.layout_sha256 != runtime.get("layout_sha256"):
            raise ValueError("Layout SHA-256 mismatch")
        layout = json.loads(layout_bytes)
        for key in ("site_id", "camera_view_id", "space_layout_version"):
            if layout.get(key) != getattr(self.profile, key):
                raise ValueError(f"Layout {key} mismatch")
        size = layout["image_size"]
        self.width, self.height = size["width"], size["height"]
        if any(type(n) is not int or n < 1 for n in (self.width, self.height)):
            raise ValueError("Invalid layout image size")
        self.boxes = {}
        for space in layout["spaces"]:
            sid, polygon = space["space_id"], space["polygon"]
            if not isinstance(sid, str) or not sid.strip() or sid in self.boxes:
                raise ValueError("Layout IDs must be unique nonempty strings")
            if not isinstance(polygon, list) or len(polygon) < 3:
                raise ValueError("Layout polygon requires at least three vertices")
            points = [(p["x"], p["y"]) for p in polygon]
            if any(type(n) is not int for p in points for n in p):
                raise ValueError("This preprocessing version requires integer pixel vertices")
            xs, ys = zip(*points)
            area2 = sum(points[i][0] * points[(i + 1) % len(points)][1]
                        - points[(i + 1) % len(points)][0] * points[i][1]
                        for i in range(len(points)))
            if area2 == 0:
                raise ValueError("Degenerate layout polygon")
            self.boxes[sid] = (min(xs), min(ys), max(xs), max(ys))
        if not self.boxes:
            raise ValueError("Layout must contain spaces")
        self.space_ids = tuple(self.boxes)
        self.profile_id = self.profile.profile_id
        checkpoint = verify_parking_checkpoint(self.profile)

        import torch
        from torch import nn
        from torch.torch_version import TorchVersion

        self.torch = torch
        self.device = torch.device(device)
        with torch.serialization.safe_globals([TorchVersion]):
            payload = torch.load(checkpoint, map_location="cpu", weights_only=True)
        if payload.get("meta", {}).get("classes") != runtime["classes"]:
            raise ValueError("Checkpoint class mapping mismatch")
        self.checkpoint_metadata = payload["meta"]
        if self.arch == "tinycnn":
            # Names/shapes match the returned A3 state_dict exactly.
            model = nn.Module()
            model.net = nn.Sequential(
                nn.Conv2d(3, 16, 3, stride=2, padding=1), nn.BatchNorm2d(16), nn.ReLU(),
                nn.Conv2d(16, 32, 3, stride=2, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
                nn.Conv2d(32, 64, 3, stride=2, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
                nn.AdaptiveAvgPool2d(1), nn.Flatten(), nn.Linear(64, 1),
            )
        else:
            from torchvision.models import vit_b_16
            model = vit_b_16(weights=None)
            model.heads.head = nn.Linear(model.heads.head.in_features, 1)
        model.load_state_dict(payload["state_dict"], strict=True)
        self.model = model.to(device=self.device, dtype=torch.float32).eval()

    def score_rgb_crops(self, crops: Sequence[np.ndarray]) -> list[float]:
        """Score decoded 64x64 RGB crops; shared with crop-level diagnostics."""
        from torchvision.transforms import functional as TF
        torch = self.torch
        scores = []
        for start in range(0, len(crops), self.batch_size):
            tensors = []
            for crop in crops[start:start + self.batch_size]:
                if crop.shape != (64, 64, 3) or crop.dtype != np.uint8:
                    raise ValueError("Expected uint8 64x64 RGB crop")
                tensor = TF.to_tensor(crop)
                if self.arch == "vit_b16":
                    tensor = TF.resize(tensor, [224, 224], interpolation=TF.InterpolationMode.BICUBIC, antialias=True)
                    tensor = TF.normalize(tensor, (0.485, 0.456, 0.406), (0.229, 0.224, 0.225))
                else:
                    tensor = TF.normalize(tensor, (0.5,) * 3, (0.25,) * 3)
                tensors.append(tensor)
            with torch.inference_mode():
                batch = torch.stack(tensors).to(self.device)
                logits = self.model.net(batch) if self.arch == "tinycnn" else self.model(batch)
                logits = logits.float().reshape(-1)
                probabilities = torch.where(torch.isfinite(logits), torch.sigmoid(logits), float("nan"))
                scores.extend(probabilities.cpu().tolist())
        return scores

    def observe(self, frame_bgr: np.ndarray | None, *, site_id: str, camera_view_id: str,
                space_layout_version: str, source_id: str, session_id: str,
                frame_index: int, media_time_s: float, visible_space_ids: Sequence[str] = (),
                registration_valid: bool = False, stale: bool = False) -> ParkingFrameObservation:
        """Caller supplies per-frame coverage and registration; defaults abstain.

        Exceptions fail the job; they must never be translated into zero occupancy.
        Invalid pixels/resolution or unconfirmed registration produce UNKNOWN.
        """
        import cv2
        from PIL import Image
        import io

        for key, value in (("site_id", site_id), ("camera_view_id", camera_view_id),
                           ("space_layout_version", space_layout_version)):
            if value != getattr(self.profile, key):
                raise ValueError(f"Requested {key} differs from profile")
        if type(registration_valid) is not bool or type(stale) is not bool:
            raise ValueError("registration_valid and stale must be booleans")
        if (isinstance(visible_space_ids, (str, bytes))
                or any(not isinstance(sid, str) for sid in visible_space_ids)
                or len(set(visible_space_ids)) != len(visible_space_ids)
                or not set(visible_space_ids) <= set(self.space_ids)):
            raise ValueError("Visible space IDs must be unique configured IDs")
        states = {sid: ParkingSpaceResult(sid, ParkingState.UNKNOWN, None, media_time_s)
                  for sid in self.space_ids}
        # Validate metadata before expensive inference.
        observation_args = dict(site_id=site_id, camera_view_id=camera_view_id,
                                space_layout_version=space_layout_version, source_id=source_id,
                                session_id=session_id, frame_index=frame_index, media_time_s=media_time_s,
                                model_profile_id=self.profile_id, model_profile_sha256=self.profile.profile_sha256,
                                checkpoint_sha256=self.profile.expected_sha256)
        ParkingFrameObservation(**observation_args, quality=QualityState.UNKNOWN, spaces=tuple(states.values()))
        usable = (not stale and registration_valid and isinstance(frame_bgr, np.ndarray)
                  and frame_bgr.dtype == np.uint8 and frame_bgr.shape == (self.height, self.width, 3))
        crops, ids = [], []
        if usable:
            for sid in visible_space_ids:
                x0, y0, x1, y1 = self.boxes[sid]
                if not (0 <= x0 < x1 < self.width and 0 <= y0 < y1 < self.height):
                    continue
                if x1 - x0 < 8 or y1 - y0 < 8:
                    continue
                crop = cv2.resize(frame_bgr[y0:y1, x0:x1], (64, 64), interpolation=cv2.INTER_AREA)
                ok, encoded = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
                if not ok:
                    raise RuntimeError("Crop encoding failed")
                with Image.open(io.BytesIO(encoded.tobytes())) as image:
                    crops.append(np.array(image.convert("RGB")))
                ids.append(sid)
            for sid, score in zip(ids, self.score_rgb_crops(crops)):
                if not math.isfinite(score) or abs(score - self.threshold) < self.margin:
                    continue
                state = ParkingState.OCCUPIED if score >= self.threshold else ParkingState.AVAILABLE
                states[sid] = ParkingSpaceResult(sid, state, score if state is ParkingState.OCCUPIED else 1 - score, media_time_s)
        known = sum(item.state is not ParkingState.UNKNOWN for item in states.values())
        quality = (QualityState.STALE if stale else QualityState.UNKNOWN if not known
                   else QualityState.VALID if known == len(states) else QualityState.PARTIAL)
        return ParkingFrameObservation(**observation_args, quality=quality, spaces=tuple(states.values()))
