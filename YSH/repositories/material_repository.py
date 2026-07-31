"""SQLite repository for material library records."""
from __future__ import annotations
import sqlite3
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID
from core.material import Material
from database.library_database import LibraryDatabase

class MaterialRepositoryConflictError(RuntimeError):
    """Raised when a material designation conflicts with an existing record."""

class MaterialRepository:
    """Persists material records using parameterized SQLite statements."""
    def __init__(self, database: LibraryDatabase) -> None:
        """Create the repository with its database dependency."""
        self._database = database
    def create(self, material: Material) -> Material:
        """Persist a new material."""
        try:
            with self._database.connection() as connection:
                connection.execute("INSERT INTO materials VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", self._values(material))
        except sqlite3.IntegrityError as error:
            raise MaterialRepositoryConflictError("Material designation must be unique.") from error
        return material
    def get(self, material_id: UUID) -> Material | None:
        """Retrieve a material by identifier."""
        with self._database.connection() as connection:
            row = connection.execute("SELECT * FROM materials WHERE id = ?", (str(material_id),)).fetchone()
        return self._map(row) if row else None
    def get_all(self) -> Sequence[Material]:
        """Return all materials in designation order."""
        with self._database.connection() as connection:
            rows = connection.execute("SELECT * FROM materials ORDER BY designation COLLATE NOCASE").fetchall()
        return tuple(self._map(row) for row in rows)
    def exists_designation(self, designation: str, excluded_id: UUID | None = None) -> bool:
        """Return whether another material has this designation."""
        sql = "SELECT 1 FROM materials WHERE designation = ? COLLATE NOCASE"
        values: tuple[str, ...] = (designation,)
        if excluded_id is not None:
            sql += " AND id != ?"; values = (designation, str(excluded_id))
        with self._database.connection() as connection:
            return connection.execute(sql, values).fetchone() is not None
    def update(self, material: Material) -> Material:
        """Persist changes to an existing material."""
        try:
            with self._database.connection() as connection:
                cursor = connection.execute("UPDATE materials SET name=?, designation=?, standard=?, yield_strength_mpa=?, roughness_mm=?, description=?, source=?, is_system=?, modified_at=? WHERE id=?", self._values(material)[1:9] + (material.modified_at.isoformat(), str(material.id)))
        except sqlite3.IntegrityError as error:
            raise MaterialRepositoryConflictError("Material designation must be unique.") from error
        if cursor.rowcount == 0: raise KeyError(f"Material '{material.id}' was not found.")
        return material
    def delete(self, material_id: UUID) -> None:
        """Delete a material by identifier."""
        with self._database.connection() as connection:
            cursor = connection.execute("DELETE FROM materials WHERE id = ?", (str(material_id),))
        if cursor.rowcount == 0: raise KeyError(f"Material '{material_id}' was not found.")
    @staticmethod
    def _values(item: Material) -> tuple[object, ...]:
        return (str(item.id), item.name, item.designation, item.standard, item.yield_strength_mpa, item.roughness_mm, item.description, item.source, int(item.is_system), item.created_at.isoformat(), item.modified_at.isoformat())
    @staticmethod
    def _map(row: sqlite3.Row) -> Material:
        return Material(id=UUID(row["id"]), name=row["name"], designation=row["designation"], standard=row["standard"], yield_strength_mpa=row["yield_strength_mpa"], roughness_mm=row["roughness_mm"], description=row["description"], source=row["source"], is_system=bool(row["is_system"]), created_at=datetime.fromisoformat(row["created_at"]), modified_at=datetime.fromisoformat(row["modified_at"]))
