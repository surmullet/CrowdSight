"""Model-independent person detector interface and integrity-checked YOLO adapter."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import platform
from pathlib import Path
from typing import Optional, Protocol, Sequence

import numpy as np

from crowdsight.common.observations import PersonDetection


@dataclass(frozen=True, slots=True)
class PersonDetectorProfile:
    """Runtime settings paired with one immutable checkpoint identity."""

    profile_id: str
    checkpoint_path: Path
    expected_sha256: str
    profile_sha256: str
    person_class_id: int = 0
    confidence: float = 0.25
    image_size: int = 1280
    device: str = "auto"

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str) or not self.profile_id.strip():
            raise ValueError("profile_id must be nonempty")
        if not isinstance(self.expected_sha256, str) or len(self.expected_sha256) != 64 or any(
            c not in "0123456789abcdefABCDEF" for c in self.expected_sha256
        ):
            raise ValueError("expected_sha256 must be a 64-character hex digest")
        if not isinstance(self.profile_sha256, str) or len(self.profile_sha256) != 64 or any(
            c not in "0123456789abcdefABCDEF" for c in self.profile_sha256
        ):
            raise ValueError("profile_sha256 must be a 64-character hex digest")
        if type(self.confidence) not in (int, float) or not math.isfinite(self.confidence) or not 0.0 < self.confidence <= 1.0:
            raise ValueError("confidence must be in (0, 1]")
        if type(self.image_size) is not int or type(self.person_class_id) is not int or self.image_size <= 0 or self.person_class_id < 0:
            raise ValueError("image_size must be positive and class ID nonnegative")
        if not isinstance(self.device, str) or not self.device.strip():
            raise ValueError("device must be a nonempty string")


class PersonDetector(Protocol):
    """Adapter contract consumed by pipeline orchestration."""

    profile_id: str

    def predict(self, frame_bgr: np.ndarray) -> Sequence[PersonDetection]:
        """Return person observations for one BGR frame."""


class PersonTracker(Protocol):
    """Sequential anonymous tracker contract, one instance per video session."""

    profile_id: str

    def track(self, frame_bgr: np.ndarray) -> Sequence[PersonDetection]:
        """Return only current observations with confirmed run-local IDs."""


class UltralyticsPersonDetector:
    """YOLO-compatible detector that verifies weights and emits shared anchors.

    Ultralytics is imported lazily. Model-specific logic remains behind this
    adapter. Each result includes a normalized bottom-centre anchor for zone
    membership and retains a pixel box only as internal rendering metadata.
    """

    def __init__(self, profile: PersonDetectorProfile) -> None:
        self.profile_id = profile.profile_id
        self._profile = profile
        self.profile_sha256 = profile.profile_sha256.lower()
        checkpoint = profile.checkpoint_path.expanduser().resolve()
        if not checkpoint.is_file():
            raise FileNotFoundError(f"Checkpoint unavailable: {checkpoint}")
        digest = self.sha256_file(checkpoint)
        if digest.lower() != profile.expected_sha256.lower():
            raise ValueError(
                f"Checkpoint SHA-256 mismatch for {checkpoint}: "
                f"expected {profile.expected_sha256}, got {digest}"
            )
        self.checkpoint_sha256 = digest.lower()
        try:
            import ultralytics
            from ultralytics import YOLO
            import torch
        except ImportError as exc:
            raise RuntimeError(
                "Ultralytics and PyTorch are required for this detector profile"
            ) from exc
        if profile.device.strip().lower() == "auto":
            self._device = "cuda:0" if torch.cuda.is_available() else "cpu"
        elif profile.device.strip().lower().startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested for the model profile but is unavailable")
        else:
            self._device = profile.device
        cuda_index = 0
        if self._device.startswith("cuda:"):
            cuda_index = int(self._device.split(":", 1)[1])
        self.runtime_metadata = {
            "ultralytics_version": getattr(ultralytics, "__version__", "unknown"),
            "model_profile_sha256": self.profile_sha256,
            "pytorch_version": str(torch.__version__),
            "cuda_runtime_version": getattr(torch.version, "cuda", None),
            "cudnn_version": torch.backends.cudnn.version(),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "numpy_version": np.__version__,
            "device": self._device,
            "cuda_available": bool(torch.cuda.is_available()),
            "device_name": (
                torch.cuda.get_device_name(cuda_index)
                if self._device.startswith("cuda") and torch.cuda.is_available()
                else "CPU"
            ),
            "confidence_threshold": profile.confidence,
            "image_size": profile.image_size,
            "person_class_id": profile.person_class_id,
        }
        self._model = YOLO(str(checkpoint))

    @staticmethod
    def sha256_file(path: Path) -> str:
        """Return a streaming SHA-256 digest without loading weights into memory."""
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def predict(self, frame_bgr: np.ndarray) -> tuple[PersonDetection, ...]:
        """Run person-only inference on a single BGR image."""
        if not isinstance(frame_bgr, np.ndarray) or frame_bgr.ndim != 3:
            raise ValueError("frame_bgr must be a three-dimensional NumPy image")
        height, width = frame_bgr.shape[:2]
        if width <= 0 or height <= 0 or frame_bgr.shape[2] != 3:
            raise ValueError("frame_bgr must have positive dimensions and 3 channels")
        outputs = self._model.predict(
            source=frame_bgr,
            conf=self._profile.confidence,
            imgsz=self._profile.image_size,
            device=self._device,
            classes=[self._profile.person_class_id],
            verbose=False,
        )
        return self._decode_result(outputs[0] if outputs else None, width, height)

    def _decode_result(
        self,
        result: object,
        width: int,
        height: int,
        track_ids: Optional[np.ndarray] = None,
    ) -> tuple[PersonDetection, ...]:
        """Convert one Ultralytics result to normalized person anchors."""
        if result is None or result.boxes is None:
            return ()
        boxes = result.boxes
        coords = boxes.xyxy.detach().cpu().numpy()
        scores = boxes.conf.detach().cpu().numpy()
        classes = boxes.cls.detach().cpu().numpy().astype(int)
        detections: list[PersonDetection] = []
        fields = zip(coords, scores, classes) if track_ids is None else zip(
            coords, scores, classes, track_ids
        )
        for row in fields:
            box, score, class_id = row[:3]
            track_id = None if track_ids is None else int(row[3])
            if class_id != self._profile.person_class_id:
                continue
            x1, y1, x2, y2 = (float(v) for v in box)
            confidence = float(score)
            if not all(math.isfinite(v) for v in (x1, y1, x2, y2, confidence)):
                continue
            if x2 <= x1 or y2 <= y1 or not 0.0 <= confidence <= 1.0:
                continue
            x1 = min(max(x1, 0.0), float(width))
            x2 = min(max(x2, 0.0), float(width))
            y1 = min(max(y1, 0.0), float(height))
            y2 = min(max(y2, 0.0), float(height))
            if x2 <= x1 or y2 <= y1:
                continue
            detections.append(
                PersonDetection(
                    x=((x1 + x2) / 2.0) / width,
                    y=y2 / height,
                    confidence=confidence,
                    track_id=track_id,
                    bbox_xyxy_px=(x1, y1, x2, y2),
                )
            )
        return tuple(detections)


class UltralyticsPersonTracker(UltralyticsPersonDetector):
    """Sequential Ultralytics tracker, configured by an approved tracker YAML.

    Create a new adapter instance for each source/session. Only tracks attached
    to current returned detections are emitted; lost/predicted tracks are never
    synthesized as observed people. Tracker implementation and IDs remain
    temporary and local to the instance.
    """

    def __init__(
        self,
        profile: PersonDetectorProfile,
        tracker_config: Path,
        expected_tracker_sha256: str,
    ) -> None:
        super().__init__(profile)
        self._tracker_config = tracker_config.expanduser().resolve()
        if not self._tracker_config.is_file():
            raise FileNotFoundError(f"Tracker config unavailable: {self._tracker_config}")
        if len(expected_tracker_sha256) != 64 or any(
            c not in "0123456789abcdefABCDEF" for c in expected_tracker_sha256
        ):
            raise ValueError("expected_tracker_sha256 must be a 64-character hex digest")
        actual_tracker_hash = self.sha256_file(self._tracker_config)
        if actual_tracker_hash.lower() != expected_tracker_sha256.lower():
            raise ValueError(
                f"Tracker config SHA-256 mismatch: expected {expected_tracker_sha256}, "
                f"got {actual_tracker_hash}"
            )
        self.tracker_config_sha256 = actual_tracker_hash.lower()

    def track(self, frame_bgr: np.ndarray) -> tuple[PersonDetection, ...]:
        if not isinstance(frame_bgr, np.ndarray) or frame_bgr.ndim != 3:
            raise ValueError("frame_bgr must be a three-dimensional NumPy image")
        height, width = frame_bgr.shape[:2]
        if width <= 0 or height <= 0 or frame_bgr.shape[2] != 3:
            raise ValueError("frame_bgr must have positive dimensions and 3 channels")
        outputs = self._model.track(
            source=frame_bgr,
            persist=True,
            tracker=str(self._tracker_config),
            conf=self._profile.confidence,
            imgsz=self._profile.image_size,
            device=self._device,
            classes=[self._profile.person_class_id],
            verbose=False,
        )
        result = outputs[0] if outputs else None
        if result is None or result.boxes is None or result.boxes.id is None:
            return ()
        ids = result.boxes.id.detach().cpu().numpy().astype(int)
        if len(ids) != len(result.boxes.xyxy):
            raise RuntimeError("Tracker ID count does not match returned boxes")
        return self._decode_result(result, width, height, ids)
