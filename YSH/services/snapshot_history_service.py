"""Append-only snapshot use cases on existing calculation payload storage."""
from __future__ import annotations

from uuid import UUID

from engineering.snapshots.models import CalculationSnapshot
from repositories.calculation_repository import CalculationRepository


class HistoryError(RuntimeError):
    """A history persistence/format failure, separate from successful engineering math."""


class SnapshotHistoryService:
    """Never update/delete a snapshot; projectless history is explicitly session-only."""
    def __init__(self, repository: CalculationRepository) -> None:
        """Configure storage without scanning any project history."""
        self._repository=repository
        self._session: dict[UUID,CalculationSnapshot]={}

    def append(self, snapshot: CalculationSnapshot) -> None:
        """Persist one atomic immutable record, or retain an unassigned session snapshot."""
        if snapshot.project_id is None:
            if snapshot.snapshot_id in self._session: raise HistoryError('Snapshot already exists')
            self._session[snapshot.snapshot_id]=snapshot
            return
        try:
            self._repository.append_snapshot(snapshot)
        except Exception as error:
            raise HistoryError('history.persistence_failed') from error

    def list(self, project_id: UUID | None) -> tuple[CalculationSnapshot, ...]:
        """Read current-project history only on demand, newest first with a UUID tie-break."""
        if project_id is None:
            rows=tuple(self._session.values())
        else:
            try:
                records=self._repository.get_snapshot_records(project_id)
                rows=tuple(CalculationSnapshot.from_payload(row.outputs['results']['snapshot']) for row in records)
                if any(row.project_id!=project_id for row in rows): raise ValueError('Invalid historical ownership')
                for record,snapshot in zip(records,rows):
                    key=f'snapshot:{snapshot.module_code.value}:{snapshot.snapshot_id}'
                    if record.id!=snapshot.snapshot_id or record.calculation_type!=key or record.created_at!=snapshot.created_at:
                        raise ValueError('Snapshot identity metadata mismatch')
            except Exception as error:
                raise HistoryError('history.invalid_record') from error
        return tuple(sorted(rows,key=lambda row:(row.created_at,str(row.snapshot_id)),reverse=True))

    def legacy(self, project_id: UUID | None) -> tuple:
        """Expose existing legacy evidence as incomplete, without fabricating frozen sources."""
        if project_id is None: return ()
        try:
            return self._repository.get_legacy_records(project_id)
        except Exception as error:
            raise HistoryError('history.persistence_failed') from error
