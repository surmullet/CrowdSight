# AI/ML interface handoff for application owners

**Status:** proposed integration contract. Backend and frontend owners must confirm field requirements and units before the schema is treated as frozen.

Machine-readable proposed v1 schemas and synthetic review fixtures are in [`contracts/v1/`](../../contracts/v1/README.md). Treat them as the source of field requirements while reviewing this handoff; they are not approved API contracts yet.

## Crowd inference boundary

Implemented adapter interfaces are in `src/crowdsight/detection/adapter.py`; YAML profile loading is in `src/crowdsight/detection/profile_loader.py`; shared frame/person observation types are in `src/crowdsight/common/observations.py`. `UltralyticsPersonDetector` returns current person detections. `UltralyticsPersonTracker` returns only tracker-associated current observations and must be instantiated per video session. The tracker adapter does not emit predicted lost tracks as observed people. Use detector-only outputs if raw detections are required.

Profile loading requires PyYAML, while inference requires NumPy, PyTorch, and the compatible Ultralytics runtime. The observed Windows/CUDA direct pins are in [`requirements/crowd-inference-cu121-windows.txt`](../../requirements/crowd-inference-cu121-windows.txt); the captured recursive exact-version lock is [`requirements/crowd-inference-cu121-windows.lock.txt`](../../requirements/crowd-inference-cu121-windows.lock.txt). The lock is not wheel-hash-locked and has not been clean-install-verified.

Install the shared adapter package from the repository root before using the documented imports:

```powershell
py -3.10 -m pip install -r requirements\crowd-inference-cu121-windows.lock.txt --extra-index-url https://download.pytorch.org/whl/cu121
py -3.10 -m pip install --no-deps -e .
```

These commands target the recorded Windows/CUDA 12.1 environment. The lock was assembled from installed package metadata for the recorded inference environment; it constrains versions but does not verify wheel hashes or prove clean-install success. For other platforms or CUDA versions, select a compatible PyTorch wheel separately, then record the exact installed versions and device in the inference output.

```python
from pathlib import Path
from crowdsight.detection import UltralyticsPersonDetector, load_person_detector_profile

profile = load_person_detector_profile(
    Path("configs/models/crowd_best_local.yaml")
    # or set CROWDSIGHT_CROWD_CHECKPOINT to an approved artifact path
)
detector = UltralyticsPersonDetector(profile)
person_observations = detector.predict(frame_bgr)
```

Sequential tracking uses `load_person_tracker()` with the same pinned model profile plus a tracker YAML whose SHA-256 is also checked. Instantiate a separate tracker for every video session. The profile loader resolves the source tracker path relative to the workspace prototype; when that sibling is unavailable, set `CROWDSIGHT_TRACKER_CONFIG` to an approved tracker YAML.

The proposed per-frame wire example:

```json
{
  "source_id": "camera-or-uav-name",
  "session_id": "unique-run-id",
  "model_profile_id": "crowd_best_local_v2",
  "model_profile_sha256": "<64-character model profile SHA-256>",
  "checkpoint_sha256": "12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc",
  "tracker_config_sha256": null,
  "frame_index": 123,
  "media_time_s": 4.1,
  "captured_at": null,
  "image_width": 1920,
  "image_height": 1080,
  "observation_valid": true,
  "quality": "VALID",
  "fully_observed_zones": ["main-plaza"],
  "registration_valid": false,
  "confidence_semantics": "RAW_MODEL_SCORE",
  "detections": [
    {
      "track_id": null,
      "x": 0.51,
      "y": 0.72,
      "confidence": 0.87
    }
  ]
}
```

Coordinates are normalized to `[0,1]`; `x,y` are the bottom-centre ground-contact approximation. Detector-only `track_id` is null. Tracking IDs are run-local and temporary. Replay `captured_at` is null; `media_time_s` must not be converted to capture UTC. Confidence is a raw model score unless calibration has been evaluated; it is not a correctness probability.

Contract v1 serializes `confidence_semantics: RAW_MODEL_SCORE` only. The inference archive preserves each raw detection score for evaluation, and `scripts/evaluate_confidence_calibration.py` measures Brier score, negative log-likelihood, and equal-width ECE against reviewed boxes by IoU matching. These diagnostics are conditional on emitted detections, do not fit a calibrator, and do not turn the raw score into a probability. A calibrated-probability output requires a reviewed contract revision, a versioned calibrator trained on a separate calibration partition, and independent test evidence (reliability diagram, Brier score, negative log-likelihood, declared-bin ECE, sample counts, and condition-stratified results) plus site-owner approval. Until those gates pass, consumers must display the value as a raw score or omit it.

### Contract decision required: boxes for annotated replay

The original product handoff schema contains only the anchor and score, but the MVP also requires annotated video. The adapter keeps `bbox_xyxy_px` internally for rendering; it is not serialized by `to_contract_dict()`. The application owners must choose one of the following before implementation:

1. Add `bbox_xyxy` in original-image pixel coordinates to the shared detection object (recommended for replay overlay; dimensions are already included); or
2. Keep boxes inside the video-processing worker and transmit anchors/counts only.

Avoid silently extending a frozen API schema.

## Quality and metric-density behavior

`QualityState` values are `VALID`, `PARTIAL`, `UNKNOWN`, and `STALE`. `UNKNOWN` and `STALE` frames must not carry detections. Inference exceptions or corrupt frames should be recorded as failed/unknown frame observations or a failed job according to the video-service recovery policy; they must never become zero occupancy. `STALE` is mainly relevant to future live ingestion and should not be applied to historical replay solely because the media timestamp is old.

`fully_observed_zones` carries the zone IDs that have complete usable coverage in this frame. For `PARTIAL`, only those listed zones may produce counts; every configured but unlisted zone is unavailable, not zero. For `VALID`, list all configured zones covered by the frame. For `UNKNOWN` or `STALE`, this list and `detections` must both be empty. `observation_valid` remains true for `PARTIAL` for compatibility with the current backend, which must use `fully_observed_zones` to avoid treating uncovered zones as valid. The list must be built where frame coverage and configured zone geometry are both available; the detector adapter alone cannot infer it.

The `assess_density_validity()` gate in `src/crowdsight/geospatial/validity.py` returns density only when the observation is valid, coverage is complete, registration is valid, calibration ID and measured usable area exist, and an independent held-out calibration residual passes an explicitly site-approved maximum. Passing also requires references and SHA-256 hashes for the calibration evidence, the independence review, and the site-policy approval, plus explicit independence-verification and site-approval flags. The gate checks that references are present and hashes are well formed; its caller must verify the referenced artifact contents and approval before setting those flags. Missing evidence or a non-finite/underflowing density calculation produces a named unavailable status. No universal residual threshold is embedded. The input may be an integer detection count or a continuous density-model estimate; the output remains an estimate and must not be displayed as an exact headcount.

Image-space heat maps remain valid as frame-relative visualizations even when geographic registration is unavailable, provided the frame observation itself is valid. They must be labeled `IMAGE_SPACE` and must not be called people/m².

## Parking occupancy boundary

The parking model is pending training. Its separate types/protocol and adapter guards are in `src/crowdsight/common/parking.py` and `src/crowdsight/parking/adapter.py`. After the training owner finalizes the YAML template, call `load_parking_model_profile()` with the YAML and a trusted artifact path or configured checkpoint environment variable. It computes the profile-file SHA-256 from the exact YAML bytes. The model-loading boundary must then call `verify_parking_checkpoint(profile)` before loading external weights; it checks the checkpoint SHA-256 against the versioned profile. Call `validate_parking_predictions()` with the configured profile, the model adapter's reported `profile_id`, requested site and camera-view IDs, layout version, configured stall IDs, frame media time, frame quality, and model results. The guard checks model/profile, site, camera-view, and layout identity; exact one-result-per-space coverage in configured order; each result's evidence time against frame media time; and UNKNOWN-only space states for UNKNOWN or STALE frames. It does not claim confidence calibration or occupancy accuracy. Proposed object:

```json
{
  "site_id": "site-01",
  "camera_view_id": "view-east-v1",
  "space_layout_version": "lot-layout-v3",
  "source_id": "parking-camera-01",
  "session_id": "run-id",
  "frame_index": 420,
  "media_time_s": 14.0,
  "captured_at": null,
  "model_profile_id": "parking_occupancy_site_v1",
  "model_profile_sha256": "<64-character model profile SHA-256>",
  "checkpoint_sha256": "<64-character model checkpoint SHA-256>",
  "confidence_semantics": "RAW_MODEL_SCORE",
  "quality": "VALID",
  "spaces": [
    {
      "space_id": "A-017",
      "state": "OCCUPIED",
      "confidence": 0.94,
      "evidence_time_s": 14.0
    }
  ]
}
```

`space_layout_version` binds each `space_id` to the exact site geometry revision. A blocked, off-frame, stale, invalid, or unsupported space is `UNKNOWN`, never implicitly `AVAILABLE`. The proposed model output is advisory. The adapter contains no API for gates, barriers, reservations, or routing.

## Questions to resolve jointly

- Which model profile will the first demo use: `best_local` (pilot lineage recovered; target-site validation and use-rights review pending) or E01 (authorized checkpoint not installed)?
- Does the backend need box coordinates for annotated replay, and in which units?
- Which video/site and zone-layout version will be used for the held-out evaluation?
- Who owns upload retention and how will footage be deleted after a run?
- For parking v1, can the product/camera owner confirm a stable fixed view for the proposed per-space classifier and name the camera/site? If not, revise the model task and contract before training. Which approved source will provide training, calibration, and locked test data?
- Is parking availability advisory-only for the foreseeable milestone? Active physical control requires a separate approved system design.

## Integration rule

Backend and frontend can build against the documented JSON fixtures before a model checkpoint is installed. Profile IDs, model/checkpoint hashes, quality state, source/session/frame, and media time must survive from inference through result export.
