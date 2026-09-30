# Proposed crowd application contract, version 1

The [crowd frame schema](crowd-frame-observation.schema.json) defines the AI/ML producer's proposed per-frame output. The application API remains proposed until the backend and frontend owners confirm transport, persistence, retention, freshness, display behavior, and error handling. Breaking changes require a new version and synchronized consumer updates.

## Files

- `crowd-frame-observation.schema.json`: one source-frame crowd observation.
- `fixtures/crowd-frame-observation.valid.json`: synthetic frame with one person.
- `fixtures/crowd-frame-observation.zero.json`: synthetic fully observed zero-person frame.
- `fixtures/crowd-frame-observation.partial.json`: synthetic partial zone coverage.
- `fixtures/crowd-frame-observation.unknown.json`: synthetic unavailable frame.
- `fixtures/crowd-frame-observation.stale.json`: synthetic expired observation.
- `fixtures/crowd-frame-observation.tracked.json`: synthetic run-local tracked observation.

Synthetic IDs and scores do not represent measured performance or approved thresholds. No media or checkpoint is stored here.

## Producer and consumer rules

- Preserve `source_id`, `session_id`, zero-based `frame_index`, elapsed source `media_time_s`, image dimensions, profile/checkpoint hashes, tracker configuration hash, and explicit quality.
- `captured_at` is null for replay unless the source supplies an actual capture timestamp. Replay time is not capture UTC.
- `VALID` requires at least one fully observed zone and permits counts only when the list covers **every configured zone**. `PARTIAL` requires at least one fully observed zone and permits counts only for IDs in `fully_observed_zones`. If no configured zone is fully observable, use `UNKNOWN`. `UNKNOWN` and `STALE` carry no detections or fully observed zones. Zero is not a quality state: a fully observed empty scene is `VALID` with an empty `detections` array (see the zero fixture); an unavailable count is not zero.
- `unavailable_reason` is `null` on `VALID`/`PARTIAL`. An `UNKNOWN` frame carries the producer-side cause: `INFERENCE_FAILURE` (adapter raised), `NMS_TIME_LIMIT_EXCEEDED` (possibly incomplete boxes), `DETECTION_LIMIT_REACHED` (count truncated at the profile cap), or `NO_FULLY_OBSERVED_ZONE` (no zone-coverage evidence). The producer never emits `STALE`; the consuming service relabels its newest observation `STALE` with reason `FRESHNESS_LIMIT_EXCEEDED` once the agreed freshness limit passes, and restores freshness when a newer usable observation arrives.
- Detection anchors `x,y` are normalized source-frame bottom-centre points. `confidence` is a raw model score, not a calibrated correctness probability; no calibrated count or density uncertainty interval exists, and none may be derived from these scores. Optional tracked IDs are temporary within one video session and require the matching tracker hash.
- Image-space heat maps are relative to the frame. Metric/geographic density requires separate valid calibration, measured area, coverage, residual, and site-approval evidence.
- JSON Schema validates structure and local field constraints; a consumer must also compare `fully_observed_zones` with the versioned configured zone set (`VALID`: exact coverage; `PARTIAL`: a nonempty proper subset), verify box/image geometry and artifact hashes, and apply freshness at its trust boundary. A producer must not infer complete zone coverage from a successful detector call alone.
- An empty, well-formed detector result means zero visible detections for that frame. A missing result, malformed person box/score, or inconsistent tracker output is an inference failure; the video layer must record `UNKNOWN` or fail the job, never convert that failure to a valid zero count.

## Decisions to record before freezing the application API

| Owner | Decision | Reviewer/date | State |
|---|---|---|---|
| AI/ML | Producer fields, geometry, quality, model provenance, and raw-score meaning. | AI/ML lead, 2026-09-26 | Producer baseline approved for implementation; 2026-09-29 amendment adds `unavailable_reason` and needs backend/frontend confirmation |
| Backend | API version/mapping, source time, errors, provenance persistence, artifact access/retention, and freshness limit. | Pending | Proposed |
| Frontend | Annotated replay, unavailable-state display, raw-score wording, heat-map kind, and experimental model label. | Pending | Proposed |
| Product/site | Permitted pilot media, view approval, retention, and alert policy. | Pending | Proposed |

The current UAV backend `POST /api/frames` body does not carry every CrowdSight provenance and quality field. Choose a versioned API or a reviewed adapter that stores omitted provenance. Record the decision and update fixtures before treating the application contract as frozen.
