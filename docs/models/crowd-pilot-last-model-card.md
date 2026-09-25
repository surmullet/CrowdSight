# Model card: `crowd_pilot_last_experimental_v1`

## Status and artifact identity

This is the final-epoch checkpoint from the E01 Plaza/VisDrone fine-tuning pilot. It is a separate experimental checkpoint from `best_local`; it is not the default profile and is not release-approved.

- SHA-256: `6d4b691a82ad74eb3d36ee61c386bd8724c2bac39eaa1945f3a3eb838bfe485f`.
- Size: 19,235,482 bytes.
- Matching external copies: `../uav-crowd-monitoring/e01-finetune-pilot-result/last.pt` and `../uav-crowd-monitoring/artifacts/e01-finetune-returned/last.pt`.
- CrowdSight profile: [`crowd_pilot_last_handoff.yaml`](../../configs/models/crowd_pilot_last_handoff.yaml), profile ID `crowd_pilot_last_experimental_v1`.
- The model file remains outside Git. Supply it only through the profile's trusted local checkpoint path or `CROWDSIGHT_CROWD_CHECKPOINT`; the adapter verifies its SHA-256.

The two external copies were hashed directly during the 2026-09-25 inventory refresh and match the expected profile digest.

## Training lineage

The UAV run record identifies dataset `e01-finetune-pilot-v1`, a 10-epoch fine-tune using PyTorch `2.10.0+cu128`, Ultralytics `8.4.143`, two Tesla T4 GPUs, image size 1280, seed 42, and deterministic mode. The initial E01 checkpoint hash is `8332891c201ec99458c567e17b059bbac59ed8fa57134d1cc7a7048905a31483`; it is available as a verified member in the external fine-tuning archive, but is not installed as a standalone CrowdSight checkpoint.

The pilot manifest records:

- 90 Plaza adaptation crops from the Plaza source video, SHA-256 `921a664f1013c0e76d1a08121263c688fadc23fa258cb3cea35e18d228506f6d`.
- 256 VisDrone replay images.
- 548 VisDrone regression-validation images previously used by the base model.

Independent target-site validation is recorded as unavailable. The inherited checkpoint/data rights require review before broader use. The VisDrone terms include noncommercial restrictions; the Plaza source has CC BY-SA attribution/share-alike requirements. Ultralytics model licensing also requires review for the intended distribution/deployment. See [the complete checkpoint inventory](crowd-model-inventory.md).

## Recorded operating point

- Person class ID: 0.
- Detector confidence threshold: 0.15.
- Image-size setting: 1280.
- Tracker: ByteTrack, one video session per instance, config SHA-256 `6d115a3345fe878f37a4c3b75f81b3b7ee31b00e0603fe6555a4d3495e7b4292`.
- Recorded tracker-selection values: high/new-track threshold 0.20, low threshold 0.15, match threshold 0.8, buffer 30, score fusion disabled.

The configuration is preserved in [`crowd_pilot_last_handoff.yaml`](../../configs/models/crowd_pilot_last_handoff.yaml). Tracking IDs are temporary within one run and are not attendance identities.

## Recorded results and limits

The UAV run report records final-epoch VisDrone regression mAP50:95 of 28.71%, below the original E01 validation's 36.04%. The pilot's maximum recorded mAP50:95 was 29.15% at epoch 4. These figures are inherited run records, not a newly reproduced comparison on an identical environment.

The source report also records an 11-frame Plaza comparison and tracker-threshold selection. Those frames came from the Plaza source used for adaptation, so the comparison is training-fit. It is not held-out site accuracy. The source record is `../uav-crowd-monitoring/docs/finetune-pilot-results.md`.

## Mixkit locked-sample inference

The candidate profile was run on the same 30 frames selected in the locked Mixkit manifest before inference. All 30 inference observations were valid; none failed. No manual labels have been added, so there are no accuracy metrics. The output is not a held-out performance claim because training-source independence is still unknown.

- Prediction artifact: `%TEMP%\crowdsight-mixkit-busy-intersection-pilot-last-predictions.json` (kept outside Git).
- Prediction artifact SHA-256: `623932bca73e0510acd481460b271618df0888def476280236d1ceba24b8b206`.
- Profile SHA-256: `a37290213919ae9118e2fa2a7defa07b00eced5457c0c74772c0139c982f4b95`.
- Checkpoint SHA-256: `6d4b691a82ad74eb3d36ee61c386bd8724c2bac39eaa1945f3a3eb838bfe485f`.
- Inference script SHA-256: `a439a9dac9b112f6bb19b36eebfe87be1d95ef2a6dd7eaea28a61d6a9304cf94`.

Independent training-source verification remains unavailable, so any score must remain exploratory unless complete lineage and separation evidence is reviewed. This profile is for comparative model and adapter work only.
