"""Phase 6 D243 bend-radius convention and Pipe Part 2 contracts."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.bend_radius import (
    BEND_RADIUS_MODES,
    DEFAULT_BEND_RADIUS_MODE,
    automatic_bend_radius_mm,
    bend_radius_mode,
)
from ui.formatting import format_user_number
from ui.pages.pipe_design_page import PipeDesignPage


ROOT = Path(__file__).resolve().parents[1]


class _Value:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


@pytest.mark.parametrize(
    ("code", "expected"),
    (("D1_5", 133.35), ("D2", 177.80), ("D3", 266.70), ("D5", 444.50), ("D10", 889.00)),
)
def test_d243_automatic_bend_radius_uses_authoritative_da(code: str, expected: float) -> None:
    radius = automatic_bend_radius_mm(code, 88.90)
    assert radius == pytest.approx(expected)
    assert format_user_number(radius) == f"{expected:.2f}".replace(".", ",")


def test_supported_bend_modes_are_stable_and_legacy_default_is_3d() -> None:
    assert [mode.label for mode in BEND_RADIUS_MODES] == ["1.5D", "2D", "3D", "5D", "10D", "Manuel"]
    assert DEFAULT_BEND_RADIUS_MODE == "D3"
    assert bend_radius_mode(None).code == "D3"
    assert bend_radius_mode("MANUAL").is_manual


def _automatic_page() -> PipeDesignPage:
    page = PipeDesignPage.__new__(PipeDesignPage)
    page._bend_mode = _Value("3D")
    page._bend_mode_codes = {mode.label: mode.code for mode in BEND_RADIUS_MODES}
    page._bend_mode_labels = {mode.code: mode.label for mode in BEND_RADIUS_MODES}
    page._last_bend_mode = "D3"
    page._manual_bend_radius_mm = ""
    page._fields = {"r": _Value(""), "da": _Value("88,90")}
    page._number = lambda key: 88.90
    page._suppress_dirty = False
    return page


def test_automatic_manual_and_automatic_transitions_keep_r_ownership_clear() -> None:
    page = _automatic_page()
    page._refresh_automatic_bend_radius()
    assert page._fields["r"].get() == "266,70"

    page._select_bend_mode("MANUAL")
    assert page._selected_bend_mode_code() == "MANUAL"
    assert page._fields["r"].get() == "266,70"
    page._fields["r"].set("300,25")
    page._on_bend_radius_change()

    page._select_bend_mode("D5")
    assert page._selected_bend_mode_code() == "D5"
    assert page._fields["r"].get() == "444,50"
    assert page._manual_bend_radius_mm == "300,25"


def test_bend_input_contracts_preserve_part1_and_formula_transparency() -> None:
    source = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")
    assert '"bend_mode": self._selected_bend_mode_code()' in source
    assert '"manual_bend_radius_mm": self._manual_bend_radius_mm' in source
    assert "self._refresh_automatic_bend_radius()" in source
    assert "b = 0,4 × (da / R) × s0" in source
    assert "formula.bend_radius_convention_note" in source
    assert "self._on_part2_change" in source
    assert "self._on_part1_change" in source


def test_bend_convention_is_documented_without_a_false_turk_loydu_radius_claim() -> None:
    source = (ROOT / "i18n/messages_tr.py").read_text(encoding="utf-8")
    assert "D243'te D, boru dış çapı da olarak alınır." in source
    assert "3D varsayılanı Türk Loydu zorunluluğu değildir." in source
