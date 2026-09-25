# Proposed application contracts, version 1

These JSON Schemas describe the proposed AI-to-application frame outputs. They are review artifacts, not a frozen API. Backend and frontend owners must approve field names, nullability, time semantics, error behavior, and versioning before implementation. Changes after approval require a new contract version and synchronized consumer updates.

## Files

- `crowd-frame-observation.schema.json`: one crowd-model frame observation.
- `parking-frame-observation.schema.json`: separate configured-space occupancy output.
- `fixtures/crowd-frame-observation.valid.json`: synthetic valid replay observation.
- `fixtures/crowd-frame-observation.partial.json`: synthetic partial observation with only one fully observed zone.
- `fixtures/crowd-frame-observation.unknown.json`: synthetic failed/unknown observation with no detections.
- `fixtures/parking-frame-observation.valid.json`: synthetic fully observed parking result with every stall classified.
- `fixtures/parking-frame-observation.partial.json`: synthetic partially observed result with a mix of known and unknown stalls.
- `fixtures/parking-frame-observation.unknown.json`: synthetic unavailable parking observation with all configured stalls unknown and confidence null.

The examples contain synthetic IDs and values and do not represent measured model performance, a real site, or approved operating thresholds. They contain no footage or checkpoint artifacts.

## Runtime semantic validation

JSON Schema validation checks the serialized structure and local field constraints; it does not establish that a parking observation matches the active site configuration or its source artifacts. At model load, `load_parking_model_profile()` computes the exact profile-file hash and `verify_parking_checkpoint()` checks the checkpoint bytes against the profile's expected SHA-256. The serializer must populate the observation's profile and checkpoint hashes from that verified profile. `validate_parking_predictions()` checks the reported profile ID, site/camera/layout identity, exactly one result for every configured `space_id` with no duplicates or extras, configured stall order, per-stall evidence time equal to the frame's `media_time_s`, and frame-quality/state consistency. `ParkingFrameObservation` repeats the per-stall/frame timestamp check when constructing the application object. A consumer that receives observations from another service must enforce equivalent configuration and provenance checks at its trust boundary. A JSON Schema validator must assert the `date-time` format for non-null `captured_at`; implementations that treat `format` as annotation only need a separate RFC 3339 check. Hash fields are syntactically constrained by the schema, but the schema cannot verify artifact bytes.

The parking schema also cannot determine whether a state is visually correct, whether the fixed camera still matches the approved view, or whether a stall layout is current in the physical site. Those require site configuration, camera health/shift checks, reviewed labels, and model evaluation; structural schema validity alone is not evidence of occupancy accuracy.

## Contract decisions for joint review

1. Should annotated replay transport pixel bounding boxes in the frame detection object, or should the video worker keep boxes internal?
2. Confirm the `fully_observed_zones` list: `PARTIAL` uses `observation_valid: true` but permits counts only for listed zones; `UNKNOWN` and `STALE` require an empty list and no detections.
3. Which field should carry the heat-map artifact reference, and what retention/access semantics apply?
4. Confirm that `confidence_semantics: RAW_MODEL_SCORE` is surfaced as an uncalibrated score; any future calibrated-probability claim requires calibration evidence and a reviewed contract revision.
5. Who approves schema changes and maintains compatibility for the two model namespaces?
6. For parking, does `camera_view_id` name the exact trained/profile-supported view, and who maintains the mapping from source IDs to view IDs?
7. Confirm parking frame quality: `VALID` means all configured stalls have known states; `PARTIAL` means a mix of known and `UNKNOWN`; `UNKNOWN`/`STALE` means every configured stall is `UNKNOWN`. The service owner must also set the freshness limit that transitions an observation to `STALE`.
8. If customer waiting-time estimates are in scope, define whether the estimate covers parking-entry wait or a customer-service queue, identify the timestamped event/throughput source and its owner, and review a separate versioned analytics contract. Do not add wait time to the parking occupancy frame output without that decision; occupancy states alone do not supply the required queue/service evidence.

## AI/ML recommendations to speed review

These are proposed defaults from the AI/ML owner, not backend/frontend approvals. An owner may accept or replace each recommendation in the review record below.

| Decision | AI/ML recommendation | Owner confirmation still needed |
|---|---|---|
| Model provenance | Preserve `model_profile_id`, profile SHA-256, checkpoint SHA-256, and tracker-config SHA-256 with every crowd frame. For parking, preserve profile/checkpoint hashes in its separate namespace. Store provenance with the persisted observation even if transport uses an adapter to the current backend model. | Backend owner chooses nested versus top-level envelope fields and persistence location. |
| Replay time | `frame_index` is zero-based; `media_time_s` is elapsed seconds from the source recording; `captured_at` is an RFC 3339 timestamp only when the source supplies a real capture time, otherwise null. Do not turn replay time into wall-clock time. | Backend owner confirms field names, timezone handling, and ordering/replay behavior. |
| Crowd quality and zones | `VALID` means every configured zone has complete usable coverage. `PARTIAL` means only IDs in `fully_observed_zones` may produce counts; uncovered zones remain unavailable. `UNKNOWN`/`STALE` carry no detections or fully observed zones. | Backend owner confirms invalid-frame behavior and how quality affects rolling alerts/history; frontend owner confirms unavailable-state display. |
| Confidence | Keep `confidence_semantics: RAW_MODEL_SCORE`; do not label it probability. For `UNKNOWN` parking space results, confidence is null. | Frontend owner decides whether raw scores are displayed to staff or kept in diagnostics. |
| Annotated replay boxes | If the product renders detector boxes on replay video, add optional `bbox_xyxy` in original-frame pixel coordinates and require `image_width`/`image_height` to interpret it. Keep the normalized bottom-centre anchor for zone logic. If overlays are out of scope, keep boxes inside the processing worker. | Backend and frontend owners confirm payload/storage cost and which consumer needs boxes before a new schema version is cut. |
| Heat-map delivery | Label frame-relative maps `IMAGE_SPACE`; label metric/geographic maps separately and only emit those after the density validity gate passes. Prefer a permission-controlled artifact reference for large map arrays instead of embedding arrays in each frame observation. | Backend owner chooses artifact reference, retention, access control, and expiry; frontend owner confirms rendering needs. |
| Parking availability | Keep parking output separate from crowd output. Bind every result to one `site_id`, exact `camera_view_id`, immutable `space_layout_version`, and one result per configured `space_id`. A blocked, off-view, stale, or ambiguous stall is `UNKNOWN`, never `AVAILABLE`. | Product/camera owner confirms fixed-view and stall-assignment assumptions; backend/frontend owners confirm advisory presentation and update behavior. |
| Staleness | Treat `STALE` as a service-time freshness decision, not a model classification. The serving layer supplies the freshness limit and converts aged evidence to stale/unknown according to its policy. | Backend owner sets and operates the freshness limit; product owner approves user-facing behavior. |
| Waiting time | Keep customer waiting-time estimation as a separate downstream analytics contract. Do not derive it from stall occupancy. | Product owner defines the queue and event source before the analytics contract is drafted. |

## Compatibility findings from the two reference applications

These are read-only integration findings from the current sibling projects, not owner approvals. The frontend folder in this repository is empty; application behavior currently lives in `../uav-crowd-monitoring/` and `../heat_map/`.

### UAV Crowd Monitor (`../uav-crowd-monitoring`)

The current Pydantic `crowd.models.Frame` API expects `source_id`, `session_id`, `mode`, `frame_index`, `tracking_epoch`, `media_time_s`, optional `captured_at`, `observation_valid`, `registration_valid`, `fully_observed_zones`, and normalized detections (`track_id`, `x`, `y`, `confidence`). CrowdSight's proposed v1 now carries `fully_observed_zones` and its normalized bottom-centre anchors/scores map to the backend's detection fields. The backend does not currently accept CrowdSight's `model_profile_id`, profile/checkpoint/tracker hashes, image dimensions, quality enum, or `confidence_semantics`. The full serialized CrowdSight observation is not a drop-in request body.

Before integration, the backend owner must choose one of these designs and record it here:

1. Extend and version the UAV API schema to carry model provenance and explicit quality semantics; or
2. Add a reviewed adapter that maps the AI record to the existing `Frame` and durably stores the omitted model provenance alongside the resulting snapshot.

For either design, agree how `PARTIAL` maps to `observation_valid` and `fully_observed_zones`, how invalid/stale/unknown frames clear temporal alert state, which process owns `tracking_epoch`, and how replay versus live determines `mode`. The current `DensityEngine` converts invalid observations to unknown zone counts and labels count uncertainty `NOT_CALIBRATED`; the frontend already displays those as unavailable rather than zero. Do not map `PARTIAL` to an ordinary fully valid frame without per-zone coverage handling.

The current integration surface is `POST /api/frames` and results appear at `/api/latest` and `/api/history`. Parking has no endpoint or consumer contract in this backend yet.

### Heat-map/UAV project (`../heat_map`)

The current pipeline writes detection and track CSV files, transforms track ground points using telemetry/camera metadata, and exposes stored flight records and GeoJSON through its API. Its `/ws/live` endpoint is still a placeholder. There is no existing endpoint that accepts CrowdSight v1 frame observations. Any integration therefore needs an agreed batch/file importer or a new versioned ingestion endpoint. Preserve the source frame/time, session-local track IDs, image versus ground coordinate distinction, calibration metadata, and model/checkpoint/profile hashes through the import; projected GeoJSON alone is insufficient model provenance.

Parking occupancy is not represented in either reference application. Keep it in a separate namespace and obtain backend/frontend agreement on `site_id`, fixed `camera_view_id`, immutable `space_layout_version`, one output per configured stall, `UNKNOWN` semantics, and advisory-only presentation before implementing a consumer.

### Decision record

No backend or frontend owner sign-off has been recorded. The proposed JSON Schemas and fixtures remain unapproved. During a joint review, record the chosen API version/mapping, timestamp and quality semantics, where model provenance is stored, parking consumer ownership, reviewer, and date here and update the contract fixtures with the approved decision.

## Review record

The schemas remain `PROPOSED`; no owner approval is recorded yet. Complete this table during the joint review before backend/frontend implementation treats the structures as frozen.

| Owner | Decisions to confirm | Reviewer/date | Status |
|---|---|---|---|
| AI/ML lead | Model/profile identifiers, frame indexing, normalized anchor semantics, unknown behavior, confidence meaning, and layout-version binding | Pending | PROPOSED |
| Backend owner | API field names/nullability, time semantics, schema versioning, error/freshness handling, persistence, and artifact references | Pending | PROPOSED |
| Frontend owner | Display semantics for quality, confidence, unknown spaces, annotated boxes, and heat-map type | Pending | PROPOSED |
| Product/pilot owner | Site permissions, retention, alert/availability thresholds, advisory-only parking scope, and acceptance criteria | Pending | PROPOSED |

After approval, record the decision date and version in this table, update both application handoffs and fixtures together, and create a new schema version for any breaking change.
