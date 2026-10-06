"""
Optimized Migration Script: Standardize IDs to UUIDs and Add Sequential display_code
- Target: Supabase PostgreSQL & SQLite Database
- Replaces non-UUID strings (session-01-*, media-01-*, audit-0001, zsv-*, zr-*, obs-*)
  with valid standard UUIDs from the original backup or generated deterministic UUIDs.
- Adds `display_code` (MED-0001, SES-0001) to `media_assets` and `sessions`.
- Uses bulk VALUES queries for ultra-fast network execution.
"""
import sys
import os
import re
import uuid
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Force unbuffered output so logs appear instantly
sys.stdout.reconfigure(line_buffering=True)
load_dotenv()

UUID_REGEX = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)

MEDIA_MAP = {
    "media-01-crowd6": "5cc6461b-1cb0-4700-8305-b01c78780785",
    "media-02-150": "4d0e3b31-186f-465f-913a-cab2359bbfa4",
    "media-03-crowd": "966712c6-c1df-4bd1-9347-c191167388d3",
}

ZSV_MAP = {
    "zsv-crowd6-v1": "4a114b09-070d-42a0-bc2e-c08cdbdda2f2",
    "zsv-crowd6-v2": "a874db06-a600-4d64-803a-c4ce693f7925",
    "zsv-crowd6-v3": "a9b9d272-fa64-4649-ae31-27c00482a291",
    "zsv-150-v1": "5d3c8aa3-2fe1-47a0-9b19-9d09794190bc",
    "zsv-150-v2": "4b1a7a3d-b92b-4832-8109-1e40b51f6744",
    "zsv-150-v3": "8658e0b9-f3b0-47ea-9a00-33fd947f6fd9",
    "zsv-150-v4": "e57ae84b-15b8-43e8-b126-34dbf19efadd",
}

SESSION_MAP = {
    "session-01-crowd6": "a914bc97-61a1-4840-ab7d-6c20c78afa0f",
    "session-02-crowd": "c12a71c0-4884-438b-9c2e-2b77613cbd83",
    "session-03-150": "8fe5393f-d235-4420-b072-285d479ec03f",
}

ARTIFACT_MAP = {
    "art-01-crowd6-dataset": "3800e5c4-f923-47aa-b6c4-705d9e23aa39",
    "art-01-crowd6-heatmap": "0c818563-a823-4eb0-82f3-1c89ef70ab50",
    "art-02-crowd-dataset": "aada10a3-fd95-4691-96cc-d368be690fa5",
    "art-02-crowd-heatmap": "c36ecc96-ad95-43b3-89c1-e27c2fba3d9f",
    "art-03-150-dataset": "a44f7fd5-dc3c-41c0-99fa-087ccf768d86",
    "art-03-150-heatmap": "e79476b8-a78e-4bf6-b98e-d7cc7bdac7d6",
}

AUDIT_MAP = {
    "audit-0001": "8ba2197e-3e88-4ee7-ba44-1fee70776834",
}


def load_backup_lookup():
    backup_path = Path("data/crowdsight.db.backup_before_rename")
    obs_lookup = {}
    zr_lookup = {}
    if backup_path.exists():
        print(f"Loading original UUID lookups from backup: {backup_path}")
        con = sqlite3.connect(backup_path)
        cur = con.cursor()
        for row in cur.execute("SELECT session_id, frame_index, id FROM observations"):
            obs_lookup[(row[0], row[1])] = row[2]
        for row in cur.execute("SELECT session_id, frame_index, zone_id, id FROM zone_results"):
            zr_lookup[(row[0], row[1], row[2])] = row[3]
        con.close()
        print(f"Loaded {len(obs_lookup)} obs UUIDs, {len(zr_lookup)} zr UUIDs from backup.")
    return obs_lookup, zr_lookup


def bulk_update_pg(conn, table_name, id_pairs, chunk_size=500):
    """Update IDs in PostgreSQL in large bulk batches using UPDATE ... FROM (VALUES ...)"""
    if not id_pairs:
        return 0
    total = len(id_pairs)
    for i in range(0, total, chunk_size):
        chunk = id_pairs[i:i + chunk_size]
        # Build parameterized values
        val_clauses = []
        params = {}
        for idx, (curr_id, target_uuid) in enumerate(chunk):
            p_old = f"o_{idx}"
            p_new = f"n_{idx}"
            val_clauses.append(f"(:{p_old}, :{p_new})")
            params[p_old] = curr_id
            params[p_new] = target_uuid
        sql = f"""
            UPDATE {table_name} AS t
            SET id = v.new_id
            FROM (VALUES {', '.join(val_clauses)}) AS v(old_id, new_id)
            WHERE t.id = v.old_id;
        """
        conn.execute(text(sql), params)
    return total


def migrate_postgres(obs_lookup, zr_lookup):
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set, skipping PostgreSQL migration.")
        return

    print("\n==================================================")
    print("Migrating PostgreSQL Database (Supabase)...")
    print("==================================================")
    engine = create_engine(db_url)

    with engine.begin() as conn:
        print("1. Adding display_code columns...")
        conn.execute(text("ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS display_code VARCHAR(32);"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_media_assets_display_code ON media_assets(display_code);"))
        conn.execute(text("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS display_code VARCHAR(32);"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_sessions_display_code ON sessions(display_code);"))

        print("2. Disabling foreign key constraints (session_replication_role = replica)...")
        conn.execute(text("SET session_replication_role = 'replica';"))

        print("3. Updating media_assets IDs...")
        for old_id, new_id in MEDIA_MAP.items():
            conn.execute(text("UPDATE media_assets SET id = :new_id WHERE id = :old_id"), {"new_id": new_id, "old_id": old_id})
            conn.execute(text("UPDATE sessions SET media_asset_id = :new_id WHERE media_asset_id = :old_id"), {"new_id": new_id, "old_id": old_id})

        print("4. Updating zone_set_versions IDs...")
        for old_id, new_id in ZSV_MAP.items():
            conn.execute(text("UPDATE zone_set_versions SET id = :new_id WHERE id = :old_id"), {"new_id": new_id, "old_id": old_id})
            conn.execute(text("UPDATE sessions SET zone_set_version_id = :new_id WHERE zone_set_version_id = :old_id"), {"new_id": new_id, "old_id": old_id})

        print("5. Updating sessions IDs and dependent FKs...")
        for old_id, new_id in SESSION_MAP.items():
            conn.execute(text("UPDATE sessions SET id = :new_id WHERE id = :old_id"), {"new_id": new_id, "old_id": old_id})
            conn.execute(text("UPDATE artifacts SET session_id = :new_id WHERE session_id = :old_id"), {"new_id": new_id, "old_id": old_id})
            conn.execute(text("UPDATE observations SET session_id = :new_id WHERE session_id = :old_id"), {"new_id": new_id, "old_id": old_id})
            conn.execute(text("UPDATE zone_results SET session_id = :new_id WHERE session_id = :old_id"), {"new_id": new_id, "old_id": old_id})
            conn.execute(text("UPDATE audit_log SET entity_id = :new_id WHERE entity_id = :old_id"), {"new_id": new_id, "old_id": old_id})

        print("6. Updating artifacts IDs...")
        for old_id, new_id in ARTIFACT_MAP.items():
            conn.execute(text("UPDATE artifacts SET id = :new_id WHERE id = :old_id"), {"new_id": new_id, "old_id": old_id})

        print("7. Updating audit_log IDs...")
        for old_id, new_id in AUDIT_MAP.items():
            conn.execute(text("UPDATE audit_log SET id = :new_id WHERE id = :old_id"), {"new_id": new_id, "old_id": old_id})

        print("8. Updating non-UUID observations (fast bulk batch)...")
        obs_rows = conn.execute(text("SELECT id, session_id, frame_index FROM observations")).fetchall()
        obs_pairs = []
        for r in obs_rows:
            curr_id, s_id, f_idx = r[0], r[1], r[2]
            if not UUID_REGEX.match(curr_id):
                target_uuid = obs_lookup.get((s_id, f_idx))
                if not target_uuid:
                    target_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"crowdsight:obs:{s_id}:{f_idx}"))
                obs_pairs.append((curr_id, target_uuid))
        bulk_update_pg(conn, "observations", obs_pairs)
        print(f"   Updated {len(obs_pairs)} observations to UUIDs.")

        print("9. Updating non-UUID zone_results (fast bulk batch)...")
        zr_rows = conn.execute(text("SELECT id, session_id, frame_index, zone_id FROM zone_results")).fetchall()
        zr_pairs = []
        for r in zr_rows:
            curr_id, s_id, f_idx, z_id = r[0], r[1], r[2], r[3]
            if not UUID_REGEX.match(curr_id):
                target_uuid = zr_lookup.get((s_id, f_idx, z_id))
                if not target_uuid:
                    target_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"crowdsight:zr:{s_id}:{f_idx}:{z_id}"))
                zr_pairs.append((curr_id, target_uuid))
        bulk_update_pg(conn, "zone_results", zr_pairs)
        print(f"   Updated {len(zr_pairs)} zone_results to UUIDs.")

        print("10. Populating display_code for media_assets...")
        media_records = conn.execute(text("SELECT id, display_code, created_at FROM media_assets ORDER BY created_at ASC")).fetchall()
        for idx, m in enumerate(media_records, start=1):
            expected_code = f"MED-{idx:04d}"
            conn.execute(text("UPDATE media_assets SET display_code = :code WHERE id = :id"), {"code": expected_code, "id": m[0]})
        print(f"    Assigned MED-0001..MED-{len(media_records):04d} across {len(media_records)} media assets.")

        print("11. Populating display_code for sessions...")
        session_records = conn.execute(text("SELECT id, display_code, created_at FROM sessions ORDER BY created_at ASC")).fetchall()
        for idx, s in enumerate(session_records, start=1):
            expected_code = f"SES-{idx:04d}"
            conn.execute(text("UPDATE sessions SET display_code = :code WHERE id = :id"), {"code": expected_code, "id": s[0]})
        print(f"    Assigned SES-0001..SES-{len(session_records):04d} across {len(session_records)} sessions.")

        print("12. Re-enabling foreign key constraints (session_replication_role = origin)...")
        conn.execute(text("SET session_replication_role = 'origin';"))

    print("\n[SUCCESS] PostgreSQL Database migration completed successfully!")


def migrate_sqlite(obs_lookup, zr_lookup):
    db_path = Path("data/crowdsight.db")
    if not db_path.exists():
        print(f"SQLite DB {db_path} does not exist, skipping.")
        return

    print("\n==================================================")
    print(f"Migrating SQLite Database ({db_path})...")
    print("==================================================")
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("PRAGMA foreign_keys = OFF;")

    cur.execute("PRAGMA table_info(media_assets)")
    cols = [r[1] for r in cur.fetchall()]
    if "display_code" not in cols:
        cur.execute("ALTER TABLE media_assets ADD COLUMN display_code VARCHAR(32);")

    cur.execute("PRAGMA table_info(sessions)")
    cols = [r[1] for r in cur.fetchall()]
    if "display_code" not in cols:
        cur.execute("ALTER TABLE sessions ADD COLUMN display_code VARCHAR(32);")

    for old_id, new_id in MEDIA_MAP.items():
        cur.execute("UPDATE media_assets SET id = ? WHERE id = ?", (new_id, old_id))
        cur.execute("UPDATE sessions SET media_asset_id = ? WHERE media_asset_id = ?", (new_id, old_id))

    for old_id, new_id in ZSV_MAP.items():
        cur.execute("UPDATE zone_set_versions SET id = ? WHERE id = ?", (new_id, old_id))
        cur.execute("UPDATE sessions SET zone_set_version_id = ? WHERE zone_set_version_id = ?", (new_id, old_id))

    for old_id, new_id in SESSION_MAP.items():
        cur.execute("UPDATE sessions SET id = ? WHERE id = ?", (new_id, old_id))
        cur.execute("UPDATE artifacts SET session_id = ? WHERE session_id = ?", (new_id, old_id))
        cur.execute("UPDATE observations SET session_id = ? WHERE session_id = ?", (new_id, old_id))
        cur.execute("UPDATE zone_results SET session_id = ? WHERE session_id = ?", (new_id, old_id))
        cur.execute("UPDATE audit_log SET entity_id = ? WHERE entity_id = ?", (new_id, old_id))

    for old_id, new_id in ARTIFACT_MAP.items():
        cur.execute("UPDATE artifacts SET id = ? WHERE id = ?", (new_id, old_id))

    for old_id, new_id in AUDIT_MAP.items():
        cur.execute("UPDATE audit_log SET id = ? WHERE id = ?", (new_id, old_id))

    cur.execute("SELECT id, session_id, frame_index FROM observations")
    obs_batch = []
    for curr_id, s_id, f_idx in cur.fetchall():
        if not UUID_REGEX.match(curr_id):
            target_uuid = obs_lookup.get((s_id, f_idx)) or str(uuid.uuid5(uuid.NAMESPACE_DNS, f"crowdsight:obs:{s_id}:{f_idx}"))
            obs_batch.append((target_uuid, curr_id))
    if obs_batch:
        cur.executemany("UPDATE observations SET id = ? WHERE id = ?", obs_batch)
    print(f"Updated {len(obs_batch)} SQLite observations.")

    cur.execute("SELECT id, session_id, frame_index, zone_id FROM zone_results")
    zr_batch = []
    for curr_id, s_id, f_idx, z_id in cur.fetchall():
        if not UUID_REGEX.match(curr_id):
            target_uuid = zr_lookup.get((s_id, f_idx, z_id)) or str(uuid.uuid5(uuid.NAMESPACE_DNS, f"crowdsight:zr:{s_id}:{f_idx}:{z_id}"))
            zr_batch.append((target_uuid, curr_id))
    if zr_batch:
        cur.executemany("UPDATE zone_results SET id = ? WHERE id = ?", zr_batch)
    print(f"Updated {len(zr_batch)} SQLite zone_results.")

    cur.execute("SELECT id, created_at FROM media_assets ORDER BY created_at ASC")
    for idx, (m_id, _) in enumerate(cur.fetchall(), start=1):
        cur.execute("UPDATE media_assets SET display_code = ? WHERE id = ?", (f"MED-{idx:04d}", m_id))

    cur.execute("SELECT id, created_at FROM sessions ORDER BY created_at ASC")
    for idx, (s_id, _) in enumerate(cur.fetchall(), start=1):
        cur.execute("UPDATE sessions SET display_code = ? WHERE id = ?", (f"SES-{idx:04d}", s_id))

    con.commit()
    con.close()
    print("[SUCCESS] SQLite Database migration completed successfully!")


if __name__ == "__main__":
    obs_lookup, zr_lookup = load_backup_lookup()
    migrate_postgres(obs_lookup, zr_lookup)
    migrate_sqlite(obs_lookup, zr_lookup)
