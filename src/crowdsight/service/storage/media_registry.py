"""Media asset catalog, metadata extraction via OpenCV, and storage registration."""
from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import cv2
from sqlalchemy import select

from crowdsight.service.artifacts.store import ArtifactSecurityError
from crowdsight.service.storage.database import DatabaseManager
from crowdsight.service.storage.models import MediaAssetRecord

SUPPORTED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".m4v", ".webm"}


class MediaRegistry:
    """Manages server catalog of recorded fixed-camera video assets."""

    def __init__(self, media_root: Path, db_manager: DatabaseManager) -> None:
        self.media_root = Path(media_root).resolve()
        self.media_root.mkdir(parents=True, exist_ok=True)
        self.db_manager = db_manager

    def _resolve_safe(self, relpath: str) -> Path:
        clean_rel = relpath.replace("\\", "/").lstrip("/")
        target = (self.media_root / clean_rel).resolve()
        try:
            target.relative_to(self.media_root)
        except ValueError as exc:
            raise ArtifactSecurityError(f"Path traversal detected: {relpath}") from exc
        return target

    @staticmethod
    def sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def inspect_video(self, file_path: Path) -> dict[str, Any]:
        """Extract video properties using OpenCV."""
        cap = cv2.VideoCapture(str(file_path))
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {file_path}")

        try:
            fps = float(cap.get(cv2.CAP_PROP_FPS))
            if fps <= 0 or not (1.0 <= fps <= 120.0):
                fps = 25.0  # Sensible default if video header is missing FPS

            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))

            codec = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)])
            duration_s = frame_count / fps if fps > 0 and frame_count > 0 else 0.0

            # Test browser playability: mp4 with avc1/h264 is typically playable
            ext = file_path.suffix.lower()
            browser_playable = ext in (".mp4", ".webm") and codec.lower() in ("avc1", "h264", "vp80", "vp90")

            return {
                "fps": fps,
                "frame_count": max(frame_count, 1),
                "width": max(width, 1),
                "height": max(height, 1),
                "codec": codec.strip() or "unknown",
                "duration_s": max(duration_s, 0.0),
                "browser_playable": browser_playable,
            }
        finally:
            cap.release()

    def register_file(
        self,
        file_path: Path,
        *,
        display_name: str | None = None,
    ) -> MediaAssetRecord:
        """Register or update a single video file in the media catalog."""
        resolved = Path(file_path).resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"Media file not found: {resolved}")

        try:
            relpath = str(resolved.relative_to(self.media_root)).replace("\\", "/")
        except ValueError as exc:
            raise ArtifactSecurityError(
                f"File {resolved} must reside inside media root {self.media_root}"
            ) from exc

        sha256 = self.sha256_file(resolved)
        info = self.inspect_video(resolved)
        name = display_name or resolved.stem

        with self.db_manager.get_session() as session:
            stmt = select(MediaAssetRecord).where(MediaAssetRecord.relpath == relpath)
            existing = session.scalar(stmt)
            if existing:
                existing.display_name = name
                existing.sha256 = sha256
                existing.duration_s = float(info["duration_s"])
                existing.fps = float(info["fps"])
                existing.frame_count = int(info["frame_count"])
                existing.width = int(info["width"])
                existing.height = int(info["height"])
                existing.codec = str(info["codec"])
                existing.browser_playable = bool(info["browser_playable"])
                session.flush()
                session.refresh(existing)
                return existing

            # Compute next sequential display_code (MED-XXXX)
            stmt_max = select(MediaAssetRecord.display_code).where(MediaAssetRecord.display_code.like("MED-%"))
            existing_codes = session.scalars(stmt_max).all()
            max_num = 0
            for code in existing_codes:
                try:
                    num = int(code.split("-")[1])
                    if num > max_num:
                        max_num = num
                except (IndexError, ValueError):
                    pass
            display_code = f"MED-{max_num + 1:04d}"

            record = MediaAssetRecord(
                display_name=name,
                display_code=display_code,
                relpath=relpath,
                sha256=sha256,
                duration_s=float(info["duration_s"]),
                fps=float(info["fps"]),
                frame_count=int(info["frame_count"]),
                width=int(info["width"]),
                height=int(info["height"]),
                codec=str(info["codec"]),
                browser_playable=bool(info["browser_playable"]),
            )
            session.add(record)
            session.flush()
            session.refresh(record)
            return record

    def list_media(self) -> Sequence[MediaAssetRecord]:
        with self.db_manager.get_session() as session:
            return list(session.scalars(select(MediaAssetRecord).order_by(MediaAssetRecord.created_at.desc())))

    def get_media_path(self, asset_id: str) -> Path:
        with self.db_manager.get_session() as session:
            stmt = select(MediaAssetRecord).where(MediaAssetRecord.id == asset_id)
            asset = session.scalar(stmt)
            if not asset:
                raise FileNotFoundError(f"Media asset not found: {asset_id}")
            return self._resolve_safe(asset.relpath)
