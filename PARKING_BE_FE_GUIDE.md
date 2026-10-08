# Parking integration guide — backend and frontend

Branch: `parking-update`. This branch provides a Python inference adapter,
CLI runners, and a proposed JSON contract. HTTP endpoints, job scheduling,
video upload/storage, and a frontend application still need implementation.

## 1. What the model does

For each **configured parking stall**, classify `OCCUPIED`, `AVAILABLE`, or
`UNKNOWN`. It does not discover stalls, detect arbitrary car boxes, or track
vehicles. A reviewed layout is required for each camera view. Registration and
per-frame stall visibility are supplied by the caller, not inferred by the model.

Selected experimental model: **Model C / ViT-B16**, raw-score threshold **0.99**.
The sampled pipeline result was 83.33% against AI-reviewed labels, including
abstentions as errors. Human review is incomplete (54/108 labels submitted).
This is exploratory evidence, not general accuracy or a real-time guarantee.

## 2. Backend: obtain the runtime artifacts

Request these files from the AI/ML owner and store them outside the repository:

| Artifact | Purpose |
|---|---|
| `checkpoint-modelC.pt` | Trained model weights; not included in Git |
| `runtime-profile.yaml` | Model architecture, hashes, threshold, camera identity |
| `layout.json` | Image dimensions, stall IDs, and integer-pixel polygons |

Model C checkpoint SHA-256:

```text
06d7b96351868f9d7a712b0851af0bb01b7c292847eff9e68375c18cbbd0ccbf
```

Current owner-local checkpoint:
`HANDOFF-20261004/T2-parking-data/modelC/checkpoint-modelC.pt`.
The existing rainy-camera profile/layout pair is in
`private-artifacts/parking-external-20261008/evaluation-round2/modelC/virat-0502/`.
These are local artifact locations, not downloadable URLs or files in the branch.
That layout applies only to its original video/view.

The checked-in `configs/models/parking_occupancy_template.yaml` is a planning
template, **not a runnable crop-model profile**. Obtain a complete profile from
the AI/ML owner. Its `runtime` must specify:

```yaml
adapter_version: parking_crop_v1
architecture: vit_b16
preprocessing: pklot_bbox_area64_jpeg95_rgb_v1
classes: {'0': AVAILABLE, '1': OCCUPIED}
layout_sha256: <SHA-256 of the exact layout.json bytes>
decision_threshold: 0.99
abstention_margin: 0.0
precision: float32
coverage_source: caller_per_frame
```

This block is the nested `runtime` section, not a complete profile. Top-level
profile fields include `profile_id`, `task`, `model_family`, `checkpoint_sha256`,
`site_id`, `camera_view_id`, and `space_layout_version`. Preserve the verified
profile/layout pair. Hash or identity mismatches raise errors.

## 3. Backend: install and run

From the repository root, use Python 3.10+ and a compatible PyTorch/torchvision
environment. The observed Windows CPU versions are recorded in
`requirements/parking-inference-cpu-windows.txt`; this is not a clean-install-
verified lock. CPU PyTorch wheels may require the PyTorch CPU package index.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements/parking-inference-cpu-windows.txt --extra-index-url https://download.pytorch.org/whl/cpu
python -m pip install -e .
```

If the recorded wheels are unavailable for your platform/Python version, obtain
a compatible runtime from the AI/ML owner and validate it before deployment.

### Python worker integration

Load one model per worker, then reuse it for frames. Example below uses the
existing rainy-camera artifacts and identities; replace all three identity
fields together with a reviewed profile/layout for another view.

```python
from pathlib import Path
import cv2
from crowdsight.parking import ParkingCropClassifier

artifacts = Path('../parking-artifacts')
model = ParkingCropClassifier(
    artifacts / 'runtime-profile.yaml',
    checkpoint_path=artifacts / 'checkpoint-modelC.pt',
    layout_path=artifacts / 'layout.json',
    device='cpu',
    batch_size=16,
)

def infer_frame(frame_bgr, frame_index, media_time_s,
                reviewed_visible_ids, alignment_is_valid):
    observation = model.observe(
        frame_bgr,
        site_id='virat-0502',
        camera_view_id='virat-0502-fixed-v1',
        space_layout_version='virat-0502-review-v1',
        source_id='uploaded-video-001',
        session_id='job-001',
        frame_index=frame_index,
        media_time_s=media_time_s,
        visible_space_ids=reviewed_visible_ids,
        registration_valid=alignment_is_valid,
        stale=False,
    )
    return observation.to_contract_dict()

# frame_bgr = cv2.imread(...) or a decoded OpenCV video frame.
# It must be uint8 BGR with exactly the layout's width and height.
```

Resize/align input into the reviewed layout coordinate system before inference.
Do not stretch an unrelated camera image into an existing layout. Crops use the
axis-aligned bounds of layout polygons, not polygon masking. Let the adapter
handle crop resizing, JPEG preprocessing, RGB conversion and normalization.

Missing visibility defaults to no visible stalls; missing registration defaults
to invalid. Both yield UNKNOWN. Blocked or unsupported stalls should be omitted
from `visible_space_ids`. Invalid pixels/resolution also yield UNKNOWN; profile,
checkpoint and identity errors fail the job. Return an error/unavailable state
instead of converting exceptions into zero occupancy.

### CLI option for decoded image frames

Create a manifest outside Git. Replace example hashes/identities with actual
values; image paths are relative to the manifest file:

```json
{
  "source_id": "uploaded-video-001",
  "session_id": "job-001",
  "site_id": "virat-0502",
  "camera_view_id": "virat-0502-fixed-v1",
  "space_layout_version": "virat-0502-review-v1",
  "frames": [{
    "path": "frames/frame-000000.png",
    "sha256": "REPLACE_WITH_IMAGE_FILE_SHA256",
    "frame_index": 0,
    "media_time_s": 0.0,
    "visible_space_ids": ["S01", "S02"],
    "registration_valid": true,
    "stale": false
  }]
}
```

Declare registration/visibility only after checking that frame. Example command:

```powershell
python scripts/run_parking_inference.py --profile ../parking-artifacts/runtime-profile.yaml --checkpoint ../parking-artifacts/checkpoint-modelC.pt --layout ../parking-artifacts/layout.json --manifest ../parking-artifacts/manifest.json --output ../parking-results/run-001
```

Output must be a **new directory outside the repository**. It contains
`observations.jsonl` (one observation per input frame) and `run.json` (completion,
hashes, runtime and timing). A partial JSONL without a completed run report is
not a completed job. This CLI reads images; video decoding/sampling belongs to
the worker. `render_external_parking_video.py` is a diagnostic replay tool.

## 4. Backend → frontend contract

Use `contracts/v1/parking-frame-observation.schema.json` as the proposed payload
schema. Full synthetic examples are in `contracts/v1/fixtures/`:

- `parking-frame-observation.valid.json`
- `parking-frame-observation.partial.json`
- `parking-frame-observation.unknown.json`

The adapter emits site/view/layout identity, source/session identity, frame index,
media time, nullable `captured_at`, model/profile hashes, `quality`,
`confidence_semantics: RAW_MODEL_SCORE`, and:

```json
{
  "spaces": [
    {"space_id": "S01", "state": "OCCUPIED", "confidence": 0.995, "evidence_time_s": 3.0},
    {"space_id": "S02", "state": "UNKNOWN", "confidence": null, "evidence_time_s": 3.0}
  ]
}
```

This is an illustrative fragment, not a complete schema-valid observation.
`media_time_s` is time within the source video, not wall-clock time. The adapter
currently emits `captured_at: null`. Confidence is an uncalibrated score for the
emitted class, not a probability that the classification is correct.

Suggested application flow (to implement, not existing endpoints):

1. Backend creates a video job, stores media and selects the matching artifacts.
2. A Python worker decodes frames, determines alignment/visibility and emits JSON.
3. Backend validates and stores observations, then serves them through polling,
   SSE or WebSocket. Keep job progress/errors in a separate envelope; the
   observation schema forbids extra fields.
4. Serve the matching layout separately so FE can map `space_id` to polygons.

Agree transport and job-envelope details with BE/FE owners. Keep torch/OpenCV in
the inference worker; FE consumes JSON and geometry only. Model initialization
is expensive, so avoid loading weights per HTTP request. CPU runs are offline
diagnostics; queue work instead of assuming live response times.

## 5. Frontend rendering

| Value | Display |
|---|---|
| `OCCUPIED` | Red + occupied text/icon |
| `AVAILABLE` | Green + available text/icon |
| `UNKNOWN` | Gray + unavailable/unknown text/icon |
| Quality `VALID` | Every configured stall has a known state |
| Quality `PARTIAL` | Known states plus unknown stalls; show partial-coverage badge |
| Quality `UNKNOWN` | No usable stall result; show unavailable |
| Quality `STALE` | Evidence is stale; all returned stalls are UNKNOWN |

Count known states directly; unknown is a separate count, not an available stall:

```javascript
const counts = observation.spaces.reduce((sum, space) => {
  sum[space.state] += 1;
  return sum;
}, { OCCUPIED: 0, AVAILABLE: 0, UNKNOWN: 0 });
const coverage = (counts.OCCUPIED + counts.AVAILABLE) / observation.spaces.length;
```

Label counts as **configured stalls**; selected regions may not cover the whole
lot. For UNKNOWN/STALE frames, display “availability unavailable” prominently
rather than a misleading “0 cars” summary. For PARTIAL frames, show both known
counts and unknown count/coverage. Do not re-threshold `confidence` in FE.

Match overlays by `space_id` and `space_layout_version`. Scale polygon coordinates
from layout dimensions into the rendered video's actual content rectangle,
including letterbox offsets. Reject results for a different source/session or
layout, and handle out-of-order frames. On video seek, select observations by
media time rather than blindly keeping the latest network response.

If showing cached predictions between inference updates, visibly mark them as
cached and display evidence age. Do not modify evidence timestamps to make old
results appear fresh. The backend defines a freshness policy; a disconnected
stream or expired result must not remain visually “available.”

## 6. Integration checklist

- BE obtains verified weights and a camera-specific profile/layout pair.
- BE runs the adapter/CLI and validates payloads against the proposed schema.
- FE develops against the checked-in synthetic fixtures before connecting jobs.
- BE/FE agree transport, error envelope, freshness, layout delivery and IDs.
- Jointly review unknown, partial, failed-job, stale and video-seek behavior.
- Keep accuracy claims provisional until the human-reviewed evaluation is complete.

This guide documents the existing code boundary; it does not claim an HTTP
service, UI integration, clean installation or end-to-end product test has run.
