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
- [Crowd runtime lock](requirements/crowd-inference-cu121-windows.lock.txt): recursive exact package versions captured from the recorded Windows/Python/CUDA inference environment; the lock has not been clean-installed and does not include wheel hashes. The smaller [direct pin set](requirements/crowd-inference-cu121-windows.txt) remains a compatibility summary.
- [Crowd evaluation format](docs/evaluation/crowd-evaluation-format.md): data contract, split/overlap evidence rules, and reproducible inference/scoring workflow.
- [MOT20 crowd-evaluation preparation](scripts/prepare_mot20_crowd_evaluation.py) and [image-sequence prediction adapter](scripts/adapt_image_sequence_predictions.py): private, hash-verified MOTChallenge label conversion and ordered-image predictions into the shared box scorer. The MOT20-05 workflow has completed locally on a locked 134-frame sample; results remain exploratory pending rights and checkpoint-lineage review.
- [MOT20-05 exploratory diagnostic](docs/models/crowd-best-local-mot20-diagnostic.md): measured box/count metrics, hashes, raw-score caveats, and unresolved rights/independence gates.
- [Crowd frame review tool](tools/crowd-frame-review.html): offline prediction-free annotation page that verifies selected source video and locked frame identity before labeling.
- [Locked Mixkit candidate manifest](docs/evaluation/manifests/mixkit-busy-intersection-test-v1.manifest.json): 30 uniform overhead frames for a sparse-scene diagnostic; permission is approved for noncommercial internal evaluation/annotation and labels remain blank.
- [Mixkit inference record](docs/models/crowd-best-local-mixkit-inference.md): pinned `crowd_best_local_v2` inference is complete for the 30 locked frames; predictions remain local/outside Git, and no accuracy metrics are available until labels are reviewed.
- [Experimental pilot-last model card](docs/models/crowd-pilot-last-model-card.md): documents the separately hashed final-epoch checkpoint and its inference on the same locked 30-frame sample.
- [Original E01 model card](docs/models/crowd-e01-handoff-model-card.md): documents the baseline checkpoint verified inside the external pilot archive and its inference on the locked sample.
- [Candidate datasets and videos](docs/evaluation/roboflow-dataset-candidates.md) and [video source notes](docs/evaluation/candidate-video-sources.md): Roboflow dataset suitability, source provenance limits, licenses, and review status.
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
