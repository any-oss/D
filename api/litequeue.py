"""LiteQueue - Lightweight Task Queue System

A production-ready, mobile-optimized task queue API built with FastAPI.
Supports SQLite (Termux/Mobile) and PostgreSQL (Server) deployments.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional, Generator

# Use unified config storage path
DB_PATH = str(Path(__file__).resolve().parent.parent / "storage" / "db" / "job_queue.db")


def init_queue() -> None:
    """Initialize the persistent job queue with WAL mode."""
    # Ensure storage directory exists (critical for Termux/Docker)
    db_dir = Path(DB_PATH).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at REAL DEFAULT (strftime('%s', 'now')),
                processed_at REAL,
                retry_count INTEGER DEFAULT 0,
                error_msg TEXT
            )
        """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON jobs(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_topic ON jobs(topic)")
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Get database connection with WAL mode enabled.
    
    Yields:
        sqlite3.Connection: Database connection object
    """
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


def enqueue(topic: str, payload: Dict[str, Any]) -> int:
    """Add a task to the queue.
    
    Args:
        topic: Task topic/queue name
        payload: Task payload dictionary
    
    Returns:
        int: ID of the newly created job
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO jobs (topic, payload) VALUES (?, ?)",
            (topic, json.dumps(payload)),
        )
        conn.commit()
        return cur.lastrowid


def dequeue(topic: str) -> Optional[Dict[str, Any]]:
    """Fetch next pending task for a specific agent skill range.
    
    Args:
        topic: Topic/queue name to dequeue from
    
    Returns:
        Dictionary with job id and payload, or None if no jobs available
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, payload FROM jobs 
            WHERE topic = ? AND status = 'pending' 
            ORDER BY created_at ASC LIMIT 1
        """,
            (topic,),
        )
        row = cur.fetchone()
        if row:
            job_id, payload_str = row
            cur.execute(
                "UPDATE jobs SET status = 'processing' WHERE id = ?", (job_id,)
            )
            conn.commit()
            return {"id": job_id, "payload": json.loads(payload_str)}
    return None


def complete_job(job_id: int, success: bool, error: Optional[str] = None) -> None:
    """Mark job as done or failed.
    
    Args:
        job_id: ID of the job to complete
        success: True if job succeeded, False if failed
        error: Error message if job failed (optional)
    """
    with get_db() as conn:
        cur = conn.cursor()
        if success:
            cur.execute(
                "UPDATE jobs SET status = 'completed', processed_at = strftime('%s', 'now') WHERE id = ?",
                (job_id,),
            )
        else:
            cur.execute(
                """UPDATE jobs SET status = 'failed', 
                   error_msg = ?, processed_at = strftime('%s', 'now'), 
                   retry_count = retry_count + 1 WHERE id = ?""",
                (error, job_id),
            )
        conn.commit()


# Initialize on import
init_queue()
