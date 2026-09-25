# Codebase plan and ownership

## Goal

Create one maintainable product repository for the CrowdSight recorded-video MVP. Keep `heat_map/` and `uav-crowd-monitoring/` intact as source/reference projects. Selectively port or adapt useful code; do not copy whole project trees, virtual environments, generated runs, datasets, checkpoints, or unrelated experiments.

## Folder ownership

| Owner | Areas | Responsibilities |
|---|---|---|
| Product lead / AI-ML owner | `src/crowdsight/detection/`, `tracking/`, `analytics/`, `heatmap/`, `geospatial/`, `configs/models/`, `docs/evaluation/`, `tests/fixtures/` | Own trained model package and versioning; detector/tracker integration; representative evaluation; count/heat-map quality; calibration validity; model limitations and release evidence. |
| Teammate 2 / application owner | `src/crowdsight/video/`, `api/`, `common/`, `frontend/`, `configs/zones/`, `configs/app/`, `docs/product/`, `docs/operations/` | Own upload/job workflow, API/schema implementation, zone editing, dashboard, freshness/quality states, access/retention design, user docs. |
| Shared | `README.md`, `tests/unit/`, `tests/integration/`, `docs/architecture/`, `scripts/` | Agree contracts first, review integration changes, run agreed MVP checks, keep setup and architecture current. |

## Suggested structure

```text
crowdsight/
  README.md
  pyproject.toml                 # or requirements.txt once dependencies are agreed
  configs/
    models/                      # model profile, thresholds, version/checksum metadata
    zones/                       # site-specific named zone definitions
    app/                         # runtime settings, retention and quality-state policy
  src/crowdsight/
    video/                       # decoding, media timestamps, job input adapters
    detection/                   # person detector interface and model adapter
    tracking/                    # anonymous per-run tracking
    analytics/                   # per-frame occupancy, trends, alert state
    heatmap/                     # frame-space and calibrated geographic maps
    geospatial/                  # calibration, projection and validity checks
    api/                         # API routes, job/result interface
    common/                      # shared schemas, validation, logging
  frontend/                      # operator dashboard
  tests/
    unit/
    integration/
    fixtures/                    # small permitted deterministic fixtures only
  scripts/                       # run, package, evaluate and demo entry points
  docs/
    product/
    architecture/
    evaluation/
    operations/
  data/samples/                  # small permitted samples; document larger data location
  outputs/                       # generated and ignored
  models/                        # weights and ignored artifacts; deliver separately
```

## Data contract to agree before parallel implementation

The proposed complete crowd and parking frame-output schemas and synthetic fixtures are maintained in [`contracts/v1/`](../../contracts/v1/README.md). They remain drafts until all three owners approve the field names, units, nullability, quality behavior, and compatibility policy.

One observation snapshot should include `source_id`, `session_id`, `frame_index`, `media_time_s`, optional timezone-aware `captured_at` for live input, `observation_valid`, `registration_valid`, and detections containing anonymous run-local `track_id`, normalized image coordinates, and confidence. Analytics output should include zone ID, visible count, optional density only with valid measured area/calibration, heat-map reference or grid, quality/freshness state, and active alert state. Replay media time must not be represented as capture UTC. Do not persist raw identities or expose raw video through aggregate endpoints.

## AI/ML owner deliverables

1. Inventory trained checkpoints: model architecture, training data provenance/license, label mapping, training/evaluation split, dependency/runtime versions, SHA-256, known limitations, and redistribution terms. Do not place large weights in Git.
2. Provide a stable adapter that accepts a decoded frame and returns person detections in a documented schema. Keep model-specific logic behind the adapter.
3. Establish a locked evaluation set split by site/flight/video, not neighboring frames. Include sparse, moderate, dense, occluded, moving-camera, lighting, altitude, and view-angle cases.
4. Produce manual ground truth and report precision/recall, count MAE/RMSE/bias, per-zone error, dense failure rate, and throughput on declared hardware. Do not claim product-level accuracy from training metrics or selected demo clips.
5. Compare detector count with tracker-assisted occupancy. Tracking IDs are temporary and are not attendance counts; do not count predicted lost tracks as observed people.
6. Define confidence/unknown handling and quality gates so weak or unsupported observations become unavailable rather than confident counts.
7. Evaluate heat-map semantics separately: image-space concentration versus calibrated metric density. For geographic density, document calibration, measured area, coverage, CRS, residual error, and invalidation rules.
8. Ship a versioned model profile with checksum, thresholds, tracker settings, preprocessing, class mapping, and compatibility requirements; document rollback and reproducibility.
9. Recommend the next model experiment only where the error analysis identifies a measurable gap.

## Two-person delivery sequence

1. Both owners approve product scope, schemas, and pilot video/ground-truth policy.
2. AI/ML owner provides a mock adapter output and baseline evaluation report; application owner builds against the schema using fixture observations.
3. Integrate detector/tracker with recorded-video job flow.
4. Add zones, heat-map display, history/export, stale/invalid states, and operator review.
5. Run held-out evaluation and a supervised pilot; decide whether results justify a live-stream phase.

## Keep out of shared product source

- `.venv/`, `__pycache__/`, `.pytest_cache/`, editor and OS caches
- raw video, full datasets, generated overlays, run outputs and logs
- checkpoints/weights unless using an approved artifact delivery or model registry
- training notebook output, Kaggle bundles/wheels, temporary archives, experiment result folders
- SAM/distributed/GPU probes or one-off source-fetch scripts unless a scoped product decision adopts them
- secrets, credentials, private telemetry, or unapproved data

Keep useful research notes, provenance manifests, schemas, tests, and reproducible evaluation scripts. Store large approved assets in a controlled artifact location with checksums and access/retention rules.
