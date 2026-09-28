# CrowdSight Project Handoff — Recorded-Video MVP

## 1. Project purpose

The project will deliver an initial crowd-monitoring product for tourist sites, plazas, campuses, and event venues. The MVP will accept recorded UAV or fixed-camera video, estimate visible occupancy in named zones, generate heat maps and time trends, and present configurable threshold alerts for operator review.

The product is a decision-support tool. Operational action remains under human control. Litter detection is excluded.

## 2. Scope and product requirements

### 2.1 MVP capabilities

- Accept a permitted recorded video through a local upload or selection workflow.
- Define and edit named monitoring zones on a video frame.
- Process footage using the selected trained person detector and tracker through a stable software interface.
- Calculate visible-person counts per zone and time trends.
- Present an image-space heat map, annotated replay, processing progress, and summary results.
- Communicate uncertainty, partial coverage, invalid observations, and stale data clearly.
- Support site-configured alert thresholds and reviewable alert episodes.
- Export documented count and run-summary data in CSV and JSON formats.

### 2.2 Explicitly excluded capabilities

- Litter detection.
- Face recognition, identity inference, demographic inference, and persistent re-identification.
- Autonomous emergency or operational response.
- Multi-UAV data fusion, public cloud deployment, live video streaming, and drone control.
- Universal safety thresholds.
- Geographic density or people-per-square-metre calculations in the absence of measured area and valid documented calibration.

### 2.3 Required interpretation of results

- Counts represent visible people in observed frames. They do not represent attendance or account for hidden people.
- Image-space heat maps are relative to the video frame and must not be presented as real-world maps.
- Track IDs may switch or fragment and must not be used as attendance totals.
- Invalid, stale, partial, or unsupported observations must be represented as unknown or unavailable, not silently converted to zero or normal status.

## 3. Team structure and work areas

The project team consists of three members: the product lead/AI-ML owner and two teammates.

The two implementation teammates jointly own backend and frontend delivery. Task ownership is selected during planning, with cross-review between the teammates. The sections below describe work areas without fixed assignments to either teammate.

### 3.1 Product lead and AI/ML owner

**Ownership areas:** `src/crowdsight/detection/`, `tracking/`, `analytics/`, `heatmap/`, `geospatial/`, and `configs/models/`.

**Responsibilities and deliverables:**

1. Maintain the selected MVP model candidate and provide its adapter, profile, and sample output for integration.
2. Document model architecture, class mapping, preprocessing, runtime dependencies, checkpoint reference/hash, and known inference limitations in the internal AI/ML record.
3. Implement a stable model adapter that accepts decoded frames and returns the agreed detection schema. API and user-interface components must remain independent of model-specific libraries.
4. Define uncertainty and unsupported-observation criteria, including the conditions under which camera movement or partial coverage invalidates mapped results.
5. Provide versioned model and tracker configuration, reproducible run instructions, and artifact provenance. Large checkpoint files must remain in approved artifact storage rather than Git.

### 3.2 Backend, video workflow, and integration

**Ownership areas:** `src/crowdsight/video/`, `api/`, `common/`, `configs/app/`, backend integration tests, and API/architecture documentation in coordination with the team.

**Responsibilities and deliverables:**

1. Implement video validation, metadata extraction, job lifecycle/status, cancellation and error reporting, and bounded local storage for the MVP.
2. Define and implement validated service/API contracts for sites, zones, job submission, progress, results, and exports.
3. Orchestrate the processing pipeline through the model adapter and analytics interfaces. API routes must not depend directly on model-specific libraries.
4. Persist only necessary job and aggregate data. Document video-access controls, demo file limits, retention periods, and deletion behavior.
5. Implement health and error states and preserve replay timestamp semantics. Recorded media time must not be represented as capture UTC.

### 3.3 Frontend and operator workflow

**Ownership areas:** `frontend/`, zone configuration UI/schema in `configs/zones/`, user-facing product and operations documentation, and frontend tests.

**Responsibilities and deliverables:**

1. Implement video selection/upload and visible job progress and error states.
2. Implement zone creation and editing, including zone names and optional measured areas. Distinguish image-relative zones from calibrated geographic zones.
3. Present annotated replay, per-zone counts, heat map, trends, alert state, quality/freshness indicators, and CSV/JSON export.
4. Represent `UNKNOWN`, `STALE`, `PARTIAL`, and `VALID` states distinctly. Missing results must not be displayed as zero.
5. Provide operator guidance explaining product limitations and the requirement for human review of alerts.

### 3.4 Shared responsibilities

All three team members share responsibility for product scope, interface contracts, pilot-data permissions, acceptance criteria, error handling, and demonstration readiness. Each owner reviews changes at adjacent component boundaries. Changes to shared schemas require corresponding updates to documentation and fixtures.

### 3.5 Planned parking-occupancy extension

Parking occupancy is a separate follow-on module, not part of the crowd MVP acceptance gate. The product lead/AI-ML owner will train and evaluate a dedicated occupancy model. The two implementation teammates will divide the parking result API, space-configuration versioning, aggregation, configuration interface, and occupancy/unknown-state presentation after the contract is approved. The initial behavior is advisory availability for operators or information displays. Gate/barrier commands, reservations, and vehicle routing require a separate approved system design and are excluded from this module contract.

Customer waiting-time estimation is a separate downstream analytics feature, not a field emitted by the occupancy model. Occupancy states alone cannot determine waiting time; the feature needs a defined queue, queue/entry observations with timestamps, and service or departure events (or measured throughput). At a joint review, the product, backend, frontend, and AI/ML owners must decide whether “waiting time” means parking-entry wait or an on-site service queue, identify the event source and responsible owner, and approve an estimate format and freshness policy. The AI/ML owner will define the estimator after those inputs exist; the two implementation teammates will divide event-input integration, result storage, and display of estimate ranges with quality/freshness and unknown states. Do not introduce customer identity or persistent re-identification.

## 4. Repository structure and asset policy

```text
crowdsight/
  README.md
  pyproject.toml or requirements files (selected after dependency audit)
  configs/
    models/                 # model profiles, thresholds, tracker pairing/checksum metadata
    zones/                  # versioned site zone examples; no private site data by default
    app/                    # runtime limits, retention, and application settings
  src/crowdsight/
    video/                  # file input, decoding, and timestamps
    detection/              # detector interface and trained-model adapter
    tracking/               # anonymous run-local tracks
    analytics/              # zone occupancy, trends, and alert episodes
    heatmap/                # image-space heat maps; geographic rendering only when valid
    geospatial/              # calibration, projection, CRS, and validity rules
    api/                    # routes and request/response handling
    common/                 # shared schemas, validation, errors, and logging
  frontend/
  tests/{unit,integration,fixtures}/
  scripts/                  # run, demo, and evaluation entry points
  docs/{product,architecture,evaluation,operations}/
  data/samples/             # small licensed/permitted examples only
  models/                   # instructions only; large checkpoint weights remain external
  outputs/                  # generated data; ignored by Git
```

### 4.1 Reuse of existing prototypes

The existing projects in `../heat_map/` and `../uav-crowd-monitoring/` are reference sources. Both projects must remain intact during source review. Candidate components require review of dependencies, licensing and provenance, data schemas, and tests. Only implementation that supports the MVP should be adapted, and adapted code must follow the agreed product interfaces.

Potentially relevant components include the detector/tracker/analytics/heat-map pipeline and model-profile configuration patterns from `heat_map/`, and video-job/API/zone-workflow concepts from `uav-crowd-monitoring/`. These are candidates for assessment; direct copying without review is not prescribed.

### 4.2 Excluded repository assets

The shared product repository must not contain virtual environments, caches, raw or full datasets, unapproved flight footage, generated videos or result directories, Kaggle bundles or wheels, temporary archives, unrelated SAM/GPU experiments, secrets, or large model weights. Useful provenance records and small deterministic fixtures should be retained. Large approved weights and media require controlled artifact storage with checksums and access rules.

## 5. Shared interface contract

The AI/ML owner defines the proposed v1 model payload and semantics. Backend and frontend implementation can start against that baseline; owners should review transport, persistence, retention, and display behavior before connecting production workflows. Record breaking payload changes as a new schema version.

The complete proposed frame-output schemas and synthetic fixtures are maintained in [`contracts/v1/`](../contracts/v1/README.md). Backend/frontend owners can begin against these AI-owned defaults; the schemas remain proposed until transport, persistence, retention, and user-display decisions are recorded in the review table.

### 5.1 Run request

```json
{
  "source_id": "camera-or-uav-name",
  "session_id": "unique-run-id",
  "video_path_or_upload_id": "server-managed-reference",
  "zone_set_id": "site-zones-v1",
  "model_profile_id": "approved-model-profile"
}
```

The API must not accept arbitrary server filesystem paths from an untrusted client.

### 5.2 Per-frame AI observation

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
  "quality": "VALID",
  "fully_observed_zones": ["north-gate"],
  "registration_valid": false,
  "confidence_semantics": "RAW_MODEL_SCORE",
  "detections": [
    {"track_id": null, "x": 0.51, "y": 0.72, "confidence": 0.87, "bbox_xyxy": [950.4, 600.0, 1008.0, 777.6]}
  ]
}
```

This synthetic example matches the complete proposed crowd observation shape; the canonical fixture is [`crowd-frame-observation.valid.json`](../contracts/v1/fixtures/crowd-frame-observation.valid.json).

Coordinates `x` and `y` are normalized to `[0,1]` and represent the bottom-centre/ground-contact image point. `bbox_xyxy` is in source-frame pixels as `[x1,y1,x2,y2]`, with exclusive right and bottom edges; the frame dimensions bound the coordinates. `track_id` is anonymous and scoped to one video run. Detector-only observations may have a null track ID. For recorded-video replay, `captured_at` remains null; capture UTC must not be fabricated. `confidence` is a raw model score, not a correctness probability.

### 5.3 Result snapshot

```json
{
  "session_id": "unique-run-id",
  "frame_index": 123,
  "media_time_s": 4.1,
  "quality": "VALID",
  "zones": [
    {
      "zone_id": "north-gate",
      "visible_count": 8,
      "density_people_per_m2": null,
      "density_status": "UNAVAILABLE_NO_CALIBRATION",
      "alert_level": "NORMAL"
    }
  ],
  "heatmap": {"kind": "IMAGE_SPACE", "artifact_id": "heatmap-frame-123"}
}
```

Required quality states are `VALID`, `PARTIAL`, `UNKNOWN`, and `STALE`. Alert thresholds require approval by the pilot-site owner. Density must be null unless measured area and valid calibration support the calculation. Alert processing should apply configurable persistence and clear durations and should report alert episodes rather than producing a notification for every frame.

## 6. Delivery phases and exit criteria

### Phase 0 — Scope and contract alignment

**Participants:** all three team members.

- Select a pilot scenario and a permitted sample video.
- Confirm the candidate MVP model interface and permitted use of its weights and data.
- Finalize zone coordinates, JSON schemas, user workflow, and quality/error states.

**Exit criteria:** the project brief and schemas are reviewed by all owners; synthetic fixtures support parallel implementation.

### Phase 1 — Integration contract and fixtures

**Lead:** AI/ML owner for the adapter payload. **Support:** backend and frontend owners for field and display requirements.

- Provide the adapter input/output example and synthetic frame-observation fixtures.
- Confirm field names, units, timestamps, and quality-state behavior with backend and frontend owners.

**Exit criteria:** the implementation teammates can build against the reviewed schema and synthetic fixtures.

### Phase 2 — Parallel implementation slices

- **AI/ML owner:** detector/tracker adapter and deterministic fixture outputs.
- **Implementation teammates, shared work:** video-job service/API using fixture observations, including progress, results, and export interfaces; dashboard and zone editor using the shared fixture/API contract, including quality-state presentation. Record one implementer and one cross-reviewer for each slice.

**Exit criteria:** an end-to-end fixture demonstration is available without model inference, and all owners confirm the interface contract.

### Phase 3 — Recorded-video integration

- Connect the versioned model adapter to the job service.
- Implement zone occupancy, image-space heat map, replay overlay, trends, alert episodes, and downloads.
- Handle unsupported, partial, and invalid observations, as well as failed and cancelled jobs.

**Exit criteria:** a permitted recorded clip produces a complete, reviewable result through a documented command or user workflow.

### Phase 4 — Product integration review

- Review the integrated recorded-video workflow, quality and freshness display, exports, failure recovery, storage/retention behavior, and operator comprehension.

**Exit criteria:** product owners review the integration behavior and usability. Live video requires a separate milestone.

## 7. MVP acceptance checklist

- [ ] A permitted recorded video can be processed with clear progress and failure information.
- [ ] Named zones can be defined and displayed over the corresponding video frame.
- [ ] Results include per-zone visible counts, time trends, an image-space heat map, and annotated replay.
- [ ] Results include model/configuration versions and source/session/frame/media-time metadata.
- [ ] Missing calibration prevents geographic density from being presented as valid.
- [ ] Invalid, stale, partial, and unsupported observations are distinguishable from zero.
- [ ] Alert thresholds are site-configurable, persistence is applied, and human review is explicit.
- [ ] CSV/JSON exports follow documented schemas.
- [ ] Model adapter inputs, outputs, provenance fields, and quality-state semantics are documented and covered by synthetic fixtures.
- [ ] Unauthorized video, data, or weights are excluded from Git; provenance and retention are documented.
- [ ] Setup, artifact retrieval, execution, outputs, and limitations are documented in the README before application release.

Alert thresholds must be approved for each pilot site. No universal operational threshold is assumed.

## 8. Working agreement

- Work in small, reviewable branches or commits with one accountable owner per area.
- Keep shared schemas stable after Phase 0. Schema changes require coordinated updates to implementation, documentation, and fixtures.
- Each integration change should document behavior, include a representative request/result, and identify unverified limitations.
- Record cross-team technical decisions in `docs/architecture/decisions.md`.
- Store source media, labels, and checkpoints in approved locations when required. Git should contain only synthetic or otherwise permitted small fixtures.
- Scope changes involving live video, geographic density, new sensors, or additional model training require review against MVP evidence.

## 9. Initial actions

- **Product lead/AI-ML owner:** provide a versioned candidate profile, adapter example, and synthetic output fixture for integration.
- **Implementation teammates, shared work:** divide the API/job proposal, fixture-backed service skeleton, storage/retention documentation, operator-flow prototype, zone and quality-state presentation, and user-facing terminology; record task owners in the team tracker.
- **All owners:** select a pilot clip/site; confirm permissions; review the JSON contract; and schedule an integration review.

## Crowd model implementation brief

For the crowd-specific integration tasks, adapter inputs and outputs, observation semantics, selected model profile, and three-person integration checklist, use [Crowd Model Handoff for the Three-Person Team](product/CROWD_MODEL_INTEGRATION_HANDOFF.md). This focused brief supplements the product-wide roles above; backend and frontend owners should review its proposed v1 schema before treating the contract as frozen.
