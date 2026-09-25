# Parking-model training data record

Complete this record for every training, calibration, validation, and test dataset version used by the separate parking model. Keep completed records, image/annotation inventories, and evidence in approved private artifact storage; commit only this blank template. Do not commit source images, stall labels, credentials, or restricted metadata.

## Dataset identity and rights

- Internal immutable dataset ID/version:
- Source platform and workspace/project/version URL:
- Export date, format, and exporter/tool version:
- Downloaded archive SHA-256 and byte size:
- Extracted annotation/config manifest SHA-256:
- Publisher, dataset title, and declared license:
- Required attribution text and redistribution terms:
- Original image/video source owner(s), URLs, and collection dates where known:
- Allowed uses explicitly reviewed (training / calibration / validation / model evaluation / redistribution):
- Permission evidence reference and SHA-256:
- Reviewer ID, review date, and decision:
- Data custodian, access-control location, retention/deletion date:
- Privacy review, including license-plate/face masking policy:

## Task and label interpretation

- Intended model task: configured-stall classification / vehicle detection / other (explain):
- Does the source dataset actually label configured stall states? yes / no / unknown
- Source class names and exact meanings:
- Mapping to `OCCUPIED`, `AVAILABLE`, or `UNKNOWN` (include reviewed examples):
- Does `empty` mean a labeled empty stall, an empty-region detector box, or something else?
- Supported vehicle types, including scooter/motorbike, bicycle, car, and other:
- Label guide/version and adjudication procedure:
- Site ID, exact fixed `camera_view_id`, and immutable `space_layout_version` if site-specific:
- Geometry/space-ID manifest reference and SHA-256:

Do not map an object-detection class such as `Motorcycle` to per-space occupancy without a reviewed assignment rule and stall-state labels. Do not assume the class name `empty` is a stall state until representative annotations are inspected.

## Image/source inventory and split integrity

Maintain a private machine-readable row for every exported image with at least:

| Field | Required meaning |
|---|---|
| `image_id` | Immutable ID within this dataset version |
| `image_sha256` | Hash of exact exported image bytes |
| `annotation_sha256` | Hash of exact annotation record/file for this image |
| `original_source_group_id` | Video, camera/date, site, burst, or source-photo group; `unknown` if unavailable |
| `original_source_ref` / `original_source_sha256` | Private location and hash of the underlying source when available |
| `derivation` | `original`, `video_frame`, `crop`, or `augmentation` |
| `parent_image_sha256` | Exact parent image for crops/augmentations; null for originals |
| `partition` | Immutable `train`, `calibration`, `validation`, or `test` assignment |

- Image-inventory manifest reference and SHA-256:
- Unique original source-group count:
- Unknown-source-group image count:
- Split assignment date/time and reviewer:
- Test selection locked before predictions/model selection: yes / no:
- Proof that all images, video frames, crops, and augmentations from each original source group stay in one partition:
- Training-source inventory declared complete: yes / no:
- Known duplicate/near-duplicate analysis method and report reference/hash:
- Independence review reference/hash and independent reviewer decision:

Assign source groups to partitions before generating crops or augmentation. Generate augmentations from the training partition only. If original source identities are unavailable, mark the affected data `unknown_or_mixed`, restrict it to exploratory training, and do not claim an independent held-out result from its published split.

## Site-video evidence (required for temporal occupancy claims)

- Permissioned source video ID, private path, SHA-256, size, resolution, FPS, and duration:
- Site/camera/date partition ID and fixed-view verification:
- `camera_view_id`, `space_layout_version`, and stall geometry SHA-256:
- Locked selected frame manifest reference/hash, selected before inference:
- Independent reviewed labels reference/hash and annotation guide version:
- Day/night, weather, glare/shadow, vehicle type/size, occlusion, and camera-shift strata:
- Any repeated events, adjacent frames, alternate encodings, or crops shared with training/calibration data:

Still images and randomly split image exports can support exploratory image classification, but cannot validate temporal stability, stale-frame behavior, tracking, queue duration, or customer waiting-time estimates. For held-out evaluation, test sources must be independently grouped and disjoint from every training and calibration source, with reviewed permission and annotations.

## Training and release linkage

- Training run ID and configuration reference/hash:
- Framework/runtime lock and hardware record:
- Training-data manifest SHA-256:
- Calibration-data manifest SHA-256 (if any):
- Locked test-manifest SHA-256:
- Model profile ID/SHA-256 and checkpoint SHA-256:
- Evaluation report reference/SHA-256:
- Known limitations and unsupported camera/parking conditions:
- Artifact storage and retrieval record:

## Completion checklist

- [ ] Exact dataset version, export, annotation map, archive, and manifests are hash-identified.
- [ ] License, attribution, source permissions, retention, and intended uses are reviewed.
- [ ] The actual label task matches the parking adapter/profile contract.
- [ ] Original-source groups, generated derivatives, and split membership are inventoried.
- [ ] Training/calibration/test partitions are source-disjoint and test selection was locked before inference.
- [ ] Site-specific test data have reviewed stall IDs, geometry version, and temporal labels.
- [ ] Weights, source media, private labels, and generated predictions remain outside Git.
