"""Source metadata access with lossless Phase 2 SourceReference mapping."""
from __future__ import annotations

from dataclasses import fields
import sqlite3

from engineering.provenance import SourceReference, SourceType
from database.library_database import LibraryDatabase
from repositories._v2_base import _Repository, _validate, _encode, _decode
from repositories.v2_errors import RepositoryValidationError
from repositories.v2_models import SourceRecord

_REFERENCE_COLUMNS = {field.name: field.name for field in fields(SourceReference)} | {
    "table": "table_reference", "formula": "formula_reference",
}


class SourceRepository(_Repository[SourceRecord]):
    """Persist source facts; deleting sources is deliberately not exposed."""

    _table = "sources"
    _model = SourceRecord

    def __init__(self, database: LibraryDatabase) -> None:
        super().__init__(database)
        self._columns = ("id", *tuple(_REFERENCE_COLUMNS.values()), "created_at", "modified_at")

    def _record_values(self, item: SourceRecord) -> tuple[object, ...]:
        if not isinstance(item, SourceRecord):
            raise RepositoryValidationError("Expected SourceRecord")
        for name, expected in self._types.items():
            _validate(name, getattr(item, name), expected)
        return (
            str(item.id),
            *(_encode(getattr(item.reference, name)) for name in _REFERENCE_COLUMNS),
            item.created_at.isoformat(), item.modified_at.isoformat(),
        )

    def _map(self, row: sqlite3.Row) -> SourceRecord:
        try:
            values = {name: (SourceType(row[column]) if name == "source_type" else _decode(name, row[column]))
                      for name, column in _REFERENCE_COLUMNS.items()}
            item = SourceRecord(
                id=_decode("id", row["id"]), reference=SourceReference(**values),
                created_at=_decode("created_at", row["created_at"]),
                modified_at=_decode("modified_at", row["modified_at"]),
            )
            self._record_values(item)
            return item
        except (ValueError, TypeError) as error:
            raise RepositoryValidationError("sources: invalid stored source metadata") from error

    def get_all(
        self, *, source_type: SourceType | None = None,
        organization: str | None = None, document: str | None = None,
        search: str | None = None,
    ) -> tuple[SourceRecord, ...]:
        clauses = []
        values = []
        if source_type is not None:
            _validate("source_type", source_type, SourceType)
            clauses.append("source_type=?")
            values.append(source_type.value)
        for name, value in (("source_organization", organization), ("document", document)):
            if value is not None:
                _validate(name, value, str)
                clauses.append(f"{name}=? COLLATE NOCASE")
                values.append(value)
        if search is not None:
            _validate("search", search, str)
            pattern = "%" + search.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"
            clauses.append("(source_organization LIKE ? ESCAPE '!' OR document LIKE ? ESCAPE '!')")
            values.extend((pattern, pattern))
        return self._list(" AND ".join(clauses) or "1=1", tuple(values))
