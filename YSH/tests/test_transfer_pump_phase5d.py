"""Presentation contracts for the Phase 5D Fuel Transfer Pump page."""

from __future__ import annotations

from pathlib import Path

from i18n.messages_en import MESSAGES as MESSAGES_EN
from i18n.messages_tr import MESSAGES as MESSAGES_TR


ROOT = Path(__file__).resolve().parents[1]


def _page_source() -> str:
    """Return the Fuel Transfer page source for display-independent checks."""
    return (ROOT / "ui" / "pages" / "transfer_pump_page.py").read_text(
        encoding="utf-8"
    )


def test_transfer_page_uses_the_d243_input_result_data_graph_layout() -> None:
    """Input/results lead into references, regression chart, and formula reference."""
    source = _page_source()

    for required_element in (
        'self._translate("section.reference_vessels")',
        'self._translate("section.new_vessel")',
        'self._translate("section.estimate_results")',
        'self._translate("section.regression_chart")',
        "TransferPumpChart(self",
        "FormulaReferencePanel(self",
    ):
        assert required_element in source

    assert 'upper.columnconfigure(0, weight=2)' in source
    assert 'upper.columnconfigure(1, weight=3)' in source
    assert 'analysis.columnconfigure(0, weight=3)' in source
    assert 'analysis.columnconfigure(1, weight=4)' in source


def test_transfer_dashboard_separates_prediction_q12_time_and_model_quality() -> None:
    """The dashboard keeps authoritative results distinct before and after calculation."""
    source = _page_source()

    assert 'self._estimate_capacity_summary = tk.StringVar(value="—")' in source
    assert 'self._emptying_time_summary = tk.StringVar(value="—")' in source
    assert 'self._required_capacity_12h_summary = tk.StringVar(value="—")' in source
    assert 'self._r_squared_summary = tk.StringVar(value="—")' in source
    assert 'normal_style_prefix="TransferResultMetric"' in source
    assert 'normal_style_prefix="TransferSecondaryMetric"' in source
    assert 'style="TransferRoundedPrimary.TButton"' in source
    assert 'self._required_12h_metric.grid(row=1, column=0, sticky="ew", pady=(4, 0))' in source
    assert 'self._emptying_result_metric.grid(row=2, column=0, sticky="ew", pady=(4, 0))' in source
    assert 'self._r_squared_metric.grid(row=3, column=0, sticky="ew", pady=(4, 0))' in source
    assert 'estimate.grid(row=0, column=0, sticky="new"' in source


def test_transfer_table_preserves_crud_identity_and_local_scrolling() -> None:
    """The visual redesign leaves service-backed UUID CRUD and local scrolling intact."""
    source = _page_source()

    assert "TechnicalTable(" in source
    assert 'self._tree.configure(style="Transfer.Treeview")' in source
    assert "UUID(selected[0])" in source
    for callback in ("self._add", "self._edit", "self._delete"):
        assert callback in source


def test_transfer_formula_and_chart_remain_authoritative_projections() -> None:
    """Formula and chart presentation do not refit or calculate regression values."""
    source = _page_source()
    formula_source = source.split("def _formula_sections", 1)[1]

    assert "self._service.calculate(capacity)" not in formula_source
    assert "TransferPumpChartModel.from_authoritative(" in source
    assert "self._formula_panel.expanded" in source


def test_transfer_visual_labels_are_available_in_english_and_turkish() -> None:
    """New visual headings remain live-localizable without translating source data."""
    keys = (
        "section.reference_vessels",
        "section.new_vessel",
        "section.regression_summary",
        "result.predicted_pump_capacity",
        "result.full_tank_discharge_time",
    )

    for key in keys:
        assert MESSAGES_EN[key]
        assert MESSAGES_TR[key]


def test_transfer_workspace_reflows_the_two_d243_workspaces() -> None:
    """Input/results and data/chart pairs stack without recreating widgets."""
    source = _page_source()

    for required_element in (
        'self._upper.bind("<Configure>", self._on_upper_configure',
        'self._analysis.bind("<Configure>", self._on_upper_configure',
        "def _reflow_layout",
        "winfo_reqwidth()",
        'mode == "wide"',
        'mode = "wide" if content_width >= max(input_result_width, analysis_width) else "stacked"',
        "self._references_card.grid_configure(",
        "self._chart_card.grid_configure(",
        "self._results_card.grid_configure(",
    ):
        assert required_element in source
    assert "xscrollcommand" not in source


def test_transfer_mass_context_is_compact_derived_information() -> None:
    """Mass mode presents source mass, derived volume, and the D243 basis separately."""
    source = _page_source()

    for required_element in (
        'self._translate("transfer.entered_fuel_mass")',
        "self._entered_mass_value",
        "self._converted_volume_summary",
        'self._translate("transfer.conversion_basis")',
        "self._conversion_detail_frame.grid_remove()",
    ):
        assert required_element in source


def test_transfer_actions_reflow_without_replacing_metrics_or_chart() -> None:
    """Responsive geometry retains original widgets, callbacks, and metrics."""
    source = _page_source()

    for required_element in (
        "def _reflow_action_buttons",
        "def _reflow_button_group",
        "self._reference_action_buttons",
        "self._estimate_action_buttons",
        "self._pump_result_metric = ResultMetric",
        "self._emptying_result_metric = ResultMetric",
        "TransferPumpChart(self",
    ):
        assert required_element in source
