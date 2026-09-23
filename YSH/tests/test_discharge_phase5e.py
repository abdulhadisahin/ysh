"""Presentation contracts for the Phase 5E Discharge Head Loss page."""

from __future__ import annotations

from pathlib import Path

from i18n.messages_en import MESSAGES as MESSAGES_EN
from i18n.messages_tr import MESSAGES as MESSAGES_TR


ROOT = Path(__file__).resolve().parents[1]


def _page_source() -> str:
    """Return the display-layer discharge page source."""
    return (ROOT / "ui" / "pages" / "discharge_head_loss_page.py").read_text(
        encoding="utf-8"
    )


def test_discharge_page_uses_the_approved_three_area_workspace() -> None:
    """Inputs, local losses, and results share one responsive upper workspace."""
    source = _page_source()

    for required_element in (
        'self._translate("section.hydraulic_inputs")',
        'self._translate("section.local_losses")',
        'self._translate("section.calculation_results")',
        'workspace.columnconfigure(0,weight=3)',
        'workspace.columnconfigure(1,weight=3)',
        'workspace.columnconfigure(2,weight=3)',
        "FormulaReferencePanel(self",
    ):
        assert required_element in source


def test_discharge_results_keep_hs_primary_and_hydraulic_values_secondary() -> None:
    """The authoritative system head is the blue primary metric, not a new result."""
    source = _page_source()

    assert 'self._translate("result.pump_discharge_head")' in source
    assert 'normal_style_prefix="DischargeResultMetric"' in source
    assert 'normal_style_prefix="DischargeLossMetric"' in source
    for metric in (
        "self._reynolds_summary",
        "self._relative_roughness_summary",
        "self._friction_factor_summary",
        "self._local_loss_summary",
        "self._pipe_loss_summary",
        "self._total_loss_summary",
    ):
        assert metric in source


def test_discharge_initial_metrics_and_sigma_k_use_page_owned_result_state() -> None:
    """Initial values are quiet and ΣK is displayed only from a service result."""
    source = _page_source()

    assert 'self._k_total_summary=tk.StringVar(value="—")' in source
    assert '"result.local_loss_coefficient",self._k_total_summary' in source
    assert "result.local_loss_coefficient_total" in source
    assert "def _clear_result_metrics" in source


def test_discharge_table_crud_and_formula_remain_authoritative() -> None:
    """Presentation retains UUID-backed local-loss actions and no UI-side solver."""
    source = _page_source()
    formula_source = source.split("def _formula_sections", 1)[1].split(
        "def _calculate", 1
    )[0]

    assert 'self._tree.configure(style="Discharge.Treeview")' in source
    assert "ScrollableTreeview(" in source
    for callback in ("self._add", "self._edit", "self._delete"):
        assert callback in source
    assert "self._service.calculate" not in formula_source


def test_discharge_phase5e_labels_are_available_in_english_and_turkish() -> None:
    """New visual headings and result names remain live-localizable."""
    for key in (
        "section.hydraulic_inputs",
        "section.calculation_results",
        "result.relative_roughness",
        "result.pump_discharge_head",
    ):
        assert MESSAGES_EN[key]
        assert MESSAGES_TR[key]


def test_discharge_workspace_reflows_from_requested_widths() -> None:
    """The three cards retain the wide layout and reflow without page scrolling."""
    source = _page_source()

    for required_element in (
        'self._workspace.bind("<Configure>",self._on_workspace_configure',
        "def _reflow_layout",
        "winfo_reqwidth()",
        'mode=="wide"',
        'mode=="two_column"',
        "self._losses_card.grid_configure(row=1,column=0,columnspan=2",
        "self._results_card.grid_configure(row=2,column=0,columnspan=1",
    ):
        assert required_element in source
    assert "xscrollcommand" not in source


def test_discharge_actions_and_supporting_metrics_reflow_in_place() -> None:
    """Narrow result cards retain their authoritative actions and supporting values."""
    source = _page_source()

    for required_element in (
        "def _reflow_action_buttons",
        "def _reflow_supporting_metrics",
        "self._loss_action_buttons",
        "self._result_action_buttons",
        "self._system_metric=ResultMetric",
        "self._k_total_summary",
        "_reflow_button_group",
    ):
        assert required_element in source


def test_discharge_uses_structured_metrics_without_redundant_result_dump() -> None:
    """Hs and its supporting values remain the sole visible result presentation."""
    source = _page_source()

    assert "self._system_metric=ResultMetric" in source
    assert "self._supporting_metric_widgets" in source
    assert 'ttk.Label(results,textvariable=self._result_summary' not in source
