# CrowdSight Implementation Progress Log

## 1. Overview & Current Status
- **Current Phase**: Phase 4 Complete -> Transitioning to Phase 5
- **Active Task**: Frontend Design, Project Setup, Design System & /dev/states (Phase 5)
- **Target Completion**: Full Stack (Backend + Frontend) Production Grade

## 2. Completed Phases
- [x] **Phase 0: Repository Discovery, Invariant Baseline, Initial ADRs, and Plan**
  - Read and cross-verified all initial documents: `README.md`, `TEAMMATE_HANDOFF.md`, `contracts/v1/` schema and 6 fixtures, model profiles, detector/tracker adapters, observation contracts, applicability gates, pyproject, and evaluation scripts.
  - Formulated 25-line understanding summary capturing key invariants and discrepancies.
  - Published 6 Proposed ADRs (`ADR-0001` through `ADR-0006`) awaiting human review.
  - Initialized `docs/PROGRESS.md` for self-recovery across sessions.
- [x] **Phase 1: Contract Layer & Domain Core**
  - Pydantic v2 schemas (`CrowdFrameObservationV1`, `DetectionV1`) matching `contracts/v1/crowd-frame-observation.schema.json`.
  - Two-stage validator (`TwoStageObservationValidator`): Draft 2020-12 JSON Schema + cross-checks (box bounds, bottom-centre anchor, tracker hash pairing, zone-set coverage).
  - Pure domain zone geometry with Shapely 2 (`ZonePolygon`, `ZoneDefinition`, `ZoneSet`, `validate_zone_set`).
  - Pure aggregation function `aggregate_frame()` enforcing invariant `visible_count IS NOT NULL <=> availability == 'COUNTED'`.
  - Freshness assessment (`FreshnessPolicy`, `assess_freshness`, `apply_freshness_to_observation`).
  - 41 unit and Hypothesis property-based tests passing with 91% domain coverage; ruff and mypy strict passing.
- [x] **Phase 2: Storage, Pipeline & Synthetic Job Runner**
  - SQLAlchemy 2.0 declarative models (`MediaAssetRecord`, `ZoneSetRecord`, `ZoneSetVersionRecord`, `SessionRecord`, `ObservationRecord`, `ZoneResultRecord`, `ArtifactRecord`, `NoteRecord`, `AuditLogRecord`).
  - Hard database CHECK constraint: `visible_count IS NOT NULL <=> availability = 'COUNTED'`.
  - SQLite WAL mode & foreign keys enabled; PostgreSQL-compatible architecture.
  - Path-traversal hardened `ArtifactStore` and OpenCV-backed `MediaRegistry`.
  - Deterministic `SyntheticDetector` generating valid moving person trajectories.
  - `VideoDecoder` with sequential decoding, single-frame retry, blank frame (`FRAME_BLANK`), and frozen frame (`FRAME_FROZEN`) anomaly detection.
  - `SessionPipeline` and `JobManager` with cooperative cancellation, partial result preservation (`PARTIAL_CANCELLED`), and orphaned worker crash recovery.
  - End-to-end tests with synthetic OpenCV video verified; 56 tests passing with 90% coverage; ruff and mypy strict passing.
- [x] **Phase 3: Application API (`/api/v1`) & OpenAPI Export**
  - FastAPI application in `src/crowdsight/service/api/app.py` with RFC 9457 Problem Details (`application/problem+json`) and stable error codes (`MEDIA_NOT_FOUND`, `MEDIA_UNREADABLE`, `ZONE_SET_INVALID`, `MODEL_CHECKPOINT_MISSING`, etc.).
  - Complete REST routers in `src/crowdsight/service/api/routers/`:
    - `health`: Liveness and readiness endpoints with database ping and configuration status.
    - `model`: Inspection of active model profile, SHA-256 digests, and `assess_crowd_operating_use` applicability status.
    - `media`: Catalog retrieval, HTTP 206 partial Range streaming, and single-frame extraction (`/frame?frame_index=`).
    - `zone_sets`: Creation, versioning, list, retrieval, and real-time geometry validation (`POST /zone-sets/validate`).
    - `sessions`: Creation with idempotent options, status polling, Server-Sent Events (SSE) progress streaming (`/events`), cooperative cancellation (`/cancel`), and cascaded deletion (`DELETE /sessions/{id}`).
    - `frames`: Playback queries (`/frames?from_t=&to_t=&limit=`) and point-in-time lookup (`/frames/at?t=`) with strict freshness policy enforcement.
    - `artifacts`: Secure token-checked file retrieval with path-traversal prevention.
    - `alerts`: Operational alerts status endpoint returning `operational_alerts_allowed = false` under experimental deployment.
  - Exported canonical OpenAPI 3.1 contract to `contracts/app-v1/openapi.json` and documentation in `contracts/app-v1/README.md`.
  - Comprehensive unit, property, and OpenAPI snapshot tests passing; 65 tests green; ruff and mypy strict passing with 0 errors.
- [x] **Phase 4: Analytics Engine & Live Model Boundary**
  - Trend analytics engine (`src/crowdsight/service/analytics/trends.py`):
    - `TrendAnalyzer` computing bucketed time series (`RAW`, `BUCKETED`, `SMOOTHED`) with statistics (`min`, `mean`, `median`, `p95`, `max`).
    - Enforced invariant: unobserved/uncounted buckets are strictly `None` / `null`, never `0.0`.
    - LTTB (Largest Triangle Three Buckets) downsampling algorithm preserving missing intervals without coercion.
  - Neutral highlight moments (`src/crowdsight/service/analytics/peaks.py`):
    - Peak visible count detection per zone with temporal suppression; zero forbidden/alarmist terms.
  - Image-space relative heat map generator (`src/crowdsight/service/analytics/heatmaps.py`):
    - Bottom-centre Gaussian splatting (`sigma` proportional to image width).
    - Perceptually uniform viridis colormap, transparent RGBA PNG, ADR-0005 quality weighting.
    - Strict `IMAGE_SPACE` metadata, `SESSION_MAX`/`WINDOW_MAX` relative normalization.
  - Quality summary metrics (`src/crowdsight/service/analytics/summary.py`):
    - Truthful breakdown of `VALID`/`PARTIAL`/`UNKNOWN`/`STALE`, reason codes, and 10-bin raw score histogram.
  - Invariant-preserving exports (`src/crowdsight/service/analytics/exports.py`):
    - JSONL archive with manifest provenance and `SEMANTICS.md` disclaimers.
    - CSV export where uncounted cells are strictly empty string `""` (never `0`!).
  - Live model boundary & checkpoint verification (`src/crowdsight/service/pipeline/model_boundary.py`):
    - SHA-256 digest validation for model profiles and checkpoints.
    - Stable error codes: `MODEL_CHECKPOINT_MISSING` and `MODEL_CHECKPOINT_HASH_MISMATCH`.
    - Safe fallback to `SyntheticDetector` in zero-weight / test environments.
  - Web proxy generation (`src/crowdsight/service/storage/proxy.py`):
    - FFmpeg H.264 MP4 proxy transcoding for non-browser playable codecs.
  - Management CLI (`src/crowdsight/cli/main.py`):
    - `crowdsight media scan`, `media register`, `session reprocess`, `session purge`, and `model verify`.
  - 86 backend tests passing; ruff clean; mypy strict passing with 0 errors; OpenAPI contract updated.

## 3. Pending Phases
- [ ] **Phase 5: Frontend Design, Project Setup, Design System & `/dev/states`**
  - `web/DESIGN.md` (plan, reflection, custom color palette, typography, visual hierarchy).
  - Vite + React + TypeScript strict + Tailwind (CSS variables) + Radix UI.
  - Self-hosted fonts with full Vietnamese diacritics.
  - Internationalization (`vi` default + `en`) via i18next.
  - OpenAPI client generation via `openapi-typescript` + `openapi-fetch`.
  - Discriminated union `ZoneReading` (Counted, NotFullyObserved, Unknown, Stale).
  - `/dev/states` page rendering all 6 contract fixtures.
- [ ] **Phase 6: Frontend Annotated Player & Review Workspace**
  - Synchronized `<video>` + `<canvas>` player with sub-pixel alignment under letterboxing/resize.
  - Dynamic overlay: bounding boxes, zone polygons, relative heat map overlay with opacity slider.
  - Interactive timeline showing quality strips, trend lines with gaps for unobserved intervals, note pins.
  - Zone cards, provenance drawer, and persistent experimental warning banner.
- [ ] **Phase 7: Frontend Operational Workflows**
  - Session library with status filters, search, and confirmed deletion.
  - New analysis wizard with catalog selection, zone-set picker, and model identity display.
  - Real-time job progress with SSE and cancel actions.
  - Interactive SVG zone polygon editor with real-time `/zone-sets/validate` feedback.
  - Model & applicability inspection page + explicitly disabled alerts status.
- [ ] **Phase 8: Security, Retention, Linters & Deployment Packaging**
  - Path traversal and security hardening tests.
  - Data retention worker and token-authenticated artifact retrieval.
  - `scripts/semantic_lint.py` checking code, UI, i18n, docs, and exports.
  - Dockerfile & `docker-compose.yml` for clean one-command deployment.
- [ ] **Phase 9: Independent Integration Review & Final Report**
  - End-to-end integration audit, adversarial tests, performance benchmarks, and accessibility verification.
  - Final report in `docs/reviews/integration-review.md`.

## 4. Key Architectural Decisions (ADRs)
- `ADR-0001`: Standalone `/api/v1` REST API decoupling from legacy UAV references.
- `ADR-0002`: SQLAlchemy 2.0 with SQLite WAL (dev) / PostgreSQL (prod) and strict CHECK constraints.
- `ADR-0003`: Fail-closed video degradation, explicit reason codes, and freshness gap limits.
- `ADR-0004`: Application-managed zone coverage, bottom-centre anchor point, and multi-zone membership.
- `ADR-0005`: Relative image-space heat maps (`IMAGE_SPACE`) with perceptual colormaps and disclaimer.
- `ADR-0006`: Managed artifact storage, 30-day default retention, and signed access tokens.

## 5. Working Assumptions & Noted Discrepancies
- **No external UAV API code**: The repo does not contain UAV backend code; CrowdSight application operates as a standalone service.
- **Model Checkpoint**: YOLO11s `best.pt` (`12824a97...`) resides outside Git. `SyntheticDetector` enables complete testing without external weights.
- **Quality vs Applicability**: Technically valid frames (`VALID`) never imply operational approval (`EXPERIMENTAL_NO_APPROVAL` is maintained).
- **Zero vs Unavailable**: Missing data is strictly represented as `null` / unavailable, never zero.
- **Density**: `density_people_per_m2` is always `null` and `density_status` is `UNAVAILABLE_NO_CALIBRATION`.

## 6. Open Items (Awaiting Real Human Review)
- Formal review and approval of the decision table in `contracts/v1/README.md`.
- Formal approval of ADR-0001 through ADR-0006.
- Site-specific camera calibration and evaluation for Vietnam target footage.

## 7. Standard Test & Validation Commands
- Backend lint & types: `ruff check src/ tests/` && `mypy src/`
- Backend tests: `pytest`
- Semantic linter: `python scripts/semantic_lint.py`
- Frontend checks: `pnpm --dir web check`
