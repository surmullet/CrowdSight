# Crowd held-out evaluation data format

`scripts/evaluate_crowd_boxes.py` scores person boxes and zone counts against independently reviewed frames. It does not run model inference, verify training provenance, read the source video, or evaluate tracking/crossings. The source-video SHA-256 must be computed and verified by the dataset-preparation process; the evaluator checks that labels and predictions refer to the same manifest source hash and records hashes of all three input documents. The manifest split may be `diagnostic`, `test`, or `held_out`, plus an explicit partition protocol. A report is metadata-eligible as a held-out candidate only when the split is `test`/`held_out`, test selection was locked before predictions, the model's training data are documented as disjoint from the test partition, and an approved data-permission record explicitly permits `model_evaluation`. The report carries the permission evidence reference, digest, and reviewer ID; the evaluator does not dereference or authenticate that evidence. Otherwise metrics are labelled exploratory, even if the manifest says `held_out`.

## Split and annotation policy

Create the train/validation/test split by video, site, or flight before selecting frames. Neighboring frames from a source clip must not be split across datasets. The test manifest should have an immutable dataset ID and source-video SHA-256. Include scene strata such as sparse/moderate/dense, view angle, person scale/altitude, lighting, occlusion and camera motion when available.

Every selected frame requires a complete manual review, reviewer identifier, and a boxes array. An empty array means a reviewed zero-person frame. Each box has `bbox_xyxy` in original image pixels and a boolean `uncertain`. Detection metrics use certain boxes as positives and ignore unmatched predictions that overlap uncertain boxes at the configured IoU threshold. Count and zone-count metrics exclude any frame with uncertain boxes, since its full count is unresolved. Report uncertain annotations and count exclusions explicitly.

## Manifest example

```json
{
  "schema_version": 1,
  "dataset_id": "pilot-site-test-v1",
  "split": "held_out",
  "evaluation_protocol": {
    "split_unit": "video",
    "test_partition_id": "pilot-camera-01-2026-09-test",
    "selection_locked_before_predictions": true
  },
  "source_id": "camera-01",
  "source_sha256": "<64-character source video SHA-256>",
  "data_permission": {
    "status": "approved",
    "permitted_uses": ["model_evaluation"],
    "evidence_ref": "private://dataset/permission-review-record",
    "evidence_sha256": "<64-character permission-evidence SHA-256>",
    "reviewer_id": "reviewer-01"
  },
  "width": 1920,
  "height": 1080,
  "zone_polygons_normalized": {
    "north-gate": [[0.1, 0.2], [0.5, 0.2], [0.5, 0.9], [0.1, 0.9]]
  },
  "samples": [
    {"frame_index": 120, "media_time_s": 4.0, "stratum": "moderate_oblique"}
  ]
}
```

The frame list is selected before running candidate models. For `test` and `held_out` inference, `run_crowd_inference.py` refuses to start unless the manifest marks selection locked, names a supported split unit and partition ID, and contains an approved `model_evaluation` permission record with evidence reference, SHA-256, and reviewer ID. This is a metadata preflight only; a named reviewer must still verify the evidence itself. Diagnostic runs can use an unlocked selection, but their reports remain exploratory or training-fit. Complete the [dataset record template](dataset-record-template.md) in the private dataset location to capture permission/provenance and split evidence; do not commit private footage or identifiable labels without approval.

## Labels example

```json
{
  "schema_version": 1,
  "dataset_id": "pilot-site-test-v1",
  "source_sha256": "<same source video SHA-256>",
  "frames": [
    {
      "frame_index": 120,
      "complete": true,
      "reviewer": "reviewer-01",
      "boxes": [
        {"bbox_xyxy": [400, 200, 438, 300], "uncertain": false}
      ]
    }
  ]
}
```

The labels file must include every manifest frame exactly once. Marking a frame complete is an assertion that all visible people were reviewed; partial annotation is not ground truth.

## Predictions example

```json
{
  "schema_version": 1,
  "dataset_id": "pilot-site-test-v1",
  "source_sha256": "<same source video SHA-256>",
  "models": {
    "best_local": {
      "profile_id": "crowd_best_local_v2",
      "profile_sha256": "<64-character model profile SHA-256>",
      "checkpoint_sha256": "12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc",
      "training_overlap_status": "unknown_or_mixed",
      "independence_evidence_ref": null,
      "independence_evidence_sha256": null,
      "training_manifest_sha256": null,
      "training_source_inventory_complete": false,
      "training_source_sha256s": [],
      "training_partition_ids": [],
      "training_evidence_file_sha256": null,
      "runtime": {"python_version": "...", "numpy_version": "...", "opencv_version": "...", "ultralytics_version": "...", "pytorch_version": "...", "cuda_runtime_version": "...", "cudnn_version": null, "platform": "...", "device": "..."},
      "frames": [
      {"frame_index": 120, "valid": true,
       "boxes": [[400, 200, 438, 300]],
       "scored_boxes": [{"bbox_xyxy": [400, 200, 438, 300], "raw_score": 0.82}]}
      ]
    }
  }
}
```

Each candidate must include every sampled frame once. `valid:false` is an explicit unknown/failed observation and must contain no boxes; it is excluded from accuracy denominators and counted in the unknown rate. Valid, reviewed zero-person frames use `valid:true` and an empty boxes array. New inference runs preserve `scored_boxes` in the same order as `boxes`; each record carries the identical `bbox_xyxy` and the detector's `raw_score`. This score is not a correctness probability. Checkpoint SHA-256, model-profile ID, and profile-file SHA-256 must be recorded for every model. Declare `training_overlap_status` as `verified_disjoint`, `verified_overlap`, `overlap_possible`, or `unknown_or_mixed`, and record the training manifest hash, complete training-source SHA-256 inventory, training partition IDs, and reference plus SHA-256 for reviewed independence evidence. Source hashes and partition IDs must be unique. The evaluator rejects malformed or duplicated evidence entries and contradictory verified claims, checks exact source-hash and partition-ID overlap, and marks detected exact overlap as training-fit even if the submitted status is unknown. All other non-held-out runs are exploratory. A metadata-eligible held-out candidate requires locked test selection, a complete/hash-identified training inventory, no detected overlap, a nonempty independence-evidence reference plus SHA-256, and an approved data-permission record permitting `model_evaluation` with evidence reference, SHA-256, and reviewer ID. It is not approved until a named reviewer verifies the referenced evidence. For `best.pt`, the local UAV pilot records now identify the checkpoint's mixed Plaza/VisDrone fine-tuning lineage and confirm Plaza source overlap; use `verified_overlap` for that Plaza diagnostic. Its independent target validation remains unavailable.

## Run and interpret

```powershell
$env:CROWDSIGHT_CROWD_CHECKPOINT = "D:\approved-artifacts\best.pt"
python scripts/run_crowd_inference.py `
  --video D:\approved-data\pilot-test.mp4 `
  --manifest data/evaluation/pilot-site-test/manifest.json `
  --profile configs/models/crowd_best_local.yaml `
  --training-evidence D:\approved-data\model-lineage\best-local-training-evidence.json `
  --output outputs/evaluation/pilot-site-test-predictions.json

python scripts/evaluate_crowd_boxes.py `
  --manifest data/evaluation/pilot-site-test/manifest.json `
  --labels data/evaluation/pilot-site-test/labels.json `
  --predictions outputs/evaluation/pilot-site-test-predictions.json `
  --output outputs/evaluation/pilot-site-test-report.json `
  --iou 0.5
```

For a previously reviewed diagnostic export, `scripts/prepare_reviewed_diagnostic.py` validates the video/label source hashes, removes incomplete frames, converts one-based review frame IDs to zero-based decoded-frame indices, and writes `split: diagnostic`. Example:

```powershell
python scripts/prepare_reviewed_diagnostic.py `
  --review-manifest ..\uav-crowd-monitoring\artifacts\e01-review-context\manifest.json `
  --reviewed-labels ..\uav-crowd-monitoring\e01-plaza-reviewed-labels.json `
  --video ..\uav-crowd-monitoring\artifacts\plaza-passage-baseline-input.avi `
  --output-dir $env:TEMP\crowdsight-e01-diagnostic
```

The source project's Plaza de Mayo labels are training-fit material for the E01 adaptation and are not held out. The UAV pilot manifest confirms that the same Plaza source video (SHA-256 `921a664f1013c0e76d1a08121263c688fadc23fa258cb3cea35e18d228506f6d`) contributed reviewed crops to the exact `best.pt` checkpoint hash; this diagnostic therefore has confirmed source and frame overlap. Use `verified_overlap` and keep the result training-fit; it must not be reported as held-out performance. The model's separate target-site independent validation remains unavailable.

Choose a new `--output-dir` for each preparation run; the tool fails rather than overwrite an existing manifest or label file.

`--training-evidence` is optional and accepts a JSON object with `training_overlap_status`, `independence_evidence_ref`, `independence_evidence_sha256`, `training_manifest_sha256`, `training_source_inventory_complete`, `training_source_sha256s`, and `training_partition_ids`. The runner hashes that evidence file and carries both its file hash and the declared training-manifest hash into predictions. A held-out candidate requires a SHA-256 for the referenced independence-evidence artifact; the evaluator records the digest but does not dereference or authenticate it. Without the option, it records `unknown_or_mixed` and an empty inventory. Use `verified_overlap` only when the training-source or partition overlap is documented; use `verified_disjoint` only when the complete training inventory and independent review support non-overlap and the evaluator's exact guards pass.

The output includes per-model evaluation scope, overlap evidence status, micro precision/recall, frame count MAE/RMSE/bias where fully certain frames exist, zone count MAE/RMSE/bias where fully certain frames exist, condition strata, uncertain annotation and count-exclusion lists, ignored predictions overlapping uncertain regions, invalid/unknown frame rate, input-document hashes, data-permission evidence metadata, and the inference/evaluator script hashes. New inference outputs record Python, NumPy, OpenCV, PyTorch, CUDA runtime, cuDNN, Ultralytics, platform, and device metadata alongside profile thresholds. This metadata improves reproduction but does not guarantee bitwise-equal results across hardware/runtime combinations. A metadata-eligible held-out report is labelled `HELD_OUT_CANDIDATE_REQUIRES_MANUAL_EVIDENCE_REVIEW` only when selection is locked, training independence evidence is complete, and an approved data-permission record covers model evaluation; the evaluator does not dereference or authenticate the independence or permission evidence references, and `release_approval` remains false. A named reviewer must inspect evidence contents and authorization before describing results as verified held-out or approved. IoU matching maximizes the number of one-to-one matches at the configured threshold. Zone counts use each box's bottom-centre point; polygon boundaries count inside. The evaluator does not establish calibration, live latency, tracking quality, or site safety. The site owner must approve numerical acceptance criteria.

### Raw-score calibration evaluation

Once labels are complete and prediction files include `scored_boxes`, run the separate calibration scorer on the same manifest, labels, predictions, and IoU rule:

```powershell
python scripts/evaluate_confidence_calibration.py `
  --manifest data/evaluation/pilot-site-test/manifest.json `
  --labels data/evaluation/pilot-site-test/labels.json `
  --predictions outputs/evaluation/pilot-site-test-predictions.json `
  --output outputs/evaluation/pilot-site-test-calibration.json `
  --iou 0.5 `
  --bins 10
```

The scorer reuses the primary evaluator's strict input and provenance checks, then assigns each emitted detection a binary outcome by maximum-cardinality one-to-one IoU matching. Unmatched predictions overlapping uncertain annotations are excluded; other unmatched predictions are false positives. It reports Brier score, negative log-likelihood, and equal-width expected calibration error overall and by manifest stratum, with bin counts and mean score/observed accuracy. Results are conditional on detections surviving the configured confidence threshold; they do not describe missed people or scores below threshold. This is a diagnostic of the raw score, not a fitted calibrator. It does not change `RAW_MODEL_SCORE`, authorize displaying probability, or establish a release/acceptance threshold. Fit a future calibrator using a distinct calibration partition only, then evaluate it once on a locked independent test set and obtain the reviewed contract and site-owner approvals described above. Old prediction files without `scored_boxes` must be regenerated; the scorer fails with that instruction rather than guessing scores.
