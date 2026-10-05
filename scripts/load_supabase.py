"""
Automated Seed Loader for Supabase / PostgreSQL.
Allows one-command migration of all CrowdSight seed data into Supabase
without manually copying and pasting dozens of SQL chunks.

Usage:
    python scripts/load_supabase.py --db-url "postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres"

Or simply run without arguments to be prompted for the connection URL:
    python scripts/load_supabase.py
"""
import os
import sys
import glob
import time
import argparse

try:
    import psycopg2
except ImportError:
    print("Error: psycopg2 is not installed. Please run: pip install psycopg2-binary")
    sys.exit(1)


def load_file(cursor, filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        sql = f.read()
    cursor.execute(sql)


def main():
    parser = argparse.ArgumentParser(description="Load CrowdSight seed data directly into Supabase PostgreSQL")
    parser.add_argument("--db-url", "-u", default=None, help="PostgreSQL connection string (URI)")
    parser.add_argument("--clean", action="store_true", help="Truncate all tables first to remove old UUID data")
    parser.add_argument("--fast-sample-only", action="store_true", help="Only load core, zone_results, and sample observations")
    args = parser.parse_args()

    db_url = args.db_url
    if not db_url:
        print("=" * 60)
        print("CrowdSight Supabase Direct Seed Loader")
        print("=" * 60)
        print("You can find your connection string in Supabase Dashboard:")
        print("  Project Settings -> Database -> Connection string -> URI")
        print("  Format: postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres")
        print("-" * 60)
        try:
            db_url = input("Enter Supabase Database URI: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(0)

    if not db_url:
        print("Error: No database URL provided.")
        sys.exit(1)

    print(f"\n[1/3] Connecting to Supabase...")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        print("  -> Connected successfully!")
    except Exception as e:
        print(f"  -> Connection failed: {e}")
        sys.exit(1)

    seed_dir = "supabase_seeds"
    if not os.path.exists(seed_dir):
        print(f"Error: {seed_dir} directory not found. Please run scripts/split_supabase_seed.py first.")
        sys.exit(1)

    p0 = os.path.join(seed_dir, "00_clean_database.sql")
    p1 = os.path.join(seed_dir, "01_core_metadata.sql")
    p2 = os.path.join(seed_dir, "02_zone_results.sql")
    p3_sample = os.path.join(seed_dir, "03_observations_sample_crowd6.sql")
    obs_dir = os.path.join(seed_dir, "observations")

    if args.clean and os.path.exists(p0):
        print(f"\n[CLEANUP] Truncating existing tables...")
        load_file(cur, p0)
        print("  -> Existing tables truncated successfully.")

    print("\n[2/3] Seeding Core Data (Clean Sequential IDs)...")
    t0 = time.time()
    
    print(f"  Executing {os.path.basename(p1)}...")
    load_file(cur, p1)
    print("  -> Core metadata loaded (media_assets, zone_sets, sessions, artifacts, audit_log).")

    print(f"  Executing {os.path.basename(p2)}...")
    load_file(cur, p2)
    print("  -> Zone results loaded (4,468 rows).")

    if args.fast_sample_only:
        print(f"  Executing {os.path.basename(p3_sample)} (Fast-track sample)...")
        load_file(cur, p3_sample)
        print("  -> Sample observations loaded.")
    else:
        obs_files = sorted(glob.glob(os.path.join(obs_dir, "obs_part_*.sql")))
        total_obs = len(obs_files)
        print(f"\n[3/3] Seeding Observations ({total_obs} parts, 2,234 frames)...")
        for idx, obs_path in enumerate(obs_files, start=1):
            name = os.path.basename(obs_path)
            t_start = time.time()
            load_file(cur, obs_path)
            dur = time.time() - t_start
            pct = (idx / total_obs) * 100
            print(f"  [{idx:02d}/{total_obs:02d}] ({pct:5.1f}%) {name} ({dur:.2f}s)")

    total_time = time.time() - t0
    print(f"\n[COMPLETED] All seed data loaded successfully in {total_time:.1f} seconds!")

    # Verify counts
    print("\nVerifying database table counts:")
    tables = ["media_assets", "zone_sets", "zone_set_versions", "sessions", "zone_results", "observations", "artifacts"]
    for t in tables:
        cur.execute(f"SELECT count(*) FROM {t}")
        cnt = cur.fetchone()[0]
        print(f"  - {t:<20}: {cnt:,} rows")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
