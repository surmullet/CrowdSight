"""Artifact storage and path-traversal hardened file management."""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path


class ArtifactSecurityError(ValueError):
    """Raised when an artifact access violates security or path containment."""


class ArtifactStore:
    """Manages generated artifacts (heatmaps, exports, proxies) in a secure root."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe(self, relpath: str) -> Path:
        """Resolve a relative path ensuring it stays strictly inside root_dir."""
        if not relpath or relpath.startswith(("/", "\\")) or ":" in relpath:
            raise ArtifactSecurityError(f"Absolute or invalid path rejected: {relpath}")
        clean_rel = relpath.replace("\\", "/")
        target = (self.root_dir / clean_rel).resolve()
        try:
            target.relative_to(self.root_dir)
        except ValueError as exc:
            raise ArtifactSecurityError(f"Path traversal detected: {relpath}") from exc
        return target

    def save_bytes(
        self,
        data: bytes,
        *,
        kind: str,
        suffix: str = ".bin",
        session_id: str | None = None,
    ) -> tuple[str, str, str]:
        """Save raw bytes to disk with SHA-256 computation.

        Returns:
            Tuple of (artifact_id, relative_path, sha256_digest)
        """
        artifact_id = str(uuid.uuid4())
        digest = hashlib.sha256(data).hexdigest()

        # Organize by kind / session_id if available
        subfolder = f"{kind.lower()}/{session_id}" if session_id else kind.lower()
        folder = self.root_dir / subfolder
        folder.mkdir(parents=True, exist_ok=True)

        clean_suffix = suffix if suffix.startswith(".") else f".{suffix}"
        filename = f"{artifact_id}{clean_suffix}"
        target_path = folder / filename
        target_path.write_bytes(data)

        relpath = str(target_path.relative_to(self.root_dir)).replace("\\", "/")
        return artifact_id, relpath, digest

    def get_path(self, relpath: str) -> Path:
        """Get verified filesystem path for relative path."""
        path = self._resolve_safe(relpath)
        if not path.is_file():
            raise FileNotFoundError(f"Artifact not found at {relpath}")
        return path

    def delete_artifact(self, relpath: str) -> bool:
        """Delete artifact file safely."""
        path = self._resolve_safe(relpath)
        if path.is_file():
            path.unlink()
            return True
        return False
