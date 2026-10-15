"""Contracts for approved static-equation artwork in the final Formula View."""

from __future__ import annotations

from pathlib import Path

from ui.assets import FORMULA_ASSET_FILENAMES, formula_asset_path
from ui.widgets.formula_view import FormulaReferencePanel


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_every_approved_formula_asset_is_packaged_at_its_canonical_path() -> None:
    """Equation artwork is supplied data, never generated at runtime."""
    expected = {
        "pipe_diameter",
        "allowable_stress",
        "base_wall_thickness",
        "bend_allowance",
        "required_wall_thickness",
        "local_loss",
        "pipe_friction_loss",
        "available_enpy",
    }

    assert expected == set(FORMULA_ASSET_FILENAMES)
    assert all(formula_asset_path(key) is not None for key in expected)


def test_formula_artwork_uses_complete_composition_and_native_text_fallback() -> None:
    """Images are visual-only and safely fall back to the stored formula string."""
    source = _source("ui/widgets/formula_view.py")

    assert "asset_names: tuple[str, ...] = ()" in source
    assert "formula_asset_path(asset_name)" in source
    assert 'fit_mode="canvas"' in source
    assert "_FORMULA_ASSET_MAX_SIDE = 260" in source
    assert "columnspan=3" in source
    assert 'sticky="n"' in source
    assert "if formula_image is None:" in source
    assert "self._render_mathtext_equations" in source


def test_variable_text_is_presented_as_aligned_native_rows_when_available() -> None:
    """Existing variable definitions gain columns without changing their content."""
    rows = FormulaReferencePanel._variable_rows(
        "D | Boru iç çapı | mm\nQ | Debi | m³/h"
    )

    assert rows == (("D", "Boru iç çapı", "mm"), ("Q", "Debi", "m³/h"))
    assert FormulaReferencePanel._variable_rows("serbest açıklama") is None
    source = _source("ui/widgets/formula_view.py")
    assert "FormulaVariablesSymbol.TLabel" in source
    assert "FormulaVariablesUnit.TLabel" in source
    assert "def _render_variable_rows" in source


def test_v2_pages_use_current_equation_text_without_legacy_artwork() -> None:
    """V2 uses current text without moving any engineering computation to the UI."""
    pipe = _source("ui/pages/pipe_design_page.py")
    discharge = _source("ui/pages/discharge_head_loss_page.py")
    suction = _source("ui/pages/suction_npsh_page.py")

    # V2 text/MathText carries the approved symbols; legacy PNGs stay packaged.
    for source in (pipe, discharge, suction):
        formula = source.split("def _formula_sections", 1)[1].split("\n    def ", 1)[0]
        assert '("local_loss", "pipe_friction_loss")' not in formula
        assert '("base_wall_thickness",)' not in formula
        assert '("available_enpy",)' not in formula
    assert "self._service.calculate" not in pipe.split("def _formula_sections", 1)[1].split("def _refresh_formula_panel", 1)[0]
    assert "self._service.calculate" not in discharge.split("def _formula_sections", 1)[1].split("def _calculate", 1)[0]
