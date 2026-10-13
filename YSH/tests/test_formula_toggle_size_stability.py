"""Regression contracts for Formula-toggle surface sizing."""

from __future__ import annotations

from pathlib import Path

from ui.theme import colors
from ui.widgets.rounded_button import RoundedImageButton


ROOT = Path(__file__).resolve().parents[1]


def test_surface_dimensions_are_idempotent_for_repeated_show_hide_labels() -> None:
    """Measured content dimensions never include a prior rendered image surface."""
    dimensions = [
        RoundedImageButton._surface_dimensions_from_content(112, 17, 14, 6)
        for _ in range(10)
    ]

    assert dimensions == [(140, 29)] * 10


def test_formula_panel_reserves_localized_show_hide_texts_for_rounded_toggles() -> None:
    """Each active language reserves its own stable maximum natural toggle width."""
    source = (ROOT / "ui/widgets/formula_view.py").read_text(encoding="utf-8")

    assert "def _configure_toggle_stable_texts" in source
    assert 'self._translate("common.show_formula")' in source
    assert 'self._translate("common.hide_formula")' in source
    assert "self._configure_toggle_stable_texts()" in source


def test_formula_identity_uses_the_d243_gold_reference_accent() -> None:
    """Formula presentation shares the restrained D243 reference language."""
    assert colors.FORMULA == colors.GOLD_DARK
