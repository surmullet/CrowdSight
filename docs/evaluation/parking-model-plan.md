# Parking occupancy model plan

## Objective

Prepare a separate AI model for parking-space occupancy. The first product behavior is advisory: per-space and per-area occupancy for staff or an information display. Gate/barrier actuation, reservations, and vehicle routing are excluded until a separately approved integration and safety design exists.

## Recommended v1 task: per-space classification

Classify each configured stall as `OCCUPIED`, `AVAILABLE`, or `UNKNOWN` using a fixed camera view and immutable space-layout version. This is the current v1 contract: the profile template declares `parking_space_occupancy_classification`, and `ParkingOccupancyModel.classify_spaces()` accepts the configured layout and space IDs and returns one result per space. The camera/site owner must confirm that the view is stable and space polygons can be maintained before data collection begins.

If the intended camera moves or fixed stall crops are not supportable, pause training and make a joint product/AI-ML decision to use vehicle detection plus stall association. That alternative needs a revised profile task, input/geometry contract, adapter implementation, label guide, and evaluation plan; do not train a detector and pass it through the current classifier contract. For either formulation, define treatment of motorcycles, oversized vehicles, partial occupancy, loading areas, invalid/occluded stalls, and spaces outside the camera view.

The target unit is a configured parking space, not a person/vehicle identity. Do not retain identity or re-identification features.

### Vietnam motorbike parking label policy

The pilot should reflect Vietnamese parking patterns, including scooters and motorbikes parked tightly, at varied angles, and sometimes several within one marked bay. Keep the v1 output as a stall state rather than a count of individual vehicles:

- Mark a stall `OCCUPIED` when the site-approved assignment rule assigns at least one parked motorbike, scooter, bicycle, car, or other supported vehicle to it. Several motorbikes assigned to one stall still produce one `OCCUPIED` result.
- Mark a stall `AVAILABLE` only when the whole usable stall is visibly clear under the approved site rule.
- Mark `UNKNOWN` when the camera cannot determine the state reliably, including heavy occlusion, a vehicle straddling two stalls without an approved allocation rule, a vehicle stopped across a stall, camera obstruction/shift, or an ambiguous stall boundary.
- Record the visible vehicle type as an annotation attribute for analysis (`motorbike`, `bicycle`, `car`, `other`, `uncertain`), not as a public model output or identity feature. Do not infer rider identity or read/retain license plates.
- Have a site representative approve how shared motorcycle bays are drawn and how tightly parked or boundary-crossing bikes are assigned before annotation starts. Use that same rule for training, validation, and test labels.

The supplied parking reference is a rendered/top-down stall illustration, useful for discussing layout and bay assignment. It is not real camera footage and must not be counted as training or evaluation evidence. Use a stable fixed camera with an approved, versioned bay layout for any site-specific parking model. Vietnam street-traffic footage can support a separate motorbike detector demo, but it cannot validate parking-space occupancy.

## Data plan

For each image or video dataset version, complete the [parking training data record](parking-training-data-record-template.md) in private artifact storage. It captures source-group IDs, image and annotation hashes, augmentation ancestry, partition assignment, rights, and whether labels actually represent stall states. Keep generated image variants in the same source partition; generate augmentations only after the source split is fixed.

- Inventory camera resolution, mounting angle, lens, frame rate, night illumination, weather exposure, compression, network/storage limits, and camera movement.
- Confirm the fixed-view assumption and approve the exact camera-view ID and space-layout version before collecting classifier crops.
- Create a site-approved label guide and annotate space geometry/version plus per-space state and observation quality.
- Capture permitted Vietnam-relevant data across dates and operating conditions: empty and full lots, day/dusk/night, shadows, rain or glare when applicable, cars, bicycles, scooters/motorbikes, mixed vehicle types, tightly packed/shared motorcycle bays, different parking angles, occlusion, parked/moving vehicles, and partial camera obstruction.
- Split by date/site/camera, not adjacent frames. Lock a held-out test set before threshold/model selection. Record source permissions, annotator policy, dataset version, and hashes.
- Ensure rare but important states have adequate examples; report class imbalance and unknown/abstention behavior.

## Output contract (proposal; application owners must approve)

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

`space_layout_version` binds each `space_id` to an immutable site geometry version; `space_id` is a configuration key, not a vehicle identity. Quality is defined consistently at frame and stall level: `VALID` requires every configured stall to be `OCCUPIED` or `AVAILABLE`; `PARTIAL` requires at least one known stall and at least one `UNKNOWN`; `UNKNOWN` and `STALE` require every configured stall to be `UNKNOWN` with null confidence. Return `UNKNOWN` for blocked, off-frame, stale, invalid, or unsupported stalls; never infer `AVAILABLE` from missing detections alone. For replay, `captured_at` remains null. The backend should aggregate only known states and show coverage and unknown-space counts.

## Evaluation

Use the machine-readable input format and scorer in [parking-evaluation-format.md](parking-evaluation-format.md) to calculate reproducible frame/space metrics once the separate model and reviewed data exist. The scorer deliberately labels results exploratory unless test selection and complete training-source evidence establish independence.

Report per-space precision, recall, F1 and a three-state confusion matrix; site-level occupied/available count MAE, signed bias and percentage error; unknown/abstention rate and observed-space coverage; results by day/night, weather, shadow/glare, vehicle type/size, occlusion and camera shift; performance on locked unseen dates/sites/cameras where available; throughput on named hardware and response to stale/dropped frames. Publish score thresholds and calibration evidence if confidence is displayed as probability.

Compare decisions against manual labels collected independently of model output. Alert/availability thresholds require site-owner approval. Metrics remain descriptive until approved acceptance thresholds exist.

## Release requirements

- Completed model card, label mapping, dataset provenance/license, data split manifest, training configuration, framework versions, checkpoint checksum, and artifact retrieval process.
- Versioned site/space geometry and camera-view metadata.
- Held-out evaluation report and known failure conditions.
- Human override/manual correction path and clear stale/unknown behavior.
- Advisory-only output. Any active physical control requires a separate product decision, hardware contract, authorization, manual override, fail-safe behavior, and field validation.

The current YAML profile is a template, not a loadable trained profile. After task definition and training, set its status to `trained_candidate` and fill its model family, checkpoint SHA-256, site, camera-view, and space-layout fields; `release_approval` must remain false during evaluation. Only after all release gates and human reviews pass may the profile move to `release_approved` with `release_approval: true`. The loader checks that status and flag agree, but does not verify the approval evidence itself. It computes `profile_sha256` from the exact YAML bytes at load time; do not place a self-referential profile hash in the YAML. Point `CROWDSIGHT_PARKING_CHECKPOINT` to the approved external artifact, load it with `load_parking_model_profile()`, verify it with `verify_parking_checkpoint()`, then pass outputs through `validate_parking_predictions()` before creating a shared frame observation.
