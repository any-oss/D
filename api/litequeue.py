import sqlite3
import json
import time
from contextlib import contextmanager
from typing import Optional, Dict, Any

DB_PATH = "data/job_queue.db"


def init_queue():
    """Initialize the persistent job queue with WAL mode."""
    import os

    os.makedirs("data", exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
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
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON jobs(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_topic ON jobs(topic)")
    conn.commit()
    conn.close()


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


def enqueue(topic: str, payload: Dict[str, Any]) -> int:
    """Add a task to the queue."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO jobs (topic, payload) VALUES (?, ?)",
            (topic, json.dumps(payload)),
        )
        conn.commit()
        return cur.lastrowid


def dequeue(topic: str) -> Optional[Dict]:
    """Fetch next pending task for a specific agent skill range."""
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
            cur.execute("UPDATE jobs SET status = 'processing' WHERE id = ?", (job_id,))
            conn.commit()
            return {"id": job_id, "payload": json.loads(payload_str)}
    return None


def complete_job(job_id: int, success: bool, error: str = None):
    """Mark job as done or failed."""
    with get_db() as conn:
        cur = conn.cursor()
        if success:
            cur.execute(
                "UPDATE jobs SET status = 'completed', processed_at = strftime('%s', 'now') WHERE id = ?",
                (job_id,),
            )
        else:
            cur.execute(
                "UPDATE jobs SET status = 'failed', error_msg = ?, processed_at = strftime('%s', 'now'), retry_count = retry_count + 1 WHERE id = ?",
                (error, job_id),
            )
        conn.commit()


# Initialize on import
init_queue()
