from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path.home() / ".sts2tracker" / "queue.db"


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS pending (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path  TEXT NOT NULL UNIQUE,
                queued_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS uploaded (
                file_path   TEXT PRIMARY KEY,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def enqueue(file_path: str) -> None:
    """送信済みでなければキューに追加する。"""
    with _conn() as conn:
        already = conn.execute(
            "SELECT 1 FROM uploaded WHERE file_path = ?", (file_path,)
        ).fetchone()
        if already:
            return
        try:
            conn.execute("INSERT INTO pending (file_path) VALUES (?)", (file_path,))
        except sqlite3.IntegrityError:
            pass  # 既にキュー済み


def mark_uploaded(file_path: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM pending WHERE file_path = ?", (file_path,))
        conn.execute(
            "INSERT OR REPLACE INTO uploaded (file_path) VALUES (?)", (file_path,)
        )


def is_uploaded(file_path: str) -> bool:
    with _conn() as conn:
        return bool(
            conn.execute(
                "SELECT 1 FROM uploaded WHERE file_path = ?", (file_path,)
            ).fetchone()
        )


def get_pending() -> list[str]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT file_path FROM pending ORDER BY queued_at"
        ).fetchall()
        return [r[0] for r in rows]
