"""SQLite schema for the editable YSH engineering data library."""
from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from core.constants import LIBRARY_DATABASE_FILENAME
from database.base_database import BaseDatabase
from database.en_10220_pipe_size_seed import (
    EN_10220_DESCRIPTION,
    EN_10220_STANDARD,
    iter_en_10220_pipe_sizes,
)
from paths import ApplicationPaths

class LibraryDatabase(BaseDatabase):
    """Creates and migrates the local engineering library database."""
    SCHEMA_VERSION = 2
    def __init__(self, database_path: Path | None = None) -> None:
        """Configure a production or test-only library database path."""
        super().__init__(database_path or ApplicationPaths().libraries_database_path)

    def create_schema(self, connection: sqlite3.Connection) -> None:
        """Create version metadata and all Version 1 library tables."""
        connection.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
        version_row = connection.execute("SELECT version FROM schema_version").fetchone()
        version = 0 if version_row is None else int(version_row["version"])
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS materials (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, designation TEXT NOT NULL COLLATE NOCASE UNIQUE,
              standard TEXT NOT NULL DEFAULT '', yield_strength_mpa REAL, roughness_mm REAL NOT NULL,
              description TEXT NOT NULL DEFAULT '', source TEXT NOT NULL, is_system INTEGER NOT NULL,
              created_at TEXT NOT NULL, modified_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS engineering_constants (
              id TEXT PRIMARY KEY, key TEXT NOT NULL COLLATE NOCASE UNIQUE, display_name TEXT NOT NULL, value REAL NOT NULL,
              unit TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '', source TEXT NOT NULL,
              is_system INTEGER NOT NULL, created_at TEXT NOT NULL, modified_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS pump_references (
              id TEXT PRIMARY KEY, ship_name TEXT NOT NULL COLLATE NOCASE UNIQUE,
              fuel_capacity_m3 REAL NOT NULL, pump_capacity_m3h REAL NOT NULL,
              description TEXT NOT NULL DEFAULT '', source TEXT NOT NULL,
              created_at TEXT NOT NULL, modified_at TEXT NOT NULL);
        """)
        if version < 2 and self._pipe_sizes_table_exists(connection):
            self._migrate_pipe_sizes(connection)
        self._create_pipe_sizes_table(connection)
        self._seed_en_10220_pipe_sizes(connection)
        if version_row is None:
            connection.execute("INSERT INTO schema_version (version) VALUES (?)", (self.SCHEMA_VERSION,))
        elif version < self.SCHEMA_VERSION:
            connection.execute("UPDATE schema_version SET version=?", (self.SCHEMA_VERSION,))

    @staticmethod
    def _pipe_sizes_table_exists(connection: sqlite3.Connection) -> bool:
        """Return whether an existing database contains the pipe-size table."""
        return connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='pipe_sizes'"
        ).fetchone() is not None

    @staticmethod
    def _create_pipe_sizes_table(connection: sqlite3.Connection) -> None:
        """Create the multi-wall pipe-size table using its logical natural key."""
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pipe_sizes (
              id TEXT PRIMARY KEY,
              nominal_diameter TEXT NOT NULL COLLATE NOCASE,
              outside_diameter_mm REAL NOT NULL,
              wall_thickness_mm REAL NOT NULL,
              inside_diameter_mm REAL NOT NULL,
              standard TEXT NOT NULL COLLATE NOCASE,
              description TEXT NOT NULL DEFAULT '',
              is_system INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              modified_at TEXT NOT NULL,
              UNIQUE(standard, nominal_diameter, outside_diameter_mm, wall_thickness_mm)
            )
            """
        )

    def _migrate_pipe_sizes(self, connection: sqlite3.Connection) -> None:
        """Replace the Version 1 DN-only unique key without losing user records."""
        connection.execute("ALTER TABLE pipe_sizes RENAME TO pipe_sizes_v1")
        self._create_pipe_sizes_table(connection)
        connection.execute(
            """
            INSERT INTO pipe_sizes (
              id, nominal_diameter, outside_diameter_mm, wall_thickness_mm,
              inside_diameter_mm, standard, description, is_system, created_at,
              modified_at
            )
            SELECT id, nominal_diameter, outside_diameter_mm, wall_thickness_mm,
                   inside_diameter_mm, standard, description, is_system,
                   created_at, modified_at
            FROM pipe_sizes_v1
            """
        )
        connection.execute("DROP TABLE pipe_sizes_v1")

    @staticmethod
    def _seed_en_10220_pipe_sizes(connection: sqlite3.Connection) -> None:
        """Insert local verified EN 10220 rows idempotently and preserve edits."""
        timestamp = datetime.now(timezone.utc).isoformat()
        connection.executemany(
            """
            INSERT OR IGNORE INTO pipe_sizes (
              id, nominal_diameter, outside_diameter_mm, wall_thickness_mm,
              inside_diameter_mm, standard, description, is_system, created_at,
              modified_at
            ) VALUES (lower(hex(randomblob(16))), ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            [
                (
                    nominal_diameter,
                    outside_diameter_mm,
                    wall_thickness_mm,
                    inside_diameter_mm,
                    EN_10220_STANDARD,
                    EN_10220_DESCRIPTION,
                    timestamp,
                    timestamp,
                )
                for (
                    nominal_diameter,
                    outside_diameter_mm,
                    wall_thickness_mm,
                    inside_diameter_mm,
                ) in iter_en_10220_pipe_sizes()
            ],
        )
