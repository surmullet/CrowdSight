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

An [`explicit-cap v3 candidate`](configs/models/crowd_best_local_v3.yaml) pins `max_detections: 300` in its hashed profile. A private rerun on the same 153 QUT frames matched every v2 count and remained `EXPLORATORY` with MAE 4.196; it did not improve accuracy. The image evaluator now treats a frame reaching that cap or producing an NMS time-limit warning as unavailable. Neither condition occurred in the QUT run, so those branches remain unexercised there. Keep v2 as the integration identity until the two implementation teammates review the profile switch and update their expected model identity. The synthetic v1 contract fixtures use v2 identifiers and placeholder hashes to illustrate field shape.

**Model identity — default and held-back candidate.** E01 (`crowd_best_local_v2` profile, checkpoint `12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc`) is the current crowd-density default. A MOT20 fine-tuned candidate checkpoint (`2ba3e5a03b845ff4997ab2234120d5ae2c887a87c0baaedf0e6e5cbec05feaa2`, stored only in private artifact storage) was compared against E01 on 2026-09-29 using a private WILDTRACK camera-C1 evaluation: 100 pre-selected frames (IDs `00000000`–`00001980`, step 20) with 2,184 clipped ground-truth boxes and zero unknown frames; inference at 1280 px, confidence 0.25, NMS IoU 0.7, max 300 detections, confidence-greedy matching at IoU 0.5.

| Model | Count MAE | Count RMSE | Signed bias | Precision @ IoU 0.5 | Recall @ IoU 0.5 |
|---|---:|---:|---:|---:|---:|
| E01 (current default) | 8.03 | 9.67 | +3.61 | 0.1411 | 0.1644 |
| MOT20 fine-tuned candidate (held back) | 37.08 | 38.64 | +37.08 | 0.2739 | 0.7390 |

The candidate's higher detection recall comes with severe overcounting (+37.08 people per frame on this selection), so it remains **exploratory**: it is not selectable through any committed profile and must not serve integration or demo counts. This comparison is exploratory external-source evidence, **not** a held-out or target-site evaluation; E01's historical training sources are incompletely inventoried and the WILDTRACK mirror rights/provenance are unverified. Promoting any candidate requires a new versioned profile, a hash-pinned checkpoint artifact, and a reviewed independent evaluation.

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
  "unavailable_reason": null,
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

| Frame quality | Meaning | `unavailable_reason` | Zone-count behavior |
|---|---|---|---|
| `VALID` | Usable frame and complete coverage of configured zones. | `null` | A zone may have a nonnegative count, including a genuine zero. |
| `PARTIAL` | Only IDs in `fully_observed_zones` have complete usable coverage. | `null` | Count listed zones only; other zones are unavailable. |
| `UNKNOWN` | Failed, unreadable, unsupported, or otherwise unusable observation. | Producer-side cause: `INFERENCE_FAILURE`, `NMS_TIME_LIMIT_EXCEEDED`, `DETECTION_LIMIT_REACHED`, or `NO_FULLY_OBSERVED_ZONE`. | No detections or zone counts; never substitute zero. |
| `STALE` | Evidence exceeds the service's freshness policy. | `FRESHNESS_LIMIT_EXCEEDED` (set by the consuming service, never the producer). | No current detections or counts; historical replay alone does not make a frame stale. |

Zero is not a quality state: a fully observed empty scene is `VALID` with an empty `detections` array, as in the zero fixture. Freshness is owned by the consuming service: the producer stamps one observation per decoded frame and never emits `STALE`; the service marks its newest observation `STALE` with `FRESHNESS_LIMIT_EXCEEDED` when the agreed freshness limit passes (for example during a stalled job or long model startup) and clears it when a newer usable observation arrives. The default freshness limit is not chosen here; it is an application decision to record in the review table below.

The model returns detections, not a calibrated site occupancy truth. If no configured zone is fully observable, use `UNKNOWN` with `NO_FULLY_OBSERVED_ZONE`. The application must distinguish a fully observed empty zone from missing evidence. `registration_valid: false` means geographic projection and people-per-square-metre density are unavailable. A frame-relative heat map may still be shown as `IMAGE_SPACE`.

### Uncertainty and calibration limits

- `confidence` values are **uncalibrated raw model scores**, not correctness probabilities. Do not show them to operators as accuracy, average them into "confidence in the count," or derive per-count intervals from them.
- **No calibrated uncertainty interval exists** for any count or density value in this handoff. No labeled, independent target-site calibration set has been run, and calibration validity is explicitly **not** claimed anywhere in this contract.
- Count error is scene-dependent and only characterized on exploratory external sources. The 2026-09-29 WILDTRACK camera-C1 comparison gave E01 count MAE 8.03, RMSE 9.67, and mean bias +3.61 people per frame (100 frames), while the earlier QUT fixed-camera diagnostic showed systematic undercounting (9 detected against 651 annotated people inside camera regions over 153 frames; zero detections in 44 of 50 frames with at least five annotated people). Neither result bounds error at a deployment site.
- Known completeness failures become explicit states, not numbers: a frame at the profile's 300-detection cap (`DETECTION_LIMIT_REACHED`) or with a non-max-suppression time-limit warning (`NMS_TIME_LIMIT_EXCEEDED`) is `UNKNOWN`, never a truncated count presented as complete.
- Metric people-per-square-metre output remains unavailable until the full evidence gate in [`assess_density_validity`](src/crowdsight/geospatial/validity.py) passes; the current demo has no approved calibration.
- The MOT20 fine-tuned candidate checkpoint stays exploratory (higher recall, +37.08 mean count bias on WILDTRACK); publish count error as descriptive evaluation evidence only, never as a guaranteed operating bound.

### Progressive recorded-video producer

[`scripts/stream_crowd_video.py`](scripts/stream_crowd_video.py) emits one flushed v1 JSON object on standard output for each decoded frame, before decoding the next. Standard error carries warnings, errors, and completion text. The application should read each JSON line as it arrives, pair it with the corresponding decoded frame using `session_id`, `frame_index`, and `media_time_s`, then forward it to the operator display over its chosen live transport. This CLI derives `media_time_s` as frame index divided by reported frame rate, so it is suitable for constant-frame-rate recordings; a variable-frame-rate decoder must supply presentation timestamps instead. The detector processes frames in source order; publishing and display can proceed concurrently. This is progressive delivery, not a measured live capture-to-display latency.

In one private five-frame v3 recorded-clip probe (`device: auto`), JSONL frames 0–4 arrived 6.488–6.754 seconds after process launch, each while the producer was still running; the process ended at 7.572 seconds. The first-result wait included Python/model startup and dominated this short run. The application should expose startup progress and buffer or delay replay until matching frame observations are available. These times are one local process-to-stdout measurement, not a service, network, rendered-frame, or live capture-to-display latency guarantee.

The video/application layer must establish coverage for each zone passed to the producer. The CLI requires every `--configured-zone`; the repeated `--fully-observed-zone` IDs must be a unique subset of those configured IDs. It emits `VALID` only when all configured zones are fully observed, `PARTIAL` when some are, and `UNKNOWN` with no detections when none are. The CLI's coverage setting is fixed for the recording; a dynamic camera/occlusion policy needs a frame-specific producer. A whole-image demo can use a single configured zone covering the visible source frame. With `CROWDSIGHT_CROWD_CHECKPOINT` set to the approved local `best.pt` path, run from the repository root:

```powershell
python -u scripts/stream_crowd_video.py --video "<approved-video-path>" --profile configs/models/crowd_best_local.yaml --source-id "camera-01" --session-id "demo-001" --configured-zone "<zone-id>" --fully-observed-zone "<zone-id>"
```

The adapter explicitly applies the historical 300-detection limit and records it in runtime metadata without changing the `crowd_best_local_v2` profile hash. A frame reaching that limit has a truncated count and is emitted as `UNKNOWN` with no detections. The stream also marks a frame `UNKNOWN` if Ultralytics warns that non-max suppression exceeded its time limit, because the returned boxes may be incomplete. Inference failure emits `UNKNOWN` for that frame; errors and warnings appear on standard error. Consumers must not convert these states to zero. A revised limit would require a new profile ID/hash and evaluation. The producer does not encode or deliver video frames, and the application must define its own frame transport and pairing policy. Before the explicit configured-zone input was added, a private five-frame Plaza smoke run with a `whole-frame` zone emitted frames 0–4 as ordered `VALID` JSONL observations and completed without inference errors. A separate injected NMS-warning probe emitted `UNKNOWN` with no detections or zones for frame 0, followed by four `VALID` observations; all five validated against the v1 JSON Schema. The revised zone-set interface has not yet been exercised. Those earlier checks cover a short recorded clip and injected warning behavior, not count accuracy, live latency, or every possible Ultralytics warning.

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
      "density_status": "UNAVAILABLE_REGISTRATION"
    }
  ],
  "heatmap": {"kind": "IMAGE_SPACE", "artifact_id": "synthetic-heatmap-42"}
}
```

The serving layer must carry operating-use status separately from frame `quality`: a technically valid frame does not mean the camera view or model is approved. The current [`assess_crowd_operating_use`](src/crowdsight/detection/applicability.py) helper fails closed to experimental status without exact site/view/profile/checkpoint approval evidence. Show that status in the UI and suppress operational alerts for experimental views. Human review remains part of any future alert workflow.

Metric density is a separate site-calibrated output. [`assess_density_validity`](src/crowdsight/geospatial/validity.py) accepts a count for a requested zone only when that zone is fully observed; a `PARTIAL` frame may still have one fully observed zone. `UNKNOWN`, `STALE`, missing counts, and unobserved zones produce an unavailable result rather than zero. A numeric people-per-square-metre value additionally requires valid registration with a CRS, a positive measured usable area with evidence, calibration and residual evidence within a site-approved limit, a reviewed independent source, and site-policy approval. Each evidence reference and SHA-256 must be verified by the caller; the helper checks their shape but does not read the artifacts. Until those conditions are met, keep `density_people_per_m2: null` and show the returned `density_status`. The current demo has no approved metric-density calibration.

Zone polygons and heat-map coordinates belong to the source image. The v1 producer supplies detection anchors and frame dimensions, not a precomputed heat map. Render one unit of relative intensity at each `VALID` detection's normalized bottom-centre anchor. A trailing time-window view may combine only `VALID` frames from the same source and session; label its window, smoothing radius, and color scale, and keep those settings fixed for comparison. Mark `UNKNOWN` and `STALE` overlays unavailable rather than reusing older data; mask unobserved zones on `PARTIAL` frames. If the camera moves, use frame-local overlays until image registration is reviewed. A heat map is relative visual concentration, not a geographic map, unique-visitor estimate, or people-per-square-metre measurement. Crowd counts alone do not establish waiting time.

## 5. Work for the two implementation teammates

The two teammates may divide these packages freely and cross-review each other's shared boundary changes. Record an implementer and reviewer for each package; no fixed backend/frontend assignment is required.

**Package A — video, job, and data boundary**

1. Accept a server-managed recording reference and zone-set version; create a processing session with progress, completion, cancellation, and actionable failure states.
2. Decode frames in source order; preserve original dimensions, zero-based frame index, and elapsed media time. Invoke the detector through the adapter and consume each JSONL observation as it arrives rather than waiting for the full recording.
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
| AI/ML producer | Frame fields, geometry, raw-score meaning, quality states, model/checkpoint hashes. | AI/ML lead, 2026-09-26 | Producer baseline approved for implementation; 2026-09-29 amendment adds `unavailable_reason` — needs backend/frontend confirmation. |
| Application data boundary | Versioned API or mapping, timestamps, errors, provenance persistence, freshness, artifact access/retention. | Pending | Proposed. |
| Operator display | Boxes, zone unavailable states, raw-score wording, heat-map kind, experimental label and alert suppression. | Pending | Proposed. |
| Product/site | Permitted pilot media, operating view, retention and future alert policy. | Pending | Proposed. |

Record the two teammates' review names, dates, and decisions here or in a linked issue/PR before marking the application contract approved.

## 6. What is ready and what remains open

| Ready for implementation | Open before operational use |
|---|---|
| Hash-identified fine-tuned `best.pt` candidate; versioned profile and detector/tracker adapters; v1 proposed crowd schema; six synthetic quality/tracking examples; fail-closed experimental applicability behavior. | Teammate approval of the application API and display contract; permitted target-camera evaluation with reviewed labels and established source independence; site/view acceptance and alert policy; calibration and usable-area evidence for metric density; deployment/redistribution rights review. |

Exploratory diagnostics already show material undercount on external fixed-camera and crowded scenes. In a private QUT fixed-camera count diagnostic, the current profile detected 9 people inside the camera regions against 651 publisher person-location annotations across 153 frames. Post-hoc count bins show zero predictions in all 22 single-person frames and in 44 of 50 frames with at least five annotated people. A second private diagnostic on the WILDTRACK camera-C1 mirror (table in section 2, 2026-09-29) showed E01 counting with materially lower error (MAE 8.03, bias +3.61) than the MOT20 fine-tuned candidate (MAE 37.08, bias +37.08), which is why the candidate stays held back. Neither result establishes Vietnam-site or independently held-out performance. The checkpoint's known fine-tuning sources are Plaza and VisDrone; complete upstream source independence is unresolved. Use the current model for the experimental demo and preserve `EXPERIMENTAL_NO_APPROVAL` until the evidence gate passes. Detailed evaluation records are retained locally outside Git.

## 7. File map

| Purpose | Location |
|---|---|
| Selected crowd profile and model checksum | [`configs/models/crowd_best_local.yaml`](configs/models/crowd_best_local.yaml) |
| Detector/tracker adapter | [`src/crowdsight/detection/adapter.py`](src/crowdsight/detection/adapter.py) |
| Progressive per-frame producer | [`scripts/stream_crowd_video.py`](scripts/stream_crowd_video.py) |
| Frame serializer and quality checks | [`src/crowdsight/common/observations.py`](src/crowdsight/common/observations.py) |
| Proposed JSON Schema and fixtures | [`contracts/v1/`](contracts/v1/README.md) |
| Application contract review decisions | [`contracts/v1/README.md`](contracts/v1/README.md) |

This file is the single teammate starting point. The linked schema and fixtures remain the machine-readable source of truth for exact producer fields.
