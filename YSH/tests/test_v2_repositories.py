"""V2 repository contracts against isolated temporary SQLite libraries."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import ast
import sqlite3
from uuid import uuid4

import pytest

from core.material import Material
from core.engineering_constant import EngineeringConstant
from repositories.material_repository import MaterialRepository
from repositories.engineering_constant_repository import EngineeringConstantRepository
from engineering.provenance import SourceReference, SourceType, VerificationStatus
from repositories.v2_models import (
    SourceRecord, RuleSet, System, Circuit, Fluid, FluidProperty, MaterialProperty,
    PipeStandardMetadata, PipeSizeMetadata, EngineeringConstantMetadata, CorrosionSourceLink,
)
from repositories.source_repository import SourceRepository
from repositories.rule_set_repository import RuleSetRepository
from repositories.system_repository import SystemRepository
from repositories.circuit_repository import CircuitRepository
from repositories.fluid_repository import FluidRepository
from repositories.fluid_property_repository import FluidPropertyRepository
from repositories.material_property_repository import MaterialPropertyRepository
from repositories.pipe_metadata_repository import PipeStandardMetadataRepository, PipeSizeMetadataRepository
from repositories.engineering_constant_metadata_repository import EngineeringConstantMetadataRepository
from repositories.corrosion_source_repository import CorrosionSourceRepository
from repositories.v2_errors import (
    RepositoryError, RepositoryConflictError, RepositoryForeignKeyError,
    RepositoryValidationError, RepositoryNotFoundError,
)
from database.library_database import LibraryDatabase

STAMP = datetime(2025, 1, 2, 3, 4, 5, 123456, timezone(timedelta(hours=3)))


def _source(**changes):
    return SourceRecord(reference=SourceReference(source_type=SourceType.ENGINEERING_REFERENCE, **changes),
                        created_at=STAMP, modified_at=STAMP)


@pytest.fixture
def parents(library_database):
    db = library_database
    source = SourceRepository(db).create(_source())
    rule = RuleSetRepository(db).create(RuleSet(code="EXAMPLE", name="Synthetic", source_id=source.id))
    system = SystemRepository(db).create(System(code="EXAMPLE", name_tr="Synthetic system"))
    circuit = CircuitRepository(db).create(Circuit(system_id=system.id, code="EXAMPLE", name_tr="Synthetic circuit"))
    fluid = FluidRepository(db).create(Fluid(code="EXAMPLE", name_tr="Synthetic fluid"))
    material = MaterialRepository(db).create(Material(name="Synthetic", designation="TEST"))
    constant = EngineeringConstantRepository(db).create(EngineeringConstant(key="test", display_name="Test", value=.85))
    with db.connection() as c:
        standard_id = c.execute("SELECT id FROM pipe_standards LIMIT 1").fetchone()[0]
        pipe_id = c.execute("SELECT id FROM pipe_sizes LIMIT 1").fetchone()[0]
        corrosion_id = c.execute("SELECT id FROM corrosion_allowance_circuits LIMIT 1").fetchone()[0]
    from uuid import UUID
    return dict(source=source, rule=rule, system=system, circuit=circuit, fluid=fluid,
                material=material, constant=constant, standard_id=UUID(standard_id),
                pipe_id=UUID(pipe_id), corrosion_id=UUID(corrosion_id))


@pytest.mark.parametrize("source_type", tuple(SourceType))
@pytest.mark.parametrize("status", (None, *tuple(VerificationStatus)))
def test_source_enum_and_unknown_metadata_round_trip(library_database, source_type, status):
    repo = SourceRepository(library_database)
    reference = SourceReference(source_type=source_type, verification_status=status)
    record = SourceRecord(reference=reference, created_at=STAMP, modified_at=STAMP)
    assert repo.create(record) == record
    assert repo.get(record.id) == record
    assert repo.get_all(source_type=source_type) == (record,)
    with library_database.connection() as c:
        row = c.execute("SELECT * FROM sources WHERE id=?", (str(record.id),)).fetchone()
        assert row["source_type"] == source_type.value
        assert row["verification_status"] == (status.value if status else None)
        for field in ("document", "revision", "article", "table_reference", "formula_reference", "verification_date"):
            assert row[field] is None


def test_source_full_reference_dates_search_and_update(library_database):
    repo = SourceRepository(library_database)
    record = _source(source_organization="Example %_! ' organization", document="Synthetic document",
                     part="8", section="2", article="3", table="8.9", formula="1",
                     revision="A", effective_date=date(2025, 1, 1), verification_date=date(2025, 2, 1),
                     verification_status=VerificationStatus.PARTIALLY_VERIFIED, notes="Not standards data")
    repo.create(record)
    assert repo.get(record.id) == record
    assert repo.get_all(organization=record.reference.source_organization, document="Synthetic document") == (record,)
    assert repo.get_all(search="%_! '") == (record,)
    assert repo.get_all(search="' OR 1=1 --") == ()
    changed = replace(record, reference=replace(record.reference, revision="B", verification_date=None),
                      modified_at=STAMP + timedelta(days=1), created_at=STAMP + timedelta(days=10))
    persisted = repo.update(changed)
    assert persisted.created_at == STAMP
    assert persisted.modified_at == changed.modified_at
    assert persisted.reference == changed.reference
    assert repo.get(record.id) == persisted
    assert not hasattr(repo, "delete")


def test_rule_codes_have_multiple_revisions_and_active_filtering(library_database):
    repo = RuleSetRepository(library_database)
    a = repo.create(RuleSet(code="CODE", name="Synthetic", revision="A", created_at=STAMP, modified_at=STAMP,
                           effective_date=date(2025, 1, 1), verification_status=VerificationStatus.UNVERIFIED))
    b = repo.create(RuleSet(code="CODE", name="Synthetic", revision="B", is_active=False))
    assert repo.get(a.id) == a
    assert set(repo.get_by_code("code")) == {a, b}
    assert repo.get_all(active_only=True) == (a,)
    assert repo.get_by_code("code", active_only=True) == (a,)
    b = repo.update(replace(b, is_active=True, verification_status=VerificationStatus.USER_SUPPLIED))
    assert set(repo.get_all(active_only=True)) == {a, b}
    with pytest.raises(RepositoryConflictError):
        repo.create(RuleSet(code="code", name="Duplicate", revision="A"))
    # Unknown revision is not unique in the Phase 3 schema: never pick one silently.
    repo.create(RuleSet(code="UNKNOWN", name="One"))
    repo.create(RuleSet(code="UNKNOWN", name="Two"))
    assert len(repo.get_by_code("UNKNOWN")) == 2


@pytest.mark.parametrize("repository,model", [(SystemRepository, System), (FluidRepository, Fluid)])
def test_master_records_empty_crud_active_flags_and_duplicate_codes(library_database, repository, model):
    repo = repository(library_database)
    assert repo.get_all() == ()
    first = repo.create(model(code="ONE", name_tr="First", name_en=None, is_factory=True))
    second = repo.create(model(code="TWO", name_tr="Second", name_en="Second", is_active=False))
    assert repo.get_by_code("one") == first
    assert repo.get(first.id) == first
    assert set(repo.get_all()) == {first, second}
    assert repo.get_all(active_only=True) == (first,)
    first = repo.update(replace(first, name_en="First", is_active=False))
    assert first.is_factory and repo.get(first.id) == first
    assert repo.get_all(active_only=True) == ()
    assert repo.get(uuid4()) is None
    assert repo.get_by_code("missing") is None
    with pytest.raises(RepositoryConflictError):
        repo.create(model(code="one", name_tr="Duplicate"))
    assert not hasattr(repo, "delete")


def test_circuit_codes_are_scoped_to_system_and_fk_is_enforced(library_database):
    systems = SystemRepository(library_database)
    a = systems.create(System(code="A", name_tr="A"))
    b = systems.create(System(code="B", name_tr="B"))
    repo = CircuitRepository(library_database)
    assert repo.get_by_system(a.id) == ()
    one = repo.create(Circuit(system_id=a.id, code="SAME", name_tr="One", is_factory=True))
    two = repo.create(Circuit(system_id=b.id, code="SAME", name_tr="Two", is_active=False))
    assert repo.get_by_code(a.id, "same") == one
    assert repo.get_by_system(b.id) == (two,)
    assert repo.get_by_system(b.id, active_only=True) == ()
    one = repo.update(replace(one, is_active=False))
    assert one.is_factory and repo.get(one.id) == one
    assert repo.get_by_system(a.id, active_only=True) == ()
    with pytest.raises(RepositoryConflictError):
        repo.create(Circuit(system_id=a.id, code="same", name_tr="Duplicate"))
    with pytest.raises(RepositoryForeignKeyError):
        repo.create(Circuit(system_id=uuid4(), code="BAD", name_tr="Bad"))


def test_fluid_name_lookup_is_literal_and_bilingual(library_database):
    repo = FluidRepository(library_database)
    fluid = repo.create(Fluid(code="X", name_tr="Synthetic", name_en="Example's fluid"))
    assert repo.find_by_name("example's fluid") == (fluid,)
    assert repo.find_by_name("' OR 1=1 --") == ()


@pytest.mark.parametrize("kind", ["fluid", "material"])
def test_property_filters_preserve_units_temperature_source_status(library_database, parents, kind):
    if kind == "fluid":
        repo, model = FluidPropertyRepository(library_database), FluidProperty
    else:
        repo, model = MaterialPropertyRepository(library_database), MaterialProperty
    owner = parents[kind].id
    base = {kind + "_id": owner, "source_id": parents["source"].id,
            "verification_status": VerificationStatus.USER_SUPPLIED,
            "created_at": STAMP, "modified_at": STAMP}
    if kind == "material":
        base["rule_set_id"] = parents["rule"].id
    first = repo.create(model(**base, property_name="test_property", value=1.23, unit="m²/s", reference_temperature_c=25.5))
    second = repo.create(model(**base, property_name="other", value=4.56, unit="MPa"))
    listing = getattr(repo, "get_by_" + kind)
    assert repo.get(first.id) == first
    assert set(listing(owner)) == {first, second}
    assert listing(owner, property_name="test_property") == (first,)
    assert listing(owner, property_name="absent") == ()
    assert first.unit == "m²/s" and first.reference_temperature_c == 25.5
    assert second.reference_temperature_c is None
    assert repo.update(replace(first, value=2.34)).value == 2.34


def _existing_rows(db):
    tables = ("materials", "engineering_constants", "pipe_standards", "pipe_sizes", "corrosion_allowance_circuits")
    with db.connection() as c:
        return {name: [tuple(row) for row in c.execute(f"SELECT * FROM {name} ORDER BY id")] for name in tables}


def test_metadata_read_write_and_link_removal_never_change_existing_values(library_database, parents):
    p = parents
    before = _existing_rows(library_database)
    cases = [
        (PipeStandardMetadataRepository(library_database), PipeStandardMetadata(standard_id=p["standard_id"], source_id=p["source"].id, standard_family="Synthetic"), "standard_id", "standard_family", "Updated"),
        (PipeSizeMetadataRepository(library_database), PipeSizeMetadata(pipe_size_id=p["pipe_id"], source_id=p["source"].id, nps="example NPS", schedule="example schedule", manufacturing_tolerance=.1, tolerance_unit="%"), "pipe_size_id", "schedule", "Updated"),
        (EngineeringConstantMetadataRepository(library_database), EngineeringConstantMetadata(constant_id=p["constant"].id, source_id=p["source"].id, rule_set_id=p["rule"].id, system_id=p["system"].id, circuit_id=p["circuit"].id, selection_reason="Synthetic"), "constant_id", "selection_reason", "Updated"),
        (CorrosionSourceRepository(library_database), CorrosionSourceLink(corrosion_circuit_id=p["corrosion_id"], source_id=p["source"].id, rule_set_id=p["rule"].id, circuit_id=p["circuit"].id), "corrosion_circuit_id", "source_id", None),
    ]
    for repo, item, key, change_field, changed_value in cases:
        identifier = getattr(item, key)
        assert repo.get(identifier) is None
        assert repo.create(item) == item
        assert repo.get(identifier) == item
        updated = replace(item, **{change_field: changed_value})
        assert repo.update(updated) == updated
        assert repo.get(identifier) == updated
        with pytest.raises(RepositoryConflictError):
            repo.create(item)
    corrosion = CorrosionSourceRepository(library_database)
    corrosion.remove(p["corrosion_id"])
    assert corrosion.get(p["corrosion_id"]) is None
    assert SourceRepository(library_database).get(p["source"].id) == p["source"]
    assert _existing_rows(library_database) == before
    with pytest.raises(RepositoryNotFoundError):
        corrosion.remove(p["corrosion_id"])


@pytest.mark.parametrize("repository,item", [
    (RuleSetRepository, RuleSet(code="BAD", name="Bad", source_id=uuid4())),
    (CircuitRepository, Circuit(system_id=uuid4(), code="BAD", name_tr="Bad")),
    (FluidPropertyRepository, FluidProperty(fluid_id=uuid4(), property_name="bad", value=1, unit="-")),
    (MaterialPropertyRepository, MaterialProperty(material_id=uuid4(), property_name="bad", value=1, unit="-")),
    (PipeStandardMetadataRepository, PipeStandardMetadata(standard_id=uuid4())),
    (PipeSizeMetadataRepository, PipeSizeMetadata(pipe_size_id=uuid4())),
    (EngineeringConstantMetadataRepository, EngineeringConstantMetadata(constant_id=uuid4())),
    (CorrosionSourceRepository, CorrosionSourceLink(corrosion_circuit_id=uuid4())),
])
def test_invalid_references_raise_typed_errors_and_leave_no_partial_records(library_database, repository, item):
    repo = repository(library_database)
    with pytest.raises(RepositoryForeignKeyError) as caught:
        repo.create(item)
    assert isinstance(caught.value.__cause__, sqlite3.IntegrityError)
    assert repo.get(getattr(item, repo._key)) is None


def test_failed_metadata_update_rolls_back_existing_link(library_database, parents):
    repo = EngineeringConstantMetadataRepository(library_database)
    item = repo.create(EngineeringConstantMetadata(constant_id=parents["constant"].id, source_id=parents["source"].id))
    with pytest.raises(RepositoryForeignKeyError):
        repo.update(replace(item, source_id=uuid4(), selection_reason="Must roll back"))
    assert repo.get(item.constant_id) == item


def test_not_found_and_database_failures_are_distinct(library_database, tmp_path):
    repo = SystemRepository(library_database)
    with pytest.raises(RepositoryNotFoundError):
        repo.update(System(code="MISSING", name_tr="Missing"))
    with pytest.raises(RepositoryError) as caught:
        SourceRepository(LibraryDatabase(tmp_path / "uninitialized.db")).get(uuid4())
    assert isinstance(caught.value.__cause__, sqlite3.OperationalError)


@pytest.mark.parametrize("change", [
    {"created_at": datetime(2025, 1, 1)},
    {"modified_at": "2025-01-01"}, {"id": "not-a-uuid"},
])
def test_invalid_timestamps_or_identity_fail_before_writing(library_database, change):
    repo = SourceRepository(library_database)
    with pytest.raises(RepositoryValidationError):
        repo.create(replace(_source(), **change))
    assert repo.get_all() == ()


@pytest.mark.parametrize("change", [{"is_active": "yes"}, {"is_factory": 2}, {"code": None}])
def test_invalid_master_types_are_validation_errors(library_database, change):
    with pytest.raises(RepositoryValidationError):
        SystemRepository(library_database).create(replace(System(code="TEST", name_tr="Test"), **change))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, "1.0"])
def test_invalid_property_numbers_are_rejected(library_database, parents, value):
    with pytest.raises(RepositoryValidationError):
        FluidPropertyRepository(library_database).create(FluidProperty(fluid_id=parents["fluid"].id, property_name="test", value=value, unit="-"))


def test_reads_do_not_write_or_create_n_plus_one_queries(library_database, parents, monkeypatch):
    repo = SourceRepository(library_database)
    repo.create(_source(document="Second"))
    with library_database.connection() as c:
        before = list(c.iterdump())
    queries = []
    connection_factory = library_database.connection
    @contextmanager
    def traced():
        with connection_factory() as c:
            c.set_trace_callback(queries.append)
            yield c
    monkeypatch.setattr(library_database, "connection", traced)
    records = repo.get_all()
    assert len(records) == 2
    assert len([q for q in queries if q.startswith("SELECT")]) == 1
    assert not any(q.startswith(("INSERT", "UPDATE", "DELETE")) for q in queries)
    for item in records:
        assert repo.get(item.id) == item
    with library_database.connection() as c:
        assert list(c.iterdump()) == before
        assert not c.execute("PRAGMA foreign_key_check").fetchall()


def test_schema_versions_and_sql_definitions_remain_frozen(library_database, parents):
    with library_database.connection() as c:
        before = list(c.execute("SELECT name,sql FROM sqlite_master ORDER BY name"))
    SystemRepository(library_database).get_all()
    with library_database.connection() as c:
        assert [tuple(row) for row in c.execute("SELECT name,sql FROM sqlite_master ORDER BY name")] == [tuple(row) for row in before]
        assert c.execute("SELECT version FROM schema_version").fetchone()[0] == 5


def test_new_repositories_have_no_ui_or_calculator_dependencies():
    root = Path(__file__).resolve().parents[1] / "repositories"
    names = ("source_repository", "rule_set_repository", "system_repository", "circuit_repository",
             "fluid_repository", "fluid_property_repository", "material_property_repository",
             "pipe_metadata_repository", "engineering_constant_metadata_repository", "corrosion_source_repository",
             "_v2_base", "v2_models", "v2_errors")
    for name in names:
        tree = ast.parse((root / f"{name}.py").read_text(encoding="utf-8-sig"))
        imports = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imports |= {a.name for node in ast.walk(tree) if isinstance(node, ast.Import) for a in node.names}
        assert not any(i.startswith(("tkinter", "ui", "matplotlib", "PIL", "services")) or "calculator" in i for i in imports)
