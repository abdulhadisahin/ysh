"""Phase 8B contracts for normalized warning context and presentation wiring."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.engineering_context import CIRCUIT_TO_WARNING_FLUID, FLUID_SYSTEMS, LINE_ROLES
from engineering.warning_rules import evaluate_npsh, evaluate_velocity
from ui.pages.pipe_design_page import PipeDesignPage
from ui.pages.discharge_head_loss_page import DischargeHeadLossPage
from ui.pages.suction_npsh_page import SuctionNPSHPage
from ui.widgets.engineering_warning_panel import EngineeringWarningPanel, normalized_findings


ROOT = Path(__file__).resolve().parents[1]


class _Value:
    def __init__(self, value: str = "") -> None: self.value = value
    def get(self) -> str: return self.value
    def set(self, value: object) -> None: self.value = str(value)


class _Panel:
    def __init__(self) -> None: self.findings = ()
    def set_findings(self, findings: object) -> None: self.findings = tuple(findings)  # type: ignore[arg-type]


def test_warning_panel_visibility_method_shows_and_collapses_with_findings() -> None:
    """Exercise the live panel method without requiring a desktop display."""
    panel = EngineeringWarningPanel.__new__(EngineeringWarningPanel)
    panel._findings = ()
    panel.winfo_children = lambda: []  # type: ignore[method-assign]
    calls: list[str] = []
    panel.grid = lambda: calls.append("show")  # type: ignore[method-assign]
    panel.grid_remove = lambda: calls.append("hide")  # type: ignore[method-assign]
    panel._render_finding = lambda *_args: None  # type: ignore[method-assign]
    finding = evaluate_velocity("DIESEL_FUEL", "SUCTION", 0.32)[0]
    panel.set_findings((finding,))
    assert panel.findings == (finding,) and calls == ["show"]
    panel.set_findings(())
    assert panel.findings == () and calls[-1] == "hide"


def test_pipe_actual_calculate_callback_uses_normalized_velocity_and_renders_warning() -> None:
    page = PipeDesignPage.__new__(PipeDesignPage)
    page._fields = {"q": _Value("1"), "v": _Value("0,32")}
    page._number = lambda key: {"q": 1.0, "v": 0.32}[key]
    page._selected_pipe_standard_code = lambda: "EN_10220"
    page._selected_circuit_code = lambda: "FUEL"
    page._selected_line_role_code = lambda: "SUCTION"
    page._warning_codes_from_result = lambda: []
    page._update_diameter_summary = lambda: None
    page._refresh_diameter_warning_message = lambda: None
    page._refresh_formula_panel = lambda: None
    page._warning_panel = _Panel()
    page._service = SimpleNamespace(calculate=lambda **_kwargs: SimpleNamespace(errors=[], diameter=SimpleNamespace(to_dict=lambda: {"diameter_mm": 59.0})))
    page._calculate_diameter()
    assert page._diameter_warning_velocity_m_s == 0.32
    assert page._warning_panel.findings[0].actual_value == 0.32


def test_discharge_render_result_reacts_to_context_without_changing_result() -> None:
    page = DischargeHeadLossPage.__new__(DischargeHeadLossPage)
    page._last_result = SimpleNamespace(flow_velocity_m_s=2.30, pipe_friction_loss_m=1.0, local_loss_m=2.0, total_hydraulic_loss_m=3.0, system_head_m=4.0, reynolds_number=1.0, relative_roughness=0.1, friction_factor=0.02, local_loss_coefficient_total=2.0, warnings=[])
    page._warning_fluid_codes = {"Dizel Yakıt": "DIESEL_FUEL", "Yağlama Yağı": "LUBE_OIL"}
    page._warning_fluid = _Value("Dizel Yakıt")
    page._warning_panel = _Panel()
    page._set_semantic_messages = lambda _messages: None
    page._result_summary = page._system_head_summary = page._local_loss_summary = page._pipe_loss_summary = page._total_loss_summary = page._reynolds_summary = page._relative_roughness_summary = page._friction_factor_summary = page._k_total_summary = _Value()
    page._translate = lambda key, **_kwargs: key
    page._render_result()
    assert page._warning_panel.findings[0].actual_value == 2.30
    page._warning_fluid.set("Yağlama Yağı")
    page._evaluate_velocity_warning()
    assert page._warning_panel.findings == ()


def test_suction_combines_velocity_and_npsh_findings_in_live_page_path() -> None:
    page = SuctionNPSHPage.__new__(SuctionNPSHPage)
    page._last_loss = SimpleNamespace(flow_velocity_m_s=0.80)
    page._last_enpy = SimpleNamespace(enpym_available_m=5.20, npsh_margin_m=-0.80)
    page._warning_fluid_codes = {"Deniz Suyu": "SEA_WATER"}
    page._warning_fluid = _Value("Deniz Suyu")
    page._warning_panel = _Panel()
    page._evaluate_engineering_warnings()
    assert {finding.severity.value for finding in page._warning_panel.findings} == {"ENGINEERING_WARNING", "CRITICAL_WARNING"}


def test_normalized_context_uses_stable_codes_and_turkish_labels() -> None:
    assert [item.code for item in FLUID_SYSTEMS] == ["DIESEL_FUEL", "LUBE_OIL", "SEA_WATER"]
    assert [item.turkish_label for item in FLUID_SYSTEMS] == ["Dizel Yakıt", "Yağlama Yağı", "Deniz Suyu"]
    assert [item.code for item in LINE_ROLES] == ["SUCTION", "DELIVERY"]
    assert CIRCUIT_TO_WARNING_FLUID == {"FUEL": "DIESEL_FUEL", "SEA_WATER": "SEA_WATER"}


def test_warning_presentation_ordering_deduplicates_and_preserves_distinct_findings() -> None:
    velocity = evaluate_velocity("DIESEL_FUEL", "SUCTION", 0.32)[0]
    critical = evaluate_npsh(3.0, 4.0)[0]
    assert normalized_findings((velocity, velocity, critical)) == (critical, velocity)
    assert normalized_findings(()) == ()


def test_warning_component_and_all_three_page_contracts_are_wired() -> None:
    panel = (ROOT / "ui/widgets/engineering_warning_panel.py").read_text(encoding="utf-8")
    pipe = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")
    discharge = (ROOT / "ui/pages/discharge_head_loss_page.py").read_text(encoding="utf-8")
    suction = (ROOT / "ui/pages/suction_npsh_page.py").read_text(encoding="utf-8")
    assert "EngineeringWarningPanel" in panel and "normalized_findings" in panel
    assert '"line_role": self._selected_line_role_code()' in pipe
    assert "warning_fluid_for_circuit" in pipe and "_evaluate_velocity_warning" in pipe
    assert '"warning_fluid":self._selected_warning_fluid()' in discharge
    assert 'evaluate_velocity(fluid,"DELIVERY",result.flow_velocity_m_s)' in discharge
    assert '"warning_fluid": self._selected_warning_fluid()' in suction
    assert 'evaluate_velocity(fluid, "SUCTION", loss.flow_velocity_m_s)' in suction
    assert "evaluate_npsh(enpy.enpym_available_m, required)" in suction


def test_phase8b_context_does_not_add_transfer_warning_rules() -> None:
    transfer = (ROOT / "ui/pages/transfer_pump_page.py").read_text(encoding="utf-8")
    assert "EngineeringWarningPanel" not in transfer
    assert "evaluate_velocity" not in transfer


def test_warning_panels_are_adjacent_to_the_results_they_qualify() -> None:
    """Keep warning presentation out of remote formula/reference page rows."""
    pipe = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")
    discharge = (ROOT / "ui/pages/discharge_head_loss_page.py").read_text(encoding="utf-8")
    suction = (ROOT / "ui/pages/suction_npsh_page.py").read_text(encoding="utf-8")
    assert "EngineeringWarningPanel(inputs, self._translate)" in pipe
    assert "row=1, column=1" in pipe and "self._wall_inputs.grid_configure(\n            row=2" in pipe
    assert "EngineeringWarningPanel(results,self._translate)" in discharge
    assert "row=4,column=0,columnspan=2" in discharge
    assert "EngineeringWarningPanel(results, self._translate)" in suction
    assert "self._warning_panel.grid(row=4, column=0, sticky=\"ew\"" in suction
