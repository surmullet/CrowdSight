"""Task queue abstractions and backends (InMemory bounded queue and Redis queue)."""
from __future__ import annotations

import logging
import os
import queue
import threading
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger("crowdsight.jobs.queue")


class BaseJobQueue(ABC):
    """Abstract base class for session job queues."""

    @abstractmethod
    def enqueue(self, session_id: str) -> None:
        """Add session_id to the processing queue."""

    @abstractmethod
    def dequeue(self, timeout: float = 1.0) -> str | None:
        """Fetch next session_id from queue, blocking up to timeout seconds."""

    @abstractmethod
    def request_cancellation(self, session_id: str) -> bool:
        """Request cooperative cancellation of a session."""

    @abstractmethod
    def is_cancelled(self, session_id: str) -> bool:
        """Check if session cancellation was requested."""

    @abstractmethod
    def clear_cancellation(self, session_id: str) -> None:
        """Clear cancellation request flag."""

    @abstractmethod
    def mark_active(self, session_id: str) -> None:
        """Mark job as actively running."""

    @abstractmethod
    def mark_completed(self, session_id: str) -> None:
        """Remove job from active set."""

    @abstractmethod
    def size(self) -> int:
        """Number of queued jobs pending processing."""

    @abstractmethod
    def active_count(self) -> int:
        """Number of jobs actively being executed."""

    @abstractmethod
    def stats(self) -> dict[str, Any]:
        """Return runtime queue statistics."""


class InMemoryJobQueue(BaseJobQueue):
    """Thread-safe in-memory queue with concurrency tracking."""

    def __init__(self, max_concurrency: int = 2) -> None:
        self.max_concurrency = max(1, max_concurrency)
        self._queue: queue.Queue[str] = queue.Queue()
        self._active_jobs: set[str] = set()
        self._cancellation_requests: set[str] = set()
        self._lock = threading.Lock()

    def enqueue(self, session_id: str) -> None:
        self._queue.put(session_id)
        logger.info("Enqueued session %s into InMemoryJobQueue (pending=%d)", session_id, self.size())

    def dequeue(self, timeout: float = 1.0) -> str | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def request_cancellation(self, session_id: str) -> bool:
        with self._lock:
            self._cancellation_requests.add(session_id)
            return True

    def is_cancelled(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._cancellation_requests

    def clear_cancellation(self, session_id: str) -> None:
        with self._lock:
            self._cancellation_requests.discard(session_id)

    def mark_active(self, session_id: str) -> None:
        with self._lock:
            self._active_jobs.add(session_id)

    def mark_completed(self, session_id: str) -> None:
        with self._lock:
            self._active_jobs.discard(session_id)

    def size(self) -> int:
        return self._queue.qsize()

    def active_count(self) -> int:
        with self._lock:
            return len(self._active_jobs)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "backend": "memory",
                "queued": self._queue.qsize(),
                "active": len(self._active_jobs),
                "max_concurrency": self.max_concurrency,
                "cancelled_flags": len(self._cancellation_requests),
            }


class RedisJobQueue(BaseJobQueue):
    """Redis-backed persistent job queue with distributed locking and worker support."""

    QUEUE_KEY = "crowdsight:jobs:queue"
    ACTIVE_KEY = "crowdsight:jobs:active"
    CANCEL_KEY = "crowdsight:jobs:cancelled"

    def __init__(self, redis_url: str, max_concurrency: int = 2) -> None:
        self.redis_url = redis_url
        self.max_concurrency = max(1, max_concurrency)
        try:
            import redis  # type: ignore[import-not-found]
            self._client: Any = redis.Redis.from_url(redis_url, decode_responses=True)
            self._client.ping()
            logger.info("Connected to Redis at %s", redis_url)
        except Exception as exc:
            logger.warning("Failed to connect to Redis (%s), falling back to InMemoryJobQueue", exc)
            self._client = None
            self._fallback = InMemoryJobQueue(max_concurrency=max_concurrency)

    def enqueue(self, session_id: str) -> None:
        if self._client is None:
            self._fallback.enqueue(session_id)
            return
        self._client.rpush(self.QUEUE_KEY, session_id)
        logger.info("Pushed session %s to Redis queue", session_id)

    def dequeue(self, timeout: float = 1.0) -> str | None:
        if self._client is None:
            return self._fallback.dequeue(timeout=timeout)
        result = self._client.blpop(self.QUEUE_KEY, timeout=int(max(1, timeout)))
        if result and len(result) == 2:
            return str(result[1])
        return None

    def request_cancellation(self, session_id: str) -> bool:
        if self._client is None:
            return self._fallback.request_cancellation(session_id)
        self._client.sadd(self.CANCEL_KEY, session_id)
        # Expire cancellation flag after 24 hours
        self._client.expire(self.CANCEL_KEY, 86400)
        return True

    def is_cancelled(self, session_id: str) -> bool:
        if self._client is None:
            return self._fallback.is_cancelled(session_id)
        return bool(self._client.sismember(self.CANCEL_KEY, session_id))

    def clear_cancellation(self, session_id: str) -> None:
        if self._client is None:
            self._fallback.clear_cancellation(session_id)
            return
        self._client.srem(self.CANCEL_KEY, session_id)

    def mark_active(self, session_id: str) -> None:
        if self._client is None:
            self._fallback.mark_active(session_id)
            return
        self._client.sadd(self.ACTIVE_KEY, session_id)

    def mark_completed(self, session_id: str) -> None:
        if self._client is None:
            self._fallback.mark_completed(session_id)
            return
        self._client.srem(self.ACTIVE_KEY, session_id)

    def size(self) -> int:
        if self._client is None:
            return self._fallback.size()
        return int(self._client.llen(self.QUEUE_KEY))

    def active_count(self) -> int:
        if self._client is None:
            return self._fallback.active_count()
        return int(self._client.scard(self.ACTIVE_KEY))

    def stats(self) -> dict[str, Any]:
        if self._client is None:
            return self._fallback.stats()
        return {
            "backend": "redis",
            "redis_url": self.redis_url,
            "queued": self.size(),
            "active": self.active_count(),
            "max_concurrency": self.max_concurrency,
        }


def create_job_queue(
    backend: str | None = None,
    max_concurrency: int = 2,
    redis_url: str | None = None,
) -> BaseJobQueue:
    """Factory creating appropriate queue based on environment configuration."""
    resolved_backend = backend or os.environ.get("CROWDSIGHT_QUEUE_BACKEND")
    resolved_redis_url = redis_url or os.environ.get("REDIS_URL") or os.environ.get("CROWDSIGHT_REDIS_URL")

    if resolved_backend == "redis" or (resolved_backend is None and resolved_redis_url):
        if not resolved_redis_url:
            resolved_redis_url = "redis://localhost:6379/0"
        return RedisJobQueue(redis_url=resolved_redis_url, max_concurrency=max_concurrency)

    concurrency = int(os.environ.get("CROWDSIGHT_MAX_CONCURRENCY", max_concurrency))
    return InMemoryJobQueue(max_concurrency=concurrency)
