"""SQLite schema and versioned migrations for the engineering data library."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from database.base_database import BaseDatabase
from database.en_10220_pipe_size_seed import (
    EN_10220_DESCRIPTION,
    EN_10220_STANDARD,
    EN_10220_STANDARD_CODE,
    iter_en_10220_pipe_sizes,
)
from paths import ApplicationPaths


class LibraryDatabase(BaseDatabase):
    """Creates and migrates the per-user editable engineering library."""

    SCHEMA_VERSION = 4

    def __init__(self, database_path: Path | None = None) -> None:
        super().__init__(database_path or ApplicationPaths().libraries_database_path)

    def create_schema(self, connection: sqlite3.Connection) -> None:
        """Create the final schema or migrate an earlier runtime library safely."""
        connection.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
        version_row = connection.execute("SELECT version FROM schema_version").fetchone()
        version = 0 if version_row is None else int(version_row["version"])
        connection.executescript(
            """
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
            """
        )
        self._create_pipe_standards_table(connection)
        self._seed_en_10220_standard(connection)
        if self._pipe_sizes_table_exists(connection) and not self._pipe_sizes_are_standard_aware(connection):
            self._migrate_pipe_sizes_to_standard_identity(connection)
        self._create_pipe_sizes_table(connection)
        self._seed_en_10220_pipe_sizes(connection)
        self._create_corrosion_allowance_circuits_table(connection)
        self._seed_corrosion_allowance_circuits(connection)
        if version_row is None:
            connection.execute("INSERT INTO schema_version (version) VALUES (?)", (self.SCHEMA_VERSION,))
        elif version < self.SCHEMA_VERSION:
            connection.execute("UPDATE schema_version SET version=?", (self.SCHEMA_VERSION,))

    @staticmethod
    def _pipe_sizes_table_exists(connection: sqlite3.Connection) -> bool:
        return connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='pipe_sizes'"
        ).fetchone() is not None

    @staticmethod
    def _pipe_sizes_are_standard_aware(connection: sqlite3.Connection) -> bool:
        return "standard_id" in {
            row["name"] for row in connection.execute("PRAGMA table_info(pipe_sizes)")
        }

    @staticmethod
    def _create_pipe_standards_table(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pipe_standards (
              id TEXT PRIMARY KEY,
              code TEXT NOT NULL COLLATE NOCASE UNIQUE,
              display_name TEXT NOT NULL,
              description TEXT NOT NULL DEFAULT '',
              source TEXT NOT NULL DEFAULT '',
              is_active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              modified_at TEXT NOT NULL
            )
            """
        )

    @staticmethod
    def _create_pipe_sizes_table(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pipe_sizes (
              id TEXT PRIMARY KEY,
              standard_id TEXT NOT NULL REFERENCES pipe_standards(id),
              nominal_diameter TEXT NOT NULL COLLATE NOCASE,
              outside_diameter_mm REAL NOT NULL,
              wall_thickness_mm REAL NOT NULL,
              inside_diameter_mm REAL NOT NULL,
              description TEXT NOT NULL DEFAULT '',
              is_system INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              modified_at TEXT NOT NULL,
              UNIQUE(standard_id, nominal_diameter, outside_diameter_mm, wall_thickness_mm)
            )
            """
        )

    def _migrate_pipe_sizes_to_standard_identity(self, connection: sqlite3.Connection) -> None:
        """Move V1/V2 free-text standards to explicit standard identities.

        Exact EN 10220 spellings are linked to the canonical seed standard.
        Other historic values become distinct ``LEGACY_*`` metadata records;
        this preserves their provenance without claiming an unverified standard.
        """
        legacy_table = "pipe_sizes_pre_phase_2a"
        connection.execute(f"ALTER TABLE pipe_sizes RENAME TO {legacy_table}")
        self._create_pipe_sizes_table(connection)
        columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({legacy_table})")}
        for row in connection.execute(f"SELECT * FROM {legacy_table}").fetchall():
            standard_id = self._standard_id_for_legacy_row(connection, row, columns)
            connection.execute(
                """
                INSERT INTO pipe_sizes (
                  id, standard_id, nominal_diameter, outside_diameter_mm,
                  wall_thickness_mm, inside_diameter_mm, description, is_system,
                  created_at, modified_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"], standard_id, row["nominal_diameter"],
                    row["outside_diameter_mm"], row["wall_thickness_mm"],
                    row["inside_diameter_mm"], row["description"] if "description" in columns else "",
                    row["is_system"] if "is_system" in columns else 0,
                    row["created_at"], row["modified_at"],
                ),
            )
        connection.execute(f"DROP TABLE {legacy_table}")

    def _standard_id_for_legacy_row(
        self, connection: sqlite3.Connection, row: sqlite3.Row, columns: set[str]
    ) -> str:
        legacy_standard = str(row["standard"]).strip() if "standard" in columns else ""
        if legacy_standard.replace("_", " ").casefold() == "en 10220" or (
            not legacy_standard
            and bool(row["is_system"] if "is_system" in columns else False)
            and self._matches_en_10220_seed_geometry(row)
        ):
            return self._en_10220_id(connection)
        return self._ensure_legacy_standard(connection, legacy_standard)

    @staticmethod
    def _matches_en_10220_seed_geometry(row: sqlite3.Row) -> bool:
        """Recognize only exact historic system rows that match the local seed."""
        return (
            str(row["nominal_diameter"]),
            float(row["outside_diameter_mm"]),
            float(row["wall_thickness_mm"]),
            float(row["inside_diameter_mm"]),
        ) in set(iter_en_10220_pipe_sizes())

    @staticmethod
    def _ensure_legacy_standard(connection: sqlite3.Connection, legacy_standard: str) -> str:
        label = legacy_standard or "Belirsiz önceki kütüphane standardı"
        code = "LEGACY_" + hashlib.sha256(label.casefold().encode("utf-8")).hexdigest()[:12].upper()
        existing = connection.execute(
            "SELECT id FROM pipe_standards WHERE code=? COLLATE NOCASE", (code,)
        ).fetchone()
        if existing is not None:
            return str(existing["id"])
        timestamp = datetime.now(timezone.utc).isoformat()
        standard_id = str(uuid4())
        connection.execute(
            """
            INSERT INTO pipe_standards (
              id, code, display_name, description, source, is_active, created_at, modified_at
            ) VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                standard_id, code, f"Mevcut Kütüphane: {label}",
                "Phase 2A sırasında serbest metin standart bilgisinden taşındı.",
                "Önceki kütüphane kaydı", timestamp, timestamp,
            ),
        )
        return str(standard_id)

    @staticmethod
    def _seed_en_10220_standard(connection: sqlite3.Connection) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        connection.execute(
            """
            INSERT OR IGNORE INTO pipe_standards (
              id, code, display_name, description, source, is_active, created_at, modified_at
            ) VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (str(uuid4()), EN_10220_STANDARD_CODE, EN_10220_STANDARD, EN_10220_DESCRIPTION, "EN 10220", timestamp, timestamp),
        )

    @staticmethod
    def _en_10220_id(connection: sqlite3.Connection) -> str:
        row = connection.execute(
            "SELECT id FROM pipe_standards WHERE code=? COLLATE NOCASE", (EN_10220_STANDARD_CODE,)
        ).fetchone()
        if row is None:
            raise RuntimeError("EN 10220 pipe standard was not initialized.")
        return str(row["id"])

    def _seed_en_10220_pipe_sizes(self, connection: sqlite3.Connection) -> None:
        """Seed only verified EN 10220 geometry and never overwrite user data."""
        timestamp = datetime.now(timezone.utc).isoformat()
        standard_id = self._en_10220_id(connection)
        connection.executemany(
            """
            INSERT OR IGNORE INTO pipe_sizes (
              id, standard_id, nominal_diameter, outside_diameter_mm,
              wall_thickness_mm, inside_diameter_mm, description, is_system,
              created_at, modified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            [
                (
                    str(uuid4()), standard_id, nominal_diameter, outside_diameter_mm,
                    wall_thickness_mm, inside_diameter_mm, EN_10220_DESCRIPTION,
                    timestamp, timestamp,
                )
                for nominal_diameter, outside_diameter_mm, wall_thickness_mm, inside_diameter_mm
                in iter_en_10220_pipe_sizes()
            ],
        )

    @staticmethod
    def _create_corrosion_allowance_circuits_table(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS corrosion_allowance_circuits (
              id TEXT PRIMARY KEY,
              code TEXT NOT NULL COLLATE NOCASE UNIQUE,
              display_name TEXT NOT NULL,
              default_corrosion_allowance_mm REAL NOT NULL,
              description TEXT NOT NULL DEFAULT '',
              is_active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              modified_at TEXT NOT NULL
            )
            """
        )

    @staticmethod
    def _seed_corrosion_allowance_circuits(connection: sqlite3.Connection) -> None:
        """Seed only the three editable D243 product defaults, without overwrites."""
        timestamp = datetime.now(timezone.utc).isoformat()
        connection.executemany(
            """
            INSERT OR IGNORE INTO corrosion_allowance_circuits (
              id, code, display_name, default_corrosion_allowance_mm,
              description, is_active, created_at, modified_at
            ) VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            [
                (str(uuid4()), "FUEL", "Yakıt Devresi", 1.0, "D243 varsayılan korozyon artımı.", timestamp, timestamp),
                (str(uuid4()), "SEA_WATER", "Deniz Suyu Devresi", 3.0, "D243 varsayılan korozyon artımı.", timestamp, timestamp),
                (str(uuid4()), "BOILER_BLOWDOWN", "Kazan Blöf Devresi", 1.5, "D243 varsayılan korozyon artımı.", timestamp, timestamp),
            ],
        )
