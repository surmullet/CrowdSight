# ADR-0003: Video Decoding, Freshness Policy, and Quality Degradation Rules

## Status
Proposed — chờ người thật duyệt

## Context
When processing recorded video, video frames are decoded sequentially. Real-world video feeds may exhibit corruption, corrupted PTS timestamps, blank frames (e.g. blackout/whiteout), frozen repeated frames, or decoding errors. Furthermore, during playback queries at time `t`, if the nearest processed frame has a timestamp gap exceeding an operational threshold, the reading must not be considered valid or current.

## Options
1. **Silent Fallback / Carry-Forward**: Carry forward the previous frame's count or substitute zero when decoding fails or gaps occur.
2. **Explicit Fail-Closed Degradation and Freshness Limit**:
   - Frame corruption or decode failure triggers a single retry; if failure persists, record an observation with `quality="UNKNOWN"` and explicit `reason_code` (e.g., `DECODE_FAILED`, `FRAME_BLANK`, `FRAME_FROZEN`).
   - If cumulative decode failure rate or consecutive `UNKNOWN` frames exceed configured thresholds, transition job status to `FAILED`.
   - Implement `freshness_max_gap_s` (default 2.0s): when querying frame state at time `t`, if `|t - nearest_media_time_s| > freshness_max_gap_s`, return `quality="STALE"`, no detections, and no zone counts.

## Decision
Adopt Option 2: Implement explicit fail-closed degradation. Zero is never substituted for missing or degraded data. Provide automated detection for blank frames (standard deviation of pixel intensities below threshold) and frozen frames (identical hash/MSE across consecutive frames). Put `ViewStabilityMonitor` (camera shift detection) behind a configuration flag that defaults to disabled until site-specific calibration.

## Consequences
- **Positive**: Strict adherence to truth in data; operators and analytical models are never misled by false zeros or stale numbers; job health is reliably monitored.
- **Negative / Trade-off**: Video with minor intermittent dropouts will report `UNKNOWN`/`STALE` gaps in trends rather than smoothly interpolated continuous curves.
