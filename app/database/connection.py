"""
Gestión de la conexión SQLite.

Proporciona inicialización del schema, transacciones con commit/rollback
y helpers ``execute`` / ``fetchall`` usados por los repositorios.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Iterable, Optional

from app.config import DB_PATH, SCHEMA_PATH


class DatabaseConnection:
    """Acceso a SQLite con claves foráneas activadas y transacciones."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path else DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._db_path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self, schema_path: Path | None = None) -> None:
        path = schema_path or SCHEMA_PATH
        sql = path.read_text(encoding="utf-8")
        with self.connect() as conn:
            conn.executescript(sql)
            conn.commit()

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(
        self,
        sql: str,
        params: Iterable | None = None,
        *,
        fetchone: bool = False,
        fetchall: bool = False,
        lastrowid: bool = False,
    ):
        params = params or ()
        with self.connect() as conn:
            cur = conn.execute(sql, params)
            conn.commit()
            if lastrowid:
                return cur.lastrowid
            if fetchone:
                return cur.fetchone()
            if fetchall:
                return cur.fetchall()
            return cur.rowcount

    def fetchall(self, sql: str, params: Iterable | None = None) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return list(conn.execute(sql, params or ()))

    def fetchone(self, sql: str, params: Iterable | None = None) -> Optional[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(sql, params or ()).fetchone()


_db: DatabaseConnection | None = None


def get_db() -> DatabaseConnection:
    global _db
    if _db is None:
        _db = DatabaseConnection()
    return _db
