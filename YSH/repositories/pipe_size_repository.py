"""SQLite repository for standard-aware pipe geometry records."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from core.pipe_size import PipeSize
from core.pipe_standard import PipeStandard
from database.library_database import LibraryDatabase


class PipeSizeRepositoryConflictError(RuntimeError):
    """Raised when a standard-scoped pipe geometry natural key conflicts."""


class PipeStandardRepositoryConflictError(RuntimeError):
    """Raised when a pipe-standard code conflicts."""


class PipeSizeRepository:
    """Persists pipe standards and their geometry with parameterized SQL."""

    def __init__(self, database: LibraryDatabase) -> None:
        self._database = database

    def create_standard(self, standard: PipeStandard) -> PipeStandard:
        try:
            with self._database.connection() as connection:
                connection.execute(
                    """
                    INSERT INTO pipe_standards (
                      id, code, display_name, description, source, is_active, created_at, modified_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._standard_values(standard),
                )
        except sqlite3.IntegrityError as error:
            raise PipeStandardRepositoryConflictError("Pipe standard code must be unique.") from error
        return standard

    def list_standards(self, *, active_only: bool = False) -> Sequence[PipeStandard]:
        query = "SELECT * FROM pipe_standards"
        if active_only:
            query += " WHERE is_active=1"
        query += " ORDER BY display_name COLLATE NOCASE"
        with self._database.connection() as connection:
            rows = connection.execute(query).fetchall()
        return tuple(self._map_standard(row) for row in rows)

    def get_standard(self, standard_id: UUID) -> PipeStandard | None:
        with self._database.connection() as connection:
            row = connection.execute("SELECT * FROM pipe_standards WHERE id=?", (str(standard_id),)).fetchone()
        return self._map_standard(row) if row else None

    def get_standard_by_code(self, code: str) -> PipeStandard | None:
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM pipe_standards WHERE code=? COLLATE NOCASE", (code,)
            ).fetchone()
        return self._map_standard(row) if row else None

    def get_standard_by_display_name(self, display_name: str) -> PipeStandard | None:
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM pipe_standards WHERE display_name=? COLLATE NOCASE", (display_name,)
            ).fetchone()
        return self._map_standard(row) if row else None

    def create(self, item: PipeSize) -> PipeSize:
        if item.standard_id is None:
            raise ValueError("A pipe size requires an explicit pipe-standard identity.")
        try:
            with self._database.connection() as connection:
                connection.execute(
                    """
                    INSERT INTO pipe_sizes (
                      id, standard_id, nominal_diameter, outside_diameter_mm,
                      wall_thickness_mm, inside_diameter_mm, description, is_system,
                      created_at, modified_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._values(item),
                )
        except sqlite3.IntegrityError as error:
            raise PipeSizeRepositoryConflictError("Pipe size dimensions within a standard must be unique.") from error
        return item

    def get(self, item_id: UUID) -> PipeSize | None:
        with self._database.connection() as connection:
            row = connection.execute(self._select_sql() + " WHERE p.id=?", (str(item_id),)).fetchone()
        return self._map(row) if row else None

    def get_all(self) -> Sequence[PipeSize]:
        with self._database.connection() as connection:
            rows = connection.execute(self._select_sql() + self._ordering_sql()).fetchall()
        return tuple(self._map(row) for row in rows)

    def list_for_standard(self, standard_id: UUID) -> Sequence[PipeSize]:
        with self._database.connection() as connection:
            rows = connection.execute(
                self._select_sql() + " WHERE p.standard_id=?" + self._ordering_sql(), (str(standard_id),)
            ).fetchall()
        return tuple(self._map(row) for row in rows)

    def exists(
        self,
        nominal_diameter: str,
        outside_diameter_mm: float,
        wall_thickness_mm: float,
        standard_id: UUID,
        excluded_id: UUID | None = None,
    ) -> bool:
        sql = (
            "SELECT 1 FROM pipe_sizes WHERE nominal_diameter=? COLLATE NOCASE "
            "AND outside_diameter_mm=? AND wall_thickness_mm=? AND standard_id=?"
        )
        values: tuple[object, ...] = (
            nominal_diameter, outside_diameter_mm, wall_thickness_mm, str(standard_id)
        )
        if excluded_id is not None:
            sql += " AND id != ?"
            values = (*values, str(excluded_id))
        with self._database.connection() as connection:
            return connection.execute(sql, values).fetchone() is not None

    def update(self, item: PipeSize) -> PipeSize:
        if item.standard_id is None:
            raise ValueError("A pipe size requires an explicit pipe-standard identity.")
        try:
            with self._database.connection() as connection:
                cursor = connection.execute(
                    """
                    UPDATE pipe_sizes SET standard_id=?, nominal_diameter=?, outside_diameter_mm=?,
                      wall_thickness_mm=?, inside_diameter_mm=?, description=?, is_system=?,
                      modified_at=? WHERE id=?
                    """,
                    self._values(item)[1:8] + (item.modified_at.isoformat(), str(item.id)),
                )
        except sqlite3.IntegrityError as error:
            raise PipeSizeRepositoryConflictError("Pipe size dimensions within a standard must be unique.") from error
        if cursor.rowcount == 0:
            raise KeyError(f"Pipe size '{item.id}' was not found.")
        return item

    def delete(self, item_id: UUID) -> None:
        with self._database.connection() as connection:
            cursor = connection.execute("DELETE FROM pipe_sizes WHERE id=?", (str(item_id),))
        if cursor.rowcount == 0:
            raise KeyError(f"Pipe size '{item_id}' was not found.")

    @staticmethod
    def _select_sql() -> str:
        return (
            "SELECT p.*, s.code AS standard_code, s.display_name AS standard_name "
            "FROM pipe_sizes p JOIN pipe_standards s ON s.id=p.standard_id"
        )

    @staticmethod
    def _ordering_sql() -> str:
        return (
            " ORDER BY s.display_name COLLATE NOCASE, "
            "CAST(SUBSTR(UPPER(p.nominal_diameter), 3) AS INTEGER), "
            "p.wall_thickness_mm, p.outside_diameter_mm"
        )

    @staticmethod
    def _values(item: PipeSize) -> tuple[object, ...]:
        return (
            str(item.id), str(item.standard_id), item.nominal_diameter,
            item.outside_diameter_mm, item.wall_thickness_mm, item.inside_diameter_mm,
            item.description, int(item.is_system), item.created_at.isoformat(), item.modified_at.isoformat(),
        )

    @staticmethod
    def _standard_values(standard: PipeStandard) -> tuple[object, ...]:
        return (
            str(standard.id), standard.code, standard.display_name, standard.description,
            standard.source, int(standard.is_active), standard.created_at.isoformat(),
            standard.modified_at.isoformat(),
        )

    @staticmethod
    def _map(row: sqlite3.Row) -> PipeSize:
        return PipeSize(
            id=UUID(row["id"]), standard_id=UUID(row["standard_id"]),
            standard=row["standard_name"], nominal_diameter=row["nominal_diameter"],
            outside_diameter_mm=row["outside_diameter_mm"], wall_thickness_mm=row["wall_thickness_mm"],
            inside_diameter_mm=row["inside_diameter_mm"], description=row["description"],
            is_system=bool(row["is_system"]), created_at=datetime.fromisoformat(row["created_at"]),
            modified_at=datetime.fromisoformat(row["modified_at"]),
        )

    @staticmethod
    def _map_standard(row: sqlite3.Row) -> PipeStandard:
        return PipeStandard(
            id=UUID(row["id"]), code=row["code"], display_name=row["display_name"],
            description=row["description"], source=row["source"], is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"]), modified_at=datetime.fromisoformat(row["modified_at"]),
        )
