"""SQLite repository for calculations owned by projects."""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from uuid import UUID, uuid4
from core.calculation import Calculation
from database.project_database import ProjectDatabase
class CalculationRepository:
    """Persists module-specific calculation data with relational project ownership."""
    def __init__(self,database:ProjectDatabase)->None:
        """Create the repository with the project database."""
        self._database=database
    def upsert_for_project_and_type(self,project_id:UUID,calculation_type:str,input_data:dict[str,object],result_data:dict[str,object],trace_data:dict[str,object],module_version:str="1")->Calculation:
        """Create or replace the saved state for a project calculation type."""
        existing=self.get_by_project_and_type(project_id,calculation_type);now=datetime.now(timezone.utc).isoformat();identifier=str(existing.id if existing else uuid4());created=existing.created_at.isoformat() if existing else now
        with self._database.connection() as connection:
            connection.execute("INSERT INTO calculations (id,project_id,calculation_type,module_version,created_at,modified_at,input_data_json,result_data_json,trace_data_json) VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(project_id,calculation_type) DO UPDATE SET module_version=excluded.module_version,modified_at=excluded.modified_at,input_data_json=excluded.input_data_json,result_data_json=excluded.result_data_json,trace_data_json=excluded.trace_data_json",(identifier,str(project_id),calculation_type,module_version,created,now,json.dumps(input_data),json.dumps(result_data),json.dumps(trace_data)))
        return Calculation(id=UUID(identifier),project_id=project_id,calculation_type=calculation_type,created_at=datetime.fromisoformat(created),inputs=input_data,outputs={"results":result_data,"trace":trace_data})
    def get_by_project_and_type(self,project_id:UUID,calculation_type:str)->Calculation|None:
        """Return saved calculation state for one project and type."""
        with self._database.connection() as connection: row=connection.execute("SELECT * FROM calculations WHERE project_id=? AND calculation_type=?",(str(project_id),calculation_type)).fetchone()
        return self._map(row) if row else None
    def get_all_by_project(self,project_id:UUID)->tuple[Calculation,...]:
        """Return every calculation belonging to a project."""
        with self._database.connection() as connection: rows=connection.execute("SELECT * FROM calculations WHERE project_id=?",(str(project_id),)).fetchall()
        return tuple(self._map(row) for row in rows)
    def delete_all_by_project(self,project_id:UUID)->None:
        """Delete every calculation belonging to a project."""
        with self._database.connection() as connection: connection.execute("DELETE FROM calculations WHERE project_id=?",(str(project_id),))
    @staticmethod
    def _map(row:sqlite3.Row)->Calculation:
        return Calculation(id=UUID(row["id"]),project_id=UUID(row["project_id"]),calculation_type=row["calculation_type"],created_at=datetime.fromisoformat(row["created_at"]),inputs=json.loads(row["input_data_json"]),outputs={"results":json.loads(row["result_data_json"]),"trace":json.loads(row["trace_data_json"])})
