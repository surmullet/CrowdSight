-- =============================================================================
-- CrowdSight Production Database Schema for PostgreSQL / Supabase
-- =============================================================================
-- Compatible with: PostgreSQL 14+, PostgreSQL 15+, PostgreSQL 16+, Supabase
-- Target ORM: SQLAlchemy 2.0 (src/crowdsight/service/storage/models.py)
-- Idempotent: Can be safely executed multiple times on a fresh or existing database.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 0. EXTENSIONS
-- Only pgcrypto is retained for cryptographic and random UUID generation.
-- (Note: In PostgreSQL 13+, gen_random_uuid() is built-in; pgcrypto provides
-- fallback safety across all PostgreSQL distributions).
-- -----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- -----------------------------------------------------------------------------
-- 1. TABLE: media_assets
-- Records ingested video assets with video metadata and integrity checksums.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS media_assets (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    display_name VARCHAR(255) NOT NULL,
    relpath VARCHAR(1024) NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    duration_s DOUBLE PRECISION NOT NULL,
    fps DOUBLE PRECISION NOT NULL,
    frame_count INTEGER NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    codec VARCHAR(64) NOT NULL,
    browser_playable BOOLEAN NOT NULL DEFAULT false,
    proxy_relpath VARCHAR(1024),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    
    CONSTRAINT uq_media_assets_relpath UNIQUE (relpath),
    CONSTRAINT ck_media_assets_duration_s CHECK (duration_s >= 0.0),
    CONSTRAINT ck_media_assets_fps CHECK (fps > 0.0),
    CONSTRAINT ck_media_assets_frame_count CHECK (frame_count >= 0),
    CONSTRAINT ck_media_assets_width CHECK (width > 0),
    CONSTRAINT ck_media_assets_height CHECK (height > 0)
);

CREATE INDEX IF NOT EXISTS ix_media_assets_sha256 ON media_assets(sha256);
CREATE INDEX IF NOT EXISTS ix_media_assets_created_at ON media_assets(created_at DESC);

COMMENT ON TABLE media_assets IS 'Ingested source video files and decoded stream metadata';
COMMENT ON COLUMN media_assets.id IS 'Unique UUID (string representation) of the media asset';
COMMENT ON COLUMN media_assets.relpath IS 'Relative file path inside the media storage root';
COMMENT ON COLUMN media_assets.sha256 IS 'SHA-256 digest of the source video binary';


-- -----------------------------------------------------------------------------
-- 2. TABLE: zone_sets
-- Logical container grouping versioned polygon zone configurations.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS zone_sets (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS ix_zone_sets_created_at ON zone_sets(created_at DESC);

COMMENT ON TABLE zone_sets IS 'Logical definition of monitoring zone configurations';


-- -----------------------------------------------------------------------------
-- 3. TABLE: zone_set_versions
-- Immutable versions of zone polygon vertices and bounding coordinates.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS zone_set_versions (
    id VARCHAR(64) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    zone_set_id VARCHAR(64) NOT NULL REFERENCES zone_sets(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    image_width INTEGER NOT NULL,
    image_height INTEGER NOT NULL,
    polygon_data JSONB NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),

    CONSTRAINT uq_zone_set_version UNIQUE (zone_set_id, version),
    CONSTRAINT ck_zone_set_versions_version CHECK (version >= 1),
    CONSTRAINT ck_zone_set_versions_image_width CHECK (image_width > 0),
    CONSTRAINT ck_zone_set_versions_image_height CHECK (image_height > 0)
);

CREATE INDEX IF NOT EXISTS ix_zone_set_versions_zone_set_id ON zone_set_versions(zone_set_id);
CREATE INDEX IF NOT EXISTS ix_zone_set_versions_polygon_data_gin ON zone_set_versions USING gin (polygon_data);

COMMENT ON TABLE zone_set_versions IS 'Immutable versioned polygon geometry for a zone set';
COMMENT ON COLUMN zone_set_versions.polygon_data IS 'JSONB structure defining zone IDs, names, and polygon vertex coordinates';


-- -----------------------------------------------------------------------------
-- 4. TABLE: sessions
-- Analysis processing runs executed on a media asset with an AI model.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    media_asset_id VARCHAR(36) NOT NULL REFERENCES media_assets(id) ON DELETE CASCADE,
    zone_set_version_id VARCHAR(64) NOT NULL REFERENCES zone_set_versions(id) ON DELETE NO ACTION,
    model_profile_id VARCHAR(128) NOT NULL,
    model_profile_sha256 VARCHAR(64) NOT NULL,
    checkpoint_sha256 VARCHAR(64) NOT NULL,
    tracker_config_sha256 VARCHAR(64),
    options JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'QUEUED',
    progress DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    processed_frames INTEGER NOT NULL DEFAULT 0,
    total_frames INTEGER NOT NULL DEFAULT 0,
    error_code VARCHAR(64),
    user_action_hint VARCHAR(512),
    applicability_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    synthetic BOOLEAN NOT NULL DEFAULT false,
    completeness VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),

    CONSTRAINT ck_sessions_status CHECK (
        status IN ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', 'CANCELLING', 'PARTIAL_CANCELLED')
    ),
    CONSTRAINT ck_sessions_completeness CHECK (
        completeness IN ('PENDING', 'FULL', 'PARTIAL')
    ),
    CONSTRAINT ck_sessions_progress CHECK (
        progress >= 0.0 AND progress <= 1.0
    ),
    CONSTRAINT ck_sessions_processed_frames CHECK (
        processed_frames >= 0
    ),
    CONSTRAINT ck_sessions_total_frames CHECK (
        total_frames >= 0
    )
);

CREATE INDEX IF NOT EXISTS ix_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS ix_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_sessions_media_asset_id ON sessions(media_asset_id);
CREATE INDEX IF NOT EXISTS ix_sessions_zone_set_version_id ON sessions(zone_set_version_id);
CREATE INDEX IF NOT EXISTS ix_sessions_options_gin ON sessions USING gin (options);

-- Trigger function to automatically update updated_at timestamp on row update
CREATE OR REPLACE FUNCTION update_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = clock_timestamp();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sessions_updated_at ON sessions;
CREATE TRIGGER trg_sessions_updated_at
BEFORE UPDATE ON sessions
FOR EACH ROW
EXECUTE FUNCTION update_sessions_updated_at();

COMMENT ON TABLE sessions IS 'Video analysis pipeline sessions with AI model provenance and lifecycle state';


-- -----------------------------------------------------------------------------
-- 5. TABLE: observations
-- Per-frame detections and ground anchors produced by the detector and tracker.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS observations (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    session_id VARCHAR(36) NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    frame_index INTEGER NOT NULL,
    media_time_s DOUBLE PRECISION NOT NULL,
    quality VARCHAR(16) NOT NULL,
    reason_code VARCHAR(64),
    payload_v1 JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),

    CONSTRAINT ck_observations_frame_index CHECK (frame_index >= 0),
    CONSTRAINT ck_observations_media_time_s CHECK (media_time_s >= 0.0),
    CONSTRAINT ck_observations_quality CHECK (
        quality IN ('VALID', 'PARTIAL', 'UNKNOWN', 'STALE')
    )
);

CREATE INDEX IF NOT EXISTS ix_obs_session_frame ON observations(session_id, frame_index);
CREATE INDEX IF NOT EXISTS ix_obs_session_time ON observations(session_id, media_time_s);
CREATE INDEX IF NOT EXISTS ix_observations_session_id ON observations(session_id);
CREATE INDEX IF NOT EXISTS ix_observations_payload_v1_gin ON observations USING gin (payload_v1);

COMMENT ON TABLE observations IS 'Per-frame raw and tracked person detections in JSONB payload';
COMMENT ON COLUMN observations.payload_v1 IS 'Standard contract v1 payload containing detections list, normalized x/y, confidence, track_id, and bbox_xyxy';


-- -----------------------------------------------------------------------------
-- 6. TABLE: zone_results
-- Aggregated occupant counts and visibility status per zone per frame.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS zone_results (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    session_id VARCHAR(36) NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    frame_index INTEGER NOT NULL,
    media_time_s DOUBLE PRECISION NOT NULL,
    zone_id VARCHAR(64) NOT NULL,
    availability VARCHAR(32) NOT NULL,
    visible_count INTEGER,

    CONSTRAINT ck_zone_results_frame_index CHECK (frame_index >= 0),
    CONSTRAINT ck_zone_results_media_time_s CHECK (media_time_s >= 0.0),
    CONSTRAINT ck_zone_results_availability CHECK (
        availability IN ('COUNTED', 'NOT_FULLY_OBSERVED', 'UNKNOWN', 'STALE')
    ),
    CONSTRAINT ck_zone_result_visible_count_availability CHECK (
        (visible_count IS NOT NULL AND availability = 'COUNTED') OR
        (visible_count IS NULL AND availability != 'COUNTED')
    ),
    CONSTRAINT ck_zone_results_visible_count_nonnegative CHECK (
        visible_count IS NULL OR visible_count >= 0
    )
);

CREATE INDEX IF NOT EXISTS ix_zone_results_session_time ON zone_results(session_id, media_time_s);
CREATE INDEX IF NOT EXISTS ix_zone_results_session_zone ON zone_results(session_id, zone_id);
CREATE INDEX IF NOT EXISTS ix_zone_results_session_frame ON zone_results(session_id, frame_index);
CREATE INDEX IF NOT EXISTS ix_zone_results_session_id ON zone_results(session_id);

COMMENT ON TABLE zone_results IS 'Frame-level zone counting results with strictly enforced availability invariants';


-- -----------------------------------------------------------------------------
-- 7. TABLE: artifacts
-- Generated artifacts including JSON dataset exports and PNG heatmaps.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS artifacts (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    session_id VARCHAR(36) REFERENCES sessions(id) ON DELETE CASCADE,
    kind VARCHAR(64) NOT NULL,
    relpath VARCHAR(1024) NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_artifacts_session_kind ON artifacts(session_id, kind);
CREATE INDEX IF NOT EXISTS ix_artifacts_expires_at ON artifacts(expires_at);
CREATE INDEX IF NOT EXISTS ix_artifacts_session_id ON artifacts(session_id);

COMMENT ON TABLE artifacts IS 'File-backed session artifacts like full dataset JSON exports and heatmap PNGs';


-- -----------------------------------------------------------------------------
-- 8. TABLE: notes
-- Operator annotations, incident markers, and timestamps during review.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notes (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    session_id VARCHAR(36) NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    media_time_s DOUBLE PRECISION NOT NULL,
    zone_id VARCHAR(64),
    text TEXT NOT NULL,
    author VARCHAR(128) NOT NULL DEFAULT 'operator',
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),

    CONSTRAINT ck_notes_media_time_s CHECK (media_time_s >= 0.0)
);

CREATE INDEX IF NOT EXISTS ix_notes_session_time ON notes(session_id, media_time_s);
CREATE INDEX IF NOT EXISTS ix_notes_session_id ON notes(session_id);

COMMENT ON TABLE notes IS 'Operator review notes and incident annotations linked to video playback time';


-- -----------------------------------------------------------------------------
-- 9. TABLE: audit_log
-- Security, purge, and administrative actions audit trail.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    action VARCHAR(64) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(64) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS ix_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS ix_audit_log_details_gin ON audit_log USING gin (details);

COMMENT ON TABLE audit_log IS 'Immutable audit records for compliance, security, and lifecycle management';
