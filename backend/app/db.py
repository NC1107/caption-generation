"""Tiny SQLite job store: one table, each job a JSON document.

Every call opens a short-lived WAL connection, so it's safe from both the API
loop and worker threads without sharing connection objects.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.models import Job, JobStatus

_DB_PATH: Path | None = None


def init_db(db_path: Path) -> None:
    """Point the store at ``db_path`` and create the schema if needed."""
    global _DB_PATH
    _DB_PATH = db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id          TEXT PRIMARY KEY,
                status      TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL,
                data        TEXT NOT NULL
            )
            """
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at)")


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    if _DB_PATH is None:
        raise RuntimeError("db.init_db() must be called before use")
    con = sqlite3.connect(_DB_PATH, timeout=30)
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=5000")
        yield con
        con.commit()
    finally:
        con.close()


def save_job(job: Job) -> None:
    with _connect() as con:
        con.execute(
            "INSERT OR REPLACE INTO jobs (id, status, created_at, updated_at, data) "
            "VALUES (?, ?, ?, ?, ?)",
            (job.id, job.status.value, job.created_at, job.updated_at, job.model_dump_json()),
        )


def get_job(job_id: str) -> Job | None:
    with _connect() as con:
        row = con.execute("SELECT data FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return Job.model_validate_json(row[0]) if row else None


def list_jobs(limit: int = 100) -> list[Job]:
    with _connect() as con:
        rows = con.execute(
            "SELECT data FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [Job.model_validate_json(r[0]) for r in rows]


def delete_job(job_id: str) -> None:
    with _connect() as con:
        con.execute("DELETE FROM jobs WHERE id = ?", (job_id,))


def jobs_by_status(*statuses: JobStatus) -> list[Job]:
    placeholders = ",".join("?" for _ in statuses)
    with _connect() as con:
        rows = con.execute(
            f"SELECT data FROM jobs WHERE status IN ({placeholders}) ORDER BY created_at ASC",
            tuple(s.value for s in statuses),
        ).fetchall()
    return [Job.model_validate_json(r[0]) for r in rows]
