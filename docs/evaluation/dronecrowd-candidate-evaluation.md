# DroneCrowd auxiliary evaluation candidate

**Status: candidate only; not approved, locked, or scored by CrowdSight.** This note records a possible external evaluation route discovered in the sibling workspace. It does not authorize use of the data or establish independent held-out performance.

## What is available locally

The sibling `heat_map/data/datasets/dronecrowd/VisDrone2020-CC/` contains an 82-sequence training list and 82 per-sequence annotation files. The extracted directory has 112 sequence folders total. The separate `testlist.txt` names 30 challenge sequences, but their annotation files are absent locally. The archive outside Git is 1,108,851,195 bytes with SHA-256 `08de7262b9f1c6fcf46f52cb88218842beb59f13e05452affd6a59252ee962c9`.

The sibling `chosen.txt` selects six sequences (`00001`, `00019`, `00037`, `00053`, `00072`, `00089`). The sibling README reports a 36-frame comparison on this selected set that included the current `best.pt` detector. Exclude all six from any new CrowdSight evaluation. The remaining 76 training-list sequences have 2,280 frames in total and a corresponding annotation file for each. This is an external candidate partition relative to the known E01 manifest, not proof of complete source independence.

## Annotation and metric compatibility

The labels are per-frame head points in `frame_id,x,y` format, not person bounding boxes. The existing CrowdSight box evaluator therefore cannot score this dataset as-is. The sibling evaluator supports point-distance matching, but its default 25-pixel radius and every-fifth-frame sampling are legacy settings, not approved CrowdSight evaluation policy. If data use is approved, create a CrowdSight-owned, provenance-gated point-evaluation manifest/scorer, decide and justify the point-matching radius before predictions, and report point precision/recall/F1 and per-frame count MAE/RMSE/bias. Do not compare these point metrics directly with box-IoU metrics. This dataset cannot establish confidence calibration unless the evaluation protocol separately defines binary correctness for emitted detections and accounts for conditioning on the score threshold.

## Permission and independence gates

- The [official DroneCrowd repository](https://github.com/VisDrone/DroneCrowd) describes 82 annotated training sequences and 30 challenge test sequences, but its repository page does not provide an explicit data license. The extracted local package has no license file. The [VisDrone privacy/data-protection page](https://aiskyeye.com/data-protection/) describes academic-use-only and CC BY-NC-SA 3.0 terms for the VisDrone2021 dataset; that page alone does not clearly establish the terms for this separate DroneCrowd 2020 challenge package. Obtain source-owner permission or an applicable license record for the intended evaluation before inference, annotation transformation, or redistribution.
- The current candidate model's immediate manifest lists Plaza and VisDrone data, not DroneCrowd. However, the complete upstream pretrained-weight and data-source inventory remains unavailable, so disjointness from the full model lineage is not established. Have the rights/provenance reviewer assess overlap before calling a result held out.
- The official [VisDrone challenge guidelines](https://aiskyeye.com/evaluate/test-guidelines_2021/) describe the 30-sequence challenge test set. Do not recover, infer, or substitute challenge labels. Use only annotations supplied with the locally available 82-sequence partition, and only after its terms are confirmed.
- Keep the existing archive, extracted data, annotations, predictions, and reports outside Git. Record the source URL, permission evidence, archive and sequence/annotation hashes, reviewer, profile/checkpoint hashes, script hash, runtime, and locked sequence/frame selection in approved private artifact storage.

## Decision

This is more promising than the Mixkit intersection for crowd localization/count diagnostics because it contains annotated aerial crowd sequences, but it is **not ready to use**. The required next steps are to establish data permission, verify no prior use of the 76 candidate sequences by this checkpoint, implement the point-based provenance-gated scorer, and then lock a sequence-level sample before inference. Until each gate passes, the candidate cannot close the held-out evaluation requirement.
