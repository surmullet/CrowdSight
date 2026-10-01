# ADR-0004: Zone Geometry, Coverage Determination, and Aggregation Rules

## Status
Proposed — chờ người thật duyệt

## Context
Zone-based counting measures how many detected persons fall inside specific areas of interest defined on the source video image. Key questions arise:
1. Who determines whether a zone is "fully observed"?
2. What geometric point represents a person?
3. How are detections handled when zones overlap?
4. How do frame quality states (`VALID`, `PARTIAL`, `UNKNOWN`, `STALE`) translate into zone counts?

## Options
1. **Model-driven coverage and centroid anchor**: Have the detector try to guess visibility, and use the bounding box center `(cx, cy)` for point-in-polygon tests.
2. **Application-driven coverage and bottom-centre anchor**:
   - `ZoneCoverageProvider` in the application determines coverage: a zone is fully observed if the frame decoded successfully, the polygon lies entirely within `[0, width] x [0, height]`, and does not intersect active blind regions.
   - Anchor point is strictly normalized bottom-centre `(x, y) = (((x1+x2)/2)/width, y2/height)` representing ground-contact position.
   - Overlapping zones: if a person's bottom-centre falls within or on the boundary of multiple zones, the person is counted in all containing zones. The zone validator warns the user upon zone configuration.
   - Aggregation strictly obeys:
     - `VALID`: all configured zones are in `fully_observed_zones`; every zone has a non-negative visible count (including genuine 0).
     - `PARTIAL`: only zones in `fully_observed_zones` have a visible count; remaining configured zones have `availability="NOT_FULLY_OBSERVED"` and `visible_count=null`.
     - `UNKNOWN` / `STALE`: all zones have `availability="UNKNOWN"` or `"STALE"` and `visible_count=null`.

## Decision
Adopt Option 2: All coverage determination belongs to the application boundary. Bounding box bottom-centre is used as the single unambiguous ground anchor. Invariant tests and property-based tests (Hypothesis) verify all aggregation rules across all states.

## Consequences
- **Positive**: Strict geometric rigor matching physical perspective; detector remains decoupled from camera-view geometry; zero is never returned for unobserved zones.
- **Negative / Trade-off**: If camera viewpoint shifts drastically, zone polygons in image space might become misaligned unless camera view stability monitoring is calibrated and enabled.
