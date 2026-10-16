"""Migration contracts using temporary databases and frozen pre-V2 schemas.

DDL fixtures were captured from commit 8e2b7a0 before changing initialization.
All rows below are synthetic; no runtime or source-tree database is opened.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3

import pytest

from database.library_database import LibraryDatabase
from database.project_database import ProjectDatabase
from database.library_v5 import TABLES, INDEXES
from database.migrations import MigrationError, migrate
from engineering.provenance import SourceType, VerificationStatus

LIBRARY_V4_DDL = ('CREATE TABLE corrosion_allowance_circuits (\n'
 '              id TEXT PRIMARY KEY,\n'
 '              code TEXT NOT NULL COLLATE NOCASE UNIQUE,\n'
 '              display_name TEXT NOT NULL,\n'
 '              default_corrosion_allowance_mm REAL NOT NULL,\n'
 "              description TEXT NOT NULL DEFAULT '',\n"
 '              is_active INTEGER NOT NULL DEFAULT 1,\n'
 '              created_at TEXT NOT NULL,\n'
 '              modified_at TEXT NOT NULL\n'
 '            )',
 'CREATE TABLE engineering_constants (\n'
 '              id TEXT PRIMARY KEY, key TEXT NOT NULL COLLATE NOCASE UNIQUE, display_name '
 'TEXT NOT NULL, value REAL NOT NULL,\n'
 "              unit TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '', source "
 'TEXT NOT NULL,\n'
 '              is_system INTEGER NOT NULL, created_at TEXT NOT NULL, modified_at TEXT NOT '
 'NULL)',
 'CREATE TABLE materials (\n'
 '              id TEXT PRIMARY KEY, name TEXT NOT NULL, designation TEXT NOT NULL COLLATE '
 'NOCASE UNIQUE,\n'
 "              standard TEXT NOT NULL DEFAULT '', yield_strength_mpa REAL, roughness_mm REAL "
 'NOT NULL,\n'
 "              description TEXT NOT NULL DEFAULT '', source TEXT NOT NULL, is_system INTEGER "
 'NOT NULL,\n'
 '              created_at TEXT NOT NULL, modified_at TEXT NOT NULL)',
 'CREATE TABLE pipe_sizes (\n'
 '              id TEXT PRIMARY KEY,\n'
 '              standard_id TEXT NOT NULL REFERENCES pipe_standards(id),\n'
 '              nominal_diameter TEXT NOT NULL COLLATE NOCASE,\n'
 '              outside_diameter_mm REAL NOT NULL,\n'
 '              wall_thickness_mm REAL NOT NULL,\n'
 '              inside_diameter_mm REAL NOT NULL,\n'
 "              description TEXT NOT NULL DEFAULT '',\n"
 '              is_system INTEGER NOT NULL,\n'
 '              created_at TEXT NOT NULL,\n'
 '              modified_at TEXT NOT NULL,\n'
 '              UNIQUE(standard_id, nominal_diameter, outside_diameter_mm, '
 'wall_thickness_mm)\n'
 '            )',
 'CREATE TABLE pipe_standards (\n'
 '              id TEXT PRIMARY KEY,\n'
 '              code TEXT NOT NULL COLLATE NOCASE UNIQUE,\n'
 '              display_name TEXT NOT NULL,\n'
 "              description TEXT NOT NULL DEFAULT '',\n"
 "              source TEXT NOT NULL DEFAULT '',\n"
 '              is_active INTEGER NOT NULL DEFAULT 1,\n'
 '              created_at TEXT NOT NULL,\n'
 '              modified_at TEXT NOT NULL\n'
 '            )',
 'CREATE TABLE pump_references (\n'
 '              id TEXT PRIMARY KEY, ship_name TEXT NOT NULL COLLATE NOCASE UNIQUE,\n'
 '              fuel_capacity_m3 REAL NOT NULL, pump_capacity_m3h REAL NOT NULL,\n'
 "              description TEXT NOT NULL DEFAULT '', source TEXT NOT NULL,\n"
 '              created_at TEXT NOT NULL, modified_at TEXT NOT NULL)',
 'CREATE TABLE schema_version (version INTEGER NOT NULL)')

PROJECT_LEGACY_DDL = ('CREATE TABLE calculations (\n'
 '                id TEXT PRIMARY KEY,\n'
 '                project_id TEXT NOT NULL,\n'
 '                calculation_type TEXT NOT NULL,\n'
 '                module_version TEXT NOT NULL,\n'
 '                created_at TEXT NOT NULL,\n'
 '                modified_at TEXT NOT NULL,\n'
 '                input_data_json TEXT NOT NULL,\n'
 '                result_data_json TEXT NOT NULL,\n'
 '                trace_data_json TEXT NOT NULL,\n'
 '                UNIQUE(project_id, calculation_type),\n'
 '                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE\n'
 '            )',
 'CREATE TABLE project_states (\n'
 '                id TEXT PRIMARY KEY,\n'
 '                project_id TEXT NOT NULL UNIQUE,\n'
 '                state_json TEXT NOT NULL,\n'
 '                schema_version INTEGER NOT NULL,\n'
 '                created_at TEXT NOT NULL,\n'
 '                modified_at TEXT NOT NULL,\n'
 '                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE\n'
 '            )',
 'CREATE TABLE projects (\n'
 '                id TEXT PRIMARY KEY,\n'
 '                name TEXT NOT NULL COLLATE NOCASE UNIQUE,\n'
 "                description TEXT NOT NULL DEFAULT '',\n"
 "                notes TEXT NOT NULL DEFAULT '',\n"
 '                created_at TEXT NOT NULL,\n'
 '                modified_at TEXT NOT NULL\n'
 '            )')

LIBRARY_TABLES = (
    "materials", "engineering_constants", "pump_references", "pipe_standards",
    "pipe_sizes", "corrosion_allowance_circuits",
)
PROJECT_TABLES = ("projects", "calculations", "project_states")
STAMP = "2025-01-01T00:00:00+00:00"


def _rows(connection, tables):
    return {table: [tuple(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY id")]
            for table in tables}


def _tables(connection):
    return {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _version(connection):
    return connection.execute("SELECT version FROM schema_version").fetchall()[0][0]


def _library_v4(path):
    with sqlite3.connect(path) as c:
        for ddl in LIBRARY_V4_DDL:
            c.execute(ddl)
        c.execute("INSERT INTO schema_version VALUES (4)")
        c.execute("INSERT INTO materials VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                  ("m", "User material", "USER", "Unverified", 195, .07, "Retain", "User", 0, STAMP, STAMP))
        c.execute("INSERT INTO engineering_constants VALUES (?,?,?,?,?,?,?,?,?,?)",
                  ("e", "custom_factor", "User constant", .85, "-", "Retain", "User", 0, STAMP, STAMP))
        c.execute("INSERT INTO pump_references VALUES (?,?,?,?,?,?,?,?)",
                  ("p", "User vessel", 123, 45, "Retain", "User", STAMP, STAMP))
        c.execute("INSERT INTO pipe_standards VALUES (?,?,?,?,?,?,?,?)",
                  ("std", "EN_10220", "User-edited standard", "Retain", "User", 0, STAMP, STAMP))
        c.execute("INSERT INTO pipe_sizes VALUES (?,?,?,?,?,?,?,?,?,?)",
                  ("pipe", "std", "DN80", 88.9, 3.2, 82.5, "User-edited row", 0, STAMP, STAMP))
        c.execute("INSERT INTO corrosion_allowance_circuits VALUES (?,?,?,?,?,?,?,?)",
                  ("corr", "FUEL", "User-edited fuel", 9.25, "Retain", 0, STAMP, STAMP))
        return _rows(c, LIBRARY_TABLES)


def _legacy_project(path):
    with sqlite3.connect(path) as c:
        for ddl in PROJECT_LEGACY_DDL:
            c.execute(ddl)
        c.execute("INSERT INTO projects VALUES (?,?,?,?,?,?)",
                  ("proj", "User project", "Retain", "Notes", STAMP, STAMP))
        c.execute("INSERT INTO calculations VALUES (?,?,?,?,?,?,?,?,?)",
                  ("calc", "proj", "pipe", "1", STAMP, STAMP, '{"q":123}', '{"d":99}', '{"trace":true}'))
        c.execute("INSERT INTO project_states VALUES (?,?,?,?,?,?)",
                  ("state", "proj", '{"keep":"exact payload"}', 37, STAMP, STAMP))
        return _rows(c, PROJECT_TABLES)


def test_fresh_library_reaches_v5_without_new_engineering_seed_data(tmp_path):
    db = LibraryDatabase(tmp_path / "fresh.db")
    db.initialize()
    with db.connection() as c:
        assert _version(c) == 5
        assert set(LIBRARY_TABLES) | {"schema_version"} | set(TABLES) == _tables(c)
        assert all(c.execute(f"SELECT count(*) FROM {name}").fetchone()[0] == 0 for name in TABLES)
        assert c.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert not c.execute("PRAGMA foreign_key_check").fetchall()


def test_v4_upgrade_preserves_every_existing_row_and_column(tmp_path):
    path = tmp_path / "v4.db"
    before = _library_v4(path)
    with sqlite3.connect(path) as c:
        ddl_before = dict(c.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"))
    db = LibraryDatabase(path)
    db.initialize()
    with db.connection() as c:
        assert _rows(c, LIBRARY_TABLES) == before
        assert _version(c) == 5
        ddl_after = dict(c.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"))
        assert all(ddl_after[name] == ddl for name, ddl in ddl_before.items())
        assert not c.execute("PRAGMA foreign_key_check").fetchall()
    db.initialize()
    with db.connection() as c:
        assert _rows(c, LIBRARY_TABLES) == before
        assert c.execute("SELECT count(*) FROM schema_version").fetchone()[0] == 1


def test_library_failure_rolls_back_ddl_data_and_version(tmp_path, monkeypatch):
    migration_globals = LibraryDatabase.create_schema.__globals__
    path = tmp_path / "v4.db"
    before = _library_v4(path)
    original = migration_globals["create_v5_schema"]

    def broken(c):
        original(c)
        c.execute("UPDATE materials SET name='Should roll back'")
        c.execute("CREATE TABLE partial_migration (id INTEGER)")
        raise RuntimeError("Injected migration failure")

    monkeypatch.setitem(migration_globals, "create_v5_schema", broken)
    db = LibraryDatabase(path)
    with pytest.raises(MigrationError, match="libraries.*version 4") as error:
        db.initialize()
    assert isinstance(error.value.__cause__, RuntimeError)
    with db.connection() as c:
        assert _version(c) == 4
        assert _rows(c, LIBRARY_TABLES) == before
        assert not (set(TABLES) | {"partial_migration"}) & _tables(c)
    monkeypatch.setitem(migration_globals, "create_v5_schema", original)
    db.initialize()
    with db.connection() as c:
        assert _version(c) == 5
        assert _rows(c, LIBRARY_TABLES) == before


def test_fresh_project_global_version_is_separate_from_state_version(tmp_path):
    db = ProjectDatabase(tmp_path / "project.db")
    db.initialize()
    with db.connection() as c:
        assert _tables(c) == set(PROJECT_TABLES) | {"schema_version"}
        assert _version(c) == 1
        assert "schema_version" in {r[1] for r in c.execute("PRAGMA table_info(project_states)")}


def test_existing_project_payloads_and_timestamps_survive_unchanged(tmp_path):
    path = tmp_path / "project.db"
    before = _legacy_project(path)
    db = ProjectDatabase(path)
    db.initialize()
    db.initialize()
    with db.connection() as c:
        assert _rows(c, PROJECT_TABLES) == before
        assert _version(c) == 1
        assert c.execute("SELECT schema_version FROM project_states").fetchone()[0] == 37
        assert not c.execute("PRAGMA foreign_key_check").fetchall()


def test_project_failed_upgrade_leaves_original_unversioned_database(tmp_path, monkeypatch):
    path = tmp_path / "project.db"
    before = _legacy_project(path)
    original = ProjectDatabase._create_legacy_schema

    def broken(self, c):
        original(self, c)
        c.execute("ALTER TABLE projects ADD COLUMN rolled_back TEXT")
        raise RuntimeError("Injected project failure")

    monkeypatch.setattr(ProjectDatabase, "_create_legacy_schema", broken)
    db = ProjectDatabase(path)
    with pytest.raises(MigrationError, match="projects.*version 0"):
        db.initialize()
    with db.connection() as c:
        assert "schema_version" not in _tables(c)
        assert _rows(c, PROJECT_TABLES) == before


def test_older_project_columns_are_upgraded_additively(tmp_path):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as c:
        c.execute("CREATE TABLE projects(project_id TEXT PRIMARY KEY, name TEXT UNIQUE, user_extension TEXT)")
        c.execute("INSERT INTO projects VALUES ('p','Original','Retain extension')")
    db = ProjectDatabase(path)
    db.initialize()
    with db.connection() as c:
        row = c.execute("SELECT id,name,user_extension,notes FROM projects").fetchone()
        assert tuple(row) == ("p", "Original", "Retain extension", "")
        assert "projects_legacy" not in _tables(c)


@pytest.mark.parametrize("table,columns,values", [
    ("circuits", "id,system_id,code,name_tr", ("bad", "missing", "BAD", "Bad")),
    ("fluid_properties", "id,fluid_id,property_name,value,unit,created_at,modified_at", ("bad", "missing", "density", 1, "kg/m³", STAMP, STAMP)),
    ("material_properties", "id,material_id,property_name,value,unit,created_at,modified_at", ("bad", "missing", "k", 1, "mm", STAMP, STAMP)),
    ("pipe_standard_metadata", "standard_id", ("missing",)),
    ("pipe_size_metadata", "pipe_size_id", ("missing",)),
    ("engineering_constant_metadata", "constant_id", ("missing",)),
    ("corrosion_allowance_sources", "corrosion_circuit_id", ("missing",)),
    ("rule_sets", "id,code,name,source_id,created_at,modified_at", ("bad", "BAD", "Bad", "missing", STAMP, STAMP)),
])
def test_foreign_keys_reject_orphan_metadata(tmp_path, table, columns, values):
    db = LibraryDatabase(tmp_path / "fk.db")
    db.initialize()
    with pytest.raises(sqlite3.IntegrityError):
        with db.connection() as c:
            placeholders = ",".join("?" for _ in values)
            c.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", values)


def test_source_enums_nulls_and_constraints_match_phase2(tmp_path):
    db = LibraryDatabase(tmp_path / "sources.db")
    db.initialize()
    with db.connection() as c:
        for item in SourceType:
            c.execute("INSERT INTO sources(id,source_type,created_at,modified_at) VALUES(?,?,?,?)",
                      (item.value, item.value, STAMP, STAMP))
        for item in VerificationStatus:
            c.execute("UPDATE sources SET verification_status=? WHERE id=?", (item.value, SourceType.USER_INPUT.value))
        row = c.execute("SELECT document,effective_date,verification_date,verification_status FROM sources WHERE id=?", (SourceType.TL_RULE.value,)).fetchone()
        assert tuple(row) == (None, None, None, None)
    with pytest.raises(sqlite3.IntegrityError):
        with db.connection() as c:
            c.execute("INSERT INTO sources(id,source_type,created_at,modified_at) VALUES ('bad','MADE_UP',?,?)", (STAMP, STAMP))
    with pytest.raises(sqlite3.IntegrityError):
        with db.connection() as c:
            c.execute("UPDATE sources SET verification_status='MADE_UP'")


def test_indexes_exist_exactly_as_documented(tmp_path):
    db = LibraryDatabase(tmp_path / "indexes.db")
    db.initialize()
    with db.connection() as c:
        explicit = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")}
        assert explicit == set(INDEXES)


@pytest.mark.parametrize("database", [LibraryDatabase, ProjectDatabase])
def test_future_versions_are_rejected_without_changing_data(tmp_path, database):
    db = database(tmp_path / "future.db")
    db.initialize()
    with db.connection() as c:
        c.execute("UPDATE schema_version SET version=999")
        before = list(c.iterdump())
    with pytest.raises(MigrationError, match="Unsupported schema version"):
        db.initialize()
    with db.connection() as c:
        assert list(c.iterdump()) == before


def test_migrations_are_ordered_and_publish_version_only_after_success(tmp_path):
    db = sqlite3.connect(tmp_path / "steps.db")
    calls = []
    def first(c):
        assert _version(c) == 0
        c.execute("CREATE TABLE first_step(id INTEGER)")
        calls.append(1)
    def second(c):
        assert _version(c) == 1
        calls.append(2)
    migrate(db, database="test", latest=2, steps={1: first, 2: second})
    assert calls == [1, 2] and _version(db) == 2
    db.close()


def test_fresh_failure_rolls_back_version_table_and_all_prior_steps(tmp_path):
    with sqlite3.connect(tmp_path / "fresh.db") as c:
        def first(c):
            c.execute("CREATE TABLE first_step(id INTEGER)")
        def broken(c):
            raise ValueError("boom")
        with pytest.raises(MigrationError):
            migrate(c, database="test", latest=2, steps={1: first, 2: broken})
        assert _tables(c) == set()


@pytest.mark.parametrize("versions", [(4,4), (-1,), (4.5,)])
def test_ambiguous_or_invalid_version_records_are_rejected(tmp_path, versions):
    path = tmp_path / "invalid.db"
    with sqlite3.connect(path) as c:
        c.execute("CREATE TABLE schema_version(version INTEGER NOT NULL)")
        c.executemany("INSERT INTO schema_version VALUES (?)", [(v,) for v in versions])
    with pytest.raises(MigrationError):
        LibraryDatabase(path).initialize()
    with sqlite3.connect(path) as c:
        assert tuple(row[0] for row in c.execute("SELECT version FROM schema_version")) == versions


@pytest.mark.parametrize("database", [LibraryDatabase, ProjectDatabase])
def test_concurrent_initialization_is_serialized_and_idempotent(tmp_path, database):
    path = tmp_path / "concurrent.db"
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: database(path).initialize(), range(2)))
    db = database(path)
    with db.connection() as c:
        assert _version(c) == db.SCHEMA_VERSION
        assert c.execute("SELECT count(*) FROM schema_version").fetchone()[0] == 1

def test_rule_revisions_and_new_source_records_survive_reopening(tmp_path):
    db = LibraryDatabase(tmp_path / "metadata.db")
    db.initialize()
    with db.connection() as c:
        c.execute("INSERT INTO sources(id,source_type,created_at,modified_at) VALUES (?,?,?,?)",
                  ("s", SourceType.ENGINEERING_REFERENCE.value, STAMP, STAMP))
        for revision in ("A", "B"):
            c.execute("INSERT INTO rule_sets(id,code,name,revision,source_id,created_at,modified_at) VALUES (?,?,?,?,?,?,?)",
                      (revision, "EXAMPLE", "Synthetic rule", revision, "s", STAMP, STAMP))
        before = _rows(c, ("sources", "rule_sets"))
    db.initialize()
    with db.connection() as c:
        assert _rows(c, ("sources", "rule_sets")) == before
    with pytest.raises(sqlite3.IntegrityError):
        with db.connection() as c:
            c.execute("INSERT INTO rule_sets(id,code,name,revision,created_at,modified_at) VALUES (?,?,?,?,?,?)",
                      ("duplicate", "EXAMPLE", "Duplicate revision", "A", STAMP, STAMP))


def test_legacy_pipe_copy_transform_is_also_rolled_back_on_later_failure(tmp_path, monkeypatch):
    path = tmp_path / "v2.db"
    with sqlite3.connect(path) as c:
        c.execute("CREATE TABLE schema_version(version INTEGER NOT NULL)")
        c.execute("INSERT INTO schema_version VALUES (2)")
        c.execute("CREATE TABLE pipe_sizes(id TEXT PRIMARY KEY, nominal_diameter TEXT, outside_diameter_mm REAL, wall_thickness_mm REAL, inside_diameter_mm REAL, standard TEXT, description TEXT, is_system INTEGER, created_at TEXT, modified_at TEXT)")
        c.execute("INSERT INTO pipe_sizes VALUES ('p','DN700',711,10,691,'User standard','Keep',0,?,?)", (STAMP, STAMP))
        before = list(c.iterdump())
    def broken(c):
        raise RuntimeError("Failure after historic copy/transform")
    monkeypatch.setitem(LibraryDatabase.create_schema.__globals__, "create_v5_schema", broken)
    with pytest.raises(MigrationError):
        LibraryDatabase(path).initialize()
    with sqlite3.connect(path) as c:
        assert list(c.iterdump()) == before


def test_missing_migration_does_not_publish_partial_schema(tmp_path):
    with sqlite3.connect(tmp_path / "missing.db") as c:
        with pytest.raises(MigrationError, match="Missing migration 0 -> 1"):
            migrate(c, database="test", latest=1, steps={})
        assert _tables(c) == set()
