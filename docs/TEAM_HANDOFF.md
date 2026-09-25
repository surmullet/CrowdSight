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
- Validation metrics and selected demonstration clips do not establish performance at a pilot site.

## 3. Team structure and role assignments

The project team consists of three members: the product lead/AI-ML owner and two teammates.

### 3.1 Product lead and AI/ML owner

**Ownership areas:** `src/crowdsight/detection/`, `tracking/`, `analytics/`, `heatmap/`, `geospatial/`, `configs/models/`, `docs/evaluation/`, and model-evaluation fixtures.

**Responsibilities and deliverables:**

1. Inventory trained checkpoints and select an MVP candidate based on evaluation evidence.
2. Document model architecture, class mapping, preprocessing, training-data provenance and license, runtime dependencies, checkpoint SHA-256, and known limitations.
3. Implement a stable model adapter that accepts decoded frames and returns the agreed detection schema. API and user-interface components must remain independent of model-specific libraries.
4. Evaluate the candidate on a locked video-level or site-level split with manual labels. Report precision, recall, count MAE/RMSE/signed bias, per-zone error, dense-scene failures, and throughput on named hardware.
5. Define uncertainty and unsupported-observation criteria, including the conditions under which camera movement or partial coverage invalidates mapped results.
6. Provide versioned model and tracker configuration, reproducible run instructions, and artifact provenance. Large checkpoint files must remain in approved artifact storage rather than Git.

### 3.2 Teammate 1 — Backend, video workflow, and integration

**Ownership areas:** `src/crowdsight/video/`, `api/`, `common/`, `configs/app/`, backend integration tests, and API/architecture documentation in coordination with the team.

**Responsibilities and deliverables:**

1. Implement video validation, metadata extraction, job lifecycle/status, cancellation and error reporting, and bounded local storage for the MVP.
2. Define and implement validated service/API contracts for sites, zones, job submission, progress, results, and exports.
3. Orchestrate the processing pipeline through the model adapter and analytics interfaces. API routes must not depend directly on model-specific libraries.
4. Persist only necessary job and aggregate data. Document video-access controls, demo file limits, retention periods, and deletion behavior.
5. Implement health and error states and preserve replay timestamp semantics. Recorded media time must not be represented as capture UTC.

### 3.3 Teammate 2 — Frontend and operator workflow

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

Parking occupancy is a separate follow-on module, not part of the crowd MVP acceptance gate. The product lead/AI-ML owner will train and evaluate a dedicated occupancy model. Teammate 1 will own the parking result API, space-configuration versioning, and aggregation after the contract is approved. Teammate 2 will own parking-space configuration and occupancy/unknown-state presentation. The initial behavior is advisory availability for operators or information displays. Gate/barrier commands, reservations, and vehicle routing require a separate approved system design and are excluded from this module contract.

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

The existing projects in `../heat_map/` and `../uav-crowd-monitoring/` are reference sources. Both projects must remain intact during evaluation. Candidate components require review of dependencies, licensing and provenance, data schemas, and tests. Only implementation that supports the MVP should be adapted, and adapted code must follow the agreed product interfaces.

Potentially relevant components include the detector/tracker/analytics/heat-map pipeline and model-profile configuration patterns from `heat_map/`, and video-job/API/zone-workflow concepts from `uav-crowd-monitoring/`. These are candidates for assessment; direct copying without review is not prescribed.

### 4.2 Excluded repository assets

The shared product repository must not contain virtual environments, caches, raw or full datasets, unapproved flight footage, generated videos or result directories, Kaggle bundles or wheels, temporary archives, unrelated SAM/GPU experiments, secrets, or large model weights. Useful provenance records, small deterministic fixtures, selected tests, and reproducible evaluation scripts should be retained. Large approved weights and media require controlled artifact storage with checksums and access rules.

## 5. Shared interface contract

The following JSON-compatible contract is the initial proposal. All three owners must review and freeze field names, units, nullability, and error semantics before parallel implementation.

The complete proposed frame-output schemas and synthetic fixtures are maintained in [`contracts/v1/`](../contracts/v1/README.md). The abbreviated examples below describe product intent; the machine-readable schemas contain the full AI-output requirements and remain unapproved pending owner review.

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
  "source_id": "camera-or-uav-name",
  "session_id": "unique-run-id",
  "frame_index": 123,
  "media_time_s": 4.1,
  "captured_at": null,
  "image_width": 1920,
  "image_height": 1080,
  "observation_valid": true,
  "registration_valid": false,
  "detections": [
    {"track_id": 17, "x": 0.51, "y": 0.72, "confidence": 0.87}
  ]
}
```

Coordinates `x` and `y` are normalized to `[0,1]` and represent the bottom-centre/ground-contact image point. `track_id` is anonymous and scoped to one video run. Detector-only observations may have a null track ID. For recorded-video replay, `captured_at` remains null; capture UTC must not be fabricated.

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
- Select a candidate MVP model and confirm permitted use and sharing of its weights and data.
- Finalize zone coordinates, JSON schemas, user workflow, and quality/error states.
- Agree proposed pilot acceptance thresholds with the site owner and document approval status.

**Exit criteria:** the project brief and schemas are reviewed by all owners; fixture data supports parallel implementation.

### Phase 1 — Measurement baseline

**Lead:** product lead/AI-ML owner. **Support:** backend owner for fixture requirements.

- Prepare a representative, manually checked evaluation subset split by video or site.
- Evaluate the current model and analyze misses, false detections, undercount, ID fragmentation, and dense-scene failures.
- Record baseline performance and limitations. Additional training should follow identified error analysis rather than precede it.

**Exit criteria:** a reproducible baseline report, model-profile draft, supported-scene description, and sample adapter output are available.

### Phase 2 — Parallel implementation slices

- **AI/ML owner:** detector/tracker adapter, deterministic fixture outputs, and evaluation command/report.
- **Backend owner:** video-job service/API using fixture observations, including progress, results, and export interfaces.
- **Frontend owner:** dashboard and zone editor using the shared fixture/API contract, including quality-state presentation.

**Exit criteria:** an end-to-end fixture demonstration is available without model inference, and all owners confirm the interface contract.

### Phase 3 — Recorded-video integration

- Connect the versioned model adapter to the job service.
- Implement zone occupancy, image-space heat map, replay overlay, trends, alert episodes, and downloads.
- Handle unsupported, partial, and invalid observations, as well as failed and cancelled jobs.

**Exit criteria:** a permitted recorded clip produces a complete, reviewable result through a documented command or user workflow.

### Phase 4 — Pilot validation and hardening

- Compare outputs with held-out manual ground truth by scene condition and zone.
- Evaluate throughput on named hardware, large-file behavior, invalid input, failure recovery, retention/deletion, and operator comprehension.
- Resolve blocking accuracy and usability issues and document residual limitations.

**Exit criteria:** the pilot owner reviews the stated limitations and measures and records a proceed/revise/stop decision. Live video requires a separate milestone.

## 7. MVP acceptance checklist

- [ ] A permitted recorded video can be processed with clear progress and failure information.
- [ ] Named zones can be defined and displayed over the corresponding video frame.
- [ ] Results include per-zone visible counts, time trends, an image-space heat map, and annotated replay.
- [ ] Results include model/configuration versions and source/session/frame/media-time metadata.
- [ ] Missing calibration prevents geographic density from being presented as valid.
- [ ] Invalid, stale, partial, and unsupported observations are distinguishable from zero.
- [ ] Alert thresholds are site-configurable, persistence is applied, and human review is explicit.
- [ ] CSV/JSON exports follow documented schemas.
- [ ] Evaluation uses manual labels and held-out site/video splits and reports errors, dense-scene failures, and throughput.
- [ ] Unauthorized video, data, or weights are excluded from Git; provenance and retention are documented.
- [ ] Setup, artifact retrieval, execution, outputs, and limitations are documented in the README before application release.

Numerical accuracy and alert thresholds must be set by the pilot-site owner. No universal standard is assumed, and no target is considered passed until supported by evaluation evidence.

## 8. Working agreement

- Work in small, reviewable branches or commits with one accountable owner per area.
- Keep shared schemas stable after Phase 0. Schema changes require coordinated updates to implementation, documentation, and fixtures.
- Each integration change should document behavior, include a representative request/result, and identify unverified limitations.
- Record cross-team technical decisions in `docs/architecture/decisions.md` and measured model results in `docs/evaluation/` with video/model/config hashes and hardware details.
- Store source media, labels, and checkpoints in approved locations when required. Git should contain only synthetic or otherwise permitted small fixtures.
- Scope changes involving live video, geographic density, new sensors, or additional model training require review against MVP evidence.

## 9. Initial actions

- **Product lead/AI-ML owner:** inventory trained models and provenance; select a candidate; draft a model profile; prepare a permitted evaluation manifest and adapter example.
- **Backend owner:** finalize the API/job proposal; implement a fixture-backed service skeleton; document storage limits and retention behavior.
- **Frontend owner:** prepare the operator-flow prototype; implement zone and quality-state presentation against the sample JSON; draft user-facing terminology.
- **All owners:** select a pilot clip/site; confirm permissions; freeze the JSON contract; schedule a review; agree numerical acceptance criteria with the pilot-site owner.
