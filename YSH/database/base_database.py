"""Reusable SQLite database infrastructure."""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class BaseDatabase(ABC):
    """Provides schema initialization and safe SQLite connections."""

    def __init__(self, database_path: Path) -> None:
        """Configure the SQLite database file used by a concrete database."""
        self._database_path = database_path

    @property
    def database_path(self) -> Path:
        """Return the local path of the SQLite database file."""
        return self._database_path

    def initialize(self) -> None:
        """Create the database file and its schema when they do not exist."""
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            self.create_schema(connection)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Yield a transaction-safe SQLite connection with foreign keys enabled."""
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @abstractmethod
    def create_schema(self, connection: sqlite3.Connection) -> None:
        """Create the database schema required by the concrete database."""
