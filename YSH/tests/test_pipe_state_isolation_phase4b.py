"""Manual-acceptance regressions for independent Pipe Part 1/Part 2 state."""

from __future__ import annotations

from pathlib import Path

from ui.pages.pipe_design_page import PipeDesignPage


ROOT = Path(__file__).resolve().parents[1]


class _Value:
    def __init__(self) -> None: self.value = ""
    def set(self, value: str) -> None: self.value = value


def _part2_page() -> PipeDesignPage:
    page = PipeDesignPage.__new__(PipeDesignPage)
    page._suppress_dirty = False
    page._diameter_result = {"diameter_mm": 74.25, "recommended_dn": "DN80", "recommended_outside_diameter_mm": 88.9}
    page._diameter_warning_codes = []
    page._wall_result = {"final_wall_thickness_mm": 2.0}
    page._formula_text = "stored"
    page._message = _Value()
    page._dirty_callback = None
    page._t = lambda key: key
    page._update_wall_summary = lambda: None
    return page


def test_every_part2_edit_domain_invalidates_only_wall_result() -> None:
    page = _part2_page()
    page._on_part2_change()
    assert page._diameter_result["recommended_dn"] == "DN80"
    assert page._wall_result == {}


def test_part1_change_invalidates_only_diameter_result() -> None:
    page = _part2_page()
    page._update_diameter_summary = lambda: None
    page._on_part1_change()
    assert page._diameter_result == {}
    assert page._wall_result == {"final_wall_thickness_mm": 2.0}


def test_visible_weld_factor_default_is_initialized_before_library_defaults() -> None:
    source = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")
    assert 'self._fields["wf"].set(format_user_number(1.0))' in source
    assert "variable.trace_add(\"write\", self._on_part1_change)" in source
    assert "variable.trace_add(\"write\", self._on_part2_change)" in source
