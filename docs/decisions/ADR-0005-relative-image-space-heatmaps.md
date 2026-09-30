# ADR-0005: Relative Image-Space Heat Maps and Colormap Selection

## Status
Proposed — chờ người thật duyệt

## Context
Crowd distribution visualization is required for operators to observe spatial patterns over time. However, camera distortion, perspective foreshortening, and lack of verified ground-plane homography/calibration mean that metric density (people/m²) cannot be computed. Operators must not be misled into interpreting heat maps as geographic heat maps or absolute density.

## Options
1. **Uncalibrated Metric Density Approximation**: Attempt to estimate people per square meter using arbitrary camera pitch angles.
2. **Strict Relative Image-Space Heat Map (`IMAGE_SPACE`)**:
   - Accumulate normalized bottom-centre points into an image-space accumulator grid matching source resolution (`image_width x image_height`).
   - Apply Gaussian blur with standard deviation `sigma` proportional to frame width (e.g., `0.02 * width`).
   - Normalize values relatively: either `SESSION_MAX` (relative across the entire recorded session) or `WINDOW_MAX` (relative within the current sliding time window).
   - Use a perceptually uniform colormap (e.g. viridis or plasma) rendered into transparent RGBA PNG.
   - For `VALID` frames: include all detections.
   - For `PARTIAL` frames: include only detections whose anchor points fall within `fully_observed_zones`.
   - For `UNKNOWN` / `STALE` frames: no detections contribute to accumulation.
   - Label every generated artifact and UI overlay explicitly: `kind="IMAGE_SPACE"`, "Tương đối trong khung hình", "Không phải mật độ người/m²".

## Decision
Adopt Option 2: Strictly enforce relative `IMAGE_SPACE` heat maps with perceptual colormaps and explicit metadata disclaimers.

## Consequences
- **Positive**: Complete scientific and visual honesty; eliminates legal and operational liability from false density claims; intuitive visual aid for crowd clustering.
- **Negative / Trade-off**: Distant clusters in perspective view will have smaller pixel footprints than foreground clusters of the same physical size.
