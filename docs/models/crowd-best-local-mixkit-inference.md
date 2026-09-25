# `crowd_best_local_v2` Mixkit inference record

## Run summary

- Run type: locked-sample inference before manual annotation; not an accuracy evaluation.
- Candidate manifest: [`mixkit-busy-intersection-test-v1.manifest.json`](../evaluation/manifests/mixkit-busy-intersection-test-v1.manifest.json); frame selection was locked before inference.
- Source video SHA-256: `e9084a41628e578d45f356e1a9ae1bfb6ad182f3786d09ad4f965aab259fe6a1`.
- Profile: `crowd_best_local_v2`; profile SHA-256 `987fd60033b06549f542fe2c3d8a965d19e7018c4964d30f7a606208cd3b115b`.
- Checkpoint SHA-256: `12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc`.
- Inference script SHA-256: `a439a9dac9b112f6bb19b36eebfe87be1d95ef2a6dd7eaea28a61d6a9304cf94`.
- Result: 30 selected frames, 30 valid inference observations, 0 unknown frames.
- Training overlap: `unknown_or_mixed`; no training evidence file was supplied. Do not describe this as verified held-out model performance.
- Manual labels: blank. No precision, recall, count error, or correctness claim can be computed yet.

## Runtime

- Windows 10 build 19045; Python 3.10.11.
- PyTorch 2.5.1+cu121, CUDA runtime 12.1, CUDA available.
- Ultralytics 8.4.153; OpenCV 5.0.0; NumPy 2.2.6.
- Device: `cuda:0`, NVIDIA GeForce GTX 1650 Ti.
- Profile operating point: confidence 0.25; image size 1280; person class ID 0.

## Artifact handling

The prediction JSON is kept outside Git at `%TEMP%\crowdsight-mixkit-busy-intersection-best-local-predictions.json`. Its SHA-256 is `d00e1154b48537f9d7e5ad42ed9472be08aee105e01171e1af8d9b45bcfbd3ec`. The repository's `outputs/` and `data/evaluation/` directories were not writable in the current sandbox, so the result remains in the local temporary directory and should be copied to approved artifact storage before temporary files are cleaned.

Reproduce from the CrowdSight repository root with the same source video, manifest, profile, checkpoint, and runtime:

```powershell
& ..\heat_map\.venv\Scripts\python.exe scripts\run_crowd_inference.py `
  --video ..\uav-crowd-monitoring\artifacts\independent-intersection\busy-intersection-fullhd.mp4 `
  --manifest docs\evaluation\manifests\mixkit-busy-intersection-test-v1.manifest.json `
  --profile configs\models\crowd_best_local.yaml `
  --checkpoint ..\heat_map\models\best.pt `
  --output $env:TEMP\crowdsight-mixkit-busy-intersection-best-local-predictions.json
```

Inference used no manually reviewed labels. Complete and adjudicate all 30 frames in the prediction-free review tool, then score the predictions. Until source independence and complete training lineage are reviewed, the result is exploratory only. The clip is sparse overhead pedestrian footage and cannot validate dense-crowd, Vietnam-domain, parking-occupancy, or waiting-time performance.
