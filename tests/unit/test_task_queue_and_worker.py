"""Unit tests for Task Queue backends and QueueWorker process."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from crowdsight.service.jobs.queue import InMemoryJobQueue, RedisJobQueue, create_job_queue
from crowdsight.service.jobs.runner import JobManager
from crowdsight.service.jobs.worker import QueueWorker
from crowdsight.service.storage.database import DatabaseManager
from crowdsight.service.storage.media_registry import MediaRegistry


def test_in_memory_job_queue_lifecycle() -> None:
    queue = InMemoryJobQueue(max_concurrency=3)
    assert queue.size() == 0
    assert queue.active_count() == 0

    queue.enqueue("sess-001")
    queue.enqueue("sess-002")
    assert queue.size() == 2

    # Dequeue
    j1 = queue.dequeue(timeout=0.1)
    assert j1 == "sess-001"
    assert queue.size() == 1

    queue.mark_active("sess-001")
    assert queue.active_count() == 1

    queue.mark_completed("sess-001")
    assert queue.active_count() == 0

    # Cancellation
    assert not queue.is_cancelled("sess-002")
    queue.request_cancellation("sess-002")
    assert queue.is_cancelled("sess-002")
    queue.clear_cancellation("sess-002")
    assert not queue.is_cancelled("sess-002")

    stats = queue.stats()
    assert stats["backend"] == "memory"
    assert stats["max_concurrency"] == 3


def test_redis_job_queue_graceful_fallback() -> None:
    # Attempting to connect to invalid redis url falls back gracefully to in-memory queue
    queue = RedisJobQueue(redis_url="redis://nonexistent-host:9999/0", max_concurrency=2)
    queue.enqueue("sess-fallback")
    assert queue.size() == 1
    job = queue.dequeue(timeout=0.1)
    assert job == "sess-fallback"


def test_create_job_queue_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("CROWDSIGHT_QUEUE_BACKEND", raising=False)
    q = create_job_queue()
    assert isinstance(q, InMemoryJobQueue)


def test_queue_worker_execution(tmp_path: Path) -> None:
    db = DatabaseManager(f"sqlite:///{tmp_path}/worker_test.db")
    db.init_db()
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    reg = MediaRegistry(media_dir, db)

    job_mgr = JobManager(db, reg)
    queue = InMemoryJobQueue(max_concurrency=2)

    processed_jobs: list[str] = []

    def mock_run_job(session_id: str) -> str:
        processed_jobs.append(session_id)
        return "COMPLETED"

    job_mgr.run_session_job = mock_run_job  # type: ignore[assignment]

    worker = QueueWorker(job_mgr, queue, concurrency=2)
    worker.start()

    queue.enqueue("job-alpha")
    queue.enqueue("job-beta")

    # Give worker a brief moment to process
    for _ in range(20):
        if len(processed_jobs) == 2:
            break
        time.sleep(0.1)

    worker.stop()

    assert "job-alpha" in processed_jobs
    assert "job-beta" in processed_jobs
    assert queue.active_count() == 0
