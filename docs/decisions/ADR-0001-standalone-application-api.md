# ADR-0001: Standalone Application API Contract vs External UAV API Reference

## Status
Proposed — chờ người thật duyệt

## Context
`TEAMMATE_HANDOFF.md` and `contracts/v1/README.md` mention a historical or sister repository "UAV API" with a `POST /api/frames` endpoint, noting that its payload does not carry CrowdSight's full provenance (model profile SHA-256, checkpoint SHA-256, tracker config hash), session metadata, or quality states (`VALID`, `PARTIAL`, `UNKNOWN`, `STALE`). The current CrowdSight repository contains the AI/ML detection adapters and contract definitions, but no active UAV backend codebase. The application requires a clean, versioned, RESTful boundary for video session orchestration, zone aggregation, playback, and analytics.

## Options
1. **Coupled / Proxying Adapter**: Attempt to emulate or proxy an external UAV API schema while inventing synthetic fields for missing provenance.
2. **Dedicated Standalone CrowdSight Application API (`/api/v1`)**: Design a clean, first-class REST API under `/api/v1` documented with OpenAPI 3.1 in `contracts/app-v1/openapi.json`. Use RFC 9457 Problem Details (`application/problem+json`) for standardized, actionable errors. Provide explicit types for sessions, media catalog, zone sets, frame observations, and analytics.

## Decision
Adopt Option 2: Implement a standalone CrowdSight application API under `/api/v1`. Treat the UAV API mentioned in handoff documentation as an external reference that is not a runtime dependency. The application schema will fully preserve AI/ML v1 contract provenance, enforce fail-closed quality boundaries, and provide complete documentation through an exported OpenAPI specification.

## Consequences
- **Positive**: Clean separation of concerns; no legacy compromises; full fidelity preservation of `contracts/v1/` observations; deterministic client generation for frontend via `openapi-typescript`.
- **Negative / Trade-off**: If a future deployment requires direct integration into an existing UAV console, a dedicated adapter bridge service will need to be written.
