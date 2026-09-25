# CrowdSight AI/ML Agent Instructions

## Mission

Build the AI/ML workstream for the recorded-video CrowdSight MVP: crowd occupancy, heat maps, zone trends, uncertainty behavior, and a separately trained parking-space occupancy model. This is decision support; operational actions require human review. Parking is advisory only. Physical gate/barrier actuation is out of scope.

Customer waiting-time estimation is a separate downstream queue-analytics extension, not an output of the parking occupancy model. Do not infer waiting time from occupied/available stall states alone. Define the queue, timestamped observations, service/entry/departure event source, responsible owner, and evaluation data before proposing an estimator or shared output schema. Use anonymous short-lived event association only when required; persistent identity and re-identification remain out of scope.

The existing `best.pt` checkpoint is hash-matched to the UAV fine-tuning pilot's returned best model. Its immediate lineage is a mixed Plaza/VisDrone training run, and the Plaza diagnostic source overlap is confirmed. Independent target validation remains unavailable; do not describe Plaza or the reused VisDrone regression set as held out. The parking model is a distinct future training effort with its own profile, data, split, and evaluation.

## Scope and ownership

AI/ML areas: `src/crowdsight/detection/`, `tracking/`, `analytics/`, `heatmap/`, `geospatial/`, `parking/`, `common/observations.py`, `common/parking.py`, `configs/models/`, `scripts/`, and `docs/evaluation/`.

Coordinate all shared schema changes with backend and frontend owners. Keep API/UI code independent of model frameworks. Maintain proposed schemas and fixtures under `contracts/`; they are not frozen until owner review is recorded.

## Data, artifacts, and provenance

- Keep model weights, source footage, full/private datasets, restricted labels, credentials, generated results, caches, and virtual environments out of Git. Use approved external artifact storage with access controls and SHA-256 records.
- Do not download model/data assets without project approval and source/license/size review.
- Preserve reference projects `../heat_map/` and `../uav-crowd-monitoring/`; reuse selected code only after reviewing dependencies, licensing, provenance, schema, and permissions.
- Never fabricate metrics, permissions, calibration, residuals, FPS, hardware, or successful runs. Label claims as measured, source-documented, assumed, or unverified.
- No faces, demographics, persistent re-identification, litter detection, drone control, or autonomous safety/parking action.

## Model and observation rules

- Keep detector/tracker dependencies behind versioned adapters. Bind checkpoint hash, profile/config hash, preprocessing, class mapping, thresholds, tracker settings, and runtime requirements.
- Tracking IDs are temporary and scoped to one video session. Never treat track count as attendance; never return predicted lost tracks as currently observed people.
- Preserve source/session/frame/media-time metadata and explicit quality. Invalid, stale, partial, blocked, or unsupported evidence is unknown/unavailable, never zero.
- Image-space heat maps are frame-relative only. Geographic density requires valid registration, CRS, complete coverage, measured usable area, and calibration evidence.
- Emit metric density only when calibration evidence, independence review, and site-policy approval each have a reference and SHA-256; independence and site approval are explicitly confirmed; and the held-out residual passes the approved maximum. Otherwise return a named unavailable status.
- Confidence is a raw score unless calibration has been measured; do not present it as a correctness probability.

## Evaluation

- Split by video, site, flight, date, camera, or a justified camera-date unit; never split neighboring frames from one source across train/validation/test.
- Record source hashes, permissions, annotation policy/version, split manifest, model/profile/checkpoint hashes, runtime versions, and hardware.
- Crowd evaluation includes detection precision/recall under a declared matching rule, per-frame/per-zone count MAE/RMSE/bias, errors by scene condition, unknown/unsupported coverage, and tracking metrics only when tracking claims are made.
- Parking evaluation is separate and stall-based: per-class and per-space metrics, occupancy count error, unknown/abstention coverage, and conditions such as day/night, weather, glare, vehicle size, occlusion, and camera movement.
- Throughput on named hardware is not live capture-to-display latency. Site owners approve acceptance thresholds; observed results remain descriptive until then.
- A report is held out only with a locked test selection, complete/hash-identified training inventory, no source or partition overlap, and reviewed independence evidence. Unknown/mixed provenance means exploratory.

## Working procedure

1. Inspect the current worktree, instructions, files, dependencies, artifacts, and Git status before broad edits. Preserve unrelated user work.
2. Make the smallest coherent change within scope and coordinate proposed contract changes with app owners.
3. Do not add or run tests unless explicitly requested. If asked to verify, run focused checks and state exact commands and limits; never imply unrun checks passed.
4. Update model cards, profiles, evaluation docs, and run instructions when behavior changes.
5. Before delivery, report files changed, evidence and checks reviewed, limitations, and the next measurable step.

## Required workstream outputs

- Checkpoint inventory/model cards; versioned crowd adapter/profile; reproducible evaluation and error analysis on permitted independent held-out data.
- Explicit quality/uncertainty and calibration-validity behavior.
- Separate parking model requirements, data/label plan, versioned integration contract, profile template, and evaluation workflow, updated when training occurs.
- Synthetic fixtures and application-owner review/signoff for stable shared contracts. Keep weights and footage outside Git.
