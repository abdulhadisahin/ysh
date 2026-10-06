"""Phase 3 regression contracts for circuit-based corrosion allowance defaults."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.corrosion_allowance_circuit import CorrosionAllowanceCircuit
from database.library_database import LibraryDatabase
from engineering.validation import ValidationError
from repositories.corrosion_allowance_circuit_repository import CorrosionAllowanceCircuitRepository
from services.corrosion_allowance_circuit_service import CorrosionAllowanceCircuitService


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def circuit_service(library_database: LibraryDatabase) -> CorrosionAllowanceCircuitService:
    return CorrosionAllowanceCircuitService(CorrosionAllowanceCircuitRepository(library_database))


def test_phase3_schema_seeds_exact_editable_d243_defaults(library_database: LibraryDatabase, circuit_service: CorrosionAllowanceCircuitService) -> None:
    with library_database.connection() as connection:
        version = connection.execute("SELECT version FROM schema_version").fetchone()["version"]
        table = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='corrosion_allowance_circuits'").fetchone()
    values = {item.code: item.default_corrosion_allowance_mm for item in circuit_service.get_active_circuits()}

    assert version == 4
    assert table is not None
    assert values == {"FUEL": 1.0, "SEA_WATER": 3.0, "BOILER_BLOWDOWN": 1.5}


def test_phase3_seed_is_idempotent_and_preserves_existing_library_data(library_database: LibraryDatabase, circuit_service: CorrosionAllowanceCircuitService) -> None:
    initial = tuple(circuit_service.get_all_circuits())
    with library_database.connection() as connection:
        before_materials = len(connection.execute("SELECT * FROM materials").fetchall())
    library_database.initialize()
    assert tuple(circuit_service.get_all_circuits()) == initial
    with library_database.connection() as connection:
        assert len(connection.execute("SELECT * FROM materials").fetchall()) == before_materials


def test_circuit_service_crud_and_validation(circuit_service: CorrosionAllowanceCircuitService) -> None:
    item = circuit_service.create_circuit(code="TEST", display_name="Test Devresi", default_corrosion_allowance_mm=2.5)
    item.default_corrosion_allowance_mm = 2.75
    assert circuit_service.update_circuit(item).default_corrosion_allowance_mm == 2.75
    with pytest.raises(ValidationError):
        circuit_service.create_circuit(code="TEST", display_name="Tekrar", default_corrosion_allowance_mm=1.0)
    with pytest.raises(ValidationError):
        circuit_service.create_circuit(code="NEGATIVE", display_name="Geçersiz", default_corrosion_allowance_mm=-1.0)
    circuit_service.delete_circuit(item.id)
    with pytest.raises(ValidationError):
        circuit_service.get_circuit_by_code("TEST")


def test_pipe_page_persists_circuit_default_and_override_state() -> None:
    source = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")
    assert '"circuit_code": self._selected_circuit_code()' in source
    assert '"corrosion_allowance_manual_override": self._corrosion_allowance_override' in source
    assert 'text=self._translate("field.circuit")' in source
    assert "def _on_circuit_selected" in source
    assert "def _update_circuit_summary" in source
    assert "result.default_corrosion_allowance" in source
    assert "result.used_corrosion_allowance" in source


def test_formula_reference_includes_circuit_context_without_changing_math() -> None:
    source = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")
    assert "s = s0 + c + b" in source
    assert "circuit_context" in source
    assert "self._selected_circuit_name()" in source


def test_circuit_library_is_service_backed_and_turkish() -> None:
    source = (ROOT / "ui/dialogs/corrosion_allowance_circuit_library_dialog.py").read_text(encoding="utf-8")
    assert "Devre / Korozyon Artımı Kütüphanesi" in source
    assert "service.create_circuit" in source
    assert "service.update_circuit" in source
    assert "service.delete_circuit" in source
