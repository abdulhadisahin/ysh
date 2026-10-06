"""Tests for the pipe-size model, repository, and service."""
from __future__ import annotations
import pytest
import sqlite3
from pathlib import Path
from core.pipe_size import PipeSize
from database.en_10220_pipe_size_seed import EN_10220_STANDARD, iter_en_10220_pipe_sizes
from database.library_database import LibraryDatabase
from engineering.validation import ValidationError
from repositories.pipe_size_repository import PipeSizeRepository
from services.pipe_size_service import PipeSizeConflictError, PipeSizeService, PipeSizeValidationError
def test_pipe_size_serialization() -> None:
    """Pipe-size data round trips through a dictionary."""
    item=PipeSize("DN50",60.3,3.2,53.9,"EN")
    assert PipeSize.from_dict(item.to_dict()).to_dict()==item.to_dict()
def test_pipe_library_contains_the_verified_en_10220_seed(pipe_size_service:PipeSizeService)->None:
    """Fresh local libraries contain every supplied EN 10220 reference row."""
    records = pipe_size_service.get_all_pipe_sizes()
    expected = tuple(iter_en_10220_pipe_sizes())
    seeded = [item for item in records if item.standard == EN_10220_STANDARD]
    assert len(seeded) == len(expected) == 148
    assert {
        (item.nominal_diameter, item.outside_diameter_mm, item.wall_thickness_mm,
         item.inside_diameter_mm)
        for item in seeded
    } == set(expected)
    assert all(item.inside_diameter_mm > 0 for item in seeded)
    assert all(
        item.inside_diameter_mm == pytest.approx(
            item.outside_diameter_mm - (2 * item.wall_thickness_mm)
        )
        for item in seeded
    )
    assert all("Seamless and welded steel tubes" in item.description for item in seeded)


def test_en_10220_seed_has_requested_dn_rows_and_ordering(pipe_size_service:PipeSizeService)->None:
    """Numeric DN sorting keeps repeated wall-thickness rows understandable."""
    records = [
        item for item in pipe_size_service.get_all_pipe_sizes()
        if item.standard == EN_10220_STANDARD
    ]
    expected_dns = (
        "DN10", "DN15", "DN20", "DN25", "DN32", "DN40", "DN50", "DN65",
        "DN80", "DN100", "DN125", "DN150", "DN200", "DN250", "DN300",
        "DN350", "DN400", "DN450", "DN500",
    )
    assert tuple(dict.fromkeys(item.nominal_diameter for item in records)) == expected_dns
    assert [item.wall_thickness_mm for item in records if item.nominal_diameter == "DN80"] == [
        3.2, 3.6, 4.0, 4.5, 5.0, 5.6, 6.3, 7.1,
    ]
    assert [item.wall_thickness_mm for item in records if item.nominal_diameter == "DN500"] == [
        6.3, 7.1, 8.0, 8.8, 10.0, 11.0, 12.5, 14.2, 16.0,
    ]
    dn80 = next(
        item for item in records
        if item.nominal_diameter == "DN80" and item.wall_thickness_mm == 5.0
    )
    assert dn80.outside_diameter_mm == 88.9
    assert dn80.inside_diameter_mm == pytest.approx(78.9)


def test_en_10220_seed_is_idempotent_and_preserves_custom_records(
    library_database: LibraryDatabase,
    pipe_size_service: PipeSizeService,
) -> None:
    """Repeated initialization neither duplicates seed data nor overwrites users."""
    custom_standard = pipe_size_service.create_standard(
        code="TEST_CUSTOM", display_name="Test Custom"
    )
    custom = pipe_size_service.create_pipe_size(
        nominal_diameter="DN700", outside_diameter_mm=711.0,
        wall_thickness_mm=10.0, inside_diameter_mm=691.0, standard_id=custom_standard.id,
    )
    before = len(pipe_size_service.get_all_pipe_sizes())
    library_database.initialize()
    records = pipe_size_service.get_all_pipe_sizes()
    assert len(records) == before
    assert pipe_size_service.get_pipe_size(custom.id).standard == "Test Custom"


def test_version_one_pipe_schema_migrates_without_losing_user_data(tmp_path: Path) -> None:
    """The minimal key migration preserves old rows and enables multiple walls."""
    path = tmp_path / "legacy-libraries.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_version VALUES (1)")
        connection.execute(
            """
            CREATE TABLE pipe_sizes (
              id TEXT PRIMARY KEY, nominal_diameter TEXT NOT NULL COLLATE NOCASE,
              outside_diameter_mm REAL NOT NULL, wall_thickness_mm REAL NOT NULL,
              inside_diameter_mm REAL NOT NULL, standard TEXT NOT NULL COLLATE NOCASE,
              description TEXT NOT NULL DEFAULT '', is_system INTEGER NOT NULL,
              created_at TEXT NOT NULL, modified_at TEXT NOT NULL,
              UNIQUE(nominal_diameter, standard)
            )
            """
        )
        connection.execute(
            "INSERT INTO pipe_sizes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("11111111-1111-1111-1111-111111111111", "DN700", 711.0, 10.0,
             691.0, "Custom", "existing user record", 0,
             "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
        )
    database = LibraryDatabase(path)
    database.initialize()
    service = PipeSizeService(PipeSizeRepository(database))
    assert any(item.nominal_diameter == "DN700" for item in service.get_all_pipe_sizes())
    service.create_pipe_size(
        nominal_diameter="DN80", outside_diameter_mm=88.9,
        wall_thickness_mm=3.0, inside_diameter_mm=82.9, standard="EN 10220",
    )
def test_pipe_size_crud(pipe_size_service:PipeSizeService)->None:
    """Pipe sizes persist and can be updated/deleted."""
    standard = pipe_size_service.create_standard(code="TEST_CRUD", display_name="Test CRUD")
    item=pipe_size_service.create_pipe_size(nominal_diameter="DN50",outside_diameter_mm=60.3,wall_thickness_mm=3.2,inside_diameter_mm=53.9,standard_id=standard.id)
    item.description="verified";pipe_size_service.update_pipe_size(item);assert pipe_size_service.get_pipe_size(item.id).description=="verified";pipe_size_service.delete_pipe_size(item.id)
def test_pipe_size_duplicate_and_geometry(pipe_size_service:PipeSizeService)->None:
    """Natural key and dimensional relationship are enforced."""
    standard = pipe_size_service.create_standard(code="TEST_DUP", display_name="Test duplicate")
    pipe_size_service.create_pipe_size(nominal_diameter="DN50",outside_diameter_mm=60.3,wall_thickness_mm=3.2,inside_diameter_mm=53.9,standard_id=standard.id)
    pipe_size_service.create_pipe_size(nominal_diameter="DN50",outside_diameter_mm=60.3,wall_thickness_mm=4.0,inside_diameter_mm=52.3,standard_id=standard.id)
    with pytest.raises(PipeSizeConflictError):pipe_size_service.create_pipe_size(nominal_diameter="dn50",outside_diameter_mm=60.3,wall_thickness_mm=3.2,inside_diameter_mm=53.9,standard_id=standard.id)
    with pytest.raises(ValidationError):pipe_size_service.create_pipe_size(nominal_diameter="DN1",outside_diameter_mm=10,wall_thickness_mm=2,inside_diameter_mm=7,standard="X")
@pytest.mark.parametrize("outer,wall,inner",[(0,1,1),(10,1,10),(10,0,10)])
def test_pipe_dimensions_must_be_positive_and_consistent(pipe_size_service:PipeSizeService,outer:float,wall:float,inner:float)->None:
    """Invalid dimensions are rejected."""
    with pytest.raises(PipeSizeValidationError):pipe_size_service.create_pipe_size(nominal_diameter=f"DN{outer}{wall}",outside_diameter_mm=outer,wall_thickness_mm=wall,inside_diameter_mm=inner)
