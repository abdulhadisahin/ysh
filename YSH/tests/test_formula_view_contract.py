"""Display-independent contracts for the structured formula audit view."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_common_formula_view_is_inline_and_expandable() -> None:
    """The common component expands in the page rather than opening a dialog."""
    source = (ROOT / "ui/widgets/formula_view.py").read_text(encoding="utf-8")
    assert "FormulaSection" in source
    assert "FormulaReferencePanel" in source
    assert "grid_remove" in source
    assert '"common.show_formula"' in source
    assert '"common.hide_formula"' in source
    assert "Toplevel" not in source


def test_pipe_formula_uses_engineering_weld_symbol_and_separate_dn_section() -> None:
    """Pipe audit output separates DN selection from the mathematical result."""
    source = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")
    assert "field.weld_factor" in source
    assert "PIPE SIZE RECOMMENDATION" in source
    assert "formula.pipe_size_recommendation_note" in source
    assert "result.required_wall_thickness" in source


def test_module_formula_references_are_static_and_result_state_driven() -> None:
    """Each tab owns an inline static reference plus stored-result audit data."""
    transfer = (ROOT / "ui/pages/transfer_pump_page.py").read_text(encoding="utf-8")
    discharge = (ROOT / "ui/pages/discharge_head_loss_page.py").read_text(encoding="utf-8")
    suction = (ROOT / "ui/pages/suction_npsh_page.py").read_text(encoding="utf-8")
    for source in (transfer, discharge, suction):
        assert "FormulaReferencePanel" in source
        assert "_formula_sections" in source
        assert "FormulaViewDialog" not in source
    assert "_estimate_result" in transfer and "LINEAR REGRESSION MODEL" in transfer
    assert "_last_result" in discharge and "formula.stage.system_manometric_head" in discharge
    assert "_last_loss" in suction and "ENPY / NPSH AVAILABLE" in suction


def test_formula_state_is_invalidated_after_user_input_changes() -> None:
    """Pages clear stale formula eligibility rather than presenting old results."""
    pipe = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")
    transfer = (ROOT / "ui/pages/transfer_pump_page.py").read_text(encoding="utf-8")
    discharge = (ROOT / "ui/pages/discharge_head_loss_page.py").read_text(encoding="utf-8")
    assert "self._diameter_result = {}" in pipe
    assert "pop(\"_estimate_result\"" in transfer
    assert "pop(\"_last_result\"" in discharge
    assert "pop(\"_last_loss\"" in (ROOT / "ui/pages/suction_npsh_page.py").read_text(
        encoding="utf-8"
    )
