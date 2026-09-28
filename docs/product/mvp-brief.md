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

## MVP success measures

The pilot owner and team must agree supported scene conditions, count tolerance, dense-scene failure reporting, alert episode quality, processing throughput, and operator usability before claiming acceptance. Record numerical thresholds and approval owner in the evaluation plan.
