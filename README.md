# CrowdSight

## Project overview

CrowdSight is a recorded-video crowd-monitoring product concept for tourist sites, plazas, campuses, and event venues. The proposed MVP analyzes UAV or fixed-camera footage to estimate visible occupancy in named zones, generate heat maps and time trends, and present reviewable threshold alerts to site operations personnel.

The system is intended to support operational decisions. Alerts require human review. Litter detection is outside the project scope.

## Documentation

- [Project handoff and delivery plan](docs/TEAM_HANDOFF.md): scope, role assignments, data contract, delivery phases, acceptance criteria, and initial actions.
- [MVP product brief](docs/product/mvp-brief.md): target users, workflow, inputs, outputs, and product boundaries.
- [Codebase plan](docs/architecture/codebase-plan.md): repository structure and selective reuse guidance for the existing prototypes.
- [Evaluation plan](docs/evaluation/plan.md): model, count, alert, throughput, and calibration evaluation requirements.
- [Demo operations runbook](docs/operations/demo-runbook.md): preparation and handling guidance for local demonstrations.

## Repository status

This repository currently contains planning documents and a directory scaffold. It does not yet contain a runnable application. Existing prototype projects are located in the sibling directories `../heat_map/` and `../uav-crowd-monitoring/`. Any reused implementation requires review of technical dependencies, tests, licensing, model provenance, and data permissions before integration.

## Product limitations and safeguards

- Counts represent visible people in observed footage; they are not attendance totals and do not include hidden people.
- Image-space heat maps describe concentration within a video frame and are not geographic maps.
- Geographic density requires valid camera calibration and a measured usable area.
- Stale, partial, invalid, and unsupported observations must be reported as unavailable rather than represented as zero or normal conditions.
- Face recognition, identity inference, demographic inference, and persistent re-identification are excluded.
- Site-approved thresholds and human review are required for operational alerts.
