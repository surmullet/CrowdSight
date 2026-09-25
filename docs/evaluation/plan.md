# Evaluation plan

The AI/ML owner prepares evaluation data and model metrics; all three owners and the pilot owner agree acceptance criteria before using alerts operationally. Crowd/person detection and parking-space occupancy are separate evaluation tasks. See [Parking occupancy model plan](parking-model-plan.md).

## Readiness and handoff gates

| Workstream | Current state | Evidence or decision required to advance |
|---|---|---|
| Existing crowd checkpoint | `best.pt` is hash-matched to the UAV E01 returned checkpoint; mixed Plaza/VisDrone lineage and known Plaza diagnostic overlap are documented in the [model inventory](../models/crowd-model-inventory.md). | Rights owner/legal reviewer confirms whether inherited data, base weights, fine-tuned checkpoint, and intended deployment/redistribution are permitted. Do not infer approval from checkpoint availability. |
| Crowd inference adapter | Versioned profile and hash-verifying detector/tracker adapters are present; inference output records profile/checkpoint hashes and runtime metadata. Direct pins and a recursive exact-version lock are recorded for the observed Windows/Python 3.10/CUDA 12.1 environment. | Integrator should clean-install and run the documented smoke on the target platform; the version lock is not hash-locked and has not been clean-install-verified. Other platforms require a separately pinned compatible PyTorch runtime. |
| Crowd held-out evaluation | Versioned manifest, manual labels/predictions format, inference runner, scorer, and independence/permission gates are implemented. No verified held-out result exists: Plaza overlaps training; `best.pt` was previously measured on the six-sequence DroneCrowd comparison; the DroneCrowd challenge annotations are absent; and `heat_map/data/videos/test.mp4` has no reviewed labels. A separately selected, nearly fixed overhead Mixkit intersection video is available in `../uav-crowd-monitoring/artifacts/independent-intersection/` with SHA-256 `e9084a41628e578d45f356e1a9ae1bfb6ad182f3786d09ad4f965aab259fe6a1`; the recorded E01 manifests do not list this clip as a direct training source. The E01 baseline and fine-tuning lineage are only partially reviewed, however, and the complete upstream pretraining/source inventory is unavailable, so disjointness is not established. A 30-frame uniform sample is locked before CrowdSight inference in the [candidate manifest](manifests/mixkit-busy-intersection-test-v1.manifest.json). `crowd_e01_t02_v1`, `crowd_best_local_v2`, and `crowd_pilot_last_experimental_v1` now have pinned predictions for those frames; prediction files remain outside Git. A prediction-free [offline review page](../../tools/crowd-frame-review.html) is ready to collect manual labels. The permission record approves noncommercial internal evaluation/annotation only; labels remain blank. The clip supports sparse overhead pedestrian diagnostics, not dense-crowd or Vietnam site evidence. | Reviewer obtains/validates a complete training-source inventory and reviews source independence; annotator completes and adjudicates all 30 frames. Then score all three pinned prediction files. Results remain exploratory until the evidence references and authorization are authenticated. See [candidate video sources](candidate-video-sources.md). |
| Uncertainty and geographic density | Quality states, raw-score semantics, and fail-closed density validity checks are defined. New crowd inference files preserve raw detector scores; a separate scorer reports Brier score, negative log-likelihood, equal-width ECE, and stratum results against manually reviewed detections. This remains descriptive and does not fit a calibrator or authorize probability claims. | Annotator completes labels; AI/ML owner reviews sample counts and condition coverage. Site supplies surveyed calibration and area evidence, independent residual review, and policy approval before metric density can be enabled. Any probability output also needs a separate calibration partition, locked independent test evidence, reviewed contract revision, and site-owner approval. |
| Parking occupancy | Separate profile and adapter implement per-space classification as the v1 default; the plan makes the fixed-camera assumption and fallback to a revised detection contract explicit. | Product/camera owner confirms a stable camera view and versioned stall layout before data collection. If those assumptions fail, agree a revised detector/association contract first. Data owner then supplies permitted labeled train/calibration/test partitions; AI/ML owner trains and evaluates a distinct checkpoint. |
| Shared application schemas | Crowd and parking v1 schemas and synthetic fixtures are available as proposals. | Backend and frontend owners resolve the contract questions and record reviewer/date approvals in [`contracts/v1/README.md`](../../contracts/v1/README.md) before treating schemas as frozen. |
| Artifact hygiene | Weight/video/archive patterns are ignored; no matching model or source-video artifacts are tracked in Git in the inspected worktree. | Continue to store approved artifacts and source media externally; inspect Git status before sharing changes. |

These gates separate implementation readiness from data evidence, legal review, trained artifacts, and owner approval. Passing a code or schema gate alone does not establish model accuracy, data rights, or release approval.

## Dataset split

Split by video, site, or flight. Never put neighboring frames from one clip across train/validation/test splits. Preserve source/license/provenance, annotation version, frame timestamps, zone version, model/config hashes, and hardware for every report.

## Report at minimum

- Precision and recall with declared person matching rule and IoU.
- If confidence is presented as a probability: keep the current raw model score as default; fit any calibrator on a separate calibration/validation partition only; label predicted detections as correct/incorrect using the declared one-to-one IoU matching rule; report reliability diagrams, Brier score, negative log-likelihood, expected calibration error with a declared binning rule, sample counts, and results by operating-condition strata on the locked independent test partition. Store the calibrator ID/hash, calibration-data manifest hash, matching rule, and test report. Site-owner approval is required before a calibrated-probability claim; v1 application contracts currently permit only `RAW_MODEL_SCORE`.
- Per-frame and per-zone count MAE, RMSE, signed bias, and error distribution.
- Results by sparse/moderate/dense scene, altitude/view angle, lighting, occlusion, motion blur, and camera movement where present.
- Dense-scene failure and unsupported-observation rate.
- Processing throughput on named hardware, separated from capture-to-display latency (MVP replay does not establish live latency).
- If tracking is evaluated: ID switches/fragmentation and their effect on occupancy; do not substitute track count for attendance.
- If geographic outputs are evaluated: calibration method, CRS, surveyed control/check points, p50/p95 map residual, zone-boundary assignment errors, observed coverage, and invalidation rules.
- If alerts are evaluated: episode precision/recall, false alerts per hour, missed sustained events, and time to alert against approved thresholds.

## Acceptance policy

The pilot/site owner must approve numerical tolerances and threshold rationale. Until that happens, report observed metrics without labeling them passed. Document unsupported conditions and show unknown/unavailable rather than forcing a count.

## Model inventory reference

Current checkpoint evidence and unresolved provenance are recorded in [crowd-model-inventory.md](../models/crowd-model-inventory.md). The inventory distinguishes locally present weights from expected but unavailable handoff artifacts and documents the limits of recorded metrics.

An exploratory 11-frame comparison for `best_local` is recorded in [crowd-best-local-plaza-diagnostic.md](../models/crowd-best-local-plaza-diagnostic.md). It does not satisfy the held-out evaluation requirement and must not be used as pilot acceptance evidence.

Geographic density remains unavailable unless the runtime gate receives a calibration-evidence reference/hash, a passing held-out residual against the site-approved maximum, an independence-review reference/hash with explicit verification, and a site-policy-approval reference/hash with explicit approval. The gate validates required fields/hash formats; the calling service must verify artifact contents and authorization before setting the approval flags. Missing inputs or a non-finite density result must fail closed to a named unavailable status.
