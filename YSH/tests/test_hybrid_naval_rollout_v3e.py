"""Presentation contracts for the V3-E Hybrid Naval button rollout."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    """Read a presentation-layer source file."""
    return (ROOT / path).read_text(encoding="utf-8")


def test_non_pipe_primary_palettes_are_solid_module_actions() -> None:
    """Transfer, Discharge, and Suction calculations use solid module fills."""
    source = _source("ui/widgets/rounded_button.py")

    for fill in ('normal=("#F47A16", "#B7520A")', 'normal=("#1265D8", "#0D55B8")', 'normal=("#2600FF", "#1E00CC")'):
        assert fill in source


def test_primary_buttons_use_white_live_text_and_crud_stays_restrained() -> None:
    """Solid calculations remain primary while CRUD and utility controls stay quieter."""
    styles = _source("ui/theme/styles.py")
    buttons = _source("ui/widgets/rounded_button.py")

    assert styles.count("_configure_rounded_solid_button(style,") == 3
    assert "foreground=colors.ON_ACCENT" in styles
    for palette in ("ADD_BUTTON_PALETTE", "EDIT_BUTTON_PALETTE", "DELETE_BUTTON_PALETTE", "CLEAR_ALL_BUTTON_PALETTE", "NEUTRAL_BUTTON_PALETTE", "FORMULA_BUTTON_PALETTE"):
        assert palette in buttons


def test_module_pages_preserve_existing_actions_and_formula_toggles() -> None:
    """The rollout changes presentation only and retains established commands."""
    pages = {
        "ui/pages/transfer_pump_page.py": ("TRANSFER_PRIMARY_PALETTE", "FORMULA_BUTTON_PALETTE"),
        "ui/pages/discharge_head_loss_page.py": ("DISCHARGE_PRIMARY_PALETTE", "FORMULA_BUTTON_PALETTE"),
        "ui/pages/suction_npsh_page.py": ("SUCTION_PRIMARY_PALETTE", "FORMULA_BUTTON_PALETTE"),
    }
    for path, required in pages.items():
        source = _source(path)
        for item in required:
            assert item in source
        assert "NEUTRAL_BUTTON_PALETTE" in source
    pipe = _source("ui/pages/pipe_design_page.py")
    assert "_PIPE_BUTTON_PALETTE" in pipe
    assert "action.use_recommended_pipe" in pipe


def test_density_polish_keeps_pipe_and_enpy_data_bindings_intact() -> None:
    """Spacing refinements do not replace authoritative result variables."""
    pipe = _source("ui/pages/pipe_design_page.py")
    suction = _source("ui/pages/suction_npsh_page.py")

    assert pipe.count("padding=(10, 8)") == 2
    assert "textvariable=self._diameter_value" in pipe
    assert "textvariable=self._wall_value" in pipe
    assert "textvariable=self._detail_values[value_key]" in suction
