# CrowdSight Team Handoff — Recorded-Video MVP

## 1. Purpose

Build a usable first version of a crowd-monitoring product for tourist sites, plazas, campuses, or event venues. It accepts a recorded UAV or fixed-camera video, estimates visible people in named zones, shows a heat map and time trends, and gives operators reviewable threshold alerts.

This is decision support. A human operator verifies conditions and decides what action to take. Littering detection is excluded.

## 2. Product scope

### MVP includes

- Upload or select a permitted recorded video.
- Define named monitoring zones on a video frame.
- Run the existing trained person detector and tracker through a stable adapter.
- Calculate per-frame visible count per zone and time trends.
- Show an image-space heat map, annotated replay, processing progress, and results.
- Clearly represent invalid, uncertain, stale, or partially observed data.
- Configure site-approved alert thresholds; show alert episodes for operator review.
- Export counts and run summaries as CSV/JSON.

### Not in MVP

- Litter detection; face recognition; identity or demographic inference; persistent re-identification; autonomous response; multi-drone fusion; public cloud deployment; live stream or drone control; universal safety thresholds.
- Geographic density/people per square metre unless the site area is measured and mapping calibration is valid and documented.

### Product truths the UI and reports must preserve

- Counts represent visible people in observed frames, not attendance or hidden people.
- Image-space heat maps are relative to the video frame; they are not maps of the real site.
- Track IDs can fragment or switch and must not be summed into attendance.
- An invalid/stale/partial observation is unknown/unavailable, never silently zero or normal.
- Detector validation metrics or a selected demo clip do not prove performance at the pilot site.

## 3. Team and ownership (three people total)

### You — Product lead and AI/ML owner

Own `src/crowdsight/detection/`, `tracking/`, `analytics/`, `heatmap/`, `geospatial/`, `configs/models/`, `docs/evaluation/`, and model evaluation fixtures.

Deliver:
1. Inventory trained checkpoints and choose the MVP candidate based on evidence.
2. Document architecture, class mapping, preprocessing, training-data provenance and license, runtime dependencies, checkpoint SHA-256, and limitations.
3. Provide a model adapter that receives a decoded frame and emits the agreed detection schema; no API/UI dependency on model-specific libraries.
4. Evaluate on a locked video-level/site-level split with manual labels; report precision, recall, count MAE/RMSE/signed bias, zone error, dense-scene failures, and throughput/hardware.
5. Define what makes an observation uncertain or unsupported and how camera motion/partial coverage invalidates map outputs.
6. Provide versioned model/tracker configuration and repeatable run instructions. Keep weight files in an approved artifact location, not Git.

### Teammate 1 — Backend, video workflow, and integration

Own `src/crowdsight/video/`, `api/`, `common/`, `configs/app/`, backend integration tests, and API/architecture documentation with the team.

Deliver:
1. Video input validation, metadata extraction, job lifecycle/status, cancellation/error reporting, and bounded local storage for the MVP.
2. A validated API/service contract for sites, zones, job submission, progress, results, and exports.
3. Pipeline orchestration that calls the model adapter and analytics without importing model-specific code into API routes.
4. Persist only necessary aggregate/job data; keep video access local and intentional. Establish documented retention/deletion and maximum file/job limits for the demo.
5. Health/error states and replay-vs-live timestamp semantics (MVP is replay; media time is not capture UTC).

### Teammate 2 — Frontend and operator workflow

Own `frontend/`, zone configuration UI/schema in `configs/zones/`, user-facing product/operations documentation, and frontend tests.

Deliver:
1. Video selection/upload and visible job progress/errors.
2. Zone creation/editing with names and optional measured areas; visually distinguish image-relative zones from calibrated geographic zones.
3. Result screen with annotated replay, per-zone counts, heat map, trends, alert state, quality/freshness indicators, and CSV/JSON export.
4. Clear `UNKNOWN`, `STALE`, `PARTIAL`, and `VALID` presentations; never render missing results as zero.
5. Operator instructions that explain limitations and state that alerts require human review.

### Shared responsibilities

All three agree product scope, contract, pilot data and permissions, target acceptance criteria, error handling, and demo flow. Each owner reviews the integration boundary of the adjacent owner. No one changes the shared schema without updating its documentation and fixtures.

## 4. Repository and file policy

```text
crowdsight/
  README.md
  pyproject.toml or requirements files (choose after import/dependency audit)
  configs/
    models/                 # model profiles, thresholds, tracker pairing/checksum metadata
    zones/                  # versioned site zone examples; no private site data by default
    app/                    # runtime limits, retention, app settings
  src/crowdsight/
    video/                  # file input, decoding, timestamps
    detection/              # detector interface and trained model adapter
    tracking/               # anonymous run-local tracks
    analytics/              # zone occupancy, trends, threshold episodes
    heatmap/                # image-space heat maps; geographic rendering only when valid
    geospatial/              # calibration, projection, CRS and validity rules
    api/                    # routes and request/response handling
    common/                 # shared schemas, validation, error types, logging
  frontend/
  tests/{unit,integration,fixtures}/
  scripts/                  # run/demo/evaluation entry points
  docs/{product,architecture,evaluation,operations}/
  data/samples/             # only small, licensed/permitted examples
  models/                   # instructions only; large checkpoint weights stay external
  outputs/                  # generated data; ignored by Git
```

### What to reuse from the two source projects

Treat `../heat_map/` and `../uav-crowd-monitoring/` as read-only references while selecting components. First inspect dependencies, license/provenance, data schemas, and tests. Port only code that supports the MVP and adapt it to one agreed schema. Keep both source folders intact.

Likely useful candidates include the detector/tracker/analytics/heat-map pipeline and config/model-profile ideas from `heat_map/`, plus video job/API/zone workflow concepts from `uav-crowd-monitoring/`. These are candidates, not a mandate to copy modules unchanged.

Do not add `.venv/`, caches, raw/full datasets, raw flight footage, generated videos or result folders, Kaggle bundles/wheels, temporary archives, one-off download scripts, unrelated SAM/GPU experiments, secrets, or large weights to the product source repository. Keep provenance, small deterministic fixtures, selected tests, and reproducible evaluation scripts. Use approved artifact storage with checksum and access rules for weights/media.

## 5. Shared interface contract (freeze before parallel coding)

Use JSON-compatible schemas and document units. Suggested first contract:

### Run request

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

### Per-frame observation from AI pipeline

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

`x`/`y` are normalized bottom-centre/ground-contact image coordinates in [0,1]. `track_id` is anonymous and local to this video run. A detector-only observation may have null `track_id`. `captured_at` stays null for recorded-video replay; do not fabricate UTC capture time.

### Result snapshot

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

Required quality states: `VALID`, `PARTIAL`, `UNKNOWN`, `STALE`. Alert levels are configured by the pilot site and must be confirmed before operational use. Density is null unless measured area and valid calibration support it. Alerting logic should require configurable persistence/clear durations and report alert episodes, not repeatedly notify every frame.

## 6. Delivery phases and checkpoints

### Phase 0 — Align (all; do this first)

- Pick one pilot scenario and one permitted sample video.
- Choose the MVP model candidate and confirm who can use/share its weights and data.
- Finalize zone coordinate convention, JSON schemas above, user flow, and error/quality states.
- Agree pilot acceptance thresholds with the site owner; record thresholds as proposed until approved.

**Exit:** brief and schemas reviewed by all three; everyone can work independently against fixtures.

### Phase 1 — Prove the measurement (AI/ML lead, backend supports fixtures)

- Create a representative, manually checked evaluation subset with whole-video/site separation.
- Run current candidate model and analyze misses, false detections, undercount, ID fragmentation, and dense-scene failures.
- Record baseline and limits. Do not start expensive retraining until failure analysis identifies a specific gap.

**Exit:** reproducible baseline report, model card/profile draft, agreed supported scene envelope, sample adapter output.

### Phase 2 — Parallel vertical slices

- AI/ML lead: detector/tracker adapter + deterministic fixture outputs + evaluation CLI/report.
- Teammate 1: video job API/service using fixture observations; progress/result/export endpoints.
- Teammate 2: dashboard and zone editor using the same fixture/API contract; quality state views.

**Exit:** a demo can show fixture observations end-to-end without model inference; owners confirm contract works.

### Phase 3 — Integrate real recorded video

- Connect the versioned model adapter to the job service.
- Implement zone occupancy, image-space heat map, replay overlay, trends, alert episodes and downloads.
- Handle unsupported/partial/invalid observations and failed or cancelled jobs.

**Exit:** one permitted recorded clip produces a complete reviewable result from a documented command/UI flow.

### Phase 4 — Validate pilot and harden

- Compare output against held-out manual ground truth by scene condition and zone.
- Check latency/throughput on named hardware, large file behavior, invalid input, failure recovery, retention/deletion, and operator comprehension.
- Fix blocking accuracy/usability issues and document residual risks.

**Exit:** pilot owner accepts stated limitations and target measures; team recommends proceed, revise, or stop. Live video is a separate milestone.

## 7. Acceptance checklist for the MVP

- [ ] User can process a permitted recorded video and see clear progress and failure reasons.
- [ ] User can define named zones and see zones over the matching video image.
- [ ] Results show per-zone visible counts, time trend, image-space heat map, and annotated replay.
- [ ] Data carries model/config versions and source/session/frame/media-time metadata.
- [ ] Missing calibration prevents geographic density from appearing as a valid number.
- [ ] Invalid, stale, partial, and unsupported outputs are distinguishable from zero.
- [ ] Alert thresholds are site-configurable, persistence is applied, and operator review is explicit.
- [ ] CSV/JSON exports match documented schemas.
- [ ] Evaluation uses manual labels and a held-out site/video split; reports errors, dense failures, and throughput honestly.
- [ ] No unauthorized video/data/weights are copied into Git; model/license provenance and data retention are documented.
- [ ] README includes setup, model artifact retrieval, run/demo command, outputs, and limitations.

The site owner must set numerical accuracy and alert thresholds. Do not invent a universal standard or claim these targets have passed before running the evaluation.

## 8. Team working agreement

- Work in small branches or focused commits with one owner per area. Keep the shared `common` schemas stable after Phase 0.
- Before merging, describe behavior changed, show a small example request/result, and note unverified limitations.
- Store decisions in `docs/architecture/decisions.md`; store measured model results in `docs/evaluation/` with the video/model/config hashes and hardware.
- Keep source media, labels, and checkpoints in approved private storage where required. Put only synthetic/small permitted fixtures in Git.
- Do not silently widen scope to live streaming, geospatial density, new sensors, or new model training; propose them after MVP evidence.

## 9. First actions by owner

- **AI/ML lead:** list available trained models and provenance; select candidate; draft model profile; prepare a small permitted evaluation manifest and adapter example.
- **Teammate 1:** propose API/job schema and local job lifecycle; create fixture-backed API stub; state storage limits and retention behavior.
- **Teammate 2:** create clickable/wireframe result flow; implement zone and quality-state interaction against agreed sample JSON; draft operator wording.
- **All three:** choose pilot clip/site, confirm permissions, freeze the JSON contract, and agree review date and numerical acceptance criteria with the pilot owner.
