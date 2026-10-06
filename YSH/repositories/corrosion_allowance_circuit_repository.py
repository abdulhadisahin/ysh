"""SQLite persistence for editable circuit corrosion-allowance defaults."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from core.corrosion_allowance_circuit import CorrosionAllowanceCircuit
from database.library_database import LibraryDatabase


class CorrosionAllowanceCircuitRepositoryConflictError(RuntimeError):
    """Raised when a circuit code is already present."""


class CorrosionAllowanceCircuitRepository:
    def __init__(self, database: LibraryDatabase) -> None:
        self._database = database

    def create(self, item: CorrosionAllowanceCircuit) -> CorrosionAllowanceCircuit:
        try:
            with self._database.connection() as connection:
                connection.execute(
                    "INSERT INTO corrosion_allowance_circuits VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    self._values(item),
                )
        except sqlite3.IntegrityError as error:
            raise CorrosionAllowanceCircuitRepositoryConflictError from error
        return item

    def get(self, item_id: UUID) -> CorrosionAllowanceCircuit | None:
        with self._database.connection() as connection:
            row = connection.execute("SELECT * FROM corrosion_allowance_circuits WHERE id=?", (str(item_id),)).fetchone()
        return self._map(row) if row else None

    def get_by_code(self, code: str) -> CorrosionAllowanceCircuit | None:
        with self._database.connection() as connection:
            row = connection.execute("SELECT * FROM corrosion_allowance_circuits WHERE code=? COLLATE NOCASE", (code,)).fetchone()
        return self._map(row) if row else None

    def list(self, *, active_only: bool = False) -> Sequence[CorrosionAllowanceCircuit]:
        query = "SELECT * FROM corrosion_allowance_circuits"
        if active_only:
            query += " WHERE is_active=1"
        query += " ORDER BY display_name COLLATE NOCASE"
        with self._database.connection() as connection:
            rows = connection.execute(query).fetchall()
        return tuple(self._map(row) for row in rows)

    def update(self, item: CorrosionAllowanceCircuit) -> CorrosionAllowanceCircuit:
        try:
            with self._database.connection() as connection:
                cursor = connection.execute(
                    "UPDATE corrosion_allowance_circuits SET code=?, display_name=?, default_corrosion_allowance_mm=?, description=?, is_active=?, modified_at=? WHERE id=?",
                    self._values(item)[1:6] + (item.modified_at.isoformat(), str(item.id)),
                )
        except sqlite3.IntegrityError as error:
            raise CorrosionAllowanceCircuitRepositoryConflictError from error
        if cursor.rowcount == 0:
            raise KeyError(item.id)
        return item

    def delete(self, item_id: UUID) -> None:
        with self._database.connection() as connection:
            cursor = connection.execute("DELETE FROM corrosion_allowance_circuits WHERE id=?", (str(item_id),))
        if cursor.rowcount == 0:
            raise KeyError(item_id)

    @staticmethod
    def _values(item: CorrosionAllowanceCircuit) -> tuple[object, ...]:
        return (str(item.id), item.code, item.display_name, item.default_corrosion_allowance_mm,
                item.description, int(item.is_active), item.created_at.isoformat(), item.modified_at.isoformat())

    @staticmethod
    def _map(row: sqlite3.Row) -> CorrosionAllowanceCircuit:
        return CorrosionAllowanceCircuit(
            id=UUID(row["id"]), code=row["code"], display_name=row["display_name"],
            default_corrosion_allowance_mm=row["default_corrosion_allowance_mm"],
            description=row["description"], is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"]), modified_at=datetime.fromisoformat(row["modified_at"]),
        )
