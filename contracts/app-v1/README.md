# CrowdSight Application Layer Contract (v1)

This directory defines the versioned HTTP REST contract for the CrowdSight application service (`/api/v1`).

## Specification Files
- [`openapi.json`](openapi.json): Machine-readable OpenAPI 3.1 schema. Used by frontend client generators (`openapi-typescript`).

## API Principles
1. **REST Resource Hierarchy**:
   - `/health`: Liveness and readiness endpoints.
   - `/api/v1/model`: Model profile metadata, checkpoint provenance, and applicability gates.
   - `/api/v1/alerts`: Operational alert gating status (permanently disabled in experimental view).
   - `/api/v1/media`: Registered recorded-video assets catalog with HTTP 206 partial streaming.
   - `/api/v1/zone-sets`: Immutable zone-set versioning and real-time polygon validation.
   - `/api/v1/sessions`: Analysis sessions, lifecycle management, and Server-Sent Events (SSE).
   - `/api/v1/sessions/{id}/frames`: Synchronized playback observations and freshness policies.
   - `/api/v1/artifacts`: Download of secure generated artifacts (heatmaps, exports, proxies).
2. **Standardized Error Handling (RFC 9457)**:
   All errors return `application/problem+json` with stable machine-readable error codes (`code`) and actionable guidance (`user_action_hint`).
3. **Fail-Closed Governance**:
   `GET /api/v1/alerts/status` explicitly returns `operational_alerts_allowed: false` with explanatory rationale.
4. **Client-Server Contract Versioning**:
   Any breaking changes to endpoints or payload structures require a new contract release (`app-v2`).
