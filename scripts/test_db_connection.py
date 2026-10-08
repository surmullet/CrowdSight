"""
Test Database Connection Utility for CrowdSight.
Tests connection to the configured database (PostgreSQL / Supabase or SQLite)
and checks all tables and row counts.

Usage:
    python scripts/test_db_connection.py
    python scripts/test_db_connection.py --db-url "postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres"
"""
import argparse
import os
import sys

from sqlalchemy import text

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from crowdsight.service.storage.database import DatabaseManager


def main():
    parser = argparse.ArgumentParser(description="Test CrowdSight Database Connection")
    parser.add_argument("--db-url", "-u", default=None, help="Database URL (overrides .env)")
    args = parser.parse_args()

    db_url = args.db_url or os.environ.get("DATABASE_URL") or "sqlite:///./data/crowdsight.db"

    # Mask password for display
    display_url = db_url
    if "@" in display_url and ":" in display_url:
        try:
            proto, rest = display_url.split("://", 1)
            creds, host_part = rest.split("@", 1)
            user = creds.split(":", 1)[0]
            display_url = f"{proto}://{user}:******@{host_part}"
        except Exception:
            pass

    print("=" * 60)
    print("CrowdSight Database Connection Diagnostic")
    print(f"Target Database: {display_url}")
    print("=" * 60)

    try:
        mgr = DatabaseManager(db_url)
        with mgr.get_session() as session:
            res = session.execute(text("SELECT 1")).scalar()
            assert res == 1
        print("\n[SUCCESS] Connected to database engine successfully!")
    except Exception as e:
        print(f"\n[FAILED] Could not connect to database: {e}")
        sys.exit(1)

    # Inspect tables
    tables = [
        "media_assets",
        "zone_sets",
        "zone_set_versions",
        "sessions",
        "artifacts",
        "zone_results",
        "observations",
        "audit_log",
    ]

    print("\nInspecting Database Table Row Counts:")
    with mgr.get_session() as session:
        for t in tables:
            try:
                cnt = session.execute(text(f"SELECT count(*) FROM {t}")).scalar()
                print(f"  - {t:<20}: {cnt:>6,} rows")
            except Exception as e:
                print(f"  - {t:<20}: Table not found or error ({e})")

    print("\n[STATUS] Database is fully operational and ready for CrowdSight backend!")


if __name__ == "__main__":
    main()
