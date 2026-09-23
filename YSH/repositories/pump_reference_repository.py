"""SQLite repository for saved fuel transfer pump references."""
from __future__ import annotations
import sqlite3
from datetime import datetime
from uuid import UUID
from core.pump_reference import PumpReference
from database.library_database import LibraryDatabase
class PumpReferenceRepository:
    """Stores reference ships in the local library database."""
    def __init__(self,database:LibraryDatabase)->None:self._database=database
    def create(self,item:PumpReference)->PumpReference:
        """Persist a reference record."""
        with self._database.connection() as c:c.execute("INSERT INTO pump_references VALUES (?,?,?,?,?,?,?,?)",(str(item.id),item.ship_name,item.fuel_capacity_m3,item.pump_capacity_m3h,item.description,item.source,item.created_at.isoformat(),item.modified_at.isoformat()))
        return item
    def get_all(self)->tuple[PumpReference,...]:
        """Return references ordered by ship name."""
        with self._database.connection() as c:rows=c.execute("SELECT * FROM pump_references ORDER BY ship_name COLLATE NOCASE").fetchall()
        return tuple(self._map(row) for row in rows)
    def get_by_id(self,item_id:UUID)->PumpReference|None:
        """Return one reference by identifier."""
        with self._database.connection() as c:row=c.execute("SELECT * FROM pump_references WHERE id=?",(str(item_id),)).fetchone()
        return self._map(row) if row else None
    def ship_name_exists(self,name:str,excluded_id:UUID|None=None)->bool:
        """Check a case-insensitive ship-name conflict."""
        sql="SELECT 1 FROM pump_references WHERE ship_name=? COLLATE NOCASE";values:tuple[str,...]=(name,)
        if excluded_id:sql+=" AND id != ?";values=(name,str(excluded_id))
        with self._database.connection() as c:return c.execute(sql,values).fetchone() is not None
    def update(self,item:PumpReference)->PumpReference:
        """Persist edits to a reference."""
        with self._database.connection() as c:c.execute("UPDATE pump_references SET ship_name=?,fuel_capacity_m3=?,pump_capacity_m3h=?,description=?,source=?,modified_at=? WHERE id=?",(item.ship_name,item.fuel_capacity_m3,item.pump_capacity_m3h,item.description,item.source,item.modified_at.isoformat(),str(item.id)))
        return item
    def delete(self,item_id:UUID)->None:
        """Delete a reference record."""
        with self._database.connection() as c:c.execute("DELETE FROM pump_references WHERE id=?",(str(item_id),))
    @staticmethod
    def _map(row:sqlite3.Row)->PumpReference:return PumpReference(id=UUID(row["id"]),ship_name=row["ship_name"],fuel_capacity_m3=row["fuel_capacity_m3"],pump_capacity_m3h=row["pump_capacity_m3h"],description=row["description"],source=row["source"],created_at=datetime.fromisoformat(row["created_at"]),modified_at=datetime.fromisoformat(row["modified_at"]))
