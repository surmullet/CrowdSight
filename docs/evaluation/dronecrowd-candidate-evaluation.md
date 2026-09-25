# DroneCrowd auxiliary evaluation candidate

**Status: candidate only; not approved, locked, or scored by CrowdSight.** This note records a possible external evaluation route discovered in the sibling workspace. It does not authorize use of the data or establish independent held-out performance.

## What is available locally

The sibling `heat_map/data/datasets/dronecrowd/VisDrone2020-CC/` contains an 82-sequence training list and 82 per-sequence annotation files. The extracted directory has 112 sequence folders total. The separate `testlist.txt` names 30 challenge sequences, but their annotation files are absent locally. The archive outside Git is 1,108,851,195 bytes with SHA-256 `08de7262b9f1c6fcf46f52cb88218842beb59f13e05452affd6a59252ee962c9`.

The sibling `chosen.txt` selects six sequences (`00001`, `00019`, `00037`, `00053`, `00072`, `00089`). The sibling README reports a 36-frame comparison on this selected set that included the current `best.pt` detector. Exclude all six from any new CrowdSight evaluation. The remaining 76 training-list sequences have 2,280 frames in total and a corresponding annotation file for each. This is an external candidate partition relative to the known E01 manifest, not proof of complete source independence.

## Annotation and metric compatibility

The labels are per-frame head points in `frame_id,x,y` format, not person bounding boxes. The existing CrowdSight box evaluator cannot score localization from these labels. The official [DroneCrowd challenge metric](https://aiskyeye.com/evaluate/crowd-counting/) is per-frame count MAE and MSE, so CrowdSight will use count-only scoring here and will not claim box-IoU precision/recall, head localization, or tracking quality. `scripts/evaluate_dronecrowd_counts.py` reports MAE, MSE, RMSE, signed count bias, unknown prediction rate, and per-sequence/per-condition count metrics. A complete point annotation is converted to its point count by the authorized private data-preparation step; no labels or footage are committed to Git. This point-count evaluation does not establish confidence calibration.

The scorer accepts three JSON documents. The manifest records a locked selection and source archive hash; each sample has a stable `sequence_id` and one-based `frame_id`. Labels contain a complete human-reviewed `person_count` for each selected frame. Predictions contain the valid/unknown state and count from the versioned CrowdSight detector plus checkpoint/profile/runtime and complete training-lineage metadata. Example row shapes:

```json
{
  "schema_version": 1,
  "dataset_id": "dronecrowd-remaining-v1",
  "split": "held_out",
  "source_sha256": "<archive-sha256>",
  "width": 1920,
  "height": 1080,
  "evaluation_protocol": {
    "split_unit": "sequence",
    "test_partition_id": "dronecrowd-remaining-sequences-v1",
    "selection_locked_before_predictions": true
  },
  "data_permission": {
    "status": "approved",
    "permitted_uses": ["model_evaluation"],
    "evidence_ref": "private://permission-review",
    "evidence_sha256": "<permission-evidence-sha256>",
    "reviewer_id": "reviewer-id"
  },
  "samples": [
    {"sequence_id": "00002", "frame_id": 1, "image_path": "sequences/00002/00001.jpg", "image_sha256": "<image-sha256>", "stratum": "dense"}
  ]
}
```

For each manifest sample, a labels frame has `sequence_id`, `frame_id`, `complete: true`, a nonempty `reviewer`, and integer `person_count`. The corresponding prediction frame has `sequence_id`, `frame_id`, `valid: true|false`, and nonnegative integer `count` when valid. An invalid frame has no count and is included in the unknown prediction rate, not accuracy metrics. The predictions root has `schema_version`, matching `dataset_id` and `source_sha256`, and `model` metadata: `profile_id`, `profile_sha256`, `checkpoint_sha256`, `training_overlap_status`, `training_source_inventory_complete`, `training_source_sha256s`, `training_sequence_inventory_complete`, `training_sequence_ids`, `training_partition_ids`, `independence_evidence_ref`, `independence_evidence_sha256`, and `runtime`. The two inventory-complete flags must reflect a reviewed, full lineage inventory; use empty arrays only when a reviewer confirms there are no entries. Exact source, partition, or sequence overlap forces `TRAINING_FIT`. A `HELD_OUT_CANDIDATE_REQUIRES_MANUAL_EVIDENCE_REVIEW` report additionally requires complete inventories, `verified_disjoint`, an independence evidence hash, and approved evaluation permission. The scorer checks metadata fields only; a named reviewer must authenticate the evidence artifacts.

Once the source owner has approved this use and the archive/image hashes and manifest are prepared, infer from the extracted image tree without loading labels:

```powershell
$env:CROWDSIGHT_CROWD_CHECKPOINT = "D:\approved-artifacts\best.pt"
python scripts/run_crowd_image_inference.py `
  --images-root D:\approved-data\dronecrowd\VisDrone2020-CC `
  --source-archive D:\approved-data\dronecrowd\dronecrowd.zip `
  --manifest D:\approved-data\dronecrowd\manifest.json `
  --profile configs/models/crowd_best_local.yaml `
  --training-evidence D:\approved-data\model-lineage\best-local-training-evidence.json `
  --output D:\approved-results\dronecrowd\predictions.json
```

The runner refuses unapproved permission metadata, archive-hash mismatch, frame-hash mismatch, path escape from the supplied image root, or dimension mismatch. It writes one result per selected frame and refuses to overwrite an existing prediction file. The runner and scorer record their own script hashes. Permission and lineage evidence references still require human authentication.

After permission is approved and selected-frame count labels and predictions are stored privately, run:

```powershell
python scripts/evaluate_dronecrowd_counts.py `
  --manifest D:\approved-data\dronecrowd\manifest.json `
  --labels D:\approved-data\dronecrowd\labels.json `
  --predictions D:\approved-results\dronecrowd\predictions.json `
  --output D:\approved-results\dronecrowd\count-report.json
```

## Permission and independence gates

- The [official DroneCrowd repository](https://github.com/VisDrone/DroneCrowd) and [Crowd Counting 2020 challenge page](https://aiskyeye.com/challenge/crowd-counting/) describe 82 annotated training sequences and 30 challenge-test sequences. The challenge page says users must register with an institutional email before participating. The [general download page](https://aiskyeye.com/download/) invites visitors to download and use datasets, but it does not identify a license for this specific DroneCrowd 2020 package. The [VisDrone privacy/data-protection page](https://aiskyeye.com/data-protection/) says the dataset is for academic use only; its copyright paragraph specifically names VisDrone2021 and assigns that dataset CC BY-NC-SA 3.0. Do not silently extend the 2021 license grant to DroneCrowd 2020, or treat the general download invitation as a complete permission record. The local archive remains without a license file. Before any CrowdSight inference or annotation transformation, obtain and retain source-specific terms/permission that cover the intended noncommercial evaluation; redistribution remains separately unapproved.
- The current candidate model's immediate manifest lists Plaza and VisDrone data, not DroneCrowd. However, the complete upstream pretrained-weight and data-source inventory remains unavailable, so disjointness from the full model lineage is not established. Have the rights/provenance reviewer assess overlap before calling a result held out.
- The official [VisDrone challenge guidelines](https://aiskyeye.com/evaluate/test-guidelines_2021/) describe the 30-sequence challenge test set. Do not recover, infer, or substitute challenge labels. Use only annotations supplied with the locally available 82-sequence partition, and only after its terms are confirmed.
- Keep the existing archive, extracted data, annotations, predictions, and reports outside Git. Record the source URL, permission evidence, archive and sequence/annotation hashes, reviewer, profile/checkpoint hashes, script hash, runtime, and locked sequence/frame selection in approved private artifact storage.

## Decision

This is more promising than the Mixkit intersection for aerial crowd-count diagnostics because it contains point-annotated crowd sequences, but it is **not ready to use**. The 76 sequence IDs and all 30 frame IDs per sequence have been frozen before any new inference in the [candidate selection record](manifests/dronecrowd-remaining-train-sequences-candidate-v1.json). The record remains pending source-specific permission and full checkpoint-lineage review; it is not a CrowdSight evaluation manifest and contains no predictions. The count scorer is now prepared, but no data processing is authorized by that code or by the public download page. Next steps are to obtain a permission record for the intended noncommercial evaluation, confirm the sequence-level annotation preparation policy, verify the 76 candidates were not present in any checkpoint training source, then produce predictions and score them. Until those gates pass, no held-out claim is supported.
