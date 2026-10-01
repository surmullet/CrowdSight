"""Tests for MediaRegistry and OpenCV video inspection."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from crowdsight.service.artifacts.store import ArtifactSecurityError
from crowdsight.service.storage.database import DatabaseManager
from crowdsight.service.storage.media_registry import MediaRegistry


def create_sample_video(path: Path, num_frames: int = 15, width: int = 320, height: int = 240, fps: float = 10.0) -> None:
    fourcc = int(cv2.VideoWriter_fourcc(*"mp4v"))  # type: ignore[attr-defined]
    writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
    for i in range(num_frames):
        frame = np.full((height, width, 3), (i * 15) % 256, dtype=np.uint8)
        writer.write(frame)
    writer.release()


@pytest.fixture
def media_env(tmp_path: Path) -> tuple[MediaRegistry, DatabaseManager, Path]:
    db = DatabaseManager(f"sqlite:///{tmp_path}/test.db")
    db.init_db()
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    registry = MediaRegistry(media_dir, db)
    return registry, db, media_dir


def test_register_and_inspect_video(media_env: tuple[MediaRegistry, DatabaseManager, Path]) -> None:
    registry, db, media_dir = media_env
    video_path = media_dir / "sample.mp4"
    create_sample_video(video_path, num_frames=20, width=320, height=240, fps=10.0)

    asset = registry.register_file(video_path, display_name="Sample Video")
    assert asset.display_name == "Sample Video"
    assert asset.frame_count >= 15
    assert asset.width == 320
    assert asset.height == 240
    assert asset.fps == 10.0
    assert len(asset.sha256) == 64

    # Fetch back
    found_path = registry.get_media_path(asset.id)
    assert found_path.resolve() == video_path.resolve()


def test_register_outside_media_dir_rejected(media_env: tuple[MediaRegistry, DatabaseManager, Path], tmp_path: Path) -> None:
    registry, _, _ = media_env
    outside_video = tmp_path / "outside.mp4"
    create_sample_video(outside_video)

    with pytest.raises(ArtifactSecurityError, match="must reside inside media root"):
        registry.register_file(outside_video)
