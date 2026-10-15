"""Bitácora local (SQLite en un volumen) de retiros: write-ahead + cola para cuando el legacy está caído."""

import sqlite3
from datetime import datetime, timedelta, timezone

PENDING, APPLIED, FAILED = "PENDING", "APPLIED", "FAILED"


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Outbox:
    def __init__(self, path):
        self._path = path
        with self._conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS retirement_outbox ("
                "request_id TEXT PRIMARY KEY, document TEXT NOT NULL, retirement_date TEXT NOT NULL, "
                "reason TEXT NOT NULL, actor TEXT NOT NULL, status TEXT NOT NULL, movement_id INTEGER, "
                "attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")

    def _conn(self):
        conn = sqlite3.connect(self._path, timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    def get(self, request_id):
        with self._conn() as conn:
            return conn.execute("SELECT * FROM retirement_outbox WHERE request_id = ?", (request_id,)).fetchone()

    def add_pending(self, request_id, document, date, reason, actor):
        now = _now()
        with self._conn() as conn:
            conn.execute("INSERT OR IGNORE INTO retirement_outbox (request_id, document, retirement_date, reason, actor, "
                         "status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (request_id, document, date, reason, actor, PENDING, now, now))

    def delete(self, request_id):
        with self._conn() as conn:
            conn.execute("DELETE FROM retirement_outbox WHERE request_id = ?", (request_id,))

    def pending(self, limit=50):
        with self._conn() as conn:
            return conn.execute("SELECT * FROM retirement_outbox WHERE status = ? ORDER BY created_at, rowid LIMIT ?",
                                (PENDING, limit)).fetchall()

    def mark_applied(self, request_id, movement_id):
        self._update(request_id, "status = ?, movement_id = ?, last_error = NULL", (APPLIED, movement_id))

    def mark_failed(self, request_id, error):
        self._update(request_id, "status = ?, last_error = ?", (FAILED, error))

    def bump_attempt(self, request_id, error):
        self._update(request_id, "attempts = attempts + 1, last_error = ?", (error,))

    def _update(self, request_id, assignments, values):
        with self._conn() as conn:
            conn.execute("UPDATE retirement_outbox SET {0}, updated_at = ? WHERE request_id = ?".format(assignments),
                         tuple(values) + (_now(), request_id))

    def counts(self):
        with self._conn() as conn:
            rows = conn.execute("SELECT status, count(*) AS n FROM retirement_outbox GROUP BY status").fetchall()
        result = {PENDING: 0, APPLIED: 0, FAILED: 0}
        result.update({r["status"]: r["n"] for r in rows})
        return result

    def purge_applied(self, days=30):
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
        with self._conn() as conn:
            conn.execute("DELETE FROM retirement_outbox WHERE status = ? AND updated_at < ?", (APPLIED, cutoff))
