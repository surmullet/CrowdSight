# Runtime smoke: `crowd_best_local_v1`

## Result

The CrowdSight adapter loaded the checkpoint and returned structurally valid detections from six selected frames. This verifies basic adapter/runtime compatibility in the recorded environment. It is not an accuracy evaluation, benchmark, or pilot acceptance result.

## Reproduction record

- Date: 2026-09-24.
- Operating system: Windows 10, build 19045.
- Python: `3.10.11`.
- Direct runtime versions: PyTorch `2.5.1+cu121`; torchvision `0.20.1+cu121`; Ultralytics `8.4.153`; NumPy `2.2.6`; OpenCV Python package `5.0.0.93` (`cv2` reports `5.0.0`); PyYAML `6.0.3`; Pillow `12.3.0`.
- Direct compatibility summary: [`requirements/crowd-inference-cu121-windows.txt`](../../requirements/crowd-inference-cu121-windows.txt). Recursive exact-version lock captured from that installed environment: [`requirements/crowd-inference-cu121-windows.lock.txt`](../../requirements/crowd-inference-cu121-windows.lock.txt). The lock is not wheel-hash-locked and has not been installed in a clean environment.
- Proposed clean-environment install commands (not yet run):

  ```powershell
  py -3.10 -m venv .venv-crowd
  .\.venv-crowd\Scripts\python -m pip install -r requirements\crowd-inference-cu121-windows.lock.txt --extra-index-url https://download.pytorch.org/whl/cu121
  .\.venv-crowd\Scripts\python -m pip install --no-deps -e .
  ```
- CrowdSight profile ID: `crowd_best_local_v1`.
- Model-profile SHA-256: `20cb9e8c95492c5b68ce86d8a57ec97a3b8e8234773d816024c5b0b450a5d2eb`.
- Checkpoint SHA-256: `12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc`.
- Tracker: BoT-SORT UAV profile, SHA-256 `f6b571babb8a7d078241934ded037f49d69dd854523a0793481456cd4043e641`. A separate sequential tracker smoke covered frames 250–259: 10 frames returned one tracked detection each and one run-local track ID was observed. Elapsed time was approximately 2.644 seconds for the sequence. This is a basic runtime/contract check, not a tracking accuracy or throughput measurement.
- Runtime device: CUDA `cuda:0`; NVIDIA GeForce GTX 1650 Ti.
- Input: `uav-crowd-monitoring/artifacts/independent-intersection/busy-intersection-fullhd.mp4`.
- Input SHA-256: `e9084a41628e578d45f356e1a9ae1bfb6ad182f3786d09ad4f965aab259fe6a1`.
- Source: Mixkit “Busy intersection aerial view”; source page and Mixkit Stock Video Free License are recorded in the reference project's `artifacts/independent-intersection/SOURCE.md` and `source.json`.
- Frame size: 1920×1080. Inference profile: confidence `0.25`, image size `1280`, person class ID `0`.
- Sampled source frame indices and detection counts: `0:0`, `250:1`, `500:3`, `750:1`, `1000:1`, `1300:2`.
- All returned anchors were within normalized `[0,1]` bounds and carried a pixel bounding box.
- Wall time for frame seeks plus six inference calls after model load: approximately 3.771 seconds. Frames were nonconsecutive, so this is not a throughput/FPS measurement.

## Interpretation limits

- No manual labels were available for this source; no precision, recall, count error, or detection correctness can be inferred.
- The checkpoint hash matches the E01 pilot-best model. The pilot manifest lists Plaza crops and VisDrone replay/previously used validation data, while the independent-intersection smoke clip is a separate source with no manual labels. It remains an adapter/runtime smoke input only; no accuracy or held-out claim follows from detections on an unlabeled clip.
- The first sampled frame produced zero detections; this was not compared with ground truth.
- The adapter/runtime pairing and basic sequential tracking have been exercised only in the listed environment. A clean-environment install, CPU inference, sequential-video pipeline integration, and any accuracy/ID-switch evaluation remain unverified.
