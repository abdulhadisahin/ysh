"""Presentation contracts for the Phase 5F Suction and ENPY page."""

from __future__ import annotations

from pathlib import Path

from i18n.messages_en import MESSAGES as MESSAGES_EN
from i18n.messages_tr import MESSAGES as MESSAGES_TR


ROOT = Path(__file__).resolve().parents[1]


def test_suction_page_keeps_two_stages_and_local_formula_panel() -> None:
    """Suction loss and ENPY remain distinct page-owned engineering stages."""
    source = (ROOT / "ui" / "pages" / "suction_npsh_page.py").read_text(
        encoding="utf-8"
    )
    for key in (
        "section.suction_inputs",
        "section.local_losses",
        "section.suction_results",
        "section.enpy_calculation",
        "FormulaReferencePanel(self",
    ):
        assert key in source


def test_suction_visuals_preserve_uuid_local_losses_and_authoritative_handlers() -> None:
    """Presentation keeps local-loss CRUD and both existing calculation handlers."""
    source = (ROOT / "ui" / "pages" / "suction_npsh_page.py").read_text(
        encoding="utf-8"
    )
    assert 'self._tree.configure(style="Suction.Treeview")' in source
    assert "self._add_loss" in source and "self._edit_loss" in source
    assert "self._delete_loss" in source
    assert "self._calculate_suction_loss" in source
    assert "self._calculate_enpy" in source
    assert 'normal_style_prefix="SuctionResultMetric"' in source
    assert 'normal_style_prefix="SuctionLossMetric"' in source


def test_suction_phase5f_labels_are_localized() -> None:
    """New section captions remain available for live EN/TR refresh."""
    for key in (
        "section.suction_inputs",
        "section.suction_results",
        "section.enpy_calculation",
        "result.flow_regime",
        "result.suction_pressure_head",
        "result.vapour_pressure_head",
    ):
        assert MESSAGES_EN[key]
        assert MESSAGES_TR[key]


def test_suction_detail_display_uses_localized_existing_result_values() -> None:
    """Supporting hydraulics render through the active translator, not English literals."""
    source = (ROOT / "ui" / "pages" / "suction_npsh_page.py").read_text(
        encoding="utf-8"
    )

    assert "self._translate('result.flow_regime')" in source
    assert "self._translate('result.suction_pressure_head')" in source
    assert "self._translate('result.vapour_pressure_head')" in source
    assert 'f"Flow velocity:' not in source
    assert 'f"Suction-pressure head:' not in source


def test_suction_structures_live_details_and_preserves_persisted_text_fallback() -> None:
    """Live values use metric rows while older saved presentation remains visible."""
    source = (ROOT / "ui" / "pages" / "suction_npsh_page.py").read_text(
        encoding="utf-8"
    )

    assert 'style="EngineeringDetails.TFrame"' in source
    assert "self._detail_values" in source
    assert "def _sync_detail_presentation" in source
    assert "self._result_fallback" in source


def test_suction_workspace_reflows_from_requested_widths_without_replacing_cards() -> None:
    """Constrained layouts grow vertically instead of squeezing three card columns."""
    source = (ROOT / "ui" / "pages" / "suction_npsh_page.py").read_text(
        encoding="utf-8"
    )

    assert 'bind("<Configure>", self._on_layout_configure, add="+")' in source
    assert "def _reflow_layout" in source
    assert "winfo_reqwidth()" in source
    assert 'mode = "two-column"' in source
    assert 'mode = "stacked"' in source
    assert "self._losses_card.grid_configure(row=2, column=0, columnspan=2" in source
    assert ".place(" not in source


def test_suction_action_row_reflows_and_metrics_keep_native_result_components() -> None:
    """Localized actions stack before clipping while result metrics retain unit coupling."""
    source = (ROOT / "ui" / "pages" / "suction_npsh_page.py").read_text(
        encoding="utf-8"
    )

    assert "def _on_actions_configure" in source
    assert "button.grid_configure(row=row, column=0" in source
    assert 'normal_style_prefix="SuctionResultMetric"' in source
    assert 'normal_style_prefix="SuctionLossMetric"' in source
