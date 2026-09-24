# CrowdSight

Recorded-video crowd monitoring and heat-map product starter. It is intended for site operations teams to review visible crowd distribution in named zones. Litter detection is out of scope.

## Start here

1. Read [Team handoff](docs/TEAM_HANDOFF.md) for scope, three-person ownership, interface contract, phased plan, and MVP acceptance checklist.
2. Read [MVP brief](docs/product/mvp-brief.md) for the user need and product boundaries.
3. Read [Codebase plan](docs/architecture/codebase-plan.md) for selective reuse from the two existing project folders.

## Current status

This repository contains planning documents and a folder scaffold; it is not a runnable application yet. Existing prototypes remain in sibling folders `../heat_map/` and `../uav-crowd-monitoring/`. The team should inspect and selectively adapt relevant pieces only after confirming code/data/model provenance and dependencies.

## Product boundaries

Counts represent visible people, not attendance. Image-space heat maps are not geographic maps. Geographic density requires valid calibration and measured area. Stale, partial, invalid, or unsupported observations must not be presented as zero or normal. No face recognition, identity inference, or persistent re-identification.
