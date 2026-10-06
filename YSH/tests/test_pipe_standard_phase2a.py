"""Phase 2A contracts for standard-owned pipe-library geometry."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from core.pipe_size import PipeSize
from database.en_10220_pipe_size_seed import EN_10220_STANDARD_CODE
from database.library_database import LibraryDatabase
from repositories.pipe_size_repository import PipeSizeRepository
from services.pipe_size_service import PipeSizeService


def test_fresh_library_creates_and_seeds_the_en_10220_standard(
    library_database: LibraryDatabase, pipe_size_service: PipeSizeService
) -> None:
    """A new runtime database starts directly at the standard-aware schema."""
    with library_database.connection() as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(pipe_sizes)")}
        version = connection.execute("SELECT version FROM schema_version").fetchone()["version"]
    standard = pipe_size_service.get_standard_by_code(EN_10220_STANDARD_CODE)

    assert version == 4
    assert "standard_id" in columns
    assert standard.display_name == "EN 10220"
    assert pipe_size_service.get_pipe_sizes_for_standard(standard.id)


def test_v2_migration_preserves_unrelated_library_data_and_en_rows(tmp_path: Path) -> None:
    """Migrating pipe identity does not rewrite materials, constants, or references."""
    path = tmp_path / "libraries-v2.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_version VALUES (2)")
        connection.executescript(
            """
            CREATE TABLE materials (id TEXT PRIMARY KEY, name TEXT NOT NULL, designation TEXT NOT NULL, standard TEXT NOT NULL, yield_strength_mpa REAL, roughness_mm REAL NOT NULL, description TEXT NOT NULL, source TEXT NOT NULL, is_system INTEGER NOT NULL, created_at TEXT NOT NULL, modified_at TEXT NOT NULL);
            CREATE TABLE engineering_constants (id TEXT PRIMARY KEY, key TEXT NOT NULL, display_name TEXT NOT NULL, value REAL NOT NULL, unit TEXT NOT NULL, description TEXT NOT NULL, source TEXT NOT NULL, is_system INTEGER NOT NULL, created_at TEXT NOT NULL, modified_at TEXT NOT NULL);
            CREATE TABLE pump_references (id TEXT PRIMARY KEY, ship_name TEXT NOT NULL, fuel_capacity_m3 REAL NOT NULL, pump_capacity_m3h REAL NOT NULL, description TEXT NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL, modified_at TEXT NOT NULL);
            CREATE TABLE pipe_sizes (id TEXT PRIMARY KEY, nominal_diameter TEXT NOT NULL, outside_diameter_mm REAL NOT NULL, wall_thickness_mm REAL NOT NULL, inside_diameter_mm REAL NOT NULL, standard TEXT NOT NULL, description TEXT NOT NULL, is_system INTEGER NOT NULL, created_at TEXT NOT NULL, modified_at TEXT NOT NULL, UNIQUE(standard, nominal_diameter, outside_diameter_mm, wall_thickness_mm));
            """
        )
        stamp = "2026-01-01T00:00:00+00:00"
        connection.execute("INSERT INTO materials VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ("m", "Material", "M", "", 200.0, 0.01, "", "test", 0, stamp, stamp))
        connection.execute("INSERT INTO engineering_constants VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ("c", "factor", "Factor", 1.0, "", "", "test", 0, stamp, stamp))
        connection.execute("INSERT INTO pump_references VALUES (?, ?, ?, ?, ?, ?, ?, ?)", ("p", "Ship", 100.0, 20.0, "", "test", stamp, stamp))
        connection.execute("INSERT INTO pipe_sizes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ("11111111-1111-1111-1111-111111111111", "DN80", 88.9, 3.2, 82.5, "EN 10220", "seed", 1, stamp, stamp))

    database = LibraryDatabase(path)
    database.initialize()
    service = PipeSizeService(PipeSizeRepository(database))
    en = service.get_standard_by_code(EN_10220_STANDARD_CODE)
    migrated = [item for item in service.get_pipe_sizes_for_standard(en.id) if item.nominal_diameter == "DN80"]
    with database.connection() as connection:
        counts = tuple(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("materials", "engineering_constants", "pump_references"))

    assert counts == (1, 1, 1)
    assert any(item.wall_thickness_mm == 3.2 for item in migrated)
    database.initialize()
    assert len(service.get_pipe_sizes_for_standard(en.id)) == 148


def test_legacy_free_text_standard_is_preserved_as_explicit_legacy_metadata(tmp_path: Path) -> None:
    """Unverified historic labels are not silently relabelled as EN 10220."""
    path = tmp_path / "legacy-standard.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_version VALUES (2)")
        connection.execute("CREATE TABLE pipe_sizes (id TEXT PRIMARY KEY, nominal_diameter TEXT NOT NULL, outside_diameter_mm REAL NOT NULL, wall_thickness_mm REAL NOT NULL, inside_diameter_mm REAL NOT NULL, standard TEXT NOT NULL, description TEXT NOT NULL, is_system INTEGER NOT NULL, created_at TEXT NOT NULL, modified_at TEXT NOT NULL)")
        connection.execute("INSERT INTO pipe_sizes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ("22222222-2222-2222-2222-222222222222", "DN700", 711.0, 10.0, 691.0, "Historic custom", "", 0, "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"))

    database = LibraryDatabase(path)
    database.initialize()
    record = next(item for item in PipeSizeService(PipeSizeRepository(database)).get_all_pipe_sizes() if item.nominal_diameter == "DN700")
    assert record.standard.startswith("Mevcut Kütüphane:")


def test_standard_scoped_queries_do_not_mix_geometry_and_allow_same_dn(
    pipe_size_service: PipeSizeService,
) -> None:
    """The natural key is standard + DN + geometry, never globally DN-only."""
    alternate = pipe_size_service.create_standard(code="TEST_ALT", display_name="Test Alt")
    created = pipe_size_service.create_pipe_size(
        nominal_diameter="DN80", outside_diameter_mm=101.6,
        wall_thickness_mm=4.0, inside_diameter_mm=93.6, standard_id=alternate.id,
    )
    pipe_size_service.create_pipe_size(
        nominal_diameter="DN80", outside_diameter_mm=101.6,
        wall_thickness_mm=5.0, inside_diameter_mm=91.6, standard_id=alternate.id,
    )
    en_records = pipe_size_service.get_pipe_sizes_for_standard(EN_10220_STANDARD_CODE)
    alternate_records = pipe_size_service.get_pipe_sizes_for_standard(alternate.id)

    assert created.standard_id == alternate.id
    assert {item.standard_id for item in alternate_records} == {alternate.id}
    assert all(item.standard_id != alternate.id for item in en_records)
    assert len([item for item in alternate_records if item.nominal_diameter == "DN80"]) == 2


def test_repository_rejects_standardless_geometry(library_database: LibraryDatabase) -> None:
    """Only the service may apply the temporary Phase 2A EN 10220 default."""
    repository = PipeSizeRepository(library_database)
    with pytest.raises(ValueError, match="standard"):
        repository.create(PipeSize("DN900", 914.4, 10.0, 894.4))


def test_legacy_editor_create_defaults_to_en_10220(pipe_size_service: PipeSizeService) -> None:
    """No new visible selector is needed before Phase 2B."""
    created = pipe_size_service.create_pipe_size(
        nominal_diameter="DN900", outside_diameter_mm=914.4,
        wall_thickness_mm=10.0, inside_diameter_mm=894.4,
    )
    assert created.standard == "EN 10220"
    assert created in pipe_size_service.get_pipe_sizes_for_standard(EN_10220_STANDARD_CODE)
