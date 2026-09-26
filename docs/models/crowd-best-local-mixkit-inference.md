# `crowd_best_local_v2` Mixkit inference record

## Evaluation status

- Run type: locked-sample inference before manual annotation; not an accuracy evaluation.
- Candidate manifest: [`mixkit-busy-intersection-test-v1.manifest.json`](../evaluation/manifests/mixkit-busy-intersection-test-v1.manifest.json); frame selection was locked before inference.
- Source video SHA-256: `e9084a41628e578d45f356e1a9ae1bfb6ad182f3786d09ad4f965aab259fe6a1`.
- Profile: `crowd_best_local_v2`; profile SHA-256 `987fd60033b06549f542fe2c3d8a965d19e7018c4964d30f7a606208cd3b115b`.
- Checkpoint SHA-256: `12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc`.
- Training overlap: `unknown_or_mixed`; no training evidence file was supplied. Do not describe this as verified held-out model performance.
- Manual labels: still blank in [`mixkit-busy-intersection-test-v1.labels-template.json`](../evaluation/manifests/mixkit-busy-intersection-test-v1.labels-template.json). No precision, recall, count error, or correctness claim can be computed yet.
- Review condition: complete all 30 labels without consulting either prediction file. SAM proposals, if generated, remain suggestions and require human correction and sign-off.

## Recorded inference runs

Both runs used the same locked 30-frame manifest and the checkpoint/profile hashes above. The CPU run is a separate execution record; no accuracy score or cross-device prediction-equivalence claim has been established.

### CUDA run

- Result: 30 selected frames, 30 valid observations, 0 unknown frames.
- Runtime: Windows 10 build 19045; Python 3.10.11; PyTorch 2.5.1+cu121; CUDA runtime 12.1; Ultralytics 8.4.153; OpenCV 5.0.0; NumPy 2.2.6; `cuda:0`, NVIDIA GeForce GTX 1650 Ti.
- Inference script SHA-256: `a439a9dac9b112f6bb19b36eebfe87be1d95ef2a6dd7eaea28a61d6a9304cf94`.
- Prediction JSON: `%TEMP%\crowdsight-mixkit-busy-intersection-best-local-predictions.json`; SHA-256 `d00e1154b48537f9d7e5ad42ed9472be08aee105e01171e1af8d9b45bcfbd3ec`.

### CPU repeat run

- Result: 30 selected frames, 30 valid observations, 0 unknown frames.
- Runtime: Windows 10 build 19045; Python 3.12.10; PyTorch 2.9.1+cpu; no CUDA; Ultralytics 8.4.143; OpenCV 4.12.0; NumPy 2.2.6; CPU.
- Inference script SHA-256: `627425e8160fabba2a9bc14d058c2cbf582984b5ad500b8c95a65205148671a2`.
- Prediction JSON, outside Git: `..\private-artifacts\mixkit-crowd-best-local-v2-predictions-20260925.json`; SHA-256 `bf3d5bf6ecff9b8abe4d3df4d1e4c34965e66d309e4d633f799324ac368d52be`.
- Profile operating point for both runs: confidence 0.25; image size 1280; person class ID 0.

Reproduce the CPU run from the CrowdSight repository root with the same source video, manifest, profile, checkpoint, and runtime:

```powershell
& ..\uav-crowd-monitoring\deliverables\crowd-monitor-app\.venv\Scripts\python.exe scripts\run_crowd_inference.py `
  --video ..\uav-crowd-monitoring\artifacts\independent-intersection\busy-intersection-fullhd.mp4 `
  --manifest docs\evaluation\manifests\mixkit-busy-intersection-test-v1.manifest.json `
  --profile configs\models\crowd_best_local.yaml `
  --checkpoint ..\heat_map\models\best.pt `
  --device cpu `
  --output ..\private-artifacts\mixkit-crowd-best-local-v2-predictions-20260925.json
```

The prediction artifacts and source video remain outside Git. Inference used no manually reviewed labels. Complete and adjudicate all 30 frames in the prediction-free review tool, then score either prediction file against the signed labels. Until source independence and complete training lineage are reviewed, the result is exploratory only. The clip is sparse overhead pedestrian footage and cannot validate dense-crowd, Vietnam-domain, parking-occupancy, or waiting-time performance.

## SAM 3.1 annotation-assistance diagnostic

A separate authorized private Kaggle T4 run processed the same 30 locked frames on 2026-09-25. It returned zero person proposals on all frames and zero invalid observations. Original-resolution review found small but visible pedestrians in several frames, so zero proposals likely include misses. It does not establish that every frame is person-free. No manual truth labels were entered, so no accuracy metric is available. See the [SAM3 Kaggle run record](../evaluation/sam3-kaggle-annotation.md).

The SAM output is a proposal artifact, not ground truth. It may be used only as a negative-heavy false-positive diagnostic after prediction-free human labels are completed. It cannot establish crowd recall/count accuracy, dense-crowd or Vietnam-domain performance, or parking performance. The private SAM bundle and outputs are excluded from Git.
