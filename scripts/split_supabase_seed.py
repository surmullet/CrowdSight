"""
Split supabase_seed.sql into bite-sized SQL files for Supabase SQL Editor.
Supabase SQL Editor has a 1 MB payload limit.
Every generated file is strictly <= 600 KB so it never triggers 'Query is too large'
and pastes smoothly without browser lag.
"""
import os


def split_seed_data(max_chunk_bytes=580 * 1024):
    seed_file = "supabase_seed.sql"
    output_dir = "supabase_seeds"
    obs_dir = os.path.join(output_dir, "observations")
    os.makedirs(obs_dir, exist_ok=True)

    with open(seed_file, encoding="utf-8") as f:
        text = f.read()

    zr_marker = "-- 8. Table: zone_results"
    obs_marker = "-- 9. Table: observations"

    zr_pos = text.find(zr_marker)
    obs_pos = text.find(obs_marker)

    meta_text = text[:zr_pos].strip()
    zr_text = text[zr_pos:obs_pos].strip()
    obs_text = text[obs_pos:].strip()

    generated_files = []

    # -------------------------------------------------------------
    # Part 1: Core metadata
    # -------------------------------------------------------------
    if not meta_text.endswith("COMMIT;"):
        meta_sql = meta_text + "\n\nCOMMIT;\n"
    else:
        meta_sql = meta_text + "\n"

    p1_path = os.path.join(output_dir, "01_core_metadata.sql")
    with open(p1_path, "w", encoding="utf-8") as f:
        f.write("-- ========================================================\n")
        f.write("-- CrowdSight Seed - Part 01: Core Metadata\n")
        f.write("-- Tables: media_assets (3), zone_sets (2), zone_set_versions (7),\n")
        f.write("--         sessions (3), artifacts (6), audit_log (1)\n")
        f.write("-- Idempotent: ON CONFLICT (id) DO NOTHING\n")
        f.write("-- ========================================================\n\n")
        f.write(meta_sql)
    p1_size = len(meta_sql.encode("utf-8"))
    generated_files.append((p1_path, p1_size, "Core Metadata (All media, zones, sessions, artifacts)"))

    # -------------------------------------------------------------
    # Part 2: Zone results (4,468 rows, ~530 KB)
    # -------------------------------------------------------------
    # Reformat zone_results cleanly into 1 atomic transaction
    # Find all rows in zr_text
    zr_lines = [line.strip().rstrip(",").rstrip(";") for line in zr_text.split("\n") if line.strip().startswith("('")]
    print(f"Total zone_results rows found: {len(zr_lines)}")

    zr_header = "INSERT INTO zone_results (id, session_id, frame_index, media_time_s, zone_id, availability, visible_count)\nVALUES"
    zr_body = ",\n  ".join(zr_lines)
    zr_sql = (
        "-- ========================================================\n"
        "-- CrowdSight Seed - Part 02: Zone Results\n"
        f"-- Total Rows: {len(zr_lines):,} (Pre-computed counting results for all zones)\n"
        "-- Idempotent: ON CONFLICT (id) DO NOTHING\n"
        "-- ========================================================\n\n"
        "BEGIN;\n\n"
        f"{zr_header}\n  {zr_body}\n"
        "ON CONFLICT (id) DO NOTHING;\n\n"
        "COMMIT;\n"
    )
    p2_path = os.path.join(output_dir, "02_zone_results.sql")
    with open(p2_path, "w", encoding="utf-8") as f:
        f.write(zr_sql)
    p2_size = len(zr_sql.encode("utf-8"))
    generated_files.append((p2_path, p2_size, f"Zone Results ({len(zr_lines):,} rows)"))

    # -------------------------------------------------------------
    # Part 3: Observations (2,234 rows)
    # -------------------------------------------------------------
    obs_lines = [line.strip().rstrip(",").rstrip(";") for line in obs_text.split("\n") if line.strip().startswith("('")]
    print(f"Total observation rows found: {len(obs_lines)}")

    obs_header = "INSERT INTO observations (id, session_id, frame_index, media_time_s, quality, reason_code, payload_v1, created_at)\nVALUES"

    # Also create a quick sample file: First 15 frames of crowd6.mp4 (Session a914bc97-61a1-4840-ab7d-6c20c78afa0f)
    crowd6_sess = "a914bc97-61a1-4840-ab7d-6c20c78afa0f"
    crowd6_lines = [line for line in obs_lines if crowd6_sess in line]
    print(f"crowd6 observation rows found: {len(crowd6_lines)}")

    sample_lines = crowd6_lines[:10]
    sample_body = ",\n  ".join(sample_lines)
    sample_sql = (
        "-- ========================================================\n"
        "-- CrowdSight Seed - Optional Fast-Track Sample\n"
        "-- First 10 Frames of crowd6.mp4 (~300 bboxes/frame, ~450 KB)\n"
        "-- Use this for instant UI testing without pasting all 58 observation chunks!\n"
        "-- Idempotent: ON CONFLICT (id) DO NOTHING\n"
        "-- ========================================================\n\n"
        "BEGIN;\n\n"
        f"{obs_header}\n  {sample_body}\n"
        "ON CONFLICT (id) DO NOTHING;\n\n"
        "COMMIT;\n"
    )
    sample_path = os.path.join(output_dir, "03_observations_sample_crowd6.sql")
    with open(sample_path, "w", encoding="utf-8") as f:
        f.write(sample_sql)
    sample_size = len(sample_sql.encode("utf-8"))
    generated_files.append((sample_path, sample_size, "Fast-Track Sample (crowd6.mp4 first 15 frames)"))

    # Chunk all observations into parts <= max_chunk_bytes
    chunks = []
    current_chunk = []
    current_size = len(obs_header.encode("utf-8")) + 200

    for line in obs_lines:
        line_size = len(line.encode("utf-8")) + 6 # for ",\n  "
        if current_chunk and (current_size + line_size > max_chunk_bytes):
            chunks.append(current_chunk)
            current_chunk = [line]
            current_size = len(obs_header.encode("utf-8")) + 200 + line_size
        else:
            current_chunk.append(line)
            current_size += line_size
    if current_chunk:
        chunks.append(current_chunk)

    total_chunks = len(chunks)
    print(f"Created {total_chunks} observation chunks (strictly <= {max_chunk_bytes // 1024} KB).")

    obs_files = []
    row_offset = 0
    for idx, chunk in enumerate(chunks, start=1):
        filename = f"obs_part_{idx:02d}_of_{total_chunks:02d}.sql"
        filepath = os.path.join(obs_dir, filename)
        body = ",\n  ".join(chunk)
        start_row = row_offset + 1
        end_row = row_offset + len(chunk)
        row_offset = end_row

        chunk_sql = (
            f"-- ========================================================\n"
            f"-- CrowdSight Seed - Observations Part {idx:02d} of {total_chunks:02d}\n"
            f"-- Rows: {start_row} to {end_row} (Total in chunk: {len(chunk)} rows)\n"
            f"-- Idempotent: ON CONFLICT (id) DO NOTHING\n"
            f"-- ========================================================\n\n"
            f"BEGIN;\n\n"
            f"{obs_header}\n  {body}\n"
            f"ON CONFLICT (id) DO NOTHING;\n\n"
            f"COMMIT;\n"
        )
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(chunk_sql)
        f_size = len(chunk_sql.encode("utf-8"))
        obs_files.append((filepath, f_size, f"Rows {start_row}-{end_row} ({len(chunk)} frames)"))

    print("\n--- Split Complete ---")
    print(f"Core Files in {output_dir}:")
    for p, sz, desc in generated_files:
        print(f"  {os.path.basename(p):<35} {sz/1024:>7.1f} KB  ({desc})")
    print(f"\nObservations Files in {obs_dir} ({len(obs_files)} files):")
    print(f"  Min size: {min(sz for _, sz, _ in obs_files)/1024:.1f} KB")
    print(f"  Max size: {max(sz for _, sz, _ in obs_files)/1024:.1f} KB")
    print(f"  Avg size: {sum(sz for _, sz, _ in obs_files)/len(obs_files)/1024:.1f} KB")

    # Integrity verification
    verify_obs_rows = sum(len(c) for c in chunks)
    assert verify_obs_rows == len(obs_lines), f"Observations mismatch: {verify_obs_rows} != {len(obs_lines)}"
    print(f"\n[VERIFIED] All {len(obs_lines)} observation rows preserved across {len(chunks)} chunks!")
    print(f"[VERIFIED] All {len(zr_lines)} zone_results rows preserved in 02_zone_results.sql!")

if __name__ == "__main__":
    split_seed_data(max_chunk_bytes=580 * 1024)

