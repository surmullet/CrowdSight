"""
Clean and Rename IDs across CrowdSight SQLite Database and Supabase Seeds.
Replaces ugly random UUIDs with clear, sequential, human-readable IDs:
  - media_assets:       media-01-crowd6, media-02-150, media-03-crowd
  - zone_sets:          zones-crowd6, zones-150
  - zone_set_versions:  zsv-crowd6-v1..v3, zsv-150-v1..v4
  - sessions:           session-01-crowd6, session-02-crowd, session-03-150
  - artifacts:          art-01-crowd6-dataset, art-01-crowd6-heatmap, etc.
  - observations:       obs-crowd6-f0000..f0627, obs-crowd-f0000..f0169, obs-150-f0000..f1435
  - zone_results:       zr-00001 .. zr-04468
  - audit_log:          audit-0001
"""
import os
import re
import json
import sqlite3
import shutil

MEDIA_MAP = {
    "5cc6461b-1cb0-4700-8305-b01c78780785": "media-01-crowd6",
    "4d0e3b31-186f-465f-913a-cab2359bbfa4": "media-02-150",
    "966712c6-c1df-4bd1-9347-c191167388d3": "media-03-crowd",
}

ZONE_SET_MAP = {
    "zones-5cc6461b-1cb0-4700-8305-b01c78780785": "zones-crowd6",
    "zones-150-real": "zones-150",
}

ZSV_MAP = {
    "4a114b09-070d-42a0-bc2e-c08cdbdda2f2": "zsv-crowd6-v1",
    "a874db06-a600-4d64-803a-c4ce693f7925": "zsv-crowd6-v2",
    "a9b9d272-fa64-4649-ae31-27c00482a291": "zsv-crowd6-v3",
    "5d3c8aa3-2fe1-47a0-9b19-9d09794190bc": "zsv-150-v1",
    "4b1a7a3d-b92b-4832-8109-1e40b51f6744": "zsv-150-v2",
    "8658e0b9-f3b0-47ea-9a00-33fd947f6fd9": "zsv-150-v3",
    "e57ae84b-15b8-43e8-b126-34dbf19efadd": "zsv-150-v4",
}

SESSION_MAP = {
    "a914bc97-61a1-4840-ab7d-6c20c78afa0f": "session-01-crowd6",
    "c12a71c0-4884-438b-9c2e-2b77613cbd83": "session-02-crowd",
    "8fe5393f-d235-4420-b072-285d479ec03f": "session-03-150",
}

SESSION_SHORT_NAMES = {
    "session-01-crowd6": "crowd6",
    "session-02-crowd": "crowd",
    "session-03-150": "150",
}

ARTIFACT_MAP = {
    "3800e5c4-f923-47aa-b6c4-705d9e23aa39": "art-01-crowd6-dataset",
    "0c818563-a823-4eb0-82f3-1c89ef70ab50": "art-01-crowd6-heatmap",
    "aada10a3-fd95-4691-96cc-d368be690fa5": "art-02-crowd-dataset",
    "c36ecc96-ad95-43b3-89c1-e27c2fba3d9f": "art-02-crowd-heatmap",
    "a44f7fd5-dc3c-41c0-99fa-087ccf768d86": "art-03-150-dataset",
    "e79476b8-a78e-4bf6-b98e-d7cc7bdac7d6": "art-03-150-heatmap",
}

AUDIT_MAP = {
    "8ba2197e-3e88-4ee7-ba44-1fee70776834": "audit-0001",
}


def update_sqlite(db_path="data/crowdsight.db"):
    print(f"\n--- Updating SQLite Database: {db_path} ---")
    shutil.copy2(db_path, db_path + ".backup_before_rename")
    print(f"Created backup: {db_path}.backup_before_rename")

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("PRAGMA foreign_keys = OFF;")

    # 1. media_assets
    for old_id, new_id in MEDIA_MAP.items():
        cur.execute("UPDATE media_assets SET id = ? WHERE id = ?", (new_id, old_id))
    print(f"Updated media_assets: {len(MEDIA_MAP)} rows")

    # 2. zone_sets
    for old_id, new_id in ZONE_SET_MAP.items():
        cur.execute("UPDATE zone_sets SET id = ? WHERE id = ?", (new_id, old_id))
    print(f"Updated zone_sets: {len(ZONE_SET_MAP)} rows")

    # 3. zone_set_versions
    for old_id, new_id in ZSV_MAP.items():
        cur.execute("UPDATE zone_set_versions SET id = ? WHERE id = ?", (new_id, old_id))
    for old_zs, new_zs in ZONE_SET_MAP.items():
        cur.execute("UPDATE zone_set_versions SET zone_set_id = ? WHERE zone_set_id = ?", (new_zs, old_zs))
    print(f"Updated zone_set_versions: {len(ZSV_MAP)} rows")

    # 4. sessions
    for old_id, new_id in SESSION_MAP.items():
        cur.execute("UPDATE sessions SET id = ? WHERE id = ?", (new_id, old_id))
    for old_m, new_m in MEDIA_MAP.items():
        cur.execute("UPDATE sessions SET media_asset_id = ? WHERE media_asset_id = ?", (new_m, old_m))
    for old_zsv, new_zsv in ZSV_MAP.items():
        cur.execute("UPDATE sessions SET zone_set_version_id = ? WHERE zone_set_version_id = ?", (new_zsv, old_zsv))
    print(f"Updated sessions: {len(SESSION_MAP)} rows")

    # 5. artifacts
    for old_id, new_id in ARTIFACT_MAP.items():
        cur.execute("UPDATE artifacts SET id = ? WHERE id = ?", (new_id, old_id))
    for old_sess, new_sess in SESSION_MAP.items():
        cur.execute("UPDATE artifacts SET session_id = ? WHERE session_id = ?", (new_sess, old_sess))
    print(f"Updated artifacts: {len(ARTIFACT_MAP)} rows")

    # 6. audit_log
    for old_id, new_id in AUDIT_MAP.items():
        cur.execute("UPDATE audit_log SET id = ? WHERE id = ?", (new_id, old_id))
    print(f"Updated audit_log: {len(AUDIT_MAP)} rows")

    # 7. observations
    cur.execute("SELECT id, session_id, frame_index, payload_v1 FROM observations ORDER BY session_id, frame_index")
    obs_rows = cur.fetchall()
    print(f"Processing {len(obs_rows)} observations in SQLite...")
    for old_id, sess_id, f_idx, payload in obs_rows:
        new_sess_id = SESSION_MAP.get(sess_id, sess_id)
        short_name = SESSION_SHORT_NAMES.get(new_sess_id, "frame")
        new_obs_id = f"obs-{short_name}-f{f_idx:04d}"

        # update payload session_id if present
        if payload and isinstance(payload, str) and sess_id in payload:
            payload = payload.replace(sess_id, new_sess_id)

        cur.execute(
            "UPDATE observations SET id = ?, session_id = ?, payload_v1 = ? WHERE id = ?",
            (new_obs_id, new_sess_id, payload, old_id),
        )
    print(f"Updated {len(obs_rows)} observations with clean IDs!")

    # 8. zone_results
    cur.execute("SELECT id, session_id FROM zone_results ORDER BY session_id, frame_index, zone_id")
    zr_rows = cur.fetchall()
    print(f"Processing {len(zr_rows)} zone_results in SQLite...")
    for idx, (old_id, sess_id) in enumerate(zr_rows, start=1):
        new_sess_id = SESSION_MAP.get(sess_id, sess_id)
        new_zr_id = f"zr-{idx:05d}"
        cur.execute(
            "UPDATE zone_results SET id = ?, session_id = ? WHERE id = ?",
            (new_zr_id, new_sess_id, old_id),
        )
    print(f"Updated {len(zr_rows)} zone_results with clean IDs!")

    con.commit()
    cur.execute("PRAGMA foreign_keys = ON;")
    con.close()
    print("SQLite update complete and committed!")


def generate_clean_sql_seeds():
    print("\n--- Generating Clean SQL Seeds from SQLite ---")
    con = sqlite3.connect("data/crowdsight.db")
    cur = con.cursor()

    output_dir = "supabase_seeds"
    obs_dir = os.path.join(output_dir, "observations")
    os.makedirs(obs_dir, exist_ok=True)

    # 00_clean_database.sql
    clean_sql = (
        "-- ========================================================\n"
        "-- CrowdSight Database Reset / Cleanup Script\n"
        "-- Run this first if you want to clear old random UUIDs\n"
        "-- ========================================================\n"
        "BEGIN;\n\n"
        "TRUNCATE TABLE artifacts, observations, zone_results, audit_log, notes, sessions, zone_set_versions, zone_sets, media_assets CASCADE;\n\n"
        "COMMIT;\n"
    )
    with open(os.path.join(output_dir, "00_clean_database.sql"), "w", encoding="utf-8") as f:
        f.write(clean_sql)

    # 01_core_metadata.sql
    # 1. media_assets
    cur.execute("SELECT id, display_name, relpath, sha256, duration_s, fps, frame_count, width, height, codec, browser_playable, proxy_relpath, created_at FROM media_assets ORDER BY id")
    media_rows = cur.fetchall()
    media_vals = []
    for r in media_rows:
        bplay = "true" if r[10] else "false"
        proxy = f"'{r[11]}'" if r[11] else "NULL"
        media_vals.append(f"  ('{r[0]}', '{r[1]}', '{r[2]}', '{r[3]}', {r[4]}, {r[5]}, {r[6]}, {r[7]}, {r[8]}, '{r[9]}', {bplay}, {proxy}, '{r[12]}')")

    # 2. zone_sets
    cur.execute("SELECT id, name, created_at FROM zone_sets ORDER BY id")
    zs_rows = cur.fetchall()
    zs_vals = [f"  ('{r[0]}', '{r[1]}', '{r[2]}')" for r in zs_rows]

    # 3. zone_set_versions
    cur.execute("SELECT id, zone_set_id, version, image_width, image_height, polygon_data, sha256, created_at FROM zone_set_versions ORDER BY zone_set_id, version")
    zsv_rows = cur.fetchall()
    zsv_vals = []
    for r in zsv_rows:
        poly_str = r[5].replace("'", "''")
        zsv_vals.append(f"  ('{r[0]}', '{r[1]}', {r[2]}, {r[3]}, {r[4]}, '{poly_str}'::jsonb, '{r[6]}', '{r[7]}')")

    # 4. sessions
    cur.execute("SELECT id, media_asset_id, zone_set_version_id, model_profile_id, model_profile_sha256, checkpoint_sha256, tracker_config_sha256, options, status, progress, processed_frames, total_frames, error_code, user_action_hint, applicability_snapshot, synthetic, completeness, created_at, updated_at FROM sessions ORDER BY id")
    sess_rows = cur.fetchall()
    sess_vals = []
    for r in sess_rows:
        opts_str = (r[7] or "{}").replace("'", "''")
        err_str = f"'{r[12]}'" if r[12] else "NULL"
        hint_str = f"'{r[13]}'" if r[13] else "NULL"
        app_str = (r[14] or "{}").replace("'", "''")
        syn_str = "true" if r[15] else "false"
        sess_vals.append(f"  ('{r[0]}', '{r[1]}', '{r[2]}', '{r[3]}', '{r[4]}', '{r[5]}', '{r[6]}', '{opts_str}'::jsonb, '{r[8]}', {r[9]}, {r[10]}, {r[11]}, {err_str}, {hint_str}, '{app_str}'::jsonb, {syn_str}, '{r[16]}', '{r[17]}', '{r[18]}')")

    # 5. artifacts
    cur.execute("SELECT id, session_id, kind, relpath, sha256, created_at, expires_at FROM artifacts ORDER BY session_id, kind")
    art_rows = cur.fetchall()
    art_vals = []
    for r in art_rows:
        exp_str = f"'{r[6]}'" if r[6] else "NULL"
        art_vals.append(f"  ('{r[0]}', '{r[1]}', '{r[2]}', '{r[3]}', '{r[4]}', '{r[5]}', {exp_str})")

    # 6. audit_log
    cur.execute("SELECT id, action, entity_type, entity_id, details, timestamp FROM audit_log ORDER BY id")
    audit_rows = cur.fetchall()
    audit_vals = []
    for r in audit_rows:
        det_str = (r[4] or "{}").replace("'", "''")
        audit_vals.append(f"  ('{r[0]}', '{r[1]}', '{r[2]}', '{r[3]}', '{det_str}'::jsonb, '{r[5]}')")

    core_sql = (
        "-- ========================================================\n"
        "-- CrowdSight Seed - Part 01: Core Metadata (Clean & Sequential IDs)\n"
        "-- Tables: media_assets (3), zone_sets (2), zone_set_versions (7),\n"
        "--         sessions (3), artifacts (6), audit_log (1)\n"
        "-- Idempotent: ON CONFLICT (id) DO NOTHING\n"
        "-- ========================================================\n\n"
        "BEGIN;\n\n"
        "-- 1. Table: media_assets\n"
        "INSERT INTO media_assets (id, display_name, relpath, sha256, duration_s, fps, frame_count, width, height, codec, browser_playable, proxy_relpath, created_at)\n"
        "VALUES\n" + ",\n".join(media_vals) + "\nON CONFLICT (id) DO NOTHING;\n\n"
        "-- 2. Table: zone_sets\n"
        "INSERT INTO zone_sets (id, name, created_at)\n"
        "VALUES\n" + ",\n".join(zs_vals) + "\nON CONFLICT (id) DO NOTHING;\n\n"
        "-- 3. Table: zone_set_versions\n"
        "INSERT INTO zone_set_versions (id, zone_set_id, version, image_width, image_height, polygon_data, sha256, created_at)\n"
        "VALUES\n" + ",\n".join(zsv_vals) + "\nON CONFLICT (id) DO NOTHING;\n\n"
        "-- 4. Table: sessions\n"
        "INSERT INTO sessions (id, media_asset_id, zone_set_version_id, model_profile_id, model_profile_sha256, checkpoint_sha256, tracker_config_sha256, options, status, progress, processed_frames, total_frames, error_code, user_action_hint, applicability_snapshot, synthetic, completeness, created_at, updated_at)\n"
        "VALUES\n" + ",\n".join(sess_vals) + "\nON CONFLICT (id) DO NOTHING;\n\n"
        "-- 5. Table: artifacts\n"
        "INSERT INTO artifacts (id, session_id, kind, relpath, sha256, created_at, expires_at)\n"
        "VALUES\n" + ",\n".join(art_vals) + "\nON CONFLICT (id) DO NOTHING;\n\n"
        "-- 6. Table: audit_log\n"
        "INSERT INTO audit_log (id, action, entity_type, entity_id, details, timestamp)\n"
        "VALUES\n" + ",\n".join(audit_vals) + "\nON CONFLICT (id) DO NOTHING;\n\n"
        "COMMIT;\n"
    )
    with open(os.path.join(output_dir, "01_core_metadata.sql"), "w", encoding="utf-8") as f:
        f.write(core_sql)
    print("Generated 01_core_metadata.sql")

    # 02_zone_results.sql
    cur.execute("SELECT id, session_id, frame_index, media_time_s, zone_id, availability, visible_count FROM zone_results ORDER BY id")
    zr_rows = cur.fetchall()
    zr_vals = []
    for r in zr_rows:
        cnt_str = str(r[6]) if r[6] is not None else "NULL"
        zr_vals.append(f"  ('{r[0]}', '{r[1]}', {r[2]}, {r[3]}, '{r[4]}', '{r[5]}', {cnt_str})")

    zr_sql = (
        "-- ========================================================\n"
        "-- CrowdSight Seed - Part 02: Zone Results (Clean IDs: zr-00001 .. zr-04468)\n"
        f"-- Total Rows: {len(zr_rows):,}\n"
        "-- Idempotent: ON CONFLICT (id) DO NOTHING\n"
        "-- ========================================================\n\n"
        "BEGIN;\n\n"
        "INSERT INTO zone_results (id, session_id, frame_index, media_time_s, zone_id, availability, visible_count)\n"
        "VALUES\n" + ",\n".join(zr_vals) + "\nON CONFLICT (id) DO NOTHING;\n\n"
        "COMMIT;\n"
    )
    with open(os.path.join(output_dir, "02_zone_results.sql"), "w", encoding="utf-8") as f:
        f.write(zr_sql)
    print("Generated 02_zone_results.sql")

    # 03_observations_sample_crowd6.sql
    cur.execute("SELECT id, session_id, frame_index, media_time_s, quality, reason_code, payload_v1, created_at FROM observations WHERE session_id = 'session-01-crowd6' ORDER BY frame_index LIMIT 10")
    sample_obs = cur.fetchall()
    sample_vals = []
    for r in sample_obs:
        code_str = f"'{r[5]}'" if r[5] else "NULL"
        pay_str = r[6].replace("'", "''")
        sample_vals.append(f"  ('{r[0]}', '{r[1]}', {r[2]}, {r[3]}, '{r[4]}', {code_str}, '{pay_str}'::jsonb, '{r[7]}')")

    sample_sql = (
        "-- ========================================================\n"
        "-- CrowdSight Seed - Optional Fast-Track Sample (Clean IDs: obs-crowd6-f0000 .. f0009)\n"
        "-- First 10 Frames of crowd6.mp4 (~300 bboxes/frame, ~450 KB)\n"
        "-- Use this for instant UI testing without pasting all 59 observation chunks!\n"
        "-- Idempotent: ON CONFLICT (id) DO NOTHING\n"
        "-- ========================================================\n\n"
        "BEGIN;\n\n"
        "INSERT INTO observations (id, session_id, frame_index, media_time_s, quality, reason_code, payload_v1, created_at)\n"
        "VALUES\n" + ",\n".join(sample_vals) + "\nON CONFLICT (id) DO NOTHING;\n\n"
        "COMMIT;\n"
    )
    with open(os.path.join(output_dir, "03_observations_sample_crowd6.sql"), "w", encoding="utf-8") as f:
        f.write(sample_sql)
    print("Generated 03_observations_sample_crowd6.sql")

    # All Observations in chunks <= 580 KB
    cur.execute("SELECT id, session_id, frame_index, media_time_s, quality, reason_code, payload_v1, created_at FROM observations ORDER BY session_id, frame_index")
    all_obs = cur.fetchall()
    print(f"Total observations to chunk: {len(all_obs)}")

    obs_header = "INSERT INTO observations (id, session_id, frame_index, media_time_s, quality, reason_code, payload_v1, created_at)\nVALUES"
    max_chunk_bytes = 580 * 1024

    obs_chunks = []
    curr_chunk = []
    curr_size = len(obs_header.encode("utf-8")) + 200

    for r in all_obs:
        code_str = f"'{r[5]}'" if r[5] else "NULL"
        pay_str = r[6].replace("'", "''")
        line = f"  ('{r[0]}', '{r[1]}', {r[2]}, {r[3]}, '{r[4]}', {code_str}, '{pay_str}'::jsonb, '{r[7]}')"
        line_size = len(line.encode("utf-8")) + 4
        if curr_chunk and (curr_size + line_size > max_chunk_bytes):
            obs_chunks.append(curr_chunk)
            curr_chunk = [line]
            curr_size = len(obs_header.encode("utf-8")) + 200 + line_size
        else:
            curr_chunk.append(line)
            curr_size += line_size
    if curr_chunk:
        obs_chunks.append(curr_chunk)

    total_chunks = len(obs_chunks)
    row_offset = 0
    for idx, chunk in enumerate(obs_chunks, start=1):
        filename = f"obs_part_{idx:02d}_of_{total_chunks:02d}.sql"
        filepath = os.path.join(obs_dir, filename)
        start_row = row_offset + 1
        end_row = row_offset + len(chunk)
        row_offset = end_row

        chunk_sql = (
            f"-- ========================================================\n"
            f"-- CrowdSight Seed - Observations Part {idx:02d} of {total_chunks:02d} (Clean IDs)\n"
            f"-- Rows: {start_row} to {end_row} (Total in chunk: {len(chunk)} rows)\n"
            f"-- Idempotent: ON CONFLICT (id) DO NOTHING\n"
            f"-- ========================================================\n\n"
            f"BEGIN;\n\n"
            f"{obs_header}\n" + ",\n".join(chunk) + "\n"
            f"ON CONFLICT (id) DO NOTHING;\n\n"
            f"COMMIT;\n"
        )
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(chunk_sql)

    print(f"Generated {total_chunks} observation chunk files in {obs_dir}!")

    # Also update full monolithic supabase_seed.sql
    full_seed_path = "supabase_seed.sql"
    with open(full_seed_path, "w", encoding="utf-8") as f:
        f.write("-- CrowdSight Full Seed Migration Script with Clean Sequential IDs\n")
        f.write(core_sql)
        f.write("\n\n" + zr_sql)
        for chunk in obs_chunks:
            f.write(f"\n\nBEGIN;\n{obs_header}\n" + ",\n".join(chunk) + "\nON CONFLICT (id) DO NOTHING;\nCOMMIT;\n")
    print(f"Updated full {full_seed_path} ({os.path.getsize(full_seed_path)/1024/1024:.2f} MB)")

    con.close()


if __name__ == "__main__":
    update_sqlite()
    generate_clean_sql_seeds()
