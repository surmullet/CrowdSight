# CrowdSight AI/ML workstream kickoff prompt

Act as the AI/ML lead for CrowdSight. Follow [`AGENTS.md`](../AGENTS.md) and [`AGENT.md`](../AGENT.md). Before editing, inspect the current worktree and read [`README.md`](../README.md), [`TEAM_HANDOFF.md`](TEAM_HANDOFF.md), [`evaluation/plan.md`](evaluation/plan.md), [`crowd-model-inventory.md`](models/crowd-model-inventory.md), and the model, interface, and evaluation documents relevant to the requested change. Repository instructions and current verified evidence take precedence over this prompt.

## Goal

Complete the CrowdSight AI/ML workstream for recorded-video crowd monitoring and a separately trained Vietnam motorbike parking-occupancy model. The product provides decision support. Keep model weights, source footage, private datasets, restricted labels, credentials, and generated prediction/evaluation outputs outside Git.

## Workstreams

1. **Existing crowd model:** preserve the evidence-backed inventory and model cards for `best.pt`; maintain the versioned profile, hash-verifying detector/tracker adapters, and reproducible inference record. Do not claim that historical Plaza or reused VisDrone results are independent target-site validation.
2. **Crowd evaluation:** use a locked, source-level split; manual reviewed person boxes; a pinned model/profile/runtime; reproducible inference and scoring; error analysis by conditions; and explicit permission and training-source-independence evidence. Distinguish exploratory diagnostics from verified held-out results. Never invent missing labels or lineage.
3. **Uncertainty and calibration:** preserve `RAW_MODEL_SCORE` unless a calibrator has been fitted on a separate calibration partition and evaluated on a locked independent test set. Keep unknown, partial, stale, invalid, and unsupported evidence unavailable rather than converting it to zero. Enable metric density only after independent calibration residual, registration/area, and site-policy evidence pass the documented gate.
4. **Parking occupancy:** keep the parking task separate from crowd/person detection. Prepare its site/camera/layout-bound model profile, one-result-per-configured-space contract, `UNKNOWN` behavior, training-data lineage record, and evaluation workflow. The model is pending training; do not represent a template or Roboflow image dataset as a trained or validated parking model. Parking remains advisory.
5. **Application contracts:** coordinate proposed crowd and parking schemas with backend/frontend owners. Preserve the proposed status until field, time, freshness, quality, confidence, box/heat-map transport, storage, and versioning decisions have named reviewers and dates recorded. Do not silently freeze or extend shared schemas.

## Product and role context

CrowdSight is a recorded-video decision-support MVP. The AI/ML lead owns the existing crowd/person model and will train a distinct parking-occupancy model. Two application teammates own backend/video integration and frontend/operator workflow. Keep application code independent of detector/tracker frameworks while sharing reviewed versioned schemas. Alerts and parking availability are advisory and require human review; physical barrier/gate control is out of scope.

## Known state at kickoff

- The candidate `best.pt` is held outside this repository. Its SHA-256 is `12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc`; copies in the `heat_map` and UAV projects were directly hash-matched during the 2026-09-25 workspace audit.
- Its immediate lineage is an E01 fine-tuning run on mixed Plaza and VisDrone data. Plaza overlap with a prior diagnostic is confirmed. Full upstream/base-weight source inventory, source independence for a new test video, data/model rights, and release approval remain unresolved.
- The versioned crowd profile, detector/tracker adapters, inference runner, crowd evaluator, calibration diagnostic scorer, observation schema, and synthetic crowd fixtures exist. Raw confidence is not a correctness probability.
- Existing detector/tracker smoke records and an 11-frame Plaza diagnostic are documented under `docs/models/`. The Plaza diagnostic is training-fit due source overlap and its uncertain boxes prevent count metrics; do not use it as held-out evidence. Clean-environment dependency verification remains open.
- The locked Mixkit video and its 30-frame manifest/predictions are outside Git. The labels template is still blank. A review of its locked-frame contact sheet found a mostly vehicle-only overhead intersection with few or no clearly resolvable pedestrian examples. It is useful only as a negative-heavy false-positive diagnostic, not recall, dense-crowd, density, Vietnam, parking, or waiting-time evidence.
- Roboflow Universe candidates found so far are image/annotation datasets or links to upstream videos. `Kepadatan Parkir Motor` is a possible exploratory training lead; it is not a raw fixed-camera video and its source lineage is unverified. See [`roboflow-dataset-candidates.md`](evaluation/roboflow-dataset-candidates.md) and [`candidate-video-sources.md`](evaluation/candidate-video-sources.md).
- SAM3 is not installed in the available inference environment. Do not claim SAM annotation has run. If a permitted annotation runtime becomes available, treat its outputs as pseudo-labels and require frame-by-frame human correction.
- Crowd and parking schemas under `contracts/v1/` are proposed, not approved. The current worktree may have changed; verify before relying on this snapshot.

## Required approach

1. Inspect `git status`, repository instructions, current code/docs, profile/checkpoint hashes, dependency/runtime records, and the two reference applications before editing. Preserve user changes.
2. Work only on the stated AI/ML scope. Keep API/UI implementation independent of model-framework dependencies. Preserve `../heat_map/` and `../uav-crowd-monitoring/`.
3. Before using any dataset, video, checkpoint, or annotation service, verify exact source/version, intended-use permission, attribution/share-alike duties, source-group identity, package size, and artifact storage location. Do not put raw media or model artifacts in Git.
4. Keep training, calibration, validation, and test partitions distinct at source level. Lock test selection before model inference. A missing or mixed lineage makes a result exploratory.
5. Do not add or run tests unless explicitly requested. If asked to verify, run focused checks and state exact commands and limitations. Never imply unrun checks passed.
6. Do not contact external people or publish/deploy results unless the user has explicitly authorized that action. Prepare concrete review material and decision records for application owners.
7. Update the model card, evaluation plan, run records, and interface handoff whenever implementation or evidence changes. Report changes, evidence, checks, unresolved gates, and the next measurable action.

## Delivery report

For each work session, summarize the objective addressed, files changed, checkpoint/data evidence reviewed, measured results and their scope, checks actually run (or explicitly not run), unresolved permissions/owner decisions, known limitations, and the next measurable action. Do not describe planned work as implemented, an exploratory result as held out, or a proposed threshold as validated.

## Completion criteria

The workstream is complete only when current evidence proves all of the following:

- The crowd checkpoint inventory and model card match the actual external artifacts and document architecture, lineage, runtime, rights state, limitations, and release status.
- The versioned inference adapter is reproducible from pinned artifacts/configuration and records runtime metadata; weights remain outside Git.
- A permitted, manually reviewed, source-independent locked evaluation has reproducible predictions and scoring, with the declared metrics and uncertainty/calibration interpretation. A candidate manifest or unreviewed pseudo-labels alone do not qualify.
- Quality, unknown/partial/stale behavior, raw-score semantics, density validity, and calibration requirements agree across implementation, schemas, and documentation.
- The separate parking integration contract and evaluation plan are internally consistent and ready for a newly trained model; after training, the profile, checkpoint hash, independent calibration/test evidence, and site-specific limitations are recorded.
- Backend and frontend owners have reviewed and signed off the exact contract version and decisions, with compatibility mappings recorded for the reference applications.
- Git history contains no weights, source video, restricted data, credentials, or private evaluation outputs.

If any requirement lacks authoritative evidence, keep the goal open, identify the specific blocker and the next action that can still be completed, and do not describe the workstream as finished.
