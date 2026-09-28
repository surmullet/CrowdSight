# Proposed crowd application contract, version 1

The [crowd frame schema](crowd-frame-observation.schema.json) defines the AI/ML producer's proposed per-frame output. The application API remains proposed until the backend and frontend owners confirm transport, persistence, retention, freshness, display behavior, and error handling. Breaking changes require a new version and synchronized consumer updates.

## Files

- `crowd-frame-observation.schema.json`: one source-frame crowd observation.
- `fixtures/crowd-frame-observation.valid.json`: synthetic frame with one person.
- `fixtures/crowd-frame-observation.partial.json`: synthetic partial zone coverage.
- `fixtures/crowd-frame-observation.unknown.json`: synthetic unavailable frame.

Additional valid-zero, stale, and tracked fixtures may be added with the same schema. Synthetic IDs and scores do not represent measured performance or approved thresholds. No media or checkpoint is stored here.

## Producer and consumer rules

- Preserve `source_id`, `session_id`, zero-based `frame_index`, elapsed source `media_time_s`, image dimensions, profile/checkpoint hashes, tracker configuration hash, and explicit quality.
- `captured_at` is null for replay unless the source supplies an actual capture timestamp. Replay time is not capture UTC.
- `VALID` permits counts for fully observed configured zones. `PARTIAL` permits counts only for IDs in `fully_observed_zones`. `UNKNOWN` and `STALE` carry no detections or fully observed zones. An unavailable count is not zero.
- Detection anchors `x,y` are normalized source-frame bottom-centre points. `confidence` is a raw model score, not a calibrated correctness probability. Optional tracked IDs are temporary within one video session and require the matching tracker hash.
- Image-space heat maps are relative to the frame. Metric/geographic density requires separate valid calibration, measured area, coverage, residual, and site-approval evidence.
- JSON Schema validates structure and local field constraints; a consumer must also verify configured zones, box/image geometry, artifact hashes, and freshness at its trust boundary.

## Decisions to record before freezing the application API

| Owner | Decision | Reviewer/date | State |
|---|---|---|---|
| AI/ML | Producer fields, geometry, quality, model provenance, and raw-score meaning. | Pending | Proposed |
| Backend | API version/mapping, source time, errors, provenance persistence, artifact access/retention, and freshness limit. | Pending | Proposed |
| Frontend | Annotated replay, unavailable-state display, raw-score wording, heat-map kind, and experimental model label. | Pending | Proposed |
| Product/site | Permitted pilot media, view approval, retention, and alert policy. | Pending | Proposed |

The current UAV backend `POST /api/frames` body does not carry every CrowdSight provenance and quality field. Choose a versioned API or a reviewed adapter that stores omitted provenance. Record the decision and update fixtures before treating the application contract as frozen.
