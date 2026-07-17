"""Local SQLite-backed record of installed mod files, used for duplicate
detection and the in-app activity log."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class ModStore:
    def __init__(self, db_path: Path):
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS installed_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_hash TEXT NOT NULL,
                filename TEXT NOT NULL,
                category TEXT NOT NULL,
                source TEXT NOT NULL,
                installed_path TEXT NOT NULL,
                installed_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_hash ON installed_files(file_hash)"
        )
        self._conn.commit()

    def is_duplicate(self, file_hash: str) -> bool:
        cursor = self._conn.execute(
            "SELECT 1 FROM installed_files WHERE file_hash = ? LIMIT 1", (file_hash,)
        )
        return cursor.fetchone() is not None

    def record_install(
        self, source: str, filename: str, category: str, file_hash: str, installed_path: str
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO installed_files
                (file_hash, filename, category, source, installed_path, installed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                file_hash,
                filename,
                category,
                source,
                installed_path,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._conn.commit()

    def get_activity_log(self) -> list[dict]:
        cursor = self._conn.execute(
            "SELECT filename, category, source, installed_path, installed_at "
            "FROM installed_files ORDER BY installed_at DESC"
        )
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def close(self) -> None:
        self._conn.close()
