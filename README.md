# CrowdSight

CrowdSight is a proposed recorded-video crowd monitoring product. The current implementation focuses on visible-person detections, counts in named image zones, trends, and a relative image-space heat map for a fixed camera. Operational alerts and people-per-square-metre density are unavailable until site-specific evaluation and calibration are approved.

## Start here

- [Teammate handoff](TEAMMATE_HANDOFF.md): product flow, exact AI/ML input and output, model identity, quality rules, two implementation work packages, and open decisions.
- [Crowd contract](contracts/v1/README.md): proposed v1 producer schema, synthetic fixtures, and application review record.

## Code map

| Area | Location |
|---|---|
| Selected crowd model profile | [`configs/models/crowd_best_local.yaml`](configs/models/crowd_best_local.yaml) |
| Detector and tracker adapter | [`src/crowdsight/detection/adapter.py`](src/crowdsight/detection/adapter.py) |
| Observation and operating-use decisions | [`src/crowdsight/common/observations.py`](src/crowdsight/common/observations.py), [`src/crowdsight/detection/applicability.py`](src/crowdsight/detection/applicability.py) |
| Proposed frame schema and examples | [`contracts/v1/crowd-frame-observation.schema.json`](contracts/v1/crowd-frame-observation.schema.json), [`contracts/v1/fixtures/`](contracts/v1/fixtures/) |
| Private-data evaluation tools | [`scripts/`](scripts/) |

The fine-tuned `best.pt` checkpoint and source footage are stored outside this repository. The application API and operator display require the two implementation teammates' review. The current model is for experimental replay; no independent Vietnam-site performance result is claimed.
