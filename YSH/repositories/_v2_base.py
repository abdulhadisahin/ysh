"""Private CRUD/codec support for concrete V2 repositories.

Identifiers are fixed by repository declarations and dataclass fields; only
values are supplied by callers. Each operation opens one database connection.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import fields
from datetime import date, datetime
from enum import Enum
import math
import sqlite3
from types import UnionType
from typing import Generic, Iterator, TypeVar, get_args, get_origin, get_type_hints
from uuid import UUID

from database.library_database import LibraryDatabase
from engineering.provenance import VerificationStatus
from repositories.v2_errors import (
    RepositoryError, RepositoryConflictError, RepositoryForeignKeyError,
    RepositoryValidationError, RepositoryNotFoundError,
)

T = TypeVar("T")


def _validate(name: str, value: object, expected: object) -> None:
    choices = get_args(expected) if get_origin(expected) is UnionType else (expected,)
    valid = False
    for choice in choices:
        if choice is type(None):
            valid |= value is None
        elif choice is float:
            try:
                valid |= type(value) in (float, int) and math.isfinite(value)
            except OverflowError:
                pass
        elif choice is date:
            valid |= type(value) is date
        elif choice is datetime:
            valid |= isinstance(value, datetime) and value.utcoffset() is not None
        elif choice is bool:
            valid |= type(value) is bool
        elif isinstance(choice, type):
            valid |= isinstance(value, choice)
    if not valid:
        raise RepositoryValidationError(f"Invalid {name}: expected {expected}")


def _encode(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bool):
        return int(value)
    return value


def _decode(name: str, value: object) -> object:
    if value is None:
        return None
    if name == "id" or name.endswith("_id"):
        return UUID(value)
    if name in ("created_at", "modified_at"):
        return datetime.fromisoformat(value)
    if name in ("effective_date", "verification_date"):
        return date.fromisoformat(value)
    if name == "verification_status":
        return VerificationStatus(value)
    if name in ("is_active", "is_factory"):
        if value not in (0, 1):
            raise ValueError("Invalid stored boolean")
        return bool(value)
    return value


class _Repository(Generic[T]):
    _table: str
    _model: type[T]
    _key = "id"

    def __init__(self, database: LibraryDatabase) -> None:
        self._database = database
        self._columns = tuple(field.name for field in fields(self._model))
        self._types = get_type_hints(self._model)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        try:
            with self._database.connection() as connection:
                yield connection
        except sqlite3.IntegrityError as error:
            code = error.sqlite_errorcode
            if code == sqlite3.SQLITE_CONSTRAINT_FOREIGNKEY:
                raise RepositoryForeignKeyError(f"{self._table}: invalid reference") from error
            if code in (sqlite3.SQLITE_CONSTRAINT_UNIQUE, sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY):
                raise RepositoryConflictError(f"{self._table}: duplicate record") from error
            raise RepositoryValidationError(f"{self._table}: constraint violation") from error
        except sqlite3.Error as error:
            raise RepositoryError(f"{self._table}: database operation failed") from error

    def _record_values(self, item: T) -> tuple[object, ...]:
        if not isinstance(item, self._model):
            raise RepositoryValidationError(f"Expected {self._model.__name__}")
        for name, expected in self._types.items():
            _validate(name, getattr(item, name), expected)
        return tuple(_encode(getattr(item, name)) for name in self._columns)

    def _map(self, row: sqlite3.Row) -> T:
        try:
            item = self._model(**{name: _decode(name, row[name]) for name in self._columns})
            self._record_values(item)
            return item
        except (ValueError, TypeError, OverflowError) as error:
            raise RepositoryValidationError(f"{self._table}: invalid stored record") from error

    def create(self, item: T) -> T:
        values = self._record_values(item)
        columns = ",".join(self._columns)
        placeholders = ",".join("?" for _ in self._columns)
        with self._connection() as c:
            c.execute(f"INSERT INTO {self._table} ({columns}) VALUES ({placeholders})", values)
        return item

    def get(self, identifier: UUID) -> T | None:
        _validate(self._key, identifier, UUID)
        with self._connection() as c:
            row = c.execute(f"SELECT * FROM {self._table} WHERE {self._key}=?", (str(identifier),)).fetchone()
            return self._map(row) if row else None

    def update(self, item: T) -> T:
        values = dict(zip(self._columns, self._record_values(item)))
        columns = tuple(name for name in self._columns if name not in (self._key, "created_at"))
        assignments = ",".join(f"{name}=?" for name in columns)
        with self._connection() as c:
            cursor = c.execute(
                f"UPDATE {self._table} SET {assignments} WHERE {self._key}=?",
                tuple(values[name] for name in columns) + (values[self._key],),
            )
            if cursor.rowcount == 0:
                raise RepositoryNotFoundError(f"{self._table}: record not found")
            # Read back actual persisted creation timestamp, within the same transaction.
            row = c.execute(f"SELECT * FROM {self._table} WHERE {self._key}=?", (values[self._key],)).fetchone()
            return self._map(row)

    def _list(self, where: str = "1=1", values: tuple[object, ...] = ()) -> tuple[T, ...]:
        # where is only supplied by concrete repository methods with static clauses.
        with self._connection() as c:
            rows = c.execute(f"SELECT * FROM {self._table} WHERE {where} ORDER BY {self._key}", values).fetchall()
            return tuple(self._map(row) for row in rows)


def _active_clause(active_only: bool) -> str:
    _validate("active_only", active_only, bool)
    return "is_active=1" if active_only else "1=1"
