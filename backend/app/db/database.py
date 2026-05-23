"""
SQLite-backed audit history.

Uses the stdlib `sqlite3` module — no ORM dependency. A new connection is
opened per call to stay friendly with FastAPI's threadpool execution.
"""
import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from typing import List, Optional, Tuple

from app.models.schemas import (
    AuditReport, HistoryEntry, HistoryDetailResponse,
)


DB_PATH = os.environ.get(
    "AUDIT_DB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "audit_history.db"),
)


_init_lock = threading.Lock()
_initialized = False


def _ensure_initialized() -> None:
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return
        os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    contracts TEXT NOT NULL,        -- json array
                    sloc INTEGER NOT NULL,
                    detectors_run TEXT NOT NULL,    -- json array
                    summary TEXT NOT NULL,          -- json object
                    source TEXT NOT NULL,
                    report TEXT NOT NULL            -- full AuditReport json
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_history_ts "
                "ON audit_history(timestamp DESC)"
            )
            conn.commit()
        _initialized = True


@contextmanager
def _conn():
    _ensure_initialized()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ─── Public API ────────────────────────────────────────────────────────────

def save_audit(report: AuditReport, source: str) -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO audit_history "
            "(timestamp, filename, contracts, sloc, detectors_run, summary, "
            " source, report) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                report.meta.timestamp,
                report.meta.filename,
                json.dumps(report.meta.contracts),
                report.meta.sloc,
                json.dumps(report.meta.detectors_run),
                json.dumps(report.summary),
                source,
                report.model_dump_json(),
            ),
        )
        return int(cur.lastrowid)


def list_audits(limit: int = 50, offset: int = 0) -> Tuple[List[HistoryEntry], int]:
    with _conn() as c:
        total = c.execute(
            "SELECT COUNT(*) AS n FROM audit_history"
        ).fetchone()["n"]
        rows = c.execute(
            "SELECT id, timestamp, filename, contracts, sloc, "
            "       detectors_run, summary "
            "FROM audit_history "
            "ORDER BY id DESC "
            "LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        entries = [
            HistoryEntry(
                id=row["id"],
                filename=row["filename"],
                contracts=json.loads(row["contracts"]),
                summary=json.loads(row["summary"]),
                sloc=row["sloc"],
                detectors_run=json.loads(row["detectors_run"]),
                timestamp=row["timestamp"],
            )
            for row in rows
        ]
        return entries, int(total)


def get_audit(audit_id: int) -> Optional[HistoryDetailResponse]:
    with _conn() as c:
        row = c.execute(
            "SELECT id, timestamp, source, report "
            "FROM audit_history WHERE id = ?",
            (audit_id,),
        ).fetchone()
        if not row:
            return None
        return HistoryDetailResponse(
            id=row["id"],
            timestamp=row["timestamp"],
            source=row["source"],
            report=AuditReport.model_validate_json(row["report"]),
        )


def delete_audit(audit_id: int) -> bool:
    with _conn() as c:
        cur = c.execute(
            "DELETE FROM audit_history WHERE id = ?", (audit_id,))
        return cur.rowcount > 0


def get_audit_source(audit_id: int) -> Optional[str]:
    """Convenience helper used by the diff endpoint."""
    with _conn() as c:
        row = c.execute(
            "SELECT source FROM audit_history WHERE id = ?",
            (audit_id,),
        ).fetchone()
        return row["source"] if row else None
