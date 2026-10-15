"""Display-independent contracts for the Phase 3 engineering formula view."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    """Read one application source file used by formula presentation tests."""
    return (ROOT / path).read_text(encoding="utf-8")


def test_reusable_formula_architecture_exposes_semantic_blocks() -> None:
    """The shared renderer owns presentation roles without calculation knowledge."""
    source = _source("ui/widgets/formula_view.py")
    for required in (
        "FormulaBlock",
        "FormulaSectionRole",
        '"formula"',
        '"variables"',
        '"substitution"',
        '"result"',
        '"note"',
    ):
        assert required in source
    assert "Calculator" not in source
    assert "Toplevel" not in source


def test_formula_design_tokens_are_centralized() -> None:
    """Formula color identities belong to the central ttk design system."""
    colors = _source("ui/theme/colors.py")
    styles = _source("ui/theme/styles.py")
    assert "FORMULA =" in colors
    assert "FORMULA_SOFT =" in colors
    for name in (
        "FormulaEquation",
        "FormulaVariables",
        "FormulaSubstitution",
        "FormulaResult",
        "FormulaNote",
    ):
        assert name in styles
    assert "FormulaStrip.TFrame" in styles


def test_formula_derivation_uses_restrained_stage_surfaces_and_accent_strips() -> None:
    """Formula stages use light surfaces, neutral borders, and semantic accents."""
    styles = _source("ui/theme/styles.py")
    renderer = _source("ui/widgets/formula_view.py")

    assert "bordercolor=colors.BORDER" in styles
    assert 'f"{name}Accent.TFrame"' in styles
    assert "typography.FORMULA_EXPRESSION" in styles
    assert "typography.FORMULA_RESULT" in styles
    assert 'style=f"{style_root}Accent.TFrame"' in renderer
    assert "rowspan=2" in renderer


def test_formula_note_remains_secondary_to_formula_and_result_stages() -> None:
    """Supporting notes use muted typography and a neutral cool-gray surface."""
    styles = _source("ui/theme/styles.py")

    note_call = styles.split('"FormulaNote"', 1)[1].split(")\n", 1
    )[0]
    assert "colors.SECONDARY_SURFACE" in note_call
    assert "colors.TEXT_MUTED" in note_call
    assert "typography.MUTED" in note_call


def test_formula_equations_use_local_mathtext_with_textual_fallbacks() -> None:
    """Display-only MathText never replaces the authoritative formula strings."""
    source = _source("ui/widgets/formula_view.py")

    assert "_MATHTEXT_LINES" in source
    assert "from matplotlib.mathtext import math_to_image" in source
    assert "math_to_image(" in source
    assert "f\"${mathtext}$\"" in source
    assert "except Exception:" in source
    assert "return None" in source
    for notation in ("\\frac", "\\sqrt", "\\pi", "\\rho", "^2", "\\mathrm"):
        assert notation in source


def test_mathtext_equations_use_bounded_readable_display_sizes() -> None:
    """Short equations render prominently while long equations retain a safe minimum."""
    renderer = _source("ui/widgets/formula_view.py")
    typography = _source("ui/theme/typography.py")

    assert "MATHTEXT_EQUATION_DISPLAY_SIZE = 17" in typography
    assert "MATHTEXT_LONG_EQUATION_SIZE = 14" in typography
    assert "MATHTEXT_MINIMUM_SIZE = 14" in typography
    assert "_LONG_EQUATION_CHARACTER_THRESHOLD = 90" in renderer
    assert "def _mathtext_font_size" in renderer
    assert "typography.MATHTEXT_EQUATION_DISPLAY_SIZE" in renderer
    assert "typography.MATHTEXT_LONG_EQUATION_SIZE" in renderer
    assert "typography.MATHTEXT_MINIMUM_SIZE" in renderer
    assert "FontProperties(size=cls._mathtext_font_size(mathtext))" in renderer


def test_mathtext_equation_rendering_remains_dpi_aware() -> None:
    """Equation sizing uses the live Tk DPI rather than a fixed raster asset."""
    source = _source("ui/widgets/formula_view.py")

    assert 'parent.winfo_fpixels("1i")' in source
    assert "dpi = max(96" in source


def test_formula_stages_reflow_without_mutating_engineering_content() -> None:
    """Formula stages use requested geometry to reflow semantic panels in place."""
    source = _source("ui/widgets/formula_view.py")
    for required in (
        "_formula_strips",
        "_reflow_strip",
        "winfo_reqwidth()",
        "columns = len(panels)",
        "columns = 2",
        "columns = 1",
        "FormulaStrip.TFrame",
    ):
        assert required in source
    assert "place(" not in source


def test_formula_panel_expands_its_content_before_measuring_stage_widths() -> None:
    """Wide workspaces allocate width to formula strips instead of a left column."""
    source = _source("ui/widgets/formula_view.py")
    assert "self.columnconfigure(0, weight=1)" in source
    assert 'sticky="nsew"' in source
    assert 'block.grid(row=row, column=0, sticky="ew"' in source


def test_pipe_formula_documents_staged_reference_and_dn_selection() -> None:
    """Pipe reference keeps the library recommendation outside the equation."""
    source = _source("ui/pages/pipe_design_page.py")
    for text in (
        "Qm³/s = Qm³/h / 3600",
        "σallow = Rp0.2 / B",
        "s0 = (da × pc) / ((20 × σallow × v) + pc)",
        "b = 0.4 × (da / R) × s0",
        "s = s0 + c + b",
        "formula.pipe_size_recommendation_note",
    ):
        assert text in source
    assert "one size larger" not in source


def test_pipe_formula_placeholders_are_localized_instead_of_english_literals() -> None:
    """Formula placeholders follow the active EN/TR language before calculation."""
    source = _source("ui/pages/pipe_design_page.py")
    assert 'self._translate("message.available_after_calculation")' in source
    assert (
        'self._translate("message.available_after_wall_thickness_calculation")'
        in source
    )
    assert 'FormulaSection("RESULT", "Available after calculation."' not in source


def test_formula_view_localizes_supporting_heading_roles() -> None:
    """Supporting panels retain their semantic role in the active language."""
    source = _source("ui/widgets/formula_view.py")
    assert '"NOTE": "formula.note"' in source
    assert '"MODEL INFORMATION": "formula.model_information"' in source


def test_formula_pages_use_localized_human_descriptions() -> None:
    """Formula text leaves mathematical symbols intact while localizing prose."""
    sources = {
        path: _source(path)
        for path in (
            "ui/pages/pipe_design_page.py",
            "ui/pages/transfer_pump_page.py",
            "ui/pages/discharge_head_loss_page.py",
            "ui/pages/suction_npsh_page.py",
        )
    }
    for key in (
        "formula.mathematical_constant",
        "formula.regression_slope",
        "formula.approved_ysh_moody_result",
        "formula.total_local_loss_coefficient",
        "formula.standard_gravity",
    ):
        assert any(key in source for source in sources.values())
    assert "Qpump = m × Vfuel + b" in sources["ui/pages/transfer_pump_page.py"]
    assert "ENPYm = PE/(ρg)" in sources["ui/pages/suction_npsh_page.py"]


def test_pipe_formula_stages_remain_complete_before_wall_calculation() -> None:
    """Base thickness and bend stages retain quiet substitution and result panels."""
    source = _source("ui/pages/pipe_design_page.py")
    assert source.count('"3. BASE WALL THICKNESS", "substitution"') >= 2
    assert source.count('"4. BEND ALLOWANCE", "substitution"') >= 2


def test_transfer_formula_separates_regression_quality_from_prediction() -> None:
    """Transfer formula view presents R² as model information, not a refit."""
    source = _source("ui/pages/transfer_pump_page.py")
    assert "Qpump = m × Vfuel + b" in source
    assert "t = Vfuel / Qpump" in source
    assert "formula.regression_model_note" in source
    assert "_service.calculate(capacity)" not in source.split("def _formula_sections", 1)[1]


def test_discharge_formula_documents_the_complete_ysh_chain() -> None:
    """Discharge reference follows the implemented coefficient-form chain."""
    source = _source("ui/pages/discharge_head_loss_page.py")
    for text in (
        "V = 4Q / (πDi²)",
        "Re = VDi / ν",
        "k/Di = k / Di",
        "Ktotal = Σ(quantity × K)",
        "hL = 6400 × Ktotal × Q² / Di⁴",
        "hf = 6.4 × 10⁶ × f × L × Q² / Di⁵",
        "Hs = Hgeo + hhat",
    ):
        assert text in source


def test_suction_formula_documents_enpy_conditions_and_optional_margin() -> None:
    """Suction reference retains hydraulic and ENPY audit meanings."""
    source = _source("ui/pages/suction_npsh_page.py")
    for text in (
        "ENPYm = PE/(ρg) − Pb/(ρg) − HEgeo − he",
        "formula.suction_enpy_note",
    ):
        assert text in source


def test_pages_keep_formula_audits_state_driven_and_inline() -> None:
    """Formula sections consume stored results and retain stale-result guards."""
    pages = {
        "ui/pages/pipe_design_page.py": "_diameter_result",
        "ui/pages/transfer_pump_page.py": "_estimate_result",
        "ui/pages/discharge_head_loss_page.py": "_last_result",
        "ui/pages/suction_npsh_page.py": "_last_loss",
    }
    for path, result_state in pages.items():
        source = _source(path)
        assert result_state in source
        assert "Available" in source or "message.available_after" in source
        assert "FormulaReferencePanel" in source
