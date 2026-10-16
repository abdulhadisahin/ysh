"""Ordered SQLite migrations with atomic rollback and contextual failures."""
from __future__ import annotations

from collections.abc import Callable, Mapping
import sqlite3

Migration = Callable[[sqlite3.Connection], None]


class MigrationError(RuntimeError):
    """A schema upgrade failed; the enclosing migration was rolled back."""


def migrate(
    connection: sqlite3.Connection, *, database: str,
    latest: int, steps: Mapping[int, Migration],
) -> None:
    """Apply N -> N+1 steps atomically, including first-time version metadata.

    A savepoint also supports callers that already own a transaction. No
    executescript is permitted in steps, because it implicitly commits SQLite
    transactions. A newer or ambiguous version is rejected without modification.
    """
    connection.execute("SAVEPOINT schema_upgrade")
    version = 0
    try:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"
        )
        rows = connection.execute("SELECT version FROM schema_version").fetchall()
        if len(rows) > 1:
            raise ValueError("schema_version must have exactly one version record")
        if rows:
            version = rows[0][0]
            if type(version) is not int or not 0 <= version <= latest:
                raise ValueError(f"Unsupported schema version {version!r}; latest is {latest}")
        else:
            connection.execute("INSERT INTO schema_version(version) VALUES (0)")
        while version < latest:
            target = version + 1
            if target not in steps:
                raise ValueError(f"Missing migration {version} -> {target}")
            steps[target](connection)
            connection.execute("UPDATE schema_version SET version=?", (target,))
            version = target
        connection.execute("RELEASE SAVEPOINT schema_upgrade")
    except Exception as error:
        connection.execute("ROLLBACK TO SAVEPOINT schema_upgrade")
        connection.execute("RELEASE SAVEPOINT schema_upgrade")
        raise MigrationError(
            f"{database} migration at version {version} (latest {latest}) failed: {error}"
        ) from error
