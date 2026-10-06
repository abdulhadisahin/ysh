"""Phase 5 contracts for manually authoritative B and Table 8.9 reference."""

from __future__ import annotations

from pathlib import Path

import pytest

from engineering.pipe_design.models import WallThicknessInput
from engineering.turk_loydu_table_8_9 import TABLE_8_9_ROWS
from engineering.validation import ValidationError
from services.pipe_design_service import PipeDesignService


ROOT = Path(__file__).resolve().parents[1]
NOTE = "Emniyet katsayısı B, Türk Loydu Bölüm 8 Tablo 8.9'a göre Boru Sınıfı II ve III çelik borular için 1,80 alınmıştır."


def test_table_8_9_reference_is_exact_and_preserves_missing_values() -> None:
    assert len(TABLE_8_9_ROWS) == 6
    assert TABLE_8_9_ROWS[0].class_i_a == "2,7" and TABLE_8_9_ROWS[0].class_ii_iii_b == "1,8"
    assert TABLE_8_9_ROWS[1].class_i_a == "2,4" and TABLE_8_9_ROWS[1].class_i_b == "1,6"
    assert TABLE_8_9_ROWS[2].class_i_b == "1,7" and TABLE_8_9_ROWS[2].class_ii_iii_b == "1,8"
    assert TABLE_8_9_ROWS[3].class_i_a == "-" and TABLE_8_9_ROWS[3].class_ii_iii_b == "-"
    assert TABLE_8_9_ROWS[4].class_ii_iii_b == "3,0"
    assert TABLE_8_9_ROWS[5].class_i_b == "-" and TABLE_8_9_ROWS[5].class_ii_iii_a == "4,0"


def test_manual_b_reaches_existing_formula_and_nonpositive_b_is_rejected(material_service: object, pipe_size_service: object, engineering_constant_service: object) -> None:
    service = PipeDesignService(material_service, pipe_size_service, engineering_constant_service)
    default = service.calculate(wall=WallThicknessInput(273.05, 16, 190, 1.8, 1, 1))
    custom = service.calculate(wall=WallThicknessInput(273.05, 16, 190, 1.6, 1, 1))
    assert default.wall_thickness is not None and custom.wall_thickness is not None
    assert custom.wall_thickness.final_wall_thickness_mm < default.wall_thickness.final_wall_thickness_mm
    with pytest.raises(ValidationError):
        service.calculate(wall=WallThicknessInput(100, 16, 190, 0, 1, 1))


def test_pipe_page_visibly_initializes_b_and_formula_uses_actual_value() -> None:
    source = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")
    messages = (ROOT / "i18n/messages_tr.py").read_text(encoding="utf-8")
    assert 'self._fields["sf"].set(format_user_number(1.8))' in source
    assert 'safety_factor = format_user_number(self._number("sf"))' in source
    assert "B = {safety_factor}" in source
    assert NOTE in messages
    assert "TurkLoyduTable89Dialog" in source
