# Product MVP brief

## User and need

Site operations and safety teams need a timely view of visible crowd distribution across named areas so they can review congestion and decide whether to verify conditions or dispatch staff.

## MVP workflow

Configure site and zones -> submit recorded UAV/fixed-camera video -> process people and per-zone occupancy -> inspect heat map, trends, freshness and quality -> review threshold alerts -> export a summary.

## Inputs

Recorded video; zone polygons; optional surveyed usable areas and calibration correspondences. Live capture timestamps and camera/UAV telemetry are future inputs, not required for the first MVP.

## Outputs

Per-frame/per-zone visible counts, image-space heat map, optional geographic density only when calibration and measured area are valid, trend and alert summaries, annotated replay and exportable structured data. Every result carries source/session/time and quality metadata.

## Explicit exclusions

Litter detection, face recognition, identity inference, persistent person re-identification, autonomous response, universal crowd-safety thresholds, and any claim that image-space pixels are real-world density.

## Planned follow-on module

Parking-space occupancy is a separate extension with its own trained model, space-layout configuration, data split, and held-out evaluation. The first output is advisory occupancy state (`OCCUPIED`, `AVAILABLE`, or `UNKNOWN`). Physical parking control through gates/barriers, reservations, or routing is excluded until a separate authorized control-system design is approved. The parking model is not yet trained or evaluated in this repository.

Customer waiting-time estimation is a separate downstream queue-analytics extension, not an output of the parking-space occupancy model. Parking occupancy alone does not reveal a wait time. The estimate requires an agreed queue definition and view, timestamped queue observations, and service/entry/departure events or independently measured throughput. Outputs must be estimates with quality/freshness and uncertainty information, never a promised exact wait. Evaluation needs permitted timestamped queue examples with independently recorded actual waits. Queue-entry versus customer-service wait, available event sources, owners, and thresholds remain decisions for joint review. No customer identity or persistent re-identification is required.

## MVP success measures

The pilot owner and team must agree supported scene conditions, count tolerance, dense-scene failure reporting, alert episode quality, processing throughput, and operator usability before claiming acceptance. Record numerical thresholds and approval owner in the evaluation plan.
