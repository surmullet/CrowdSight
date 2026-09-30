# CrowdSight Implementation Progress Log

## 1. Overview & Current Status
- **Current Phase**: Phase 0 Complete -> Transitioning to Phase 1
- **Active Task**: Preparing Contract & Domain Layer (Phase 1)
- **Target Completion**: Full Stack (Backend + Frontend) Production Grade

## 2. Completed Phases
- [x] **Phase 0: Repository Discovery, Invariant Baseline, Initial ADRs, and Plan**
  - Read and cross-verified all initial documents: `README.md`, `TEAMMATE_HANDOFF.md`, `contracts/v1/` schema and 6 fixtures, model profiles, detector/tracker adapters, observation contracts, applicability gates, pyproject, and evaluation scripts.
  - Formulated 25-line understanding summary capturing key invariants and discrepancies.
  - Published 6 Proposed ADRs (`ADR-0001` through `ADR-0006`) awaiting human review.
  - Initialized `docs/PROGRESS.md` for self-recovery across sessions.

## 3. Pending Phases
- [ ] **Phase 1: Contract Layer & Domain Core**
  - Pydantic v2 schemas for v1 observations (`contracts/v1/crowd-frame-observation.schema.json`).
  - Two-stage validator: JSON Schema structure + domain consistency (box bounds, bottom-centre anchor match, tracker hash pairing, zone coverage).
  - Pure domain zone geometry (Shapely 2), `aggregate_frame()` function, and freshness policy.
  - Unit tests validating all 6 fixtures + Hypothesis property-based tests for invariants.
- [ ] **Phase 2: Storage, Pipeline & Synthetic Job Runner**
  - SQLAlchemy 2.0 models with DB-level CHECK constraints.
  - Alembic migrations (SQLite WAL & PostgreSQL compatible).
  - Media asset catalog & managed artifact store.
  - Deterministic `SyntheticDetector` for zero-weight CI/dev.
  - Video decoding pipeline, frame degradation (blank/frozen detection), cooperative cancellation, retry, and crash recovery.
- [ ] **Phase 3: Application API (`/api/v1`) & OpenAPI Export**
  - FastAPI routers (`/health`, `/api/v1/model`, `/media`, `/zone-sets`, `/sessions`, `/analytics`, `/alerts/status`).
  - RFC 9457 Problem Details (`application/problem+json`).
  - SSE progress streaming with polling fallback.
  - HTTP Range / 206 partial streaming for media assets.
  - Export OpenAPI specification to `contracts/app-v1/openapi.json`.
- [ ] **Phase 4: Analytics Engine & Live Model Boundary**
  - Trend series (RAW, BUCKETED with statistics, SMOOTHED, LTTB downsampling).
  - Highlights / peak moments detection (neutral, non-alarmist descriptions).
  - Gaussian image-space relative heat map (`IMAGE_SPACE`, transparent RGBA PNG).
  - Real model checkpoint & profile verification against expected SHA-256 digests.
  - FFmpeg browser-compatible H.264 proxy generator.
  - CLI tools (`crowdsight media`, `crowdsight session`, `crowdsight model verify`).
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
