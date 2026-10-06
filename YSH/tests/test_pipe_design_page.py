"""Regression tests for the pipe-design page UI behavior."""

from __future__ import annotations

from pathlib import Path

from ui.pages.pipe_design_page import PipeDesignPage
from i18n.translator import Translator


ROOT = Path(__file__).resolve().parents[1]


def test_pipe_page_keeps_two_visual_engineering_stages_and_no_head_loss_inputs() -> None:
    """The presentation separates pipe sizing from wall thickness only."""
    source = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")
    assert 'diameter_inputs.grid(row=0, column=0' in source
    assert 'wall_inputs.grid(row=2, column=0' in source
    assert '"calculation.calculate_diameter"' in source
    assert '"calculation.calculate_wall_thickness"' in source
    for forbidden in ("Kinematic Viscosity", "Reynolds", "Friction Factor"):
        assert forbidden not in source


class _FakeStringVar:
    """Provide only the string-variable contract needed by display tests."""

    def __init__(self) -> None:
        self.value = ""

    def set(self, value: str) -> None:
        """Record the current display text."""
        self.value = value

    def get(self) -> str:
        """Return the current test value."""
        return self.value


class _FakeWidget:
    """Record state updates without creating Tkinter widgets."""

    def __init__(self) -> None:
        self.state_value: str | None = None

    def configure(self, **kwargs: object) -> None:
        if "state" in kwargs:
            self.state_value = str(kwargs["state"])


def test_recommended_pipe_transfer_uses_only_the_authoritative_outside_diameter() -> None:
    """A DN or calculated hydraulic diameter can never be copied into ``da``."""
    page = PipeDesignPage.__new__(PipeDesignPage)
    page._diameter_result = {
        "diameter_mm": 74.25,
        "recommended_dn": "DN80",
        "recommended_outside_diameter_mm": 88.9,
    }
    page._fields = {"da": _FakeStringVar()}
    page._manual_da_override = True
    page._suppress_dirty = False
    dirty_calls: list[None] = []
    page._dirty_callback = lambda: dirty_calls.append(None)

    page._use_recommended_pipe()

    assert page._fields["da"].value == "88.9"
    assert page._fields["da"].value not in {"74.25", "80", "DN80"}
    assert page._manual_da_override is False
    assert dirty_calls == [None]


def test_recommended_pipe_transfer_rejects_missing_or_non_authoritative_values() -> None:
    """The action remains inert without a valid library outside-diameter field."""
    page = PipeDesignPage.__new__(PipeDesignPage)
    page._diameter_result = {"diameter_mm": 74.25, "recommended_dn": "DN80"}
    page._fields = {"da": _FakeStringVar()}
    page._manual_da_override = False
    page._suppress_dirty = False
    page._dirty_callback = None

    page._use_recommended_pipe()

    assert page._fields["da"].value == ""


def test_pipe_diameter_calculation_no_longer_automatically_overwrites_da() -> None:
    """The explicit transfer action protects an existing wall-thickness input."""
    source = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")
    calculate_diameter = source.split("def _calculate_diameter", 1)[1].split(
        "def _calculate_wall", 1
    )[0]

    assert 'self._fields["da"].set' not in calculate_diameter
    assert "def _use_recommended_pipe" in source
    assert "command=self._use_recommended_pipe" in source
    assert 'state="disabled"' in source


def test_pipe_design_page_can_disable_and_enable_widgets() -> None:
    """The page should toggle the state of its contained widgets."""
    widget_a = _FakeWidget()
    widget_b = _FakeWidget()

    page = PipeDesignPage.__new__(PipeDesignPage)
    page._widgets = [widget_a, widget_b]

    page.set_workspace_enabled(False)
    page.set_workspace_enabled(True)

    assert widget_a.state_value == "normal"
    assert widget_b.state_value == "normal"


def test_pipe_diameter_summary_uses_the_stored_distinct_dn_recommendation() -> None:
    """The UI renders existing result data and does not independently derive DN."""
    page = PipeDesignPage.__new__(PipeDesignPage)
    page._display_places = 6
    page._diameter_summary = _FakeStringVar()
    page._diameter_result = {"diameter_mm": 74.25, "recommended_dn": "DN80"}

    page._update_diameter_summary()

    assert page._diameter_summary.value == "74,25 mm\nRecommended Nominal Size: DN80"


def test_pipe_diameter_summary_clears_and_reports_out_of_range_state() -> None:
    """Invalidated and unsupported results never show a stale or false DN."""
    page = PipeDesignPage.__new__(PipeDesignPage)
    page._display_places = 6
    page._diameter_summary = _FakeStringVar()
    page._diameter_result = {
        "diameter_mm": 600.0,
        "recommended_dn": None,
        "warnings": ["no_suitable_dn"],
    }
    page._diameter_warning_codes = ["no_suitable_dn"]
    page._translate = Translator("en").translate

    page._update_diameter_summary()
    assert "No suitable DN available" in page._diameter_summary.value

    page._diameter_result = {}
    page._diameter_warning_codes = []
    page._update_diameter_summary()
    assert page._diameter_summary.value == "—"


def test_pipe_dn_warning_renders_with_the_active_language_without_recalculation() -> None:
    """A persisted semantic warning changes language without re-running the service."""
    translator = Translator("en")
    page = PipeDesignPage.__new__(PipeDesignPage)
    page._translate = translator.translate
    page._message = _FakeStringVar()
    page._diameter_warning_codes = ["no_suitable_dn"]

    page._refresh_diameter_warning_message()
    assert page._message.value == "No suitable DN available in the current Pipe Size Library."

    translator.set_language("tr")
    page._refresh_diameter_warning_message()
    assert page._message.value == "Mevcut Boru Ölçüleri Kütüphanesinde uygun DN bulunamadı."

    translator.set_language("en")
    page._refresh_diameter_warning_message()
    assert page._message.value == "No suitable DN available in the current Pipe Size Library."


def test_pipe_page_restores_the_dn_from_existing_saved_diameter_result() -> None:
    """Project-state restoration needs no separate recommendation persistence."""
    source = PipeDesignPage.load_state.__code__.co_names
    assert "_diameter_result" in source
    assert "_update_diameter_summary" in source


def test_pipe_layout_reflows_from_live_requested_widths_without_absolute_geometry() -> None:
    """Responsive Pipe cards adapt through measured grid reflow and page scrolling."""
    source = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")

    assert 'bind("<Configure>", self._on_layout_configure, add="+")' in source
    assert "def _reflow_diameter_cards" in source
    assert "def _reflow_wall_workspace" in source
    assert "winfo_reqwidth()" in source
    assert "wall-two-column" in source
    assert "wall-stacked" in source
    assert ".place(" not in source


def test_pipe_result_units_remain_in_compact_metric_containers() -> None:
    """Units share non-expanding metric grids with their authoritative values."""
    source = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")

    assert "diameter_metrics.columnconfigure(0, weight=0)" in source
    assert "wall_metrics.columnconfigure(0, weight=0)" in source
    assert 'text="mm", style="PipeMetricUnit.TLabel"' in source
