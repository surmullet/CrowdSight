# Candidate video sources for exploratory evaluation

These are candidate sources only. No video has been downloaded, annotated, or admitted to an evaluation split. Inspect the actual clip, capture source metadata and SHA-256, and record a data-permission decision before creating labels or running model predictions. Keep downloaded media and frame exports outside Git.

## General crowd-density candidate

- **Clip:** [Aerial view of a large crowd of people walking in the park](https://www.pexels.com/video/aerial-view-of-a-large-crowd-of-people-walking-in-the-park-19201625/)
- **Pexels metadata:** 3840×2160, 16:9, 23 seconds, 23.98 fps; page description says overhead city-park view.
- **Use:** Potential external exploratory crowd/person-count diagnostic after visual inspection. It is not Vietnam traffic footage and cannot validate motorbike detection or parking occupancy.

## Vietnam motorbike traffic candidates

- **Clip:** [Vehicles in a Busy Intersection](https://www.pexels.com/video/vehicles-in-a-busy-intersection-5036725/)
- **Pexels metadata:** 1920×1080, 16:9, 11 seconds. The page includes a time-lapse tag.
- **Visual inspection:** The preview shows a low oblique street-level view beneath an overpass, with motorbikes passing through the intersection and no marked parking bays. The view does not match the fixed overhead parking reference and is unsuitable for stall-occupancy evaluation. It may support only a short qualitative Vietnam traffic demo; do not use it as target parking or crowd-density evidence.
- **Alternative:** [Busy Vietnamese City Traffic with Motorbikes](https://www.pexels.com/video/busy-vietnamese-city-traffic-with-motorbikes-33383205/)
- **Page metadata:** 3840×2160, 60 seconds, 59.94 fps; page description identifies motorbike traffic in Vietnam. The page does not establish a fixed CCTV angle.
- **Use:** Potential exploratory motorbike/traffic demo only after frame review. Neither candidate is established as fixed-camera parking footage, so neither can validate parking-space occupancy. No public candidate found so far matches the required fixed overhead view of a Vietnam motorbike parking area; request pilot-camera footage and owner permission for the parking workstream.

## License and annotation handling

The [Pexels license](https://www.pexels.com/license/) says its videos are free to use and modify, and lists use on websites, apps, and presentations. It also restricts certain uses involving identifiable people and forbids implying endorsement. Record the license URL and the date the source was checked in the private dataset manifest. This is a practical source check, not a legal opinion or proof of rights in the people depicted.

SAM-generated masks or boxes are **pseudo-labels**. A human reviewer must correct missed, duplicate, merged, or wrong-class instances before metrics are reported. Keep source frames, pseudo-labels, reviewed labels, and predictions separate. Freeze the sampled frame list and split before model predictions. Use a new video as exploratory external evaluation only; do not call it a site-acceptance test or claim Vietnam-domain performance unless its camera and scene match the intended pilot.

## Current access status

The current Python runtime does not have the `sam3`, `segment_anything`, or `ultralytics` packages installed, and no SAM-related credential environment variable is configured. No SAM3 annotation has been run. To proceed, make an authorized SAM3 runtime available in this environment (for example, the official model/API access configured through a local secret store); do not commit credentials or place tokens in this repository. Then visually inspect the selected video, produce candidate annotations, and manually review them before evaluating a model.
