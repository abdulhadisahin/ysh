"""Phase 4 contracts for the manually authoritative weld factor v."""

from __future__ import annotations

from pathlib import Path

import pytest

from engineering.pipe_design.models import WallThicknessInput
from engineering.validation import ValidationError
from services.pipe_design_service import PipeDesignService


ROOT = Path(__file__).resolve().parents[1]
NOTE = "Kaynak Faktörü dikişsiz borular için 1 alınmıştır. (Türk Loydu)"


def test_weld_factor_default_and_manual_value_reach_existing_formula(material_service: object, pipe_size_service: object, engineering_constant_service: object) -> None:
    service = PipeDesignService(material_service, pipe_size_service, engineering_constant_service)
    default = service.calculate(wall=WallThicknessInput(273.05, 16.0, 190.0, 1.8, 1.0, 1.0))
    manual = service.calculate(wall=WallThicknessInput(273.05, 16.0, 190.0, 1.8, 0.85, 1.0))
    assert default.wall_thickness is not None and manual.wall_thickness is not None
    assert manual.wall_thickness.final_wall_thickness_mm > default.wall_thickness.final_wall_thickness_mm


@pytest.mark.parametrize("weld_factor", [0.0, -1.0])
def test_non_positive_weld_factor_remains_rejected(weld_factor: float, material_service: object, pipe_size_service: object, engineering_constant_service: object) -> None:
    service = PipeDesignService(material_service, pipe_size_service, engineering_constant_service)
    with pytest.raises(ValidationError):
        service.calculate(wall=WallThicknessInput(100.0, 16.0, 190.0, 1.8, weld_factor, 1.0))


def test_pipe_page_keeps_v_independent_and_formula_view_reports_actual_value() -> None:
    source = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")
    assert 'self._fields["wf"].set(format_user_number(values["weld_factor"]))' in source
    assert 'weld_factor = format_user_number(self._number("wf"))' in source
    assert "v = {weld_factor}" in source
    assert "formula.weld_factor_reference_note" in source
    assert "_on_circuit_selected" in source
    assert "PipeSizeService.DEFAULT_STANDARD_CODE" in source


def test_reference_note_is_exact_turkish_information_only() -> None:
    source = (ROOT / "i18n/messages_tr.py").read_text(encoding="utf-8")
    assert NOTE in source
    assert "Türk Loydu)" in source
    assert "table" not in NOTE.casefold() and "section" not in NOTE.casefold()
