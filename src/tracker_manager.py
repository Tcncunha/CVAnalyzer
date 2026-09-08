"""
SQLite application tracker — persistence for job application tracking.

Uses the stdlib sqlite3 module. Each function opens its own short-lived
connection, safe for repeated Streamlit reruns. WAL mode is enabled.
"""

import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "tracker.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    cv_version TEXT DEFAULT '',
    status TEXT DEFAULT 'applied',
    job_url TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    applied_date TEXT DEFAULT (datetime('now')),
    updated_date TEXT DEFAULT (datetime('now')),
    follow_up_date TEXT DEFAULT ''
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.execute(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _default_follow_up(applied_date: str) -> str:
    base = date.today()
    try:
        base = date.fromisoformat(applied_date[:10])
    except ValueError:
        pass
    return (base + timedelta(days=7)).isoformat()


def add_application(company: str, role: str, cv_version: str = "", job_url: str = "", notes: str = "", follow_up_date: str = "") -> int:
    conn = _connect()
    try:
        applied_date = date.today().isoformat()
        if not follow_up_date:
            follow_up_date = _default_follow_up(applied_date)
        cur = conn.execute(
            """INSERT INTO applications
               (company, role, cv_version, job_url, notes, applied_date, follow_up_date)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (company, role, cv_version, job_url, notes, applied_date, follow_up_date),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_application(app_id: int, status: str | None = None, notes: str | None = None, follow_up_date: str | None = None, cv_version: str | None = None) -> None:
    conn = _connect()
    try:
        fields = []
        params = []
        if status is not None:
            fields.append("status = ?")
            params.append(status)
        if notes is not None:
            fields.append("notes = ?")
            params.append(notes)
        if follow_up_date is not None:
            fields.append("follow_up_date = ?")
            params.append(follow_up_date)
        if cv_version is not None:
            fields.append("cv_version = ?")
            params.append(cv_version)
        if fields:
            fields.append("updated_date = datetime('now')")
            params.append(app_id)
            conn.execute(f"UPDATE applications SET {', '.join(fields)} WHERE id = ?", params)
            conn.commit()
    finally:
        conn.close()


def delete_application(app_id: int) -> None:
    conn = _connect()
    try:
        conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))
        conn.commit()
    finally:
        conn.close()


def list_applications() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM applications ORDER BY applied_date DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_stats(cv_version: str | None = None) -> dict:
    conn = _connect()
    try:
        if cv_version:
            all_rows = conn.execute("SELECT status FROM applications WHERE cv_version = ?", (cv_version,)).fetchall()
        else:
            all_rows = conn.execute("SELECT status FROM applications").fetchall()
        total = len(all_rows)
        by_status: dict[str, int] = {}
        for r in all_rows:
            status = r["status"]
            by_status[status] = by_status.get(status, 0) + 1
        interviews = by_status.get("interview", 0)
        offers = by_status.get("offer", 0)
        return {
            "total": total,
            "by_status": by_status,
            "conversion_interview": round(interviews / total * 100, 1) if total else 0.0,
            "conversion_offer": round(offers / total * 100, 1) if total else 0.0,
        }
    finally:
        conn.close()


def clear_all() -> None:
    conn = _connect()
    try:
        conn.execute("DELETE FROM applications")
        conn.commit()
    finally:
        conn.close()
