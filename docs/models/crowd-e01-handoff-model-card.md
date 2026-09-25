# Model card: `crowd_e01_t02_v1`

## Status and artifact identity

This is the original E01-T02 YOLO11s person detector and conservative ByteTrack baseline. The checkpoint is present inside the external UAV fine-tuning archive, but it is not installed or stored in CrowdSight.

- Profile: [`crowd_e01_handoff.yaml`](../../configs/models/crowd_e01_handoff.yaml), profile ID `crowd_e01_t02_v1`.
- Embedded checkpoint: `../uav-crowd-monitoring/artifacts/e01-finetune-pilot.zip#weights/e01.pt`.
- Source archive size: 174,734,900 bytes; archive SHA-256 `74393ff0dba9878d195f11fdd9a1ad58a607a53e99f0288b6b81dd72ee8bfd5c`.
- Embedded checkpoint size: 19,241,754 bytes; SHA-256 `8332891c201ec99458c567e17b059bbac59ed8fa57134d1cc7a7048905a31483`.
- The checkpoint was extracted only to `%TEMP%` for inference; no weight file was added to Git.

The archive hash and embedded checkpoint hash were computed directly. The member digest matches the expected value in the profile and the sibling UAV baseline record.

## Training lineage and recorded benchmark

The sibling source record documents a YOLO11s detector with one `person` class, trained from the `yolo11s.pt` initialization on VisDrone DET, merging categories 1 (pedestrian) and 2 (people). Its converted dataset contains 6,471 training and 548 validation images. Recorded training arguments include a 60-epoch limit, image size 1280, global batch 16, seed 42, and two Tesla T4 GPUs; the available source record does not prove all 60 epochs completed. The checkpoint’s immediate training-source dataset is VisDrone. The sibling stock-detector probe contains a `yolo11s.pt` copy whose SHA-256 matches the current publisher-hosted YOLO11s file; the probe identifies it as COCO-pretrained. However, the historical E01 training record has no initialization-file hash or resolved URL, so this is supporting lineage evidence, not proof of exact byte identity with the training input. The full source inventory and Mixkit independence remain unresolved; see the [checkpoint inventory](crowd-model-inventory.md).

The source record reports validation precision 79.13%, recall 66.33%, mAP50 73.63%, and mAP50:95 36.04%. These are inherited benchmark-validation figures, not newly reproduced measurements and not pilot-site accuracy. See `../uav-crowd-monitoring/docs/phase1-baseline-and-dual-t4.md`.

## Recorded operating point

- Person class ID: 0.
- Detector confidence threshold: 0.15.
- Image-size setting: 1280.
- Tracker: ByteTrack T02, high threshold 0.45, low threshold 0.15, new-track threshold 0.45, match threshold 0.80, buffer 30, score fusion enabled.
- The Mixkit inference below used the detector only. It did not evaluate tracking or occupancy.

## Mixkit locked-sample inference

The detector was run on the same 30 frames locked before inference in the Mixkit candidate manifest. All 30 observations were valid; none failed. Manual labels remain blank. Training-source independence is not established, so this is an unscored exploratory prediction set, not held-out accuracy evidence.

- Prediction artifact: `%TEMP%\crowdsight-mixkit-busy-intersection-e01-handoff-predictions.json` (outside Git).
- Prediction artifact SHA-256: `8498478c09ce4cec9ce2ca2de89eca4311929b8ab7d74b88daa89b68ed2d3cd3`.
- Profile SHA-256: `30cdaa8970d5ef718459b5a97b3800ef63e3d320f03da7d10ef205730c9c3771`.
- Checkpoint SHA-256: `8332891c201ec99458c567e17b059bbac59ed8fa57134d1cc7a7048905a31483`.
- Inference script SHA-256: `a439a9dac9b112f6bb19b36eebfe87be1d95ef2a6dd7eaea28a61d6a9304cf94`.

Use the [checkpoint inventory](crowd-model-inventory.md) for the complete candidate list, source rights status, and lineage limitations.
