"""SQLite schema for the editable YSH engineering data library."""
from __future__ import annotations
import sqlite3
from pathlib import Path
from core.constants import LIBRARY_DATABASE_FILENAME
from database.base_database import BaseDatabase

class LibraryDatabase(BaseDatabase):
    """Creates and migrates the local engineering library database."""
    SCHEMA_VERSION = 1
    def __init__(self, database_path: Path | None = None) -> None:
        """Configure a production or test-only library database path."""
        super().__init__(database_path or Path(__file__).resolve().parent / LIBRARY_DATABASE_FILENAME)

    def create_schema(self, connection: sqlite3.Connection) -> None:
        """Create version metadata and all Version 1 library tables."""
        connection.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
        if connection.execute("SELECT 1 FROM schema_version").fetchone() is None:
            connection.execute("INSERT INTO schema_version (version) VALUES (?)", (self.SCHEMA_VERSION,))
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS materials (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, designation TEXT NOT NULL COLLATE NOCASE UNIQUE,
              standard TEXT NOT NULL DEFAULT '', yield_strength_mpa REAL, roughness_mm REAL NOT NULL,
              description TEXT NOT NULL DEFAULT '', source TEXT NOT NULL, is_system INTEGER NOT NULL,
              created_at TEXT NOT NULL, modified_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS pipe_sizes (
              id TEXT PRIMARY KEY, nominal_diameter TEXT NOT NULL COLLATE NOCASE, outside_diameter_mm REAL NOT NULL,
              wall_thickness_mm REAL NOT NULL, inside_diameter_mm REAL NOT NULL, standard TEXT NOT NULL COLLATE NOCASE,
              description TEXT NOT NULL DEFAULT '', is_system INTEGER NOT NULL, created_at TEXT NOT NULL, modified_at TEXT NOT NULL,
              UNIQUE(nominal_diameter, standard));
            CREATE TABLE IF NOT EXISTS engineering_constants (
              id TEXT PRIMARY KEY, key TEXT NOT NULL COLLATE NOCASE UNIQUE, display_name TEXT NOT NULL, value REAL NOT NULL,
              unit TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '', source TEXT NOT NULL,
              is_system INTEGER NOT NULL, created_at TEXT NOT NULL, modified_at TEXT NOT NULL);
        """)
