# CrowdSight REST API Reference (`/api/v1`)

## 1. Overview

The CrowdSight REST API provides programmatic access to video catalog inspection, zone geometry validation, batch inference session orchestration, frame-level observation queries, and relative image-space analytics.

- **Base URL**: `/api/v1`
- **Canonical Specification**: Exported to [contracts/app-v1/openapi.json](../contracts/app-v1/openapi.json).
- **Authentication**: Optional Bearer token via `Authorization: Bearer <token>` or `CROWDSIGHT_API_TOKEN` environment variable. Mandatory in production environments.

---

## 2. RFC 9457 Problem Details (`application/problem+json`)

All HTTP 4xx and 5xx errors strictly return RFC 9457 Problem Details objects with stable error codes and actionable user hints.

### Example Problem Response
```json
{
  "type": "https://crowdsight.local/errors/ZONE_SET_INVALID",
  "title": "Zone Set Invalid",
  "status": 400,
  "detail": "Zone 'Khu vực A' contains self-intersecting polygon geometry.",
  "instance": "/api/v1/zone-sets/validate",
  "code": "ZONE_SET_INVALID",
  "user_action_hint": "Please verify polygon vertices do not cross each other.",
  "timestamp": "2026-09-30T10:45:00Z"
}
```

### Stable Error Codes Reference Table
| Error Code | HTTP Status | Description | User Action Hint |
| :--- | :--- | :--- | :--- |
| `MEDIA_NOT_FOUND` | 404 | Media asset not found in catalog | Scan directory with `crowdsight media scan` |
| `MEDIA_UNREADABLE` | 400 | Video file cannot be opened or decoded | Check video container format and permissions |
| `ZONE_SET_INVALID` | 400 | Zone polygon geometry violates simple polygon rules | Adjust vertices to prevent self-intersections |
| `MODEL_CHECKPOINT_MISSING` | 500 | Weight checkpoint file missing on server | Ensure checkpoint exists at configured path |
| `MODEL_CHECKPOINT_HASH_MISMATCH` | 500 | Checkpoint SHA-256 digest does not match profile | Verify weight file integrity against profile |
| `MODEL_PROFILE_MISMATCH` | 500 | Profile configuration does not match expected SHA-256 | Verify YAML configuration file |
| `INFERENCE_FAILURE_RATE_EXCEEDED` | 500 | Over 25% of video frames failed inference | Check GPU health or model parameters |
| `DECODE_FAILURE_RATE_EXCEEDED` | 500 | Over 10% of frames corrupted or unreadable | Inspect input video stream integrity |
| `CANCELLED_BY_USER` | 200/400 | Session was stopped via cooperative cancel | View partial results or restart session |
| `STORAGE_FULL` | 507 | Filesystem storage capacity exhausted | Purge aged sessions using retention CLI |
| `INTERNAL_ERROR` | 500 | Unhandled server exception | Inspect server logs for traceback |

---

## 3. Core API Endpoints

### 3.1 System & Model Identity
- `GET /health`: Liveness and readiness probe returning database and configuration status.
- `GET /api/v1/model/profile`: Inspect active model profile, SHA-256 hashes, image size, and raw threshold.
- `GET /api/v1/alerts/status`: Returns `operational_alerts_allowed: false` with explanation of experimental gating.

### 3.2 Media Catalog
- `GET /api/v1/media`: List all registered media assets in server catalog.
- `GET /api/v1/media/{media_id}`: Retrieve detailed metadata for a media asset (duration, FPS, resolution, codec).
- `GET /api/v1/media/{media_id}/stream`: Stream video footage with full HTTP 206 Partial Content Range support.
- `GET /api/v1/media/{media_id}/frame?frame_index=0`: Extract single frame JPEG for zone drawing and reference.

### 3.3 Zone Sets & Geometry Validation
- `GET /api/v1/zone-sets`: List all configured zone sets.
- `POST /api/v1/zone-sets`: Create a new immutable zone set and initial version.
- `POST /api/v1/zone-sets/validate`: Real-time geometric validation (checks vertices $\ge 3$, simple non-self-intersecting polygons, image coordinate containment, and overlap warnings).

### 3.4 Analysis Sessions
- `POST /api/v1/sessions`: Enqueue a new video analysis job with parameters (`media_id`, `zone_set_version_id`, `frame_stride`, `use_synthetic`).
- `GET /api/v1/sessions`: List sessions with status and progress filters.
- `GET /api/v1/sessions/{session_id}`: Get session execution state, processing FPS, and quality breakdown.
- `POST /api/v1/sessions/{session_id}/cancel`: Request cooperative cancellation.
- `DELETE /api/v1/sessions/{session_id}`: Cascade delete session record, observations, and physical artifacts on disk.
- `GET /api/v1/sessions/{session_id}/events`: Server-Sent Events (SSE) stream broadcasting live progress and quality tallies.

### 3.5 Observations & Frame Queries
- `GET /api/v1/sessions/{session_id}/frames?from_t=&to_t=&limit=`: Time-windowed paginated query for observation records.
- `GET /api/v1/frames/at?session_id=&t=`: Temporal point query applying strict freshness policy gap checks (`STALE` when gap $> \text{freshness\_max\_gap\_s}$).

### 3.6 Analytics & Exports
- `GET /api/v1/sessions/{session_id}/trends?zone_id=&bucket_s=&series=`: Bucketed and LTTB-downsampled trend lines. Gaps for unobserved intervals strictly return `null`.
- `GET /api/v1/sessions/{session_id}/peaks?zone_id=&top_k=`: Top visible person count moments.
- `GET /api/v1/sessions/{session_id}/summary`: Complete quality breakdown and 10-bin raw detector score histogram.
- `GET /api/v1/sessions/{session_id}/heatmaps`: Relative image-space Gaussian heat map artifact generation.
- `GET /api/v1/artifacts/{artifact_id}`: Secure token-verified download of generated PNGs and export archives.
- `GET /api/v1/sessions/{session_id}/export/{format}`: Export observations v1 JSONL or CSV zone counts with manifest and `SEMANTICS.md`.
