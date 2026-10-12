"""Standalone background worker process for asynchronous session video processing."""
from __future__ import annotations

import argparse
import logging
import os
import signal
import threading
import time
from typing import Any

from crowdsight.service.artifacts.store import ArtifactStore
from crowdsight.service.jobs.queue import BaseJobQueue, create_job_queue
from crowdsight.service.jobs.runner import JobManager
from crowdsight.service.storage.database import DatabaseManager
from crowdsight.service.storage.media_registry import MediaRegistry

logger = logging.getLogger("crowdsight.worker")


class QueueWorker:
    """Manages pool of worker threads processing jobs from BaseJobQueue."""

    def __init__(
        self,
        job_manager: JobManager,
        queue: BaseJobQueue,
        concurrency: int = 2,
    ) -> None:
        self.job_manager = job_manager
        self.queue = queue
        self.concurrency = max(1, concurrency)
        self._running = False
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        """Start worker threads in background."""
        if self._running:
            return
        self._running = True
        logger.info(
            "Starting QueueWorker with concurrency=%d on queue backend=%s",
            self.concurrency,
            self.queue.stats().get("backend", "unknown"),
        )

        for i in range(self.concurrency):
            thread = threading.Thread(
                target=self._worker_loop,
                name=f"crowdsight-worker-{i+1}",
                daemon=True,
            )
            thread.start()
            self._threads.append(thread)

    def stop(self, timeout: float = 5.0) -> None:
        """Signal workers to stop and wait for active jobs to finish."""
        if not self._running:
            return
        logger.info("Stopping QueueWorker (active jobs: %d)...", self.queue.active_count())
        self._running = False
        for thread in self._threads:
            thread.join(timeout=timeout)
        self._threads.clear()
        logger.info("QueueWorker stopped.")

    def _worker_loop(self) -> None:
        """Continuous worker loop polling queue and executing jobs."""
        while self._running:
            try:
                session_id = self.queue.dequeue(timeout=1.0)
                if not session_id:
                    continue

                logger.info("Worker picked up session job: %s", session_id)
                self.queue.mark_active(session_id)
                try:
                    status = self.job_manager.run_session_job(session_id)
                    logger.info("Worker finished session %s with final status: %s", session_id, status)
                except Exception as exc:
                    logger.exception("Worker encountered unhandled exception on session %s: %s", session_id, exc)
                finally:
                    self.queue.mark_completed(session_id)
            except Exception as loop_exc:
                if self._running:
                    logger.error("Error in worker polling loop: %s", loop_exc)
                    time.sleep(0.5)


def run_standalone_worker(
    db_url: str | None = None,
    media_dir: str | None = None,
    artifacts_dir: str | None = None,
    concurrency: int = 2,
    queue_backend: str | None = None,
) -> None:
    """Run worker process until SIGINT/SIGTERM."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    resolved_db = db_url or os.environ.get("DATABASE_URL", "sqlite:///./data/crowdsight.db")
    db_mgr = DatabaseManager(resolved_db)
    db_mgr.init_db()

    media_path = os.environ.get("CROWDSIGHT_MEDIA_DIR", "./data/media") if not media_dir else media_dir
    art_path = os.environ.get("CROWDSIGHT_ARTIFACTS_DIR", "./data/artifacts") if not artifacts_dir else artifacts_dir

    from pathlib import Path
    media_reg = MediaRegistry(Path(media_path), db_mgr)
    art_store = ArtifactStore(Path(art_path))
    job_queue = create_job_queue(backend=queue_backend, max_concurrency=concurrency)
    job_mgr = JobManager(db_mgr, media_reg, art_store, job_queue=job_queue)

    # Recover any orphaned jobs from previous crashes
    recovered = job_mgr.recover_orphaned_jobs()
    if recovered > 0:
        logger.warning("Recovered %d orphaned jobs on worker startup", recovered)

    worker = QueueWorker(job_mgr, job_queue, concurrency=concurrency)
    worker.start()

    stop_event = threading.Event()

    def handle_signal(sig: int, frame: Any) -> None:
        logger.info("Received termination signal %d. Initiating graceful shutdown...", sig)
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    print(f"[*] CrowdSight Queue Worker running with concurrency={concurrency} (Press Ctrl+C to stop)...")
    while not stop_event.is_set():
        time.sleep(0.5)

    worker.stop()
    print("[*] Worker shut down gracefully.")


def main() -> None:
    parser = argparse.ArgumentParser(description="CrowdSight Standalone Job Queue Worker")
    parser.add_argument("--concurrency", type=int, default=2, help="Number of concurrent worker threads")
    parser.add_argument("--queue-backend", choices=["memory", "redis"], default=None, help="Queue backend to use")
    parser.add_argument("--db-url", default=None, help="Database connection URL")
    args = parser.parse_args()

    run_standalone_worker(
        db_url=args.db_url,
        concurrency=args.concurrency,
        queue_backend=args.queue_backend,
    )


if __name__ == "__main__":
    main()
