# Roboflow dataset candidates

Checked 2026-09-25. These are candidate image datasets for exploratory training or evaluation planning. No data has been downloaded, labels have not been inspected image by image, and no candidate is approved as independent test data. Roboflow Universe datasets are image/annotation packages, not source videos; they cannot replace a fixed-camera video clip for temporal evaluation or a demo.

## Recommended first review: BridgeGuard3

- Project: [BridgeGuard3 on Roboflow Universe](https://universe.roboflow.com/iax-my/bridgeguard3)
- Published metadata: 11,621 images, 1 dataset version, classes `person`, `motorcycle`, and `mobility_device`; project declares CC BY 4.0.
- Publisher description says it targets overhead CCTV views typical of urban bridges in Malaysia, and that it aggregates public surveillance-style imagery and video-derived frames as a base dataset intended for later site-specific fine-tuning.
- Possible use: candidate source for warm-starting person/motorcycle detection and visually reviewing overhead CCTV conditions. It is a closer camera/class match than general street or aerial-drone datasets.
- Limits: bridge surveillance is not parking-stall occupancy; labels do not provide stall polygons, stall states, customer counts, or arrival/wait-time labels. Malaysia is not Vietnam. The page does not establish source-level permissions for every underlying image, source grouping for splits, video IDs, or whether frames from the same recording cross partitions. Do not use its default version split as independent test evidence unless those points are audited.
- Decision: inspect source attribution, version details, representative images, exact split, and download size before any download. If approved, use only for exploratory training; collect a separate Vietnam parking-camera test set.

## Crowd-specific candidate: OverHead Detection

- Project: [OverHead Detection on Roboflow Universe](https://universe.roboflow.com/abhayfinal/overhead-detection)
- Published metadata: 6,607 images across 2 versions; classes `head`, `people`, `person`, and `head-top-view`; project declares CC BY 4.0.
- Possible use: candidate overhead person/head detector pretraining or label-policy review.
- Limits: the project has no published dataset description. It mixes head and person-like classes, and the page does not provide underlying source identities or source-separated split evidence. It does not describe Vietnam traffic or parking. Do not use as held-out evaluation and do not merge its classes into the CrowdSight person class without manual label mapping and sample review.
- Decision: lower priority than BridgeGuard3 until source and image composition are reviewed.

## Vietnam motorbike domain candidate: CCTV Vietnam

- Project: [CCTV Vietnam on Roboflow Universe](https://universe.roboflow.com/vehicle-qmmot/cctv-vietnam)
- Published metadata: 391 images, one version, classes `car`, `truck`, `bus`, and `motorcycle`; project declares CC BY 4.0.
- Possible use: inspect for Vietnam-style motorbike appearance and camera conditions; if source and annotation quality are confirmed, it may be a small domain-adaptation/training candidate for vehicle detection.
- Limits: the project has no published dataset description and no `person`, stall, or occupancy labels. It cannot evaluate crowd counts, parking-space states, or waiting time. The page does not establish source recording identities, split independence, or the origins/rights of the underlying images.
- Decision: image review and source metadata audit required; exploratory training only unless independent source-level evidence is obtained.

## Traffic detector candidate: Traffic Density Prediction

- Project: [Traffic Density Prediction on Roboflow Universe](https://universe.roboflow.com/prediction-of-traffic-situations-using-realtime-traffic-density-estimation/traffic-density-prediction)
- Published metadata: 9,087 images across 7 versions; classes include `motorcycle`, `pedestrian`, `bicycle`, `car`/`vehicle`, `truck`, `bus`-adjacent tricycle types; project declares CC BY 4.0.
- Possible use: a larger exploratory source for motorbike/person detector adaptation and traffic-scene review.
- Limits: no published dataset description or visible source-level recording/split provenance in the summary metadata. It is a traffic dataset, not a stall occupancy or queue-duration dataset. It cannot support waiting-time or temporal tracking evaluation without the original ordered videos and timestamps.
- Decision: inspect selected version, examples, source/video identities, and split lineage before use; training-only unless provenance is independently established.

## Parking motorbike detection candidate: Parking Lot Occupany

- Project: [Parking Lot Occupany on Roboflow Universe](https://universe.roboflow.com/mohamed-traore-w4h8y/parking-lot-occupany)
- Published metadata: 350 project images across 3 versions; classes `vehicle` and `moped or motorcycle`; project declares CC BY 4.0. The page says it combines annotated images forked from several public Roboflow projects and includes images from YouTube videos. The hosted model references a version with 842 images, so version counts differ and must be resolved before selecting a package.
- Possible use: the closest candidate found so far for exploratory parking-area motorbike/vehicle detection.
- Limits: it does not label individual parking stalls or occupied/free state. The underlying YouTube source list, recording identities, camera angle, source rights, and source-separated split lineage are not established by the page summary. A declared project license does not by itself settle rights in every upstream source.
- Decision: inspect version pages and image examples; verify source attribution and permission before download or model use. Do not treat the default split as held-out evidence.

## Parking-area motorbike detection discovery candidate: Parking Lot Occupany 2

- Project: [Parking Lot Occupany 2 on Roboflow Universe](https://universe.roboflow.com/homework-bngpb/parking-lot-occupany-2)
- Published metadata: 2,444 images, one version, classes `car` and `motorcycle`; project declares CC BY 4.0.
- Possible use: candidate for exploratory motorbike appearance review in parking contexts.
- Limits: source dataset is attributed to a homework workspace with little project description; no stall-state labels, source provenance, camera consistency, or split independence is established in the metadata reviewed.
- Decision: review samples and provenance before use; lower confidence than a documented, site-specific collection.

## Parking occupancy candidate: IAX MY Carpark Occupancy v3

- Project/version: [IAX MY Carpark Occupancy v3](https://universe.roboflow.com/iax-my/carpark-occupancy-5j5aj/dataset/3)
- Search-index metadata suggests 1,437 images after augmentation, with a 1,260/118/59 train/valid/test split and possible classes including car, empty, occupied, motorcycle, and bus. The version page was rate-limited during this check, so exact labels, license, camera source, split construction, and package size remain unverified.
- Possible use: only a candidate for parking model exploration if the exact version page and image samples confirm fixed-camera stall-level labels and motorcycle relevance.
- Limits: split independence is unknown; augmentation can create leakage if derived examples are distributed across partitions. Any Roboflow split must be audited against source image/video identity. No claim of Vietnam-domain performance is supported.
- Decision: do not download until the exact version metadata and license can be verified.

## Potential parking layout reference: Parking Space Detection - Occupancy v1

- Version: [Capstone Project parking occupancy v1](https://universe.roboflow.com/capstone-project-vb3su/parking-space-detection-occupancy/dataset/1)
- Published metadata: 217 images, CC BY 4.0, all 217 assigned to test, with no train or validation images; no augmentations listed.
- Possible use: inspect annotation vocabulary and stall-state representation after visual review.
- Limits: a test-only version cannot train a model. The page does not establish motorbike coverage, source grouping, site/camera match, or that 217 images represent 217 independent scenes. Its all-test split is not automatically independent evidence.
- Decision: reference only unless another suitable version or source is verified.

## Data intake gates before download or model use

1. Confirm project approval for the specific dataset/version and intended use. Record the source URL, access date, declared license, attribution text, version ID, and SHA-256 for the downloaded archive and extracted manifest.
2. Review representative images and labels; identify class mapping, camera angle, source videos/cameras/dates, and whether the target motorbike/parking conditions appear.
3. Inspect source-level provenance and partition IDs. Keep all frames and derived augmentations from one original source in one partition. If source identities are unavailable, classify the dataset as training-only exploratory material and never as held-out evidence.
4. Record any rehosting, annotation, attribution, and redistribution limits. Keep image files, annotations, and model weights outside Git in approved artifact storage with access controls.
5. For actual time-based crowd or waiting-time validation, obtain permissioned fixed-camera footage and annotate locked timestamps. Still-image datasets cannot validate temporal tracking, queue duration, or waiting-time estimates.

## Source pages

- [BridgeGuard3](https://universe.roboflow.com/iax-my/bridgeguard3)
- [OverHead Detection](https://universe.roboflow.com/abhayfinal/overhead-detection)
- [CCTV Vietnam](https://universe.roboflow.com/vehicle-qmmot/cctv-vietnam)
- [Traffic Density Prediction](https://universe.roboflow.com/prediction-of-traffic-situations-using-realtime-traffic-density-estimation/traffic-density-prediction)
- [Parking Lot Occupany](https://universe.roboflow.com/mohamed-traore-w4h8y/parking-lot-occupany)
- [Parking Lot Occupany 2](https://universe.roboflow.com/homework-bngpb/parking-lot-occupany-2)
- [IAX MY Carpark Occupancy v3](https://universe.roboflow.com/iax-my/carpark-occupancy-5j5aj/dataset/3)
- [Parking Space Detection - Occupancy v1](https://universe.roboflow.com/capstone-project-vb3su/parking-space-detection-occupancy/dataset/1)
