-- ========================================================
-- CrowdSight Database Reset / Cleanup Script
-- Run this first if you want to clear old random UUIDs
-- ========================================================
BEGIN;

TRUNCATE TABLE artifacts, observations, zone_results, audit_log, notes, sessions, zone_set_versions, zone_sets, media_assets CASCADE;

COMMIT;
