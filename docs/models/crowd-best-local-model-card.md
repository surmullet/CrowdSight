# Model card: `best_local` candidate

## Status

Candidate custom person detector available as `../heat_map/models/best.pt`, `../uav-crowd-monitoring/e01-finetune-pilot-result/best.pt`, and `../uav-crowd-monitoring/artifacts/e01-finetune-returned/best.pt`. All three files were directly hashed and match `12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc`. The UAV import report records that hash as the `best.pt` returned from `e01-finetune-pilot-v1`. The pilot manifest hash is `93d36c7a9583ceee28dafdab679a484391e0f8f63fbd3b8a0354a8adbc0b5cf7`; the report lists the initial E01 checkpoint hash `8332891c201ec99458c567e17b059bbac59ed8fa57134d1cc7a7048905a31483`. The fine-tune manifest has 90 Plaza adaptation crops, 256 VisDrone replay images, and 548 VisDrone regression-validation images. The Plaza source was also used by the diagnostic set, so that comparison is training-fit. The run record explicitly says independent target validation is unavailable. This card documents lineage but does not approve deployment or claim held-out site performance.

The matching training artifacts are in the UAV project, not under `heat_map/runs/`. They record a 10-epoch fine-tune on two Tesla T4s using PyTorch 2.10.0+cu128 and Ultralytics 8.4.143, image size 1280, seed 42, and deterministic training. The base E01 model is documented as YOLO11s trained on VisDrone DET (categories 1 and 2 merged into person). The manifest notes that VisDrone regression validation had already been used by the base model, so it is not an independent test for this fine-tune.

## Intended use

Person detection in recorded UAV/fixed-camera frames for visible occupancy analysis, subject to held-out evaluation and supported-view definition. Tracking can be added for temporal association but does not produce unique attendance. No identity inference or persistent re-identification is intended.

## Available configuration facts

- Current CrowdSight profile ID: `crowd_best_local_v2`; historical run profile ID: `crowd_best_local_v1`.
- Current profile file SHA-256: `987fd60033b06549f542fe2c3d8a965d19e7018c4964d30f7a606208cd3b115b`.
- Source checkpoint: `heat_map/models/best.pt`.
- Matching returned pilot artifact: `uav-crowd-monitoring/artifacts/e01-finetune-returned/best.pt`.
- Expected file SHA-256: `12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc`.
- Source inference settings: person class ID 0, confidence threshold 0.25, image-size setting 1280, automatic device selection.
- Source profile pairs the checkpoint with `botsort_uav.yaml`; tracker settings and source-file checksum are recorded in `configs/models/crowd_best_local.yaml`.
- Training source profile: fine-tuned E01 pilot-best checkpoint; base architecture YOLO11s.
- Fine-tuning runtime recorded in the UAV import/run provenance: PyTorch `2.10.0+cu128`, Ultralytics `8.4.143`; two Tesla T4s; 10 epochs; image size 1280; seed 42; deterministic mode.
- Data manifest roles: 90 user-reviewed Plaza crops, 256 VisDrone train-replay images, and 548 VisDrone regression-validation images. The regression-validation data were previously used by the base model; independent target-site validation is recorded as unavailable.
- Rights-review state in the current profile: VisDrone data rights pending; Ultralytics YOLO license pending; release approval pending.

## Remaining owner confirmation

- Exact base-model training code/commit and full artifact lineage for the initial E01 checkpoint.
- Deployment/redistribution terms for VisDrone-derived weights/data and the inherited E01 checkpoint. The official [VisDrone terms](https://aiskyeye.com/data-protection/) state academic-use-only availability and CC BY-NC-SA 3.0 terms, including a noncommercial restriction. Treat commercial deployment and redistribution as blocked until the rights owner/legal reviewer confirms the rights or grants written permission; the effect of the terms on trained weights requires legal review.
- Ultralytics YOLO licensing for the exact installed version and intended use. Ultralytics' [official license page](https://www.ultralytics.com/license) says trained/fine-tuned YOLO models are covered by AGPL-3.0 by default and proprietary/commercial products require AGPL-compliant release or an Enterprise License. Confirm the applicable terms with the rights owner/legal reviewer.
- Fine-tune code commit and complete training-source inventory; the existing pilot manifest identifies the mix but does not establish a target-site independent test partition.
- Intended operating envelope: camera height/view angle, minimum person pixel scale, frame rate, lighting and crowd density.
- Whether the checkpoint can be transferred to approved artifact storage and used in the target deployment. The Plaza source provenance also records [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) attribution/share-alike conditions.

## Performance

No independent pilot-site performance result is claimed for this candidate. Plaza metrics are training-fit because the same source video contributed reviewed crops to this checkpoint. VisDrone regression-validation results are not independent because those images were previously used by the base model. Evaluation must use a new, permitted, locked site/video split and manual labels; required metrics and split rules are defined in `docs/evaluation/plan.md`.

## Limitations and abstention

Expected risks include small or occluded people, overlap in dense scenes, camera motion, blur, shadows, unusual viewpoints, and tracker fragmentation. Until these are measured, unsupported or invalid frames must be marked unavailable and counted in coverage reporting. Confidence is a model score, not calibrated probability.

## Privacy and safety

Outputs are anonymous frame-local detections/tracks. Face recognition, demographics, and persistent identity tracking are excluded. Threshold alerts remain subject to human review and site approval.
