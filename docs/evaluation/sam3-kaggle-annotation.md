# SAM3.1 annotation assistance on Kaggle

**Status:** private 30-frame annotation batch prepared; no SAM output produced yet.

This runbook records the bounded SAM3.1 attempt for the Mixkit intersection clip. It is intended to resume reproducibly after the Hugging Face credential is configured. SAM masks are proposals only; a human must review every selected frame before labels are used.

## Private Kaggle artifacts

- Dataset: [CrowdSight Mixkit 30-Frame SAM3 Annotation Batch](https://www.kaggle.com/datasets/surmullet/crowdsight-mixkit-30-frame-sam3-annotation-batch)
- Notebook: [CrowdSight Mixkit SAM3.1 30-Frame Annotation](https://www.kaggle.com/code/surmullet/crowdsight-mixkit-sam3-1-30-frame-annotation/edit)
- Both are configured as private. The dataset contains the bounded experiment bundle and 30 sampled JPEG frames; the source video is not included.
- The input manifest records hashes and identifies 30 frames covering approximately 60 seconds, sampled at approximately two-second intervals. This sparse selection supports qualitative review and a limited false-positive diagnostic only. It cannot establish tracking quality, temporal stability, recall, crowd-count accuracy, or held-out performance.

## Observed Kaggle setup

On 2026-09-25, the notebook started on Kaggle GPU T4 x2 and confirmed both visible devices as Tesla T4 GPUs with 15 GiB each. The worker is configured to use GPU 0. Its isolated Python 3.12 runtime installed PyTorch 2.9.1+cu126 and the SAM repository at commit `660a5e9e1b8b4c02c0ad97229b88a09a6e4ff5b7`; `pip check` reported no broken requirements.

Execution stopped before SAM checkpoint access or inference. The notebook reported that no Kaggle user secret named `HF_TOKEN` exists. The GPU session was stopped after recording the failure. No SAM model weights were retrieved and no annotation results exist.

## Resume procedure

1. Confirm the Hugging Face account has access approval for the exact [SAM 3.1 checkpoint repository](https://huggingface.co/facebook/sam3.1) and has an authorized read token. The experiment manifest specifies `facebook/sam3.1` and `sam3.1_multiplex.pt`.
2. In Kaggle, create a user secret named `HF_TOKEN` under **Add-ons → Secrets**. Enter the token only in Kaggle's secret form; do not place it in notebook cells, outputs, this repository, or chat.
3. Attach/enable `HF_TOKEN` for the private notebook. The notebook reads it using Kaggle's secrets client and does not print it.
4. Select **Run All**. The cells verify the input bundle, install the isolated runtime, check GPU and model access, run the configured FP16 SAM3.1 inference on the 30 frames, and create a private result ZIP.
5. Download the result ZIP and review its masks against all 30 source frames using the separate reviewer labels template. Keep machine proposals and human-approved labels as separate private artifacts. Do not score the proposals as ground truth.
6. Store the result archive, log, review record, and their SHA-256 hashes in approved private artifact storage. Keep the Hugging Face token and all video/frame/model artifacts out of Git.

## Interpretation and constraints

- The Kaggle path uses experimental FP16 inference on T4. It is not Meta's unchanged BF16 setup, and model accuracy has not been established for this path.
- The output is annotation assistance, not an evaluation result. Human correction is required for missed, duplicate, merged, or incorrect masks.
- The Mixkit video is already documented as a negative-heavy, non-Vietnam, overhead-traffic sample with sparse resolvable pedestrians. It is not suitable evidence for dense-crowd, Vietnam fixed-camera, motorbike-occupancy, or parking performance.
- Any later metric requires complete reviewed labels, an appropriate dataset and locked source-level split, full checkpoint training-lineage evidence, and reviewed independence and permission evidence. See the [evaluation plan](plan.md) and [Mixkit source review](candidate-video-sources.md).
