# Da Nang CCTV dataset access request brief

**Purpose:** request controlled access for a noncommercial, internal research evaluation of the CrowdSight pedestrian detector. This brief is a draft for the project owner to review and send; no request has been sent and no dataset has been accessed.

## Candidate fit and limits

The paper describes 23,364 images extracted from continuous, fixed-view CCTV streams at Da Nang intersections. The images include manually refined pedestrian boxes and are split by source video. This is a useful candidate for evaluating image-level person detection and frame-level person counts in Vietnamese fixed-camera scenes. The paper does not offer a public source-video release in its data statement, so tracking, temporal stability, parking occupancy, and customer waiting time cannot be evaluated unless separate video access is explicitly granted.

The source says access is available for noncommercial research on reasonable request under controlled access. Commercial use requires explicit author permission. The article's CC BY 4.0 license applies to the article and does not itself grant dataset access. Treat the dataset as unavailable until the authors provide written terms.

## Draft request

**Subject:** Request for controlled noncommercial research access to the Da Nang CCTV traffic dataset

Dear Corresponding Author,

CrowdSight is a university/team prototype for camera-based crowd and traffic-scene monitoring. A noncommercial research evaluation of an existing pedestrian detector is being planned. The model would be run only on data supplied under terms approved by the dataset authors. Results would be treated as exploratory until model lineage and source-level independence are reviewed.

Could you please advise whether controlled access can be granted for this specific use and provide the applicable written terms? To scope the evaluation accurately, please also clarify:

1. Which files can be provided: image frames, annotations, source videos, or a subset; and whether image-only use is the only permitted option.
2. The video/camera/source identifiers for each image and the exact train, validation, and test partition mapping, so source-level overlap can be checked.
3. The pedestrian annotation policy, including completeness expectations, treatment of occluded or ambiguous people, and any reviewer or quality-control metadata.
4. Whether permitted use includes running a pre-existing model for internal evaluation, retaining derived predictions and aggregate metrics, and showing anonymized examples in a private internal review.
5. Required storage, access control, retention/deletion, attribution, publication, and redistribution conditions for source images, annotations, predictions, and derived model artifacts.
6. Whether any additional institutional, ethics, or data-protection approval is required before access.

The candidate checkpoint is identified by SHA-256 `12824a97e19a747c3f852ca335ca3b4e2bfb60e05770c059154265f7761a4ccc`. Its documented immediate training lineage includes VisDrone data and Plaza de Mayo adaptation crops. The complete upstream training inventory is not yet established, so no independence claim will be made without the authors' source/partition metadata and a separate lineage review.

No source media, labels, or identifiable information would be redistributed. The evaluation would use only the permissions and storage conditions explicitly granted by the authors. If the proposed use is outside the dataset's access policy, please let us know the permitted scope or decline the request.

Thank you for your time.

**Project contact:** [name and institutional email to be completed by the project owner]

## Intake gate after a response

Before transferring any files, record the received access terms, authorized uses, authorized recipients, retention/deletion rule, attribution, data custodian, and permission-evidence file hash in the private dataset record. Obtain only the approved data. Preserve the authors' source-video grouping and original partition mapping. Compare those identities against the complete CrowdSight training lineage before any result is described as held out. If only image frames are provided, limit conclusions to image-level detection and per-frame counts.

The paper's data-availability statement and dataset description are at [Tech Science Press (2026)](https://www.techscience.com/cmc/v88n1/67301/html). This document is a request draft, not evidence of permission.
