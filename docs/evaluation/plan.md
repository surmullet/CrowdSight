# Evaluation plan

The AI/ML owner prepares evaluation data and model metrics; all three owners and the pilot owner agree acceptance criteria before using alerts operationally.

## Dataset split

Split by video, site, or flight. Never put neighboring frames from one clip across train/validation/test splits. Preserve source/license/provenance, annotation version, frame timestamps, zone version, model/config hashes, and hardware for every report.

## Report at minimum

- Precision and recall with declared person matching rule and IoU.
- Per-frame and per-zone count MAE, RMSE, signed bias, and error distribution.
- Results by sparse/moderate/dense scene, altitude/view angle, lighting, occlusion, motion blur, and camera movement where present.
- Dense-scene failure and unsupported-observation rate.
- Processing throughput on named hardware, separated from capture-to-display latency (MVP replay does not establish live latency).
- If tracking is evaluated: ID switches/fragmentation and their effect on occupancy; do not substitute track count for attendance.
- If geographic outputs are evaluated: calibration method, CRS, surveyed control/check points, p50/p95 map residual, zone-boundary assignment errors, observed coverage, and invalidation rules.
- If alerts are evaluated: episode precision/recall, false alerts per hour, missed sustained events, and time to alert against approved thresholds.

## Acceptance policy

The pilot/site owner must approve numerical tolerances and threshold rationale. Until that happens, report observed metrics without labeling them passed. Document unsupported conditions and show unknown/unavailable rather than forcing a count.
