# CrowdSight — teammate handoff

**Status:** AI/ML crowd producer baseline ready for implementation. The application API, persistence, retention, and display details still require review by the two implementation teammates. The current model is suitable for an experimental recorded-video demo; site-specific accuracy and operational alert use have not been approved.

## 1. Product to build now

Process a permitted **recorded fixed-camera video**. Display the original video with visible-person boxes, named-zone counts over time, a relative heat map aligned to the image, and explicit unavailable states. The count is the number of **visible detected people in an observed zone**, not attendance or a safety measure. This handoff covers only the crowd workstream.

The AI/ML deliverable is a versioned person detector and a proposed per-frame observation contract. The application deliverable is video processing, zone aggregation, storage/API, replay, trends, heat-map presentation, and operator review. Operational alerts remain disabled for the current experimental camera view.

## 2. Input → processing → output

| Boundary | Input | Owner | Output |
|---|---|---|---|
| Application job | Server-managed recorded-video reference; `source_id`, new `session_id`, configured zone set, selected model profile. A client must not supply an arbitrary server filesystem path. | Application | Job ID, progress, error/completion state, selected configuration and applicability status. The exact HTTP envelope is still proposed. |
| Video decoder → detector | One decoded **BGR** frame (`height × width × 3`), zero-based `frame_index`, elapsed `media_time_s`, original width and height. The profile selects person class `0`, image size `1280`, raw-score cutoff `0.25`, and the checkpoint. | Video integration + AI/ML adapter | Zero or more person detections for the current frame. Each has a source-pixel box, normalized bottom-centre anchor, and raw model score. |
| Per-frame observation | Detections plus source/session/time/model hashes, configured zone coverage, and observation quality. The video/application layer supplies zone coverage; the detector cannot establish it. | Shared boundary | One `crowd-frame-observation` v1 object, shown below. |
| Zone analytics | Observation, versioned image-space zone polygons, and coverage/freshness rules. | Application | Per-zone visible count or unavailable state, trend samples, and optional human-reviewed alert episodes. |
| Operator display | Frame, matching observation, zone results, and heat-map artifact. | Application | Annotated replay, visible-count trend, **image-space** relative heat map, quality/applicability labels, and clear errors. |

`best.pt` is the E01 YOLO11s person detector after a Plaza/VisDrone fine-tuning pilot. Selected profile: `crowd_best_local_v2`; checkpoint SHA-256: `12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc`. The model weight stays outside Git and is selected on the server through `CROWDSIGHT_CROWD_CHECKPOINT`. The profile lives at [`configs/models/crowd_best_local.yaml`](configs/models/crowd_best_local.yaml); the detector interface and implementation live at [`src/crowdsight/detection/adapter.py`](src/crowdsight/detection/adapter.py). Application code should call the adapter rather than import Ultralytics directly.

## 3. Exact per-frame output for integration

The proposed producer schema is [`contracts/v1/crowd-frame-observation.schema.json`](contracts/v1/crowd-frame-observation.schema.json). This complete **synthetic** `VALID` example shows the field names and units; the repeated `a`/`b` hashes are placeholders, not real model hashes:

```json
{
  "source_id": "demo-camera-01",
  "session_id": "synthetic-run-001",
  "model_profile_id": "crowd_best_local_v2",
  "model_profile_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "checkpoint_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "tracker_config_sha256": null,
  "frame_index": 42,
  "media_time_s": 1.4,
  "captured_at": null,
  "image_width": 1920,
  "image_height": 1080,
  "observation_valid": true,
  "registration_valid": false,
  "fully_observed_zones": ["north-gate"],
  "confidence_semantics": "RAW_MODEL_SCORE",
  "quality": "VALID",
  "detections": [
    {
      "track_id": null,
      "x": 0.51,
      "y": 0.72,
      "confidence": 0.87,
      "bbox_xyxy": [950.4, 600.0, 1008.0, 777.6]
    }
  ]
}
```

- `frame_index` starts at zero. `media_time_s` is elapsed time in the **source recording**, not wall-clock time. Set `captured_at` to `null` unless the source supplies an actual capture timestamp.
- `bbox_xyxy` is `[x1, y1, x2, y2]` in **original-frame pixels**; right/bottom edges are exclusive. `x` and `y` are normalized to `[0,1]` and locate the box's bottom centre. Use the same original frame dimensions when scaling overlays.
- `confidence` is an **uncalibrated raw detector score**, not the probability that a person is present. The `0.25` cutoff is a model inference setting, not a site alert threshold.
- `track_id` is `null` for detector-only output. Optional tracking requires one tracker instance per session; IDs are temporary within that run and a non-null ID requires the matching `tracker_config_sha256`.
- Preserve profile, checkpoint, and tracker hashes with persisted results. The application must validate the model profile and checkpoint identity at the model boundary.

The canonical synthetic examples are [`VALID`](contracts/v1/fixtures/crowd-frame-observation.valid.json), [`VALID` zero](contracts/v1/fixtures/crowd-frame-observation.zero.json), [`PARTIAL`](contracts/v1/fixtures/crowd-frame-observation.partial.json), [`UNKNOWN`](contracts/v1/fixtures/crowd-frame-observation.unknown.json), [`STALE`](contracts/v1/fixtures/crowd-frame-observation.stale.json), and [tracked](contracts/v1/fixtures/crowd-frame-observation.tracked.json). Use these fixtures to implement the consumer before live model integration.

### Quality and count rules

| Frame quality | Meaning | Zone-count behavior |
|---|---|---|
| `VALID` | Usable frame and complete coverage of configured zones. | A zone may have a nonnegative count, including a genuine zero. |
| `PARTIAL` | Only IDs in `fully_observed_zones` have complete usable coverage. | Count listed zones only; other zones are unavailable. |
| `UNKNOWN` | Failed, unreadable, unsupported, or otherwise unusable observation. | No detections or zone counts; never substitute zero. |
| `STALE` | Evidence exceeds the service's freshness policy. | No current detections or counts; historical replay alone does not make a frame stale. |

The model returns detections, not a calibrated site occupancy truth. If no configured zone is fully observable, use `UNKNOWN`. The application must distinguish a fully observed empty zone from missing evidence. `registration_valid: false` means geographic projection and people-per-square-metre density are unavailable. A frame-relative heat map may still be shown as `IMAGE_SPACE`.

## 4. Application result and operator behavior

The **application** should aggregate a valid frame into a result shaped approximately as follows. This is an illustrative service response, **not** the frozen per-frame AI schema:

```json
{
  "session_id": "synthetic-run-001",
  "frame_index": 42,
  "media_time_s": 1.4,
  "quality": "VALID",
  "model_applicability": {
    "status": "EXPERIMENTAL_NO_APPROVAL",
    "operational_alerts_allowed": false
  },
  "zones": [
    {
      "zone_id": "north-gate",
      "visible_count": 1,
      "density_people_per_m2": null,
      "density_status": "UNAVAILABLE_NO_CALIBRATION"
    }
  ],
  "heatmap": {"kind": "IMAGE_SPACE", "artifact_id": "synthetic-heatmap-42"}
}
```

The serving layer must carry operating-use status separately from frame `quality`: a technically valid frame does not mean the camera view or model is approved. The current [`assess_crowd_operating_use`](src/crowdsight/detection/applicability.py) helper fails closed to experimental status without exact site/view/profile/checkpoint approval evidence. Show that status in the UI and suppress operational alerts for experimental views. Human review remains part of any future alert workflow.

Zone polygons and heat-map coordinates belong to the source image. A heat map is relative visual concentration, not a geographic map or people-per-square-metre measurement. Crowd counts alone do not establish waiting time.

## 5. Work for the two implementation teammates

The two teammates may divide these packages freely and cross-review each other's shared boundary changes. Record an implementer and reviewer for each package; no fixed backend/frontend assignment is required.

**Package A — video, job, and data boundary**

1. Accept a server-managed recording reference and zone-set version; create a processing session with progress, completion, cancellation, and actionable failure states.
2. Decode frames in source order; preserve original dimensions, zero-based frame index, and elapsed media time. Invoke the detector through the adapter.
3. Validate and store v1 observations with exact model/configuration hashes. Define a versioned API or explicit mapping from v1 observations to the existing UAV API; its current `POST /api/frames` body is not a direct match.
4. Define result/artifact storage, access, expiry, and deletion. Keep weights, source video, private labels, generated videos, and credentials out of Git.
5. Handle missing checkpoint, hash mismatch, bad video, unsupported frame, and inference failure as job errors or `UNKNOWN` observations according to a documented recovery policy.

**Package B — zones and operator workflow**

1. Configure named source-image polygons and aggregate per-zone visible counts only from fully observed zones. Produce time trends and image-relative heat-map artifacts.
2. Build annotated recorded-video replay using the matching frame, pixel boxes, and `media_time_s`. Keep overlays aligned after resize.
3. Show valid zero, `PARTIAL`, `UNKNOWN`, and `STALE` differently. Show experimental model applicability and keep operational alerts off while unapproved.
4. Label heat maps `IMAGE_SPACE`; keep metric density unavailable without valid registration, measured area, and reviewed calibration evidence. Hide raw scores or label them as raw model scores.
5. Provide a fixture-backed screen before connecting real inference, then connect the permitted demo recording through the job API.

**AI/ML lead:** maintain the checkpoint/profile/adapter and synthetic producer fixtures; answer geometry and quality questions; continue private independent evaluation and calibration review; join the schema review.

**Joint review before treating the application contract as frozen:** choose API envelope and schema version, storage of provenance, heat-map artifact reference and retention, freshness rule, zone-coverage source, error mapping, and display of experimental status. Any breaking field change needs a new contract version and updated fixtures.

| Review area | Decision required | Reviewer and date | State |
|---|---|---|---|
| AI/ML producer | Frame fields, geometry, raw-score meaning, quality states, model/checkpoint hashes. | AI/ML lead, 2026-09-26 | Producer baseline approved for implementation. |
| Application data boundary | Versioned API or mapping, timestamps, errors, provenance persistence, freshness, artifact access/retention. | Pending | Proposed. |
| Operator display | Boxes, zone unavailable states, raw-score wording, heat-map kind, experimental label and alert suppression. | Pending | Proposed. |
| Product/site | Permitted pilot media, operating view, retention and future alert policy. | Pending | Proposed. |

Record the two teammates' review names, dates, and decisions here or in a linked issue/PR before marking the application contract approved.

## 6. What is ready and what remains open

| Ready for implementation | Open before operational use |
|---|---|
| Hash-identified fine-tuned `best.pt` candidate; versioned profile and detector/tracker adapters; v1 proposed crowd schema; six synthetic quality/tracking examples; fail-closed experimental applicability behavior. | Teammate approval of the application API and display contract; permitted target-camera evaluation with reviewed labels and established source independence; site/view acceptance and alert policy; calibration and usable-area evidence for metric density; deployment/redistribution rights review. |

Exploratory diagnostics already show material undercount on external fixed-camera and crowded scenes. In a private QUT fixed-camera count diagnostic, the current profile detected 9 people inside the camera regions against 651 publisher person-location annotations across 153 frames. This result does **not** establish Vietnam-site or independently held-out performance. Use the current model for the experimental demo and preserve `EXPERIMENTAL_NO_APPROVAL` until the evidence gate passes. The published model status and measured limitations are documented in the [model card](docs/models/crowd-best-local-model-card.md) and [evaluation notes](docs/evaluation/plan.md).

## 7. File map

| Purpose | Location |
|---|---|
| Selected crowd profile and model checksum | [`configs/models/crowd_best_local.yaml`](configs/models/crowd_best_local.yaml) |
| Detector/tracker adapter | [`src/crowdsight/detection/adapter.py`](src/crowdsight/detection/adapter.py) |
| Frame serializer and quality checks | [`src/crowdsight/common/observations.py`](src/crowdsight/common/observations.py) |
| Proposed JSON Schema and fixtures | [`contracts/v1/`](contracts/v1/README.md) |
| AI/ML model card and evaluation status | [`docs/models/crowd-best-local-model-card.md`](docs/models/crowd-best-local-model-card.md), [`docs/evaluation/plan.md`](docs/evaluation/plan.md) |
| Product plan and contract review details | [`docs/TEAM_HANDOFF.md`](docs/TEAM_HANDOFF.md), [`contracts/v1/README.md`](contracts/v1/README.md) |

This file is the single teammate starting point. The linked schema and fixtures remain the machine-readable source of truth for exact producer fields.
