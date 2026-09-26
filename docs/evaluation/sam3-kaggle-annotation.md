# SAM3.1 annotation assistance on Kaggle

**Status:** private 30-frame SAM 3.1 annotation-assistance run completed on Kaggle T4 on 2026-09-25. No reviewed ground-truth labels or accuracy results were produced.

This runbook records the bounded SAM3.1 annotation-assistance run for the Mixkit intersection clip. SAM masks are proposals only; a human must review every selected frame before labels are used.

## Private Kaggle artifacts

- Dataset: [CrowdSight Mixkit 30-Frame SAM3 Annotation Batch](https://www.kaggle.com/datasets/surmullet/crowdsight-mixkit-30-frame-sam3-annotation-batch)
- Notebook: [CrowdSight Mixkit SAM3.1 30-Frame Annotation](https://www.kaggle.com/code/surmullet/crowdsight-mixkit-sam3-1-30-frame-annotation/edit)
- Both are configured as private. The dataset contains the bounded experiment bundle and 30 sampled JPEG frames; the source video is not included.
- The input manifest records hashes and identifies 30 frames covering approximately 60 seconds, sampled at approximately two-second intervals. This sparse selection supports qualitative review and a limited false-positive diagnostic only. It cannot establish tracking quality, temporal stability, recall, crowd-count accuracy, or held-out performance.

## Observed Kaggle setup and completed run

On 2026-09-25, the notebook started on Kaggle GPU T4 x2 and confirmed both visible devices as Tesla T4 GPUs with 15 GiB each. The worker is configured to use GPU 0. Its isolated Python 3.12 runtime installed PyTorch 2.9.1+cu126 and the SAM repository at commit `660a5e9e1b8b4c02c0ad97229b88a09a6e4ff5b7`; `pip check` reported no broken requirements.

The missing Kaggle `HF_TOKEN` issue was resolved in the authorized Kaggle runtime using its secret mechanism. Hugging Face checkpoint access succeeded and SAM 3.1 inference completed on all 30 selected frames. The run reported zero person proposals, zero invalid observations, and two bounded tracking sessions (24 and 6 frames). The run's maximum and mean raw person occupancy were both zero. Processing time was 41.22 seconds end-to-end (about 0.728 frames/second), and model loading took 20.04 seconds. Peak GPU allocated/reserved memory was 6.38/6.71 GiB. End-to-end throughput includes CPU conversion, overlay rendering, and encoding; it must not be presented as live model latency.

The zero-proposal output should not be interpreted as evidence that the frames are person-free. A subsequent visual pass over all 30 original-resolution sampled frames confirmed that several frames contain small but visible pedestrians on the sidewalk and crosswalk, indicating likely missed person proposals. The pass was visual triage only: it did not create verified per-frame counts or bounding boxes and is not independent human annotation. The `manual_counts.csv` truth fields remain blank. Do not score the zero-proposal output as a negative-only diagnostic until every frame has complete human review and the labels are independently checked. This sample cannot establish dense-crowd, Vietnam-domain, fixed-camera, or parking performance. Tracking continuity is within each short sampling session only; the approximately two-second source-frame gaps make cross-frame identity unsuitable for evaluation.

The private run output and log were not placed in this repository. The downloaded copies and hashes are recorded in the private artifact bundle's `SAM3_RUN_RESULTS.md`; verify them before transfer or archival. The bundle is outside Git. The ZIP's embedded `manifest.json` identifies every included output file by SHA-256 and size.

## Reproduction and review procedure

1. To reproduce the run, confirm the Hugging Face account has access approval for the exact [SAM 3.1 checkpoint repository](https://huggingface.co/facebook/sam3.1) and has an authorized read token. The experiment manifest specifies `facebook/sam3.1` and `sam3.1_multiplex.pt`.
2. In Kaggle, create or enable the user secret named `HF_TOKEN` under **Add-ons → Secrets**. Enter the token only in Kaggle's secret form; do not place it in notebook cells, outputs, this repository, or chat.
3. Attach/enable `HF_TOKEN` for the private notebook. The notebook reads it using Kaggle's secrets client and does not print it.
4. The bounded 30-frame run is already complete. To reproduce it, select **Run All** in the private notebook with the same pinned inputs and secret configuration; first ensure the GPU quota and checkpoint access are available.
5. Review the output masks against all 30 source frames using the separate reviewer labels template. Keep machine proposals and human-approved labels as separate private artifacts. Do not score the proposals as ground truth.
6. Preserve the result archive, log, review record, and their SHA-256 hashes in approved private artifact storage. The archive and log from this run are already preserved in the local private artifact bundle. Keep the Hugging Face token and all video/frame/model artifacts out of Git.

## Interpretation and constraints

- The Kaggle path uses experimental FP16 inference on T4. It is not Meta's unchanged BF16 setup, and model accuracy has not been established for this path.
- The output is annotation assistance, not an evaluation result. Human correction is required for missed, duplicate, merged, or incorrect masks.
- The Mixkit video is already documented as a negative-heavy, non-Vietnam, overhead-traffic sample with sparse resolvable pedestrians. It is not suitable evidence for dense-crowd, Vietnam fixed-camera, motorbike-occupancy, or parking performance.
- Any later metric requires complete reviewed labels, an appropriate dataset and locked source-level split, full checkpoint training-lineage evidence, and reviewed independence and permission evidence. See the [evaluation plan](plan.md) and [Mixkit source review](candidate-video-sources.md).
