"""Relative image-space heat map generator with perceptual colormap and transparency."""
from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from crowdsight.service.domain.zones import ZoneSet


@dataclass(frozen=True, slots=True)
class HeatmapMetadata:
    kind: str
    image_width: int
    image_height: int
    window_from_t: float | None
    window_to_t: float | None
    frames_used: int
    frames_discarded: int
    normalization_method: str
    colormap: str
    sha256: str
    disclaimer: str


@dataclass(frozen=True, slots=True)
class HeatmapGenerationResult:
    png_bytes: bytes
    metadata: HeatmapMetadata


class ImageSpaceHeatmapGenerator:
    """Generates 2D Gaussian image-space relative heat maps.

    Strict invariant: Always relative to source frame coordinates (IMAGE_SPACE).
    Never geographic, never density in people/m2.
    """

    @staticmethod
    def generate(
        observations: Sequence[dict[str, Any]],
        image_width: int,
        image_height: int,
        zone_set: ZoneSet | None = None,
        window_from_t: float | None = None,
        window_to_t: float | None = None,
        normalization_method: str = "SESSION_MAX",
    ) -> HeatmapGenerationResult:
        if image_width <= 0 or image_height <= 0:
            raise ValueError("image_width and image_height must be positive")

        accumulator = np.zeros((image_height, image_width), dtype=np.float32)
        frames_used = 0
        frames_discarded = 0

        # Build fast zone lookup if zone_set provided
        active_zones = {z.zone_id: z for z in zone_set.zones} if zone_set else {}

        for obs in observations:
            t = float(obs.get("media_time_s", 0.0))
            if window_from_t is not None and t < window_from_t:
                continue
            if window_to_t is not None and t > window_to_t:
                continue

            quality = str(obs.get("quality", "UNKNOWN"))
            fully_observed = set(obs.get("fully_observed_zones", []))

            if quality == "VALID":
                # VALID: accumulate all detections
                frames_used += 1
                detections = obs.get("detections", [])
                for d in detections:
                    # x, y are normalized bottom-centre coords [0, 1]
                    norm_x = float(d["x"])
                    norm_y = float(d["y"])
                    px = int(round(min(max(norm_x * image_width, 0.0), float(image_width - 1))))
                    py = int(round(min(max(norm_y * image_height, 0.0), float(image_height - 1))))
                    accumulator[py, px] += 1.0

            elif quality == "PARTIAL":
                # PARTIAL: only accumulate detections whose anchor is within fully observed zones
                frames_used += 1
                detections = obs.get("detections", [])
                for d in detections:
                    norm_x = float(d["x"])
                    norm_y = float(d["y"])
                    px_f = min(max(norm_x * image_width, 0.0), float(image_width - 1))
                    py_f = min(max(norm_y * image_height, 0.0), float(image_height - 1))

                    # Check if anchor falls in any fully observed zone
                    in_observed = False
                    for zid in fully_observed:
                        zone = active_zones.get(zid)
                        if zone and zone.contains_point(px_f, py_f):
                            in_observed = True
                            break

                    if in_observed:
                        px = int(round(px_f))
                        py = int(round(py_f))
                        accumulator[py, px] += 1.0

            else:
                # UNKNOWN / STALE: discard completely
                frames_discarded += 1

        # Apply Gaussian splatting with sigma proportional to image width
        sigma = max(15.0, image_width * 0.02)
        blurred = cv2.GaussianBlur(accumulator, (0, 0), sigmaX=sigma, sigmaY=sigma)

        max_val = float(np.max(blurred))
        if max_val > 0.0:
            norm_layer = (blurred / max_val)
        else:
            norm_layer = blurred

        # Colormap mapping (Viridis colormap is perceptually uniform)
        uint8_intensity = np.clip(norm_layer * 255.0, 0, 255).astype(np.uint8)
        colored_bgr = cv2.applyColorMap(uint8_intensity, cv2.COLORMAP_VIRIDIS)

        # Build transparent RGBA
        b = colored_bgr[:, :, 0]
        g = colored_bgr[:, :, 1]
        r = colored_bgr[:, :, 2]

        # Transparent alpha where intensity is negligible
        alpha = np.where(
            norm_layer > 0.02,
            np.clip(norm_layer * 200.0 + 35.0, 0, 215).astype(np.uint8),
            np.uint8(0),
        )

        rgba = cv2.merge([b, g, r, alpha])

        # Encode to PNG
        success, buf = cv2.imencode(".png", rgba)
        if not success:
            raise RuntimeError("Failed to encode heat map to PNG")

        png_bytes = buf.tobytes()
        digest = hashlib.sha256(png_bytes).hexdigest()

        metadata = HeatmapMetadata(
            kind="IMAGE_SPACE",
            image_width=image_width,
            image_height=image_height,
            window_from_t=window_from_t,
            window_to_t=window_to_t,
            frames_used=frames_used,
            frames_discarded=frames_discarded,
            normalization_method=normalization_method,
            colormap="viridis",
            sha256=digest,
            disclaimer="Tương đối trong khung hình — không phải mật độ người/m² hay bản đồ địa lý.",
        )

        return HeatmapGenerationResult(png_bytes=png_bytes, metadata=metadata)
