# CrowdSight

## Project overview

CrowdSight is a recorded-video crowd-monitoring product concept for tourist sites, plazas, campuses, and event venues. The proposed MVP analyzes UAV or fixed-camera footage to estimate visible occupancy in named zones, generate heat maps and time trends, and present reviewable threshold alerts to site operations personnel.

The system is intended to support operational decisions. Alerts require human review. Litter detection is outside the project scope.

## Documentation

- [Project handoff and delivery plan](docs/TEAM_HANDOFF.md): scope, role assignments, data contract, delivery phases, acceptance criteria, and initial actions.
- [MVP product brief](docs/product/mvp-brief.md): target users, workflow, inputs, outputs, and product boundaries.
- [Codebase plan](docs/architecture/codebase-plan.md): repository structure and selective reuse guidance for the existing prototypes.
- [Evaluation plan](docs/evaluation/plan.md): model, count, alert, throughput, and calibration evaluation requirements.
- [Crowd model inventory](docs/models/crowd-model-inventory.md): local checkpoint hashes, provenance status, and evidence limits.
- [Candidate crowd model card](docs/models/crowd-best-local-model-card.md): verified facts and owner-confirmation items for `best_local`.
- [Candidate runtime smoke record](docs/models/crowd-best-local-runtime-smoke.md): exact checkpoint/runtime/source evidence and limits from a six-frame inference check.
- [Candidate Plaza diagnostic](docs/models/crowd-best-local-plaza-diagnostic.md): small manually reviewed diagnostic comparison with explicit provenance and non-held-out limitations.
- [Crowd runtime pins](requirements/crowd-inference-cu121-windows.txt): direct package versions observed during the adapter smoke; clean-environment installation remains unverified.
- [Crowd evaluation format](docs/evaluation/crowd-evaluation-format.md): data contract, split/overlap evidence rules, and reproducible inference/scoring workflow.
- [Density estimator model card](docs/models/density-net-model-card.md): separate model type and unverified source benchmark details.
- [AI/ML integration note](docs/evaluation/AI_ML_INTERFACE_HANDOFF.md): proposed shared schemas and decisions for both application owners.
- [Parking occupancy model plan](docs/evaluation/parking-model-plan.md): task, data, interface, evaluation, and release requirements for the separate model.
- [Parking evaluation format](docs/evaluation/parking-evaluation-format.md): versioned manifest, reviewed-label, prediction, and lineage inputs for the parking scorer.
- [Parking occupancy evaluator](scripts/evaluate_parking_occupancy.py): reproducible per-stall, abstention, confusion-matrix, and site-count metrics for future labeled runs.
- [Demo operations runbook](docs/operations/demo-runbook.md): preparation and handling guidance for local demonstrations.

## Repository status

This repository contains planning documents, an initial AI/ML adapter/schema layer, and evaluation tooling. It is not yet a complete or verified runnable application. Existing prototype projects are located in the sibling directories `../heat_map/` and `../uav-crowd-monitoring/`. Any reused implementation requires review of technical dependencies, tests, licensing, model provenance, and data permissions before integration.

## Product limitations and safeguards

- Counts represent visible people in observed footage; they are not attendance totals and do not include hidden people.
- Image-space heat maps describe concentration within a video frame and are not geographic maps.
- Geographic density requires valid camera calibration and a measured usable area.
- Stale, partial, invalid, and unsupported observations must be reported as unavailable rather than represented as zero or normal conditions.
- Face recognition, identity inference, demographic inference, and persistent re-identification are excluded.
- Site-approved thresholds and human review are required for operational alerts.

## AI/ML starting point

The `best_local` checkpoint and density estimator remain in the reference `heat_map/` project; no model weights or source footage are stored here. See the [checkpoint inventory](docs/models/crowd-model-inventory.md), [candidate model card](docs/models/crowd-best-local-model-card.md), and [AI/ML integration handoff](docs/evaluation/AI_ML_INTERFACE_HANDOFF.md). The parking model is a separate planned workstream and has not been trained or evaluated in this repository.
