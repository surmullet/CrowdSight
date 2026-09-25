# Candidate video sources for exploratory evaluation

These are source candidates, not approved evaluation splits. The Pexels candidates below have not been downloaded or annotated. One Mixkit clip is already available in a sibling project, but has no reviewed labels and has not been admitted to an evaluation split. Record a data-permission decision before held-out inference; keep downloaded media and frame exports outside Git.

## Existing independent overhead test candidate

- **Clip:** [Busy intersection aerial view](https://mixkit.co/free-stock-video/busy-intersection-aerial-view-60/)
- **Source page:** describes a static drone view over an avenue, parking lots, cars, trees, and pedestrians; lists 1920×1080 Full HD, about 60 seconds, and the Mixkit Stock Video Free License.
- **Local source record:** the downloaded original and source evidence already exist outside this repository in the sibling UAV project at `../uav-crowd-monitoring/artifacts/independent-intersection/`. Source SHA-256: `e9084a41628e578d45f356e1a9ae1bfb6ad182f3786d09ad4f965aab259fe6a1`; 202,527,196 bytes; 1,429 decoded frames; 23.976 fps; 1920×1080; 59.60 seconds. The local sampling contact sheet was created before model inference.
- **Visual/source review:** nearly fixed overhead drone view with sparse pedestrians around sidewalks and crosswalks. Small people and tree occlusion make it useful for a sparse-scene miss/false-positive diagnostic, but it is not a dense-crowd benchmark, Vietnam footage, or fixed CCTV. Parking stalls are not individually labelled, so this is not parking occupancy or waiting-time evidence.
- **Known training relationship:** the sibling source record says the clip was not used in the E01 fine-tuning pilot and was reserved before inference for comparison. Upstream pretraining/source-identity overlap has not been independently audited.
- **Permission status:** the source page states the clip is under Mixkit's Stock Video Free License and permits personal or commercial project use; the license page describes download, copy, modification, distribution, public performance, and broadcast rights, subject to Mixkit User Terms. Record a named data-owner review and the applicable terms/evidence in the private manifest before running the held-out gate or redistributing frames/labels. This source review is not a rights determination.
- **Locked sampling draft:** [manifest](manifests/mixkit-busy-intersection-test-v1.manifest.json) selects 30 frames uniformly at indices 0, 48, …, 1392, before CrowdSight inference. The source's recorded 23.976 fps gives roughly 2.002 seconds between selected frames. A blank [labels template](manifests/mixkit-busy-intersection-test-v1.labels-template.json) is ready for review. The manifest deliberately records permission as pending, so the inference runner must refuse the test run until a named data owner completes the review.
- **Annotation tool:** [crowd-frame-review.html](../../tools/crowd-frame-review.html) is an offline prediction-free reviewer. Serve the CrowdSight directory on loopback (`py -3.10 -m http.server 8765 --directory D:/code/save/intergrated_product/crowdsight`), open `http://127.0.0.1:8765/tools/crowd-frame-review.html`, and load the manifest plus the original sibling video. It verifies SHA-256, size, dimensions, duration, and decoded frame index before showing a frame; it autosaves labels in browser local storage and downloads JSON for private storage. The video is selected locally and is never uploaded by the page.
- **Use:** highest-priority available candidate for external sparse overhead crowd/person evaluation after every selected frame receives complete manual labels and permission evidence is reviewed. Any resulting report must remain exploratory unless the complete training inventory and source-independence evidence are reviewed.

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

## Parking CCTV source leads found through Roboflow

The Roboflow [Parking Lot Occupany project](roboflow-dataset-candidates.md#parking-motorbike-detection-candidate-parking-lot-occupany) lists eight YouTube recordings as sources for its annotated images, including [FAPS H.264 PC-DVR CCTV Parking Lot Overview](https://www.youtube.com/watch?v=Z-ZgqqwEQZ4) and [ClearPix Camera Grocery Parking Lot](https://www.youtube.com/watch?v=KhtwB8faMpU). These are leads for visual review, not approved evaluation clips: source-level use rights, camera stability, motorcycle content, and exact relation between source frames and dataset images require review. They are not identified as Vietnam footage. If the model trains on that Roboflow dataset, any source video whose frames appear in it must be excluded from the held-out test partition.

## License and annotation handling

The [Pexels license](https://www.pexels.com/license/) says its videos are free to use and modify, and lists use on websites, apps, and presentations. It also restricts certain uses involving identifiable people and forbids implying endorsement. Record the license URL and the date the source was checked in the private dataset manifest. This is a practical source check, not a legal opinion or proof of rights in the people depicted.

SAM-generated masks or boxes are **pseudo-labels**. A human reviewer must correct missed, duplicate, merged, or wrong-class instances before metrics are reported. Keep source frames, pseudo-labels, reviewed labels, and predictions separate. Freeze the sampled frame list and split before model predictions. Use a new video as exploratory external evaluation only; do not call it a site-acceptance test or claim Vietnam-domain performance unless its camera and scene match the intended pilot.

## Current access status

The current Python runtime does not have the `sam3`, `segment_anything`, or `ultralytics` packages installed, and no SAM-related credential environment variable is configured. No SAM3 annotation has been run. To proceed, make an authorized SAM3 runtime available in this environment (for example, the official model/API access configured through a local secret store); do not commit credentials or place tokens in this repository. Then visually inspect the selected video, produce candidate annotations, and manually review them before evaluating a model.

The sibling UAV project has a SAM 3.1 inference output for a different Pexels clip, not this intersection source. Its saved output is a model estimate rather than ground truth and cannot be substituted as labels. Its local Python environment also does not contain `sam3`, `torch`, OpenCV, or Ultralytics at this check. The intersection source remains unlabelled; SAM-generated proposals, if produced later, require frame-by-frame human correction.
