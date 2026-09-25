# Parking occupancy evaluation format

This workflow evaluates the parking model separately from crowd detection. It is model-agnostic and expects manually reviewed frame-level states for every configured stall. `scripts/evaluate_parking_occupancy.py` computes descriptive results; it does not approve release thresholds or validate safety for physical controls.

## Split and lineage rules

Partition by date, site, camera, or camera-date before selecting frames. Do not distribute adjacent frames, repeated recordings of the same parking event, or near-duplicate views across train/validation/test. Lock the test partition and selected frame list before generating predictions. A held-out candidate also requires a manifest `data_permission` record approved for `model_evaluation`, with a private evidence reference, its SHA-256, and a reviewer ID; the report records these fields but does not verify the evidence content. Use a new immutable `dataset_id`, `partition_id`, source-video SHA-256, and `camera_view_id` for each source partition. Record the immutable `space_layout_version` and exact configured `space_ids`. The candidate model's configured `camera_view_id` must match the test manifest; this prevents evaluation outside the camera view the site-specific model supports.

Every label and prediction input must match the manifest dataset, source hash, and layout version. Each sampled frame must appear exactly once in labels and predictions, and every frame must include every configured stall exactly once. A reviewed but obscured/unresolvable stall uses label state `UNKNOWN`; it is excluded from class metrics. A model abstention uses prediction state `UNKNOWN` with null confidence. It counts toward abstention and reduces known prediction coverage; it is not counted as `AVAILABLE`.

## Manifest example

```json
{
  "schema_version": 1,
  "dataset_id": "site-01-parking-test-v1",
  "split": "test",
  "site_id": "site-01",
  "camera_view_id": "view-east-v1",
  "space_layout_version": "lot-layout-v3",
  "partition_id": "camera-east-2026-09-test",
  "source_sha256": "<64-character-video-sha256>",
  "data_permission": {
    "status": "approved",
    "permitted_uses": ["model_evaluation"],
    "evidence_ref": "private://dataset/permission-review-record",
    "evidence_sha256": "<64-character permission-evidence SHA-256>",
    "reviewer_id": "reviewer-01"
  },
  "space_ids": ["A-017", "A-018"],
  "evaluation_protocol": {
    "split_unit": "camera_date",
    "selection_locked_before_predictions": true
  },
  "samples": [
    {"frame_index": 420, "media_time_s": 14.0},
    {"frame_index": 900, "media_time_s": 30.0}
  ]
}
```

## Labels and predictions

Labels contain complete manual review and an identifiable reviewer for each selected frame:

```json
{
  "schema_version": 1,
  "dataset_id": "site-01-parking-test-v1",
  "space_layout_version": "lot-layout-v3",
  "source_sha256": "<same-video-sha256>",
  "frames": [
    {"frame_index": 420, "complete": true, "reviewer": "reviewer-01",
     "spaces": [{"space_id": "A-017", "state": "OCCUPIED"},
                {"space_id": "A-018", "state": "UNKNOWN"}]}
  ]
}
```

Predictions identify model and training lineage separately:

```json
{
  "schema_version": 1,
  "dataset_id": "site-01-parking-test-v1",
  "space_layout_version": "lot-layout-v3",
  "source_sha256": "<same-video-sha256>",
  "model": {
    "profile_id": "parking_occupancy_site_v1",
    "camera_view_id": "view-east-v1",
    "profile_sha256": "<64-character-profile-sha256>",
    "checkpoint_sha256": "<64-character-checkpoint-sha256>"
  },
  "training_evidence": {
    "overlap_status": "unknown_or_mixed",
    "source_inventory_complete": false,
    "source_sha256s": [],
    "partition_ids": [],
    "manifest_sha256": null,
    "independence_evidence_ref": null,
    "independence_evidence_sha256": null
  },
  "frames": [
    {"frame_index": 420,
     "spaces": [{"space_id": "A-017", "state": "OCCUPIED", "confidence": 0.94},
                {"space_id": "A-018", "state": "UNKNOWN", "confidence": null}]}
  ]
}
```

The example has one frame for brevity; actual files must account for every manifest frame and every configured stall. Store full inputs and reviewer details in the approved private dataset location, not in Git when restricted.

## Run

```powershell
python scripts/evaluate_parking_occupancy.py `
  --manifest D:\approved-data\parking-test\manifest.json `
  --labels D:\approved-data\parking-test\labels.json `
  --predictions D:\approved-results\parking-test-predictions.json `
  --output D:\approved-results\parking-test-report.json
```

Declare `overlap_status` as `verified_disjoint`, `verified_overlap`, `overlap_possible`, or `unknown_or_mixed`; the source/partition lists should record the evidence behind that status and contain unique entries. The evaluator rejects malformed or duplicate inventory entries, contradictory verified claims, and automatically marks detected exact source-hash or partition overlap as training-fit even when the submitted status is unknown.

The report includes a confusion matrix with `OCCUPIED` and `AVAILABLE` ground-truth rows and `OCCUPIED`, `AVAILABLE`, and `UNKNOWN` prediction columns; manual `UNKNOWN` labels are excluded and reported separately. It also includes per-class precision/recall/F1 for the two known ground-truth classes, per-stall accuracy and abstention, known-label coverage, and occupied/available count MAE, RMSE, and bias for frames where every stall label and prediction is known. It also reports occupied-count MAPE only for frames with nonzero occupied ground truth; zero-occupancy frames are counted separately because percentage error is undefined there. The report records all input hashes and the evaluator script hash, the manifest's data-permission record, and the training-manifest hash, completeness flag, source-hash inventory, and partition IDs used for its overlap decision. A metadata-eligible held-out report is labelled `HELD_OUT_CANDIDATE_REQUIRES_MANUAL_EVIDENCE_REVIEW` only when test selection is locked, training inventory is complete and hash-identified, training source and partition lists are nonempty, there is no recorded source or partition overlap, the independence-evidence reference has a recorded SHA-256, and the manifest includes an approved data-permission record with `model_evaluation` use, evidence reference and SHA-256, and reviewer ID. The evaluator does not inspect the independence or permission evidence references; it records the independence review as `NOT_VERIFIED_BY_EVALUATOR_REVIEW_REQUIRED` and keeps `release_approval: false`. A named reviewer must verify evidence contents and authorization before describing results as verified held-out or approved. Otherwise the report is exploratory.

## Interpretation and additional evaluation

This scorer does not calculate confidence calibration, temporal stability, throughput, stale-frame response, or generalization by weather/time/vehicle type. Record those as separate analyses: reliability diagrams and Brier score for confidence when confidence is exposed; day/night, shadow/glare, weather, size/type, occlusion, camera-shift strata; and measured latency/throughput on named hardware. Calibration must be fit on training/validation data only, then evaluated on the locked test set. Any acceptance threshold requires product/site-owner approval. The initial product remains advisory; this score report cannot authorize gate/barrier actuation.
