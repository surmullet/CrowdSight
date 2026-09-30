"""Command-line interface for CrowdSight administration and operations."""
from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, select

from crowdsight.service.artifacts.store import ArtifactStore
from crowdsight.service.jobs.runner import JobManager
from crowdsight.service.pipeline.model_boundary import ModelBoundaryService
from crowdsight.service.storage.database import DatabaseManager
from crowdsight.service.storage.media_registry import SUPPORTED_EXTENSIONS, MediaRegistry
from crowdsight.service.storage.models import (
    ArtifactRecord,
    AuditLogRecord,
    ObservationRecord,
    SessionRecord,
    ZoneResultRecord,
)


def _get_services(
    db_path: Path | None = None,
    media_dir: Path | None = None,
    artifact_dir: Path | None = None,
) -> tuple[DatabaseManager, MediaRegistry, ArtifactStore, JobManager]:
    data_dir = Path(os.environ.get("CROWDSIGHT_DATA_DIR", "./data")).resolve()
    db_file = db_path or (data_dir / "crowdsight.db")
    media_root = media_dir or (data_dir / "media")
    art_root = artifact_dir or (data_dir / "artifacts")

    data_dir.mkdir(parents=True, exist_ok=True)
    media_root.mkdir(parents=True, exist_ok=True)
    art_root.mkdir(parents=True, exist_ok=True)

    db_mgr = DatabaseManager(f"sqlite:///{db_file.as_posix()}")
    db_mgr.init_db()
    media_reg = MediaRegistry(media_root=media_root, db_manager=db_mgr)
    art_store = ArtifactStore(root_dir=art_root)
    job_mgr = JobManager(db_manager=db_mgr, media_registry=media_reg)

    return db_mgr, media_reg, art_store, job_mgr


def cmd_media_scan(args: argparse.Namespace) -> int:
    target_dir = Path(args.directory).resolve()
    if not target_dir.is_dir():
        print(f"Error: Directory not found: {target_dir}", file=sys.stderr)
        return 1

    _, media_reg, _, _ = _get_services()
    found = 0
    registered = 0

    print(f"Scanning for video assets in {target_dir}...")
    for ext in SUPPORTED_EXTENSIONS:
        for file_path in target_dir.rglob(f"*{ext}"):
            found += 1
            try:
                rec = media_reg.register_file(file_path)
                print(f"  [+] Registered: {rec.display_name} ({rec.width}x{rec.height}, {rec.fps:.1f} fps, {rec.codec})")
                registered += 1
            except Exception as exc:
                print(f"  [!] Skipped {file_path.name}: {exc}", file=sys.stderr)

    print(f"Scan complete: found {found}, registered {registered}.")
    return 0


def cmd_media_register(args: argparse.Namespace) -> int:
    file_path = Path(args.filepath).resolve()
    if not file_path.is_file():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        return 1

    _, media_reg, _, _ = _get_services()
    try:
        rec = media_reg.register_file(file_path, display_name=args.name)
        print("Successfully registered media asset:")
        print(f"  ID: {rec.id}")
        print(f"  Display Name: {rec.display_name}")
        print(f"  Resolution: {rec.width}x{rec.height}")
        print(f"  FPS: {rec.fps:.2f}")
        print(f"  Duration: {rec.duration_s:.2f}s")
        print(f"  Codec: {rec.codec} (Browser Playable: {rec.browser_playable})")
        return 0
    except Exception as exc:
        print(f"Error registering file: {exc}", file=sys.stderr)
        return 1


def cmd_session_reprocess(args: argparse.Namespace) -> int:
    session_id = args.session_id
    db_mgr, _, _, job_mgr = _get_services()

    with db_mgr.get_session() as db:
        sess = db.get(SessionRecord, session_id)
        if not sess:
            print(f"Error: Session {session_id} not found", file=sys.stderr)
            return 1

        print(f"Clearing previous observations and results for session {session_id}...")
        db.execute(delete(ZoneResultRecord).where(ZoneResultRecord.session_id == session_id))
        db.execute(delete(ObservationRecord).where(ObservationRecord.session_id == session_id))
        sess.status = "QUEUED"
        sess.progress = 0.0
        sess.processed_frames = 0
        sess.error_code = None
        sess.user_action_hint = None
        sess.completeness = "PENDING"
        db.commit()

    print(f"Starting pipeline execution for session {session_id}...")
    final_status = job_mgr.run_session_job(session_id)
    print(f"Reprocessing completed with status: {final_status}")
    return 0 if final_status == "COMPLETED" else 1


def cmd_session_purge(args: argparse.Namespace) -> int:
    days = int(args.older_than_days)
    if days < 0:
        print("Error: --older-than-days must be non-negative", file=sys.stderr)
        return 1

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    db_mgr, _, art_store, _ = _get_services()

    purged = 0
    with db_mgr.get_session() as db:
        old_sessions = list(
            db.scalars(select(SessionRecord).where(SessionRecord.created_at < cutoff))
        )
        for s in old_sessions:
            sid = s.id
            # Delete artifacts from disk
            arts = list(db.scalars(select(ArtifactRecord).where(ArtifactRecord.session_id == sid)))
            for a in arts:
                try:
                    art_store.delete_artifact(a.relpath)
                except Exception:
                    pass

            db.delete(s)
            audit = AuditLogRecord(
                action="SESSION_PURGED_CLI",
                entity_type="session",
                entity_id=sid,
                details={"cutoff_days": days},
            )
            db.add(audit)
            purged += 1

        db.commit()

    print(f"Purge complete: deleted {purged} sessions created before {cutoff.isoformat()}.")
    return 0


def cmd_model_verify(args: argparse.Namespace) -> int:
    cfg_path = Path(args.config).resolve() if args.config else None
    service = ModelBoundaryService(default_config_path=cfg_path)

    try:
        res = service.verify_model(config_path=cfg_path)
    except Exception as exc:
        print(f"Error loading model configuration: {exc}", file=sys.stderr)
        return 1

    print("=" * 65)
    print(" CROWDSIGHT MODEL BOUNDARY VERIFICATION")
    print("=" * 65)
    print(f"Profile ID:          {res.profile_id}")
    print(f"Model Family:        {res.model_family}")
    print(f"Profile File:        {res.profile_path}")
    print(f"Profile SHA-256:     {res.profile_sha256}")
    print("-" * 65)
    print(f"Expected Checkpoint: {res.expected_checkpoint_sha256}")

    if not res.checkpoint_available or res.checkpoint_path is None:
        print("Checkpoint File:     NOT FOUND (status: MISSING)")
        print("Actual SHA-256:      N/A")
    else:
        print(f"Checkpoint File:     {res.checkpoint_path}")
        print(f"Actual SHA-256:      {res.actual_checkpoint_sha256}")

    status_str = "VERIFIED (MATCH)" if res.is_checkpoint_valid else (
        "MISSING" if not res.checkpoint_available else "MISMATCH"
    )
    print(f"Checkpoint Status:   {status_str}")

    if res.tracker_config_path:
        print("-" * 65)
        print(f"Tracker Config:      {res.tracker_config_path}")
        print(f"Tracker SHA-256:     {res.tracker_config_sha256}")

    print("-" * 65)
    print(f"Applicability Gate:  {res.applicability.status.value}")
    print(f"Operational Alerts:  {'ALLOWED' if res.applicability.operational_alerts_allowed else 'DISABLED (Fail-Closed)'}")
    print("=" * 65)

    if res.error_code:
        print(f"\n[!] Verification Issue: {res.error_code} - {res.error_message}")
        print("Note: In zero-weight or development environments, SyntheticDetector is used.")
        return 1

    print("\n[+] Model boundary and checkpoint verified successfully.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="crowdsight",
        description="CrowdSight fixed-camera crowd monitoring administration CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # media scan
    p_scan = subparsers.add_parser("media-scan", help="Scan directory and register video assets")
    p_scan.add_argument("directory", help="Directory path to scan for video files")
    p_scan.set_defaults(func=cmd_media_scan)

    # media register
    p_reg = subparsers.add_parser("media-register", help="Register a single video asset")
    p_reg.add_argument("filepath", help="Path to video file")
    p_reg.add_argument("--name", help="Display name for video asset", default=None)
    p_reg.set_defaults(func=cmd_media_register)

    # session reprocess
    p_rep = subparsers.add_parser("session-reprocess", help="Rerun processing pipeline for a session")
    p_rep.add_argument("session_id", help="Session ID to reprocess")
    p_rep.set_defaults(func=cmd_session_reprocess)

    # session purge
    p_pur = subparsers.add_parser("session-purge", help="Purge old sessions and their artifacts")
    p_pur.add_argument("--older-than-days", type=int, default=30, help="Purge cutoff in days (default: 30)")
    p_pur.set_defaults(func=cmd_session_purge)

    # model verify
    p_mod = subparsers.add_parser("model-verify", help="Verify model profile and checkpoint SHA-256 digests")
    p_mod.add_argument("--config", help="Custom model config YAML path", default=None)
    p_mod.set_defaults(func=cmd_model_verify)

    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func:
        return int(func(args))
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
