"""Semantic layout contracts for the Phase-2 calculation-page redesign."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _page_source(name: str) -> str:
    """Read one calculation-page implementation for display-independent checks."""
    return (ROOT / "ui" / "pages" / name).read_text(encoding="utf-8")


def test_all_calculation_pages_use_shared_section_and_card_components() -> None:
    """All pages share Phase-1 primitives rather than independent color choices."""
    for name in (
        "pipe_design_page.py", "transfer_pump_page.py",
        "discharge_head_loss_page.py", "suction_npsh_page.py",
    ):
        source = _page_source(name)
        assert "SectionHeader" in source
        assert "InputCard" in source
        assert "ResultCard" in source
        assert "FormulaReferencePanel" in source


def test_pipe_layout_keeps_independent_stages_and_distinct_dn_result() -> None:
    """Presentation does not couple the two existing Pipe Design handlers."""
    source = _page_source("pipe_design_page.py")
    assert "section.pipe_diameter_inputs" in source
    assert "section.wall_thickness_inputs" in source
    assert "self._calculate_diameter" in source
    assert "self._calculate_wall" in source
    assert "result.recommended_nominal_size" in source


def test_transfer_layout_preserves_reference_crud_graph_and_estimate_paths() -> None:
    """The regression page keeps its table, graph, and authoritative callbacks."""
    source = _page_source("transfer_pump_page.py")
    assert "section.reference_vessels" in source
    assert "section.regression_summary" in source
    assert "section.estimate_results" in source
    assert "TransferPumpChart" in source
    for callback in ("self._add", "self._edit", "self._delete", "self._calculate"):
        assert callback in source


def test_discharge_and_suction_layouts_preserve_local_loss_and_stage_actions() -> None:
    """Hydraulic card hierarchy does not replace local-loss or ENPY workflows."""
    discharge = _page_source("discharge_head_loss_page.py")
    suction = _page_source("suction_npsh_page.py")
    assert "section.local_losses" in discharge and "self._calculate" in discharge
    assert "section.local_losses" in suction and "section.enpy_inputs" in suction
    assert "self._calculate_suction_loss" in suction
    assert "self._calculate_enpy" in suction


def test_phase_two_action_hierarchy_uses_semantic_styles() -> None:
    """Calculate, clear, CRUD, and formula actions retain semantic ttk styles."""
    sources = "\n".join(
        _page_source(name)
        for name in (
            "pipe_design_page.py", "transfer_pump_page.py",
            "discharge_head_loss_page.py", "suction_npsh_page.py",
        )
    )
    for style in (
        "RoundedPrimary.TButton",
        "RoundedNeutral.TButton",
        "RoundedDelete.TButton",
        "RoundedEdit.TButton",
        "RoundedFormula.TButton",
    ):
        assert style in sources
