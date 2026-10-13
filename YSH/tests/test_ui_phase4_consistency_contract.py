"""Display-independent contracts for the final UI consistency pass."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(relative_path: str) -> str:
    """Read a source file from the YSH package for a semantic UI check."""
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_theme_provides_consistent_dialog_tree_and_control_styles() -> None:
    """Shared ttk styling covers forms, dialogs, tabs, and data tables."""
    source = _source("ui/theme/styles.py")
    for required in (
        "Dialog.TFrame",
        "DialogTitle.TLabel",
        "DialogHint.TLabel",
        "Data.Treeview",
        "Data.Treeview.Heading",
        "TEntry",
        "TCombobox",
        "ChartSummary.TLabel",
        '("active", colors.PRIMARY_SOFT)',
    ):
        assert required in source


def test_shared_treeview_and_formula_widgets_use_central_spacing() -> None:
    """Common scroll and formula widgets avoid page-specific visual rules."""
    treeview = _source("ui/widgets/scrollable_treeview.py")
    formula = _source("ui/widgets/formula_view.py")
    assert 'tree_options.setdefault("style", "Data.Treeview")' in treeview
    assert "from ui.theme.spacing import MD, SM" in formula
    assert "FormulaResult" in formula


def test_project_and_library_dialogs_keep_semantic_button_hierarchy() -> None:
    """Dialog actions preserve their verified workflows with shared visual roles."""
    sources = "\n".join(
        _source(path)
        for path in (
            "ui/dialogs/library_dialog.py",
            "ui/dialogs/new_project_dialog.py",
            "ui/dialogs/open_project_dialog.py",
            "ui/dialogs/save_project_as_dialog.py",
            "ui/dialogs/delete_project_dialog.py",
            "ui/dialogs/pump_reference_dialog.py",
            "ui/dialogs/local_loss_item_dialog.py",
        )
    )
    for style in ("Primary.TButton", "Secondary.TButton", "Success.TButton", "Danger.TButton", "Neutral.TButton"):
        assert style in sources
    assert "<Return>" in sources
    assert "<Escape>" in sources


def test_hydraulic_pages_emphasize_primary_results_without_new_calculators() -> None:
    """Result hierarchy is presentation-only and keeps existing handlers intact."""
    discharge = _source("ui/pages/discharge_head_loss_page.py")
    suction = _source("ui/pages/suction_npsh_page.py")
    for source, result_name, handler in (
            (discharge, "result.system_manometric_head", "self._calculate"),
        (suction, "result.available_npsh", "self._calculate_enpy"),
    ):
        assert "ResultMetric" in source
        assert result_name in source
        assert handler in source
    assert "Calculator(" not in discharge
    assert "Calculator(" not in suction


def test_chart_is_embedded_and_uses_theme_palette_without_refitting() -> None:
    """Chart presentation remains a single embedded display of model data."""
    source = _source("ui/widgets/transfer_pump_chart.py")
    assert "FigureCanvasTkAgg" in source
    assert "from ui.theme import colors" in source
    assert "colors.GOLD" in source
    assert "colors.NAVY" in source
    assert "def render" in source
    assert "calculate(" not in source
