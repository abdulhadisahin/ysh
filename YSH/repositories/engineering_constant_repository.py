"""SQLite repository for engineering constants."""
from __future__ import annotations
import sqlite3
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID
from core.engineering_constant import EngineeringConstant
from database.library_database import LibraryDatabase

class EngineeringConstantRepositoryConflictError(RuntimeError):
    """Raised when an engineering-constant key conflicts."""
class EngineeringConstantRepository:
    """Persists editable engineering constants."""
    def __init__(self, database: LibraryDatabase) -> None: self._database = database
    def create(self, item: EngineeringConstant) -> EngineeringConstant:
        """Persist a new engineering constant."""
        try:
            with self._database.connection() as c: c.execute("INSERT INTO engineering_constants VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", self._values(item))
        except sqlite3.IntegrityError as error: raise EngineeringConstantRepositoryConflictError("Constant key must be unique.") from error
        return item
    def get(self, item_id: UUID) -> EngineeringConstant | None:
        """Retrieve a constant by identifier."""
        with self._database.connection() as c: row=c.execute("SELECT * FROM engineering_constants WHERE id=?", (str(item_id),)).fetchone()
        return self._map(row) if row else None
    def get_by_key(self, key: str) -> EngineeringConstant | None:
        """Retrieve a constant by case-insensitive key."""
        with self._database.connection() as c: row=c.execute("SELECT * FROM engineering_constants WHERE key=? COLLATE NOCASE", (key,)).fetchone()
        return self._map(row) if row else None
    def get_all(self) -> Sequence[EngineeringConstant]:
        """Return all constants ordered by key."""
        with self._database.connection() as c: rows=c.execute("SELECT * FROM engineering_constants ORDER BY key COLLATE NOCASE").fetchall()
        return tuple(self._map(row) for row in rows)
    def exists_key(self, key: str, excluded_id: UUID | None=None) -> bool:
        """Return whether a different constant has this key."""
        sql="SELECT 1 FROM engineering_constants WHERE key=? COLLATE NOCASE"; values:tuple[str,...]=(key,)
        if excluded_id is not None: sql += " AND id != ?"; values=(key,str(excluded_id))
        with self._database.connection() as c: return c.execute(sql,values).fetchone() is not None
    def update(self,item:EngineeringConstant)->EngineeringConstant:
        """Persist an existing constant."""
        try:
            with self._database.connection() as c: cursor=c.execute("UPDATE engineering_constants SET key=?,display_name=?,value=?,unit=?,description=?,source=?,is_system=?,modified_at=? WHERE id=?",self._values(item)[1:8]+(item.modified_at.isoformat(),str(item.id)))
        except sqlite3.IntegrityError as error: raise EngineeringConstantRepositoryConflictError("Constant key must be unique.") from error
        if cursor.rowcount==0: raise KeyError(f"Constant '{item.id}' was not found.")
        return item
    def delete(self,item_id:UUID)->None:
        """Delete a constant."""
        with self._database.connection() as c: cursor=c.execute("DELETE FROM engineering_constants WHERE id=?",(str(item_id),))
        if cursor.rowcount==0: raise KeyError(f"Constant '{item_id}' was not found.")
    @staticmethod
    def _values(item:EngineeringConstant)->tuple[object,...]: return (str(item.id),item.key,item.display_name,item.value,item.unit,item.description,item.source,int(item.is_system),item.created_at.isoformat(),item.modified_at.isoformat())
    @staticmethod
    def _map(row:sqlite3.Row)->EngineeringConstant: return EngineeringConstant(id=UUID(row["id"]),key=row["key"],display_name=row["display_name"],value=row["value"],unit=row["unit"],description=row["description"],source=row["source"],is_system=bool(row["is_system"]),created_at=datetime.fromisoformat(row["created_at"]),modified_at=datetime.fromisoformat(row["modified_at"]))
