"""Database engine configuration and session lifecycle management."""
from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from crowdsight.service.storage.models import Base


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: object, connection_record: object) -> None:
    """Enforce SQLite WAL mode and foreign key constraints only for SQLite."""
    module_name = type(dbapi_connection).__module__
    if "sqlite" not in module_name:
        return
    cursor = getattr(dbapi_connection, "cursor", None)
    if cursor is not None:
        try:
            c = cursor()
            c.execute("PRAGMA foreign_keys=ON")
            c.execute("PRAGMA journal_mode=WAL")
            c.close()
        except Exception:
            pass


class DatabaseManager:
    """Manages SQLAlchemy 2.0 Engine and Session creation."""

    def __init__(self, db_url: str) -> None:
        # Standardize postgres:// to postgresql://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        self.db_url = db_url

        # If SQLite path does not exist, ensure parent directory exists
        if db_url.startswith("sqlite:///"):
            raw_path = db_url.replace("sqlite:///", "")
            if raw_path != ":memory:":
                db_file = Path(raw_path).resolve()
                db_file.parent.mkdir(parents=True, exist_ok=True)

        engine_kwargs: dict = {
            "echo": False,
            "future": True,
        }
        if "postgresql" in db_url:
            from sqlalchemy.pool import NullPool
            engine_kwargs["poolclass"] = NullPool

        self.engine = create_engine(
            db_url,
            **engine_kwargs,
        )
        self.session_factory = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            future=True,
        )

    def init_db(self) -> None:
        """Create all tables in the database."""
        Base.metadata.create_all(self.engine)

    def drop_db(self) -> None:
        """Drop all tables (used in test tear-down)."""
        Base.metadata.drop_all(self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Provide a transactional session scope."""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


_default_manager: DatabaseManager | None = None


def get_default_database_manager(db_url: str | None = None) -> DatabaseManager:
    global _default_manager
    if _default_manager is None:
        if not db_url:
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:
                pass
            import os
            db_url = os.environ.get("DATABASE_URL") or "sqlite:///./data/crowdsight.db"
        _default_manager = DatabaseManager(db_url)
    return _default_manager


def get_db_session() -> Generator[Session, None, None]:
    """Dependency helper for FastAPI endpoints."""
    manager = get_default_database_manager()
    with manager.get_session() as session:
        yield session
