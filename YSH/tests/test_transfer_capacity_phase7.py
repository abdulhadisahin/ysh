"""Phase 7 D243 tonne conversion and 12-hour Transfer Pump contracts."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.pump_reference import PumpReference
from engineering.input_parsing import parse_engineering_float
from engineering.transfer_pump.capacity_basis import (
    CAPACITY_MODE_MASS,
    CAPACITY_MODE_VOLUME,
    FUEL_DENSITY_T_PER_M3,
    resolve_fuel_capacity,
)
from engineering.validation import ValidationError, ValidationIssue
from services.transfer_pump_service import TransferPumpService
from ui.formatting import format_user_number


ROOT = Path(__file__).resolve().parents[1]


class _References:
    def __init__(self) -> None:
        self.records = [
            PumpReference("A", 100.0, 20.0),
            PumpReference("B", 200.0, 30.0),
            PumpReference("C", 300.0, 40.0),
        ]

    def get_all_references(self) -> list[PumpReference]:
        return self.records


def test_ton_capacity_uses_fixed_d243_basis_without_premature_rounding() -> None:
    resolved = resolve_fuel_capacity(CAPACITY_MODE_MASS, 6654.0)

    assert FUEL_DENSITY_T_PER_M3 == 0.83
    assert resolved.volume_m3 == pytest.approx(6654 / 0.83)
    assert resolved.volume_m3 != round(resolved.volume_m3, 2)
    assert format_user_number(resolved.volume_m3) == "8.016,87"
    assert resolved.required_capacity_12h_m3h == pytest.approx((6654 / 0.83) / 12)
    assert format_user_number(resolved.required_capacity_12h_m3h) == "668,07"


@pytest.mark.parametrize("raw", ("6654", "6654,5", "6654.5"))
def test_existing_parser_accepts_tonne_decimal_input_forms(raw: str) -> None:
    value = parse_engineering_float(raw, field_name="Yakıt Kütlesi", field_key="field.fuel_capacity_mass")
    assert value is not None and value > 0


@pytest.mark.parametrize("value", (0.0, -1.0, float("nan")))
def test_invalid_tonne_values_are_rejected(value: float) -> None:
    with pytest.raises(ValidationError) as caught:
        resolve_fuel_capacity(CAPACITY_MODE_MASS, value)
    assert caught.value.issue.field_key == "field.fuel_capacity_mass"


def test_direct_volume_mode_bypasses_conversion() -> None:
    resolved = resolve_fuel_capacity(CAPACITY_MODE_VOLUME, 8016.87)
    assert resolved.volume_m3 == 8016.87
    assert resolved.required_capacity_12h_m3h == pytest.approx(8016.87 / 12)


def test_tonne_and_equivalent_volume_use_the_same_unchanged_regression_path() -> None:
    service = TransferPumpService(_References())
    ton_resolution, ton_result = service.calculate_from_capacity_input(CAPACITY_MODE_MASS, 6654.0)
    volume_resolution, volume_result = service.calculate_from_capacity_input(
        CAPACITY_MODE_VOLUME, ton_resolution.volume_m3
    )

    assert ton_result.predicted_pump_capacity_m3h == pytest.approx(volume_result.predicted_pump_capacity_m3h)
    assert ton_result.estimated_emptying_time_hours == pytest.approx(volume_result.estimated_emptying_time_hours)
    assert ton_result.regression_model == volume_result.regression_model
    assert volume_resolution.volume_m3 == pytest.approx(ton_resolution.volume_m3)


def test_transfer_page_contract_keeps_source_units_q12_and_regression_separate() -> None:
    source = (ROOT / "ui/pages/transfer_pump_page.py").read_text(encoding="utf-8")
    assert '"capacity_input_mode": self._selected_capacity_mode()' in source
    assert "calculate_from_capacity_input" in source
    assert '"result.required_capacity_12h"' in source
    assert 'FormulaSection("FORMULA", "Q12 = V / 12"' in source
    assert 'FormulaSection("FORMULA", "V = M / ρ"' in source
    assert "self._capacity.set(\"\")" in source


def test_transfer_localized_labels_are_turkish_and_keep_d243_basis_explicit() -> None:
    source = (ROOT / "i18n/messages_tr.py").read_text(encoding="utf-8")
    assert '"transfer.capacity_mode.volume": "Hacim [m³]"' in source
    assert '"transfer.capacity_mode.mass": "Kütle [ton]"' in source
    assert "D243 dönüşüm katsayısı: 0,83 t/m³" in source
    assert "regresyon tahmini değildir" in source


def test_capacity_mode_validation_uses_semantic_issue() -> None:
    with pytest.raises(ValidationError) as caught:
        resolve_fuel_capacity("unexpected", 10.0)
    assert caught.value.issue == ValidationIssue("capacity_input_mode_invalid")
