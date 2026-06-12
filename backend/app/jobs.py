"""Background jobs: a small async worker pool over the SQLite queue. No Redis."""

from __future__ import annotations

import asyncio
import logging
import shutil
from datetime import UTC, datetime, timedelta

from app import db
from app.config import Settings
from app.models import TERMINAL_STATUSES, Job, JobOptions, JobStatus

log = logging.getLogger("caption.jobs")


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def new_job(job_id: str, filename: str, size: int, options: JobOptions) -> Job:
    now = utcnow()
    return Job(
        id=job_id,
        status=JobStatus.queued,
        progress=0.0,
        stage_message="Queued",
        filename=filename,
        size=size,
        created_at=now,
        updated_at=now,
        options=options,
    )


class JobManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self._workers: list[asyncio.Task] = []
        self._retention_task: asyncio.Task | None = None
        self._stopping = False

    async def start(self) -> None:
        self._recover()
        n = max(1, self.settings.worker_concurrency)
        self._workers = [asyncio.create_task(self._worker(i)) for i in range(n)]
        self._retention_task = asyncio.create_task(self._retention_loop())
        log.info("Job manager started with %d worker(s)", n)

    async def stop(self) -> None:
        self._stopping = True
        for t in self._workers:
            t.cancel()
        if self._retention_task:
            self._retention_task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)

    def _recover(self) -> None:
        """On boot, requeue queued jobs and fail any caught mid-run."""
        for job in db.jobs_by_status(JobStatus.queued):
            self.queue.put_nowait(job.id)
        for job in db.jobs_by_status(
            JobStatus.extracting, JobStatus.transcribing, JobStatus.enhancing
        ):
            job.status = JobStatus.failed
            job.error = "Interrupted by a server restart. Please run the job again."
            job.updated_at = utcnow()
            db.save_job(job)

    def submit(self, job: Job) -> None:
        db.save_job(job)
        self.queue.put_nowait(job.id)

    async def _worker(self, idx: int) -> None:
        from app.pipeline import run_pipeline  # local import avoids an import cycle

        while not self._stopping:
            try:
                job_id = await self.queue.get()
            except asyncio.CancelledError:
                break
            try:
                job = db.get_job(job_id)
                if job is None or job.status in TERMINAL_STATUSES:
                    continue
                log.info("worker %d: starting job %s", idx, job_id)
                await asyncio.to_thread(run_pipeline, job_id, self.settings)
            except asyncio.CancelledError:
                break
            except Exception:  # noqa: BLE001 — pipeline records its own failures; guard the loop
                log.exception("worker %d: unhandled error on job %s", idx, job_id)
                self._fail(job_id, "Unexpected error. See server logs.")
            finally:
                self.queue.task_done()

    def _fail(self, job_id: str, error: str) -> None:
        job = db.get_job(job_id)
        if job is None:
            return
        job.status = JobStatus.failed
        job.error = error
        job.updated_at = utcnow()
        db.save_job(job)

    async def _retention_loop(self) -> None:
        hours = self.settings.job_retention_hours
        if hours <= 0:
            return
        while not self._stopping:
            try:
                self._purge_old(hours)
            except Exception:  # noqa: BLE001
                log.exception("retention sweep failed")
            await asyncio.sleep(3600)

    def _purge_old(self, hours: int) -> None:
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        for job in db.list_jobs(limit=10_000):
            try:
                created = datetime.fromisoformat(job.created_at)
            except ValueError:
                continue
            if created < cutoff:
                shutil.rmtree(self.settings.uploads_dir / job.id, ignore_errors=True)
                shutil.rmtree(self.settings.outputs_dir / job.id, ignore_errors=True)
                db.delete_job(job.id)
                log.info("purged expired job %s", job.id)
