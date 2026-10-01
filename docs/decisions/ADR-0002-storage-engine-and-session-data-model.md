# ADR-0002: Storage Engine, Invariant Enforcement, and Session Data Model

## Status
Proposed — chờ người thật duyệt

## Context
CrowdSight requires persistent storage for registered media assets, immutable zone-set versions, video processing sessions, validated per-frame observations, zone aggregation readings, generated artifacts, operator notes, and audit logs. The system must strictly enforce that missing observations never equate to zero visible persons, and prevent accidental data corruption or schema drift across developer environments and production.

## Options
1. **NoSQL / Document Store (e.g., MongoDB)**: Flexible JSON storage, but lacks native relational guarantees and schema-level CHECK constraints for critical invariants.
2. **SQLAlchemy 2.0 with PostgreSQL (Production) and SQLite WAL (Development / Local)**: Use Alembic migrations, strongly-typed declarative models, and database CHECK constraints (e.g., `CHECK (visible_count IS NOT NULL <-> availability = 'COUNTED')`).

## Decision
Adopt Option 2: Use SQLAlchemy 2.0 with Alembic. For local development, tests, and CI, default to SQLite configured with Write-Ahead Logging (`PRAGMA journal_mode=WAL`) and foreign keys enabled. Ensure full PostgreSQL compatibility for production deployments. Implement database-level CHECK constraints ensuring that `zone_results` cannot have a `visible_count` unless `availability == 'COUNTED'`. Store complete v1 observation payloads in JSON/JSONB columns with indexed query columns (`session_id`, `frame_index`, `media_time_s`, `quality`).

## Consequences
- **Positive**: Hard invariant guarantees enforced at the database engine level; painless local setup without requiring a live external database server for running test suites; clean migration path via Alembic.
- **Negative / Trade-off**: SQLite dialect specifics (e.g. JSON querying nuances) must be abstracted cleanly via SQLAlchemy so migration to PostgreSQL remains seamless.
