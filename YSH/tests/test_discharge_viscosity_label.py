"""Regression test for the unit-neutral discharge viscosity label."""

from __future__ import annotations

from pathlib import Path


def test_discharge_viscosity_label_is_unit_neutral() -> None:
    """Require the selector, rather than the field label, to show the unit."""
    source = (
        Path(__file__).resolve().parents[1]
        / "ui"
        / "pages"
        / "discharge_head_loss_page.py"
    ).read_text(encoding="utf-8")

    assert '"field.kinematic_viscosity"' in source
