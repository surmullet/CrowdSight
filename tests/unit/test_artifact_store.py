"""Tests for ArtifactStore and path traversal defense."""
from __future__ import annotations

from pathlib import Path

import pytest

from crowdsight.service.artifacts.store import (
    ArtifactSecurityError,
    ArtifactStore,
)


@pytest.fixture
def store(tmp_path: Path) -> ArtifactStore:
    return ArtifactStore(tmp_path)


def test_save_and_retrieve_artifact(store: ArtifactStore) -> None:
    data = b"synthetic png content"
    art_id, relpath, sha256 = store.save_bytes(
        data,
        kind="IMAGE_SPACE_HEATMAP",
        suffix=".png",
        session_id="sess-123",
    )
    assert art_id
    assert relpath.endswith(".png")
    assert "sess-123" in relpath

    path = store.get_path(relpath)
    assert path.is_file()
    assert path.read_bytes() == data


def test_path_traversal_rejected(store: ArtifactStore) -> None:
    with pytest.raises(ArtifactSecurityError, match="Path traversal detected"):
        store.get_path("../../etc/passwd")

    with pytest.raises(ArtifactSecurityError, match="Path traversal detected"):
        store.get_path("..\\..\\windows\\system32\\calc.exe")


def test_delete_artifact(store: ArtifactStore) -> None:
    art_id, relpath, _ = store.save_bytes(b"temp", kind="TEMP", suffix=".tmp")
    assert store.get_path(relpath).is_file()
    deleted = store.delete_artifact(relpath)
    assert deleted is True
    with pytest.raises(FileNotFoundError):
        store.get_path(relpath)
