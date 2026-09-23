"""Persistence for one versioned JSON workspace state per project."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from database.project_database import ProjectDatabase


class ProjectStateRepository:
    """Store complete Version 1 project workspaces in the project database."""

    def __init__(self, database: ProjectDatabase) -> None:
        """Configure project-state persistence."""
        self._database = database

    def save(self, project_id: UUID, state: dict[str, object]) -> None:
        """Insert or replace one JSON state transactionally for a project."""
        now = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
        with self._database.connection() as connection:
            row = connection.execute("SELECT id, created_at FROM project_states WHERE project_id=?", (str(project_id),)).fetchone()
            identifier = row["id"] if row else str(uuid4())
            created = row["created_at"] if row else now
            connection.execute(
                "INSERT INTO project_states (id, project_id, state_json, schema_version, created_at, modified_at) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(project_id) DO UPDATE SET state_json=excluded.state_json, schema_version=excluded.schema_version, modified_at=excluded.modified_at",
                (identifier, str(project_id), payload, int(state.get("schema_version", 1)), created, now),
            )

    def get(self, project_id: UUID) -> dict[str, object] | None:
        """Return the saved state for a project, if one exists."""
        with self._database.connection() as connection:
            row = connection.execute("SELECT state_json FROM project_states WHERE project_id=?", (str(project_id),)).fetchone()
        return None if row is None else dict(json.loads(row["state_json"]))

    def delete(self, project_id: UUID) -> None:
        """Delete only a project's saved workspace state."""
        with self._database.connection() as connection:
            connection.execute("DELETE FROM project_states WHERE project_id=?", (str(project_id),))
