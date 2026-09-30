# ADR-0006: Data Retention Lifecycle, Artifact Security, and Purge Operations

## Status
Proposed — chờ người thật duyệt

## Context
Recorded video sessions, frame observations, and derived image heat maps consume substantial disk storage and may be subject to organizational data retention policies. Furthermore, raw video files and generated artifacts should not be exposed via unauthenticated arbitrary filesystem paths.

## Options
1. **Unmanaged Storage / Direct Static Serving**: Store files in arbitrary public folders without expiration or lifecycle cleanup.
2. **Managed Storage Lifecycle with Short-Lived Access Tokens**:
   - Store all generated artifacts (heat maps, proxy videos, exports) in a dedicated managed artifact directory referenced only by UUIDs.
   - Enforce configurable data retention via `CROWDSIGHT_RETENTION_DAYS` (default proposed: 30 days, pending formal product/site review).
   - Implement scheduled background cleanup task and explicit `DELETE /api/v1/sessions/{id}` endpoint that permanently purges session database rows, related zone readings, and on-disk artifacts with an immutable audit log entry.
   - Serve media streams and artifacts through protected endpoints verifying session ownership or short-lived signed tokens (`/api/v1/artifacts/{id}`).
   - Strictly prohibit client-supplied arbitrary paths to prevent path traversal vulnerabilities.

## Decision
Adopt Option 2: Implement managed artifact storage, 30-day default retention policy with audit logging, and signed / token-authenticated artifact retrieval.

## Consequences
- **Positive**: Hardened security against directory traversal; predictable disk utilization; verifiable audit trail for regulatory compliance.
- **Negative / Trade-off**: Operators wanting indefinite archival must explicitly export sessions before the retention period expires.
