"""SQLite 数据存储层 — 线程安全"""

import sqlite3
import threading
import os
from datetime import datetime, timedelta
from typing import Optional

from src.constants import DB_PATH, DATA_DIR


class StorageManager:
    def __init__(self, db_path: str = DB_PATH):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_dir()
        self._connect()
        self.init_db()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)

    def _connect(self):
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = NORMAL")
        self._conn.execute("PRAGMA cache_size = -2000")
        self._conn.execute("PRAGMA temp_store = MEMORY")

    def init_db(self):
        with self._lock:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS apps (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    exe_path    TEXT    UNIQUE NOT NULL,
                    exe_name    TEXT    NOT NULL,
                    display_name TEXT,
                    category    TEXT    DEFAULT 'uncategorized',
                    is_hidden   INTEGER DEFAULT 0,
                    first_seen  TEXT    NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_id      INTEGER NOT NULL REFERENCES apps(id),
                    window_title TEXT,
                    start_time  TEXT    NOT NULL,
                    end_time    TEXT,
                    duration_s  INTEGER,
                    is_idle     INTEGER DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_app_id
                    ON sessions(app_id);
                CREATE INDEX IF NOT EXISTS idx_sessions_start_time
                    ON sessions(start_time);
                CREATE INDEX IF NOT EXISTS idx_sessions_date
                    ON sessions(date(start_time));

                CREATE TABLE IF NOT EXISTS daily_summary (
                    date        TEXT    NOT NULL,
                    app_id      INTEGER NOT NULL REFERENCES apps(id),
                    total_seconds INTEGER NOT NULL DEFAULT 0,
                    session_count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (date, app_id)
                );
            """)

    # ── 应用管理 ──

    def get_or_create_app(self, exe_path: str, exe_name: str) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT id FROM apps WHERE exe_path = ?", (exe_path,)
            ).fetchone()
            if row:
                return row["id"]
            now = datetime.now().isoformat()
            cur = self._conn.execute(
                "INSERT INTO apps (exe_path, exe_name, display_name, first_seen) "
                "VALUES (?, ?, ?, ?)",
                (exe_path, exe_name, exe_name, now),
            )
            self._conn.commit()
            return cur.lastrowid

    # ── 会话管理 ──

    def start_session(
        self, app_id: int, window_title: Optional[str] = None
    ) -> int:
        now = datetime.now().isoformat()
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO sessions (app_id, window_title, start_time) "
                "VALUES (?, ?, ?)",
                (app_id, window_title, now),
            )
            self._conn.commit()
            return cur.lastrowid

    def end_session(self, session_id: int):
        now = datetime.now()
        with self._lock:
            row = self._conn.execute(
                "SELECT start_time FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if not row:
                return
            start = datetime.fromisoformat(row["start_time"])
            duration = int((now - start).total_seconds())
            self._conn.execute(
                "UPDATE sessions SET end_time = ?, duration_s = ? WHERE id = ?",
                (now.isoformat(), duration, session_id),
            )
            self._conn.commit()

    # ── 每日汇总 ──

    def flush_daily_summary(self, date_str: Optional[str] = None):
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        with self._lock:
            self._conn.execute(
                "DELETE FROM daily_summary WHERE date = ?", (date_str,)
            )
            self._conn.execute(
                """
                INSERT INTO daily_summary (date, app_id, total_seconds, session_count)
                SELECT date(start_time), app_id,
                       COALESCE(SUM(duration_s), 0),
                       COUNT(*)
                FROM sessions
                WHERE date(start_time) = ? AND duration_s IS NOT NULL
                GROUP BY app_id
                """,
                (date_str,),
            )
            self._conn.commit()

    # ── 查询 ──

    def get_today_summary(self) -> list:
        today = datetime.now().strftime("%Y-%m-%d")
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT a.exe_name, a.display_name,
                       COALESCE(SUM(s.duration_s), 0) AS total_seconds
                FROM sessions s
                JOIN apps a ON a.id = s.app_id
                WHERE date(s.start_time) = ?
                  AND a.is_hidden = 0
                GROUP BY s.app_id
                ORDER BY total_seconds DESC
                """,
                (today,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_today_total_seconds(self) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        with self._lock:
            row = self._conn.execute(
                """
                SELECT COALESCE(SUM(s.duration_s), 0) AS total
                FROM sessions s
                JOIN apps a ON a.id = s.app_id
                WHERE date(s.start_time) = ? AND a.is_hidden = 0
                """,
                (today,),
            ).fetchone()
        return row["total"] if row else 0

    def get_daily_summary(self, date_str: str) -> list:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT a.exe_name, a.display_name,
                       ds.total_seconds, ds.session_count
                FROM daily_summary ds
                JOIN apps a ON a.id = ds.app_id
                WHERE ds.date = ? AND a.is_hidden = 0
                ORDER BY ds.total_seconds DESC
                """,
                (date_str,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_range_summary(self, start_date: str, end_date: str) -> list:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT ds.date, a.exe_name, a.display_name,
                       ds.total_seconds
                FROM daily_summary ds
                JOIN apps a ON a.id = ds.app_id
                WHERE ds.date BETWEEN ? AND ? AND a.is_hidden = 0
                ORDER BY ds.date, ds.total_seconds DESC
                """,
                (start_date, end_date),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_current_app_name(self, session_id: int) -> Optional[str]:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT a.display_name
                FROM sessions s
                JOIN apps a ON a.id = s.app_id
                WHERE s.id = ?
                """,
                (session_id,),
            ).fetchone()
        return row["display_name"] if row else None

    # ── 清理 ──

    def cleanup_old_data(self, days: int = 90):
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with self._lock:
            self._conn.execute(
                "DELETE FROM sessions WHERE date(start_time) < ?", (cutoff,)
            )
            self._conn.execute(
                "DELETE FROM daily_summary WHERE date < ?", (cutoff,)
            )
            self._conn.commit()

    # ── 导出 ──

    def export_csv(self, start_date: str, end_date: str, filepath: str):
        import csv

        rows = self.get_range_summary(start_date, end_date)
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["日期", "应用", "使用时长(秒)", "使用时长"])
            for r in rows:
                secs = r["total_seconds"]
                h, m = divmod(secs, 3600)
                m, s = divmod(m, 60)
                readable = f"{h}h {m}m {s}s"
                writer.writerow([
                    r["date"],
                    r["display_name"] or r["exe_name"],
                    secs,
                    readable,
                ])

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
