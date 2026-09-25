# `crowd_best_local_v1` Plaza diagnostic

## Scope and interpretation

This is a manual-label **training-fit diagnostic**, not held-out model validation, pilot acceptance, or a release decision. The exact checkpoint SHA-256 matches the E01 pilot's returned `best.pt`. Its pilot manifest records 90 reviewed Plaza adaptation crops from the same source-video SHA-256 listed below; the evaluated frames therefore overlap the model's training source and reviewed frame selection. The pilot run records independent target validation as unavailable. The measured values below describe only this small, targeted comparison.

The current evaluator report records `training_overlap_status: verified_overlap` and `evaluation_scope: TRAINING_FIT_MANUAL_LABEL_EVALUATION_OVERLAP_CONFIRMED`. The original predictions were generated before the pilot lineage was joined to the CrowdSight evaluation manifest; the lineage-enriched scoring run below recomputes the report from the same cached predictions, labels, and manifest without rerunning inference.

## Result

| Measure | Result |
|---|---:|
| Complete reviewed frames | 11 |
| Certain person boxes | 457 |
| Uncertain person annotations | 26 across all 11 frames |
| IoU matching threshold | 0.50 |
| True positives / false positives / false negatives | 67 / 125 / 390 |
| Precision / recall | 0.3490 / 0.1466 |
| Predictions ignored for overlap with uncertain boxes | 2 |
| Invalid/unknown prediction frames | 0 / 11 |
| Count and zone-count metrics | Not reported: no frame was fully unambiguous |
| Tracking or crossing metrics | Not evaluated |

The uniform subset (6 frames) had 39 TP, 56 FP, 200 FN, precision 0.4105 and recall 0.1632. The diagnostic subset (5 frames) had 28 TP, 69 FP, 190 FN, precision 0.2887 and recall 0.1284. These small, deliberately selected subsets are not statistically representative.

Detection metrics match certain manual boxes first using maximum-cardinality one-to-one matching. Unmatched predictions overlapping an uncertain annotation at IoU >= 0.50 are ignored. Count metrics require frames without uncertain annotations, so this run reports no count MAE, RMSE, bias, or zone-count result.

## Provenance

- Dataset: `e01-plaza-review-v1`; 12 review rows existed, with incomplete frame 135 excluded, leaving 11 complete frames.
- Source video: `../uav-crowd-monitoring/artifacts/plaza-passage-baseline-input.avi`; SHA-256 `921a664f1013c0e76d1a08121263c688fadc23fa258cb3cea35e18d228506f6d`.
- Source: “Video aéreo de la ronda de las Abuelas de Plaza de Mayo,” creator ProtoplasmaKid, Wikimedia Commons, [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The source project's local attribution record is `../uav-crowd-monitoring/artifacts/e01-finetune-pilot/provenance/plaza-source.md`.
- Original reviewed-label SHA-256: `dcfac99bd9cca131590692df25ef879d9c3fbdb1b01dda16c62680ef329d53a2`.
- Prepared manifest SHA-256: `774fb79af07e621e489fed7739ebd20aae28e75939046ef9cd0ad0dbce465517`.
- Prepared labels SHA-256: `a16fb39c2f50529838f44c0ceb43da1eaf83c780edd29bc85152d5aad6fbece7`.
- Training source evidence: UAV pilot manifest SHA-256 `93d36c7a9583ceee28dafdab679a484391e0f8f63fbd3b8a0354a8adbc0b5cf7`; imported-run report SHA-256 `63829b088a3e83c52dfc640170e98db180c2233a71c96fbbdec954fb13bffbb2`; run-provenance SHA-256 `9a406de50b8da1d56dd38f23972a3bf4abacb592127ce9059ecb13bdb42050e4`.
- Training mix: 90 reviewed Plaza crops from the source video below; 256 VisDrone replay images; 548 VisDrone regression-validation images previously used by the E01 base model. Target-independent validation is recorded as unavailable.
- Training-evidence JSON SHA-256: `9296f117c8b6a6a28d69463868bd85ca18af36b0a3c292d775958a5a5f1678df`.
- Predictions with lineage SHA-256: `f638bd70460e1dbeb6911e47263fcff4759745fb104498a3aa446a604cc68453`.
- Report JSON SHA-256: `7fa6bacc847e8896e1e7244e5a3c7b16fbdc7200255882bc79f636d065e860be`.
- Crowd profile SHA-256: `20cb9e8c95492c5b68ce86d8a57ec97a3b8e8234773d816024c5b0b450a5d2eb`.
- Checkpoint SHA-256: `12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc`.
- Runtime: Windows 10 build 19045; Python 3.10.11; PyTorch 2.5.1+cu121; Ultralytics 8.4.153; CUDA on NVIDIA GeForce GTX 1650 Ti; confidence 0.25; image size 1280; person class 0.
- Script SHA-256 values: preparation `77250a5aeaee3fe30e3898ff6e19054b7d9b1757d71f4cb03eaed2f7541fd11c`; inference recorded in predictions `e74a1c7f4ce79244cc0828c80fcfb90b6c76df471cb24ae4d50552c8b783a1f3`; current evaluator `41917af0e450365eb1bfee97caae37ab44e83b9c454bd500905c0bfbcce8db51`.

Prepared manifest, labels, predictions, training-evidence JSON, and report JSON were kept under the system temporary directory, not copied into Git. The lineage-enriched scoring step reused the recorded predictions and added the now-verified pilot lineage; it did not rerun inference. Recreate the manifest/labels using [`prepare_reviewed_diagnostic.py`](../../scripts/prepare_reviewed_diagnostic.py), the source project's review manifest, labels, and AVI; run inference with the historical v1 profile to reproduce raw predictions; then supply the pilot training-evidence JSON and run the scorer. The raw source video and checkpoint remain outside CrowdSight.
