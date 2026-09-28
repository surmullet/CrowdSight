# Crowd Model Handoff for the Three-Person Team

**Purpose:** Give the two implementation teammates the inputs, outputs, and integration rules needed to build the crowd-monitoring product slice.

**Status:** Integration can proceed against the proposed v1 contract and synthetic fixtures. The contract is not frozen until the backend and frontend owners review it together.

## Product slice

For a selected recorded video, the system detects visible people in each decoded frame, optionally associates detections with run-local track IDs, aggregates counts over configured image zones, and displays annotated replay, count trends, and a relative image-space heat map. All results must retain timestamps and observation quality. Missing, invalid, stale, or partly observed evidence must never silently appear as a zero count.

This is visible-occupancy decision support. It does not estimate hidden people, attendance, people per square metre, or site safety. It does not identify people. Tracker IDs are temporary within one processing run and are not attendance identities.

**Proposed applicability rule for joint review:** Observation quality describes whether frame and zone evidence is available; `VALID` does not certify count accuracy or approval of the camera view. The serving job/API should carry a separate site-and-profile approval or experimental status, and the operator display should show that status with counts. The product/site owner must approve the operating view and alert policy before counts are used as operational decision support. The v1 frame payload contains no site-approval field; consumers must not infer approval from `VALID` or a nonzero detection count.

## Selected integration candidate

- Profile: `crowd_best_local_v2`, YOLO11s person detector.
- Current profile file SHA-256: `987fd60033b06549f542fe2c3d8a965d19e7018c4964d30f7a606208cd3b115b`.
- Class mapping: `person` → class ID `0`.
- Input: decoded BGR frame; configured inference size is 1280; configured confidence cutoff is 0.25.
- Checkpoint SHA-256: `12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc`.
- Checkpoint file: external to this repository, supplied through `CROWDSIGHT_CROWD_CHECKPOINT`; do not commit model weights, videos, labels, or generated outputs.
- The profile pins the paired BoT-SORT configuration by SHA-256. See the profile for its exact values.
- Confidence values are raw detector scores. `0.25` is the current inference cutoff, not a calibrated probability or approved site threshold.

Start with [the profile](../../configs/models/crowd_best_local.yaml), [the adapter](../../src/crowdsight/detection/adapter.py), and the synthetic contract fixtures linked below. Keep DensityNet separate: it predicts density maps/counts and does not emit person boxes or track IDs.


## Input and output boundary

### Input to the crowd adapter

- One decoded BGR video frame at a time, with frame width and height.
- The processing run provides `source_id`, `session_id`, monotonically increasing `frame_index`, and `media_time_s` derived from the video timeline.
- The run selects a model profile. The adapter loads the checkpoint from `CROWDSIGHT_CROWD_CHECKPOINT`; clients must not send a local filesystem path.
- The current candidate profile uses image size 1280, confidence cutoff 0.25, and class ID 0 for `person`. These are model configuration values, not site acceptance thresholds.
- The orchestrator supplies configured zone IDs and coverage status. The detector cannot decide whether the camera fully observed a zone.

### Output from the crowd adapter

For each processed frame, return the proposed v1 crowd observation with provenance and quality fields, plus zero or more person detections. Each detection contains pixel `bbox_xyxy`, normalized bottom-centre `(x, y)`, and a raw detector score. `track_id` and `tracker_config_sha256` are both null when tracking is not enabled; when a track ID is emitted, its tracker configuration hash is required.

The backend then uses valid observations and configured zone polygons to produce per-zone visible-person counts, quality/freshness state, run timestamps, and result references. The frontend displays these as annotated replay, count trends, and a relative image-space heat map. Density in people per square metre remains unavailable unless a separate approved calibration and measured zone area are provided.

Use the [valid](../../contracts/v1/fixtures/crowd-frame-observation.valid.json), [valid-zero](../../contracts/v1/fixtures/crowd-frame-observation.zero.json), [partial](../../contracts/v1/fixtures/crowd-frame-observation.partial.json), [unknown](../../contracts/v1/fixtures/crowd-frame-observation.unknown.json), [stale](../../contracts/v1/fixtures/crowd-frame-observation.stale.json), and [tracked](../../contracts/v1/fixtures/crowd-frame-observation.tracked.json) synthetic fixtures. The [contract guide](../../contracts/v1/README.md) defines each field.

## Work for each teammate

### Teammate 1 — Backend and video integration

**Own:** `src/crowdsight/video/`, `api/`, shared `common/` integration, and the processing-job lifecycle.

1. Integrate video decoding with the versioned detection adapter. The API and orchestration layer must call the adapter interface rather than importing YOLO or Ultralytics directly.
2. Preserve the input video/run ID, frame index, media timestamp, model profile ID and hash, tracker profile ID and hash, and observation quality in results.
3. Pass `fully_observed_zones` only when the video pipeline can establish full frame coverage for those configured zones. The detector cannot infer camera coverage or zone visibility on its own.
4. Aggregate only valid observations for fully observed zones. Represent `UNKNOWN`, `STALE`, and `PARTIAL` explicitly. An unavailable result is not zero; a valid zero is allowed only when a zone was fully observed and no person was detected.
5. Keep all coordinates tied to the source frame. Boxes use pixel `xyxy` coordinates with exclusive right/bottom edges; anchors are normalized bottom-centre points.
6. Keep tracker IDs scoped to one run. Do not persist them as identities or join them across videos. Every non-null track ID must carry the matching tracker-config SHA-256; detector-only output must use null IDs and a null tracker hash.
7. Return actionable job errors for unreadable video, missing checkpoint, profile/hash mismatch, unsupported frame, and inference failure. Do not accept an arbitrary filesystem path from a client.

**Deliver:** one documented service boundary, result provenance in the API response, quality-state behavior, and an example response using the shared fixture.

### Teammate 2 — Frontend and operator display

**Own:** `frontend/` and the operator-facing video/zone workflow.

1. Display the original frame with detection boxes and replay timestamps. Keep image coordinates aligned when the preview is resized.
2. Display per-zone count trends only with the observation quality and freshness state. Show `UNKNOWN`, `STALE`, and `PARTIAL` distinctly; never substitute zero for missing evidence.
3. Render the heat map in source-image coordinates and label it as a relative image-space visualization. Do not present it as a geographic map or people-per-square-metre surface.
4. If raw scores are shown, label them “raw model score,” not probability or confidence percentage. Hiding raw scores is acceptable for the first operator UI.
5. Explain that counts cover visible people only and that run-local tracker IDs may switch or fragment. Keep operators in control of any alert response.
6. Provide a simple recorded-video demo path and visible progress, completion, and error states.

**Deliver:** annotated replay, zone-count/quality display, relative heat map, and a short operator explanation using synthetic or permitted demo footage.

## AI/ML lead work

1. Maintain the selected model profile, adapter, model card, checkpoint hash, tracker pairing, and inference/runtime manifest as one versioned candidate.
2. Publish synthetic fixtures whenever the proposed adapter payload changes.
3. Explain model configuration fields, raw-score semantics, and known unsupported conditions to both teammates.
4. Resolve integration questions about detection geometry, quality states, and provenance as the teammates implement against the shared fixtures.
5. Review the adapter and shared contract with both teammates; resolve field names and timestamp units before calling v1 frozen.

## Proposed observation contract rules

Machine-readable draft: [crowd v1 contract](../../contracts/v1/README.md) and [frame schema](../../contracts/v1/crowd-frame-observation.schema.json), SHA-256 `10ac87286ed0f003be0232d246041e5265849c942ef920d43febb077108c8c36` at this handoff. Implementation boundary: [detector adapter](../../src/crowdsight/detection/adapter.py) and [observation serializer](../../src/crowdsight/common/observations.py). Backend and frontend review should record this schema digest with reviewer and date; a changed digest requires another review.

- `VALID`: all reported zones are fully observed for that sample.
- `PARTIAL`: only listed fully observed zones can support a count; uncovered zones remain unavailable.
- `UNKNOWN`: evidence cannot support a count. Return no detections/count for this state.
- `STALE`: evidence exists but is too old for the consumer's freshness policy. Do not reuse it as a current count.
- The service/orchestrator, not the detector, supplies zone-coverage quality.
- Detection boxes are frame-pixel coordinates; normalized anchors use bottom-centre `(x, y)` in `[0,1]`.
- Heat maps are relative to the image unless a separately reviewed camera calibration and ground-plane mapping are available.

## Joint acceptance checklist

- [ ] Backend and frontend review the proposed observation schema and agree on names, units, timestamps, and error representation.
- [ ] Both clients handle `VALID`, `PARTIAL`, `UNKNOWN`, and `STALE` without converting missing data to zero.
- [ ] Model/profile/checkpoint/tracker provenance survives from inference to displayed/exported result.
- [ ] A permitted fixed-camera demo runs end to end with the interface and quality semantics shown above.
- [ ] Backend, frontend, and product owners agree where site/profile applicability is stored and how unapproved counts are labeled or withheld from operational alerts.
