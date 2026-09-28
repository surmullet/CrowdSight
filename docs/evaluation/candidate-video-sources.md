# Crowd video sources for evaluation

These sources are candidates or exploratory diagnostics, not target-site acceptance results. Keep media, labels, and predictions outside Git. Lock source videos and selected frames before inference, record permissions and hashes, and separate human-reviewed labels from model-assisted proposals.

## Existing Mixkit overhead clip

The [Busy intersection aerial view](https://mixkit.co/free-stock-video/busy-intersection-aerial-view-60/) is a nearly fixed overhead drone clip. A locked 30-frame [manifest](manifests/mixkit-busy-intersection-test-v1.manifest.json) and [permission review](mixkit-busy-intersection-permission-review.md) exist for private, noncommercial internal evaluation and annotation. The clip is sparse; visible pedestrians are small. The private SAM 3.1 assistance run produced zero person proposals and no reviewed ground truth. It cannot currently support count accuracy or dense-crowd claims. Model-source independence is unverified.

## Dense pedestrian diagnostic

The official [MOT20 benchmark](https://motchallenge.net/data/MOT20/) supplied publisher annotations for a locked 134-frame MOT20-05 exploratory run. The [diagnostic report](../models/crowd-best-local-mot20-diagnostic.md) records precision 0.6702, recall 0.3155, count MAE 103.18, and bias -103.18. This is a training sequence, not the benchmark test set. Current archive rights and complete checkpoint independence remain unverified; keep the data private and do not call the result held out.

## Fixed-camera research leads

- [SAIVT-QUT Crowd Counting](https://researchdatafinder.qut.edu.au/individual/n1251) provides three fixed-camera campus sequences, sparsely annotated person locations, ROI masks, and calibration. The publisher lists CC BY-SA 3.0 Australia and free download. The full archive passed local integrity checks, and all 153 annotated frames were locked and evaluated privately with the pinned model. The diagnostic shows substantial undercount and remains exploratory. QUT is in Australia, not Vietnam, and point annotations support count error rather than box IoU. Source media, labels, predictions, and the numeric report remain outside Git.
- The [Crosswalk dataset](https://github.com/Nanasaki-Ai/Crosswalk) describes fixed overhead Bangkok footage. Its GitHub educational/noncommercial statement and Figshare CC BY declaration need reconciliation before transfer. Its published event labels are not complete frame-level person boxes, so independent crowd labels would be required.
- The [Da Nang CCTV dataset paper](https://www.techscience.com/cmc/v88n1/67301/html) describes continuous fixed-view Vietnam recordings with pedestrian annotations and a video-level split. Dataset access is controlled and available on reasonable request for noncommercial research; article CC BY terms do not automatically license the underlying images. The [access brief](da-nang-cctv-access-request.md) records permission, source, partition, and label questions for an authorized request.

The selected `best.pt` model has documented Plaza/VisDrone fine-tuning sources but incomplete upstream source ancestry. An external dataset is therefore exploratory until source-level independence from all training and pretraining material is reviewed. No candidate above establishes target-site fixed-camera performance.
