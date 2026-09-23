"""SQLite repository for pipe-size library records."""
from __future__ import annotations
import sqlite3
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID
from core.pipe_size import PipeSize
from database.library_database import LibraryDatabase

class PipeSizeRepositoryConflictError(RuntimeError):
    """Raised when a pipe-size natural key conflicts."""
class PipeSizeRepository:
    """Persists pipe size records with parameterized SQLite queries."""
    def __init__(self, database: LibraryDatabase) -> None: self._database = database
    def create(self, item: PipeSize) -> PipeSize:
        """Persist a new pipe size."""
        try:
            with self._database.connection() as c: c.execute("INSERT INTO pipe_sizes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", self._values(item))
        except sqlite3.IntegrityError as error: raise PipeSizeRepositoryConflictError("Pipe size dimensions and standard must be unique.") from error
        return item
    def get(self, item_id: UUID) -> PipeSize | None:
        """Retrieve a pipe size by identifier."""
        with self._database.connection() as c: row = c.execute("SELECT * FROM pipe_sizes WHERE id=?", (str(item_id),)).fetchone()
        return self._map(row) if row else None
    def get_all(self) -> Sequence[PipeSize]:
        """Return every stored pipe size."""
        with self._database.connection() as c: rows = c.execute("SELECT * FROM pipe_sizes ORDER BY CAST(SUBSTR(UPPER(nominal_diameter), 3) AS INTEGER), wall_thickness_mm, outside_diameter_mm, standard COLLATE NOCASE").fetchall()
        return tuple(self._map(row) for row in rows)
    def exists(self, nominal_diameter: str, outside_diameter_mm: float, wall_thickness_mm: float, standard: str, excluded_id: UUID | None = None) -> bool:
        """Return whether another record has the natural pipe-size key."""
        sql = "SELECT 1 FROM pipe_sizes WHERE nominal_diameter=? COLLATE NOCASE AND outside_diameter_mm=? AND wall_thickness_mm=? AND standard=? COLLATE NOCASE"; values: tuple[object, ...] = (nominal_diameter, outside_diameter_mm, wall_thickness_mm, standard)
        if excluded_id is not None: sql += " AND id != ?"; values = (*values, str(excluded_id))
        with self._database.connection() as c: return c.execute(sql, values).fetchone() is not None
    def update(self, item: PipeSize) -> PipeSize:
        """Persist an existing pipe size."""
        try:
            with self._database.connection() as c: cursor = c.execute("UPDATE pipe_sizes SET nominal_diameter=?, outside_diameter_mm=?, wall_thickness_mm=?, inside_diameter_mm=?, standard=?, description=?, is_system=?, modified_at=? WHERE id=?", self._values(item)[1:8] + (item.modified_at.isoformat(), str(item.id)))
        except sqlite3.IntegrityError as error: raise PipeSizeRepositoryConflictError("Pipe size dimensions and standard must be unique.") from error
        if cursor.rowcount == 0: raise KeyError(f"Pipe size '{item.id}' was not found.")
        return item
    def delete(self, item_id: UUID) -> None:
        """Delete a pipe size."""
        with self._database.connection() as c: cursor = c.execute("DELETE FROM pipe_sizes WHERE id=?", (str(item_id),))
        if cursor.rowcount == 0: raise KeyError(f"Pipe size '{item_id}' was not found.")
    @staticmethod
    def _values(item: PipeSize) -> tuple[object, ...]: return (str(item.id), item.nominal_diameter, item.outside_diameter_mm, item.wall_thickness_mm, item.inside_diameter_mm, item.standard, item.description, int(item.is_system), item.created_at.isoformat(), item.modified_at.isoformat())
    @staticmethod
    def _map(row: sqlite3.Row) -> PipeSize: return PipeSize(id=UUID(row["id"]), nominal_diameter=row["nominal_diameter"], outside_diameter_mm=row["outside_diameter_mm"], wall_thickness_mm=row["wall_thickness_mm"], inside_diameter_mm=row["inside_diameter_mm"], standard=row["standard"], description=row["description"], is_system=bool(row["is_system"]), created_at=datetime.fromisoformat(row["created_at"]), modified_at=datetime.fromisoformat(row["modified_at"]))
