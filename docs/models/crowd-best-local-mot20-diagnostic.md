# Crowd best.pt MOT20-05 exploratory diagnostic (v4)

## Status

Local exploratory evaluation using publisher-provided MOT20 training annotations. This is not held-out performance, site acceptance, deployment approval, or a rights determination. Full checkpoint lineage and independence from MOT20 remain unverified. MOT20 does not represent Vietnam motorbike traffic, parking, or waiting time.

## Locked evaluation

- Dataset ID: mot20-mot20-05-stride25-test-v4. Sequence: MOT20-05 training sequence; complete sequence is split unit.
- Sampling: every 25th frame plus last frame; 134 frames.
- Archive hashes: video ebcf0e3d44e4f50b5357d24817e5db485d777633d1b8ca9e8380d1c8437dbdd7; labels 95decf629c332f80ace18024bf876996e6be89908ec593f05cda000270d6d9ad.
- Manifest SHA-256 aa991e52bd38d5377d8819b9f613bb62b613017268f6258e270d7d4b205e9ed5.
- Labels SHA-256 f2cbb1d371f5b57146bd5475e85bf5392af1b80925e234ee6a859f247a44bcef.
- Checkpoint SHA-256 12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc.
- Profile SHA-256 987fd60033b06549f542fe2c3d8a965d19e7018c4964d30f7a606208cd3b115b.
- Image prediction SHA-256 7f0f397974d246096aae8ab9defb3ff8fbda996c8123fc4b9013c7122eef8638. Adapted prediction SHA-256 ecd18282ec97bb2e789d826d25effda8616b2f86df499104f485bf12cf41df28.
- Runtime: Windows 10 build 19045, Python 3.12.10, PyTorch 2.9.1+cpu, Ultralytics 8.4.143, NumPy 2.2.6, CPU; threshold 0.25, image size 1280, class ID 0.
- Private output: ../private-artifacts/mot20-official-20260926/evaluation/mot20-05-stride25-v4.
- Script SHA-256 values: preparation faa49002ee4097ee1e8be9f5bf8cad0cf7b5c6ac8a2bb14248477a9f7c9b29bb; inference dc430ee32611fd75574759694e54fd94ea5cd5b172a98d5ec5f5517b9cc5b34b; adaptation f5d645aac5b2e06c2e8a8de7d78efc67dd4ae4ae044505c0e0bf3d765fb85f6c; box evaluator d92684d3272de3f40438a53e2a0cf2ac752064ac1226f3d0ca2dea2b9c7e256b; calibration scorer 5564a7cd3fc59517a7b2eb50ce8803bc196e87ef95439559b9c1c49bae6f7286. The adapted prediction and scoring reports carry inference provenance.

## Results

Inference valid on all 134 frames and emitted 12,294 detections. TP 8,240, FP 4,054, FN 17,880; precision 0.67024565, recall 0.31546708; count MAE 103.1791, RMSE 105.0382, signed bias -103.1791. Substantial undercounting is present at this operating point. Results apply only to sampled MOT20-05 pedestrians.

## Raw-score diagnostic

Computed only over emitted detections surviving threshold 0.25; it does not assess missed people and no calibrator was fitted. Brier 0.31010028, NLL 0.82096427, equal-width ECE 0.31191638, N=12,294. Scores remain RAW_MODEL_SCORE, not probabilities. Calibration JSON SHA-256 640954d2be083cd466e61efc234b8521129b1c27eabfe734bb0e84712d1b3643; reliability SVG SHA-256 4f414c20a25428d35984900dac269b0b87d0d47cb1cdbbc96cea6f36bdca13a0.

## Annotation transformation and rights

Publisher ground truth was filtered to marked pedestrians (class_id=1, mark!=0), converted from left/top/width/height to xyxy, clipped at image boundaries for partially visible boxes, and degenerate boxes rejected. The product lead authorized private local noncommercial evaluation and acquisition. ZIP CRC checks passed; data remain outside Git. The v4 manifest records dataset_license_status as UNVERIFIED; the historical CC BY-NC-SA 3.0 notice is explicitly marked unauthenticated. The evaluator records NOT_VERIFIED_BY_EVALUATOR_REVIEW_REQUIRED. Human terms review is required before redistribution or rights claims. Do not upload or publish source or derivatives.

## Next actions

1. Ask a named data/legal reviewer to authenticate applicable terms and derivative handling.
2. Inventory complete upstream pretraining and fine-tuning ancestry of best.pt; compare all known sources and partitions with MOT20-05.
3. If independence cannot be proven, retain this as exploratory and select a permitted independent dataset for any held-out evaluation.
4. Obtain permitted Vietnam fixed-camera data for product relevance; assess parking model separately after its training data and checkpoint exist.
