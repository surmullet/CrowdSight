"""FastAPI dependency injection provider for service singletons and repositories."""
from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy.orm import Session

from crowdsight.service.artifacts.store import ArtifactStore
from crowdsight.service.jobs.runner import JobManager
from crowdsight.service.storage.database import DatabaseManager
from crowdsight.service.storage.media_registry import MediaRegistry

_db_manager: DatabaseManager | None = None
_media_registry: MediaRegistry | None = None
_artifact_store: ArtifactStore | None = None
_job_manager: JobManager | None = None


def init_service_dependencies(
    *,
    db_url: str | None = None,
    media_dir: Path | None = None,
    artifacts_dir: Path | None = None,
) -> None:
    """Initialize global service dependencies (called at application lifespan startup)."""
    global _db_manager, _media_registry, _artifact_store, _job_manager

    if not db_url:
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        import os
        db_url = os.environ.get("DATABASE_URL") or "sqlite:///./data/crowdsight.db"

    base_dir = Path("./data").resolve()
    media_path = Path(media_dir).resolve() if media_dir else base_dir / "media"
    art_path = Path(artifacts_dir).resolve() if artifacts_dir else base_dir / "artifacts"

    media_path.mkdir(parents=True, exist_ok=True)
    art_path.mkdir(parents=True, exist_ok=True)

    _db_manager = DatabaseManager(db_url)
    _db_manager.init_db()

    _media_registry = MediaRegistry(media_path, _db_manager)
    _artifact_store = ArtifactStore(art_path)
    _job_manager = JobManager(_db_manager, _media_registry, _artifact_store)


def get_db_manager() -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        init_service_dependencies()
    assert _db_manager is not None
    return _db_manager


def get_db() -> Generator[Session, None, None]:
    manager = get_db_manager()
    with manager.get_session() as session:
        yield session


def get_media_registry() -> MediaRegistry:
    global _media_registry
    if _media_registry is None:
        init_service_dependencies()
    assert _media_registry is not None
    return _media_registry


def get_artifact_store() -> ArtifactStore:
    global _artifact_store
    if _artifact_store is None:
        init_service_dependencies()
    assert _artifact_store is not None
    return _artifact_store


def get_job_manager() -> JobManager:
    global _job_manager
    if _job_manager is None:
        init_service_dependencies()
    assert _job_manager is not None
    return _job_manager
