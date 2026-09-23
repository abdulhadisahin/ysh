"""Semantic contracts for the Phase-1 YSH ttk visual design system."""

from __future__ import annotations

from pathlib import Path

from ui.theme import colors


ROOT = Path(__file__).resolve().parents[1]


def test_design_system_exposes_the_approved_semantic_palette() -> None:
    """Phase 5A keeps final color decisions centralized rather than page-local."""
    assert colors.NAVY == "#0B2F5B"
    assert colors.DEEP_NAVY == "#062449"
    assert colors.NAVY_TEXT == "#102A43"
    assert colors.PIPE == "#00FFFF"
    assert colors.TRANSFER == "#F47A16"
    assert colors.DISCHARGE == "#1265D8"
    assert colors.SUCTION == "#2600FF"
    assert colors.APP_BACKGROUND == "#F5F8FC"
    assert colors.SECONDARY_SURFACE == "#F1F5F9"
    assert colors.CARD_SURFACE == "#FFFFFF"
    assert colors.BORDER == "#D5DEE9"
    assert colors.STRONG_BORDER == "#B8C6D8"
    assert colors.ERROR == "#E52B32"
    assert colors.TEXT_PRIMARY != colors.BACKGROUND


def test_ttk_styles_cover_tabs_buttons_and_project_identity() -> None:
    """The shared style layer defines visual behavior for main-shell semantics."""
    source = (ROOT / "ui/theme/styles.py").read_text(encoding="utf-8")
    for style_name in (
        "Primary.TButton", "Secondary.TButton", "Success.TButton",
        "Warning.TButton", "Danger.TButton", "Neutral.TButton",
    ):
        assert style_name in source
    assert 'background=[("selected", colors.PRIMARY)' in source
    assert "active_project" in source
    assert "Project.Treeview" in source
    assert "Vertical.TScrollbar" in source
    assert "WarningCard.TLabelframe" in source
    assert "CriticalResultMetric" in source
    assert "UnavailableResultMetric" in source


def test_theme_defines_the_existing_shell_and_sidebar_style_hooks() -> None:
    """Shell composition uses explicit native-ttk styles instead of defaults."""
    source = (ROOT / "ui/theme/styles.py").read_text(encoding="utf-8")

    for style_name in (
        "HeaderBrand.TFrame",
        "HeaderUtility.TFrame",
        "Ribbon.TFrame",
        "CommandGroup.TFrame",
        "CommandGroupTitle.TLabel",
        "SidebarPanel.TFrame",
        "SidebarActions.TFrame",
        "SidebarSearchLabel.TLabel",
        "ActiveProject.TFrame",
        "ActiveProjectTitle.TLabel",
        "ActiveProjectName.TLabel",
    ):
        assert style_name in source


def test_theme_uses_navy_structure_and_native_input_state_treatment() -> None:
    """The final shell refinement avoids default ttk chrome without new widgets."""
    source = (ROOT / "ui/theme/styles.py").read_text(encoding="utf-8")

    assert 'style.configure("Header.TFrame", background=colors.NAVY)' in source
    assert 'style.configure("Ribbon.TFrame", background=colors.NAVY)' in source
    assert "foreground=colors.HEADER_GROUP_TEXT" in source
    assert 'style.configure("Status.TFrame", background=colors.NAVY)' in source
    assert 'style.configure("YSH.TNotebook.Tab", background=colors.NAVY' in source
    assert 'style.map("TEntry", bordercolor=[("focus", colors.PRIMARY)' in source
    assert 'fieldbackground=[("readonly", colors.SURFACE_ALT)' in source


def test_calculation_pages_share_neutral_surfaces_and_module_result_accents() -> None:
    """Cross-page polish keeps cards calm while primary metrics retain identity."""
    source = (ROOT / "ui/theme/styles.py").read_text(encoding="utf-8")

    for style_name in (
        "InputCard.TLabelframe",
        "CalculationCard.TLabelframe",
        "ResultCard.TLabelframe",
        "TransferResultMetric",
        "TransferSecondaryMetric",
        "DischargeResultMetric",
        "DischargeLossMetric",
        "SuctionResultMetric",
        "SuctionLossMetric",
        "Transfer.Treeview",
        "Discharge.Treeview",
        "Suction.Treeview",
        "EngineeringDetails.TFrame",
    ):
        assert style_name in source
    assert "colors.CARD_SURFACE, colors.BORDER, colors.TEXT_SECONDARY" in source
    for style_name in (
        "PrimaryCalculate.TButton",
        "Transfer.Primary.TButton",
        "Discharge.Primary.TButton",
        "Suction.Primary.TButton",
    ):
        assert style_name in source


def test_result_metric_preserves_units_and_quiets_unavailable_placeholders() -> None:
    """Shared metrics keep engineering quantities coupled without false success color."""
    source = (ROOT / "ui/widgets/cards.py").read_text(encoding="utf-8")

    assert "self._unit_label.grid(row=1, column=2" in source
    assert 'style=f"{normal_style_prefix}Accent.TFrame"' in source
    assert 'self._value_variable.trace_add("write", self._refresh_value_style)' in source
    assert 'style_prefix = "UnavailableResultMetric"' in source


def test_main_window_retains_project_commands_and_treeview_bindings() -> None:
    """Visual changes do not replace verified project-management workflows."""
    source = (ROOT / "ui/main_window.py").read_text(encoding="utf-8")
    for callback in (
        "self._open_new_project", "self._open_project", "self._save_project",
        "self._delete_project", "self._refresh_projects",
    ):
        assert callback in source
    for event in ("<Double-1>", "<Return>", "<Delete>"):
        assert event in source
    assert "tags=(\"active_project\",)" in source
    assert '"menu.file.save_project_as"' in source
    assert '"menu.file.close_project"' in source


def test_ui_phase_one_does_not_introduce_ttkbootstrap_or_engineering_logic() -> None:
    """The design phase remains a safe native-ttk presentation change."""
    source = (ROOT / "ui/theme/styles.py").read_text(encoding="utf-8")
    manifests = "\n".join(
        (ROOT.parent / "pyproject.toml").read_text(encoding="utf-8")
        for _ in [None]
    )
    assert "ttkbootstrap" not in source.casefold()
    assert "ttkbootstrap" not in manifests.casefold()


def test_pipe_button_prototype_has_complete_native_ttk_states() -> None:
    """Pipe-only modern buttons retain an accessible state-map contract."""
    source = (ROOT / "ui/theme/styles.py").read_text(encoding="utf-8")

    assert '"PipePrimary.TButton"' in source
    assert '"PipeNeutral.TButton"' in source
    for state in ('("disabled",', '("pressed",', '("active",'):
        assert state in source
    assert "focusthickness=1" in source
    assert "padding=(16, 8)" in source


def test_pipe_image_button_prototype_keeps_live_text_and_four_surface_states() -> None:
    """Rounded Pipe surfaces are image-backed without rasterizing translations."""
    widget_source = (ROOT / "ui/widgets/rounded_button.py").read_text(encoding="utf-8")
    page_source = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")

    assert "class RoundedImageButton(ttk.Button)" in widget_source
    assert "compound=\"center\"" in widget_source
    assert "transparency_set" in widget_source
    for state in ("normal", "hover", "pressed", "disabled"):
        assert state in widget_source
    assert "RoundedImageButton(" in page_source
    assert "_PIPE_BUTTON_PALETTE" in page_source
    assert "_PIPE_NEUTRAL_BUTTON_PALETTE" in page_source
    assert "_PIPE_FORMULA_BUTTON_PALETTE" in page_source
    assert "Çapı Hesapla" not in widget_source
    assert "Calculate Diameter" not in widget_source


def test_pipe_button_v2_uses_independent_light_fills_and_colored_outlines() -> None:
    """V2 keeps real rounded borders distinct from the light button interior."""
    page_source = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")
    widget_source = (ROOT / "ui/widgets/rounded_button.py").read_text(encoding="utf-8")

    assert 'normal=(colors.PIPE, colors.PIPE_DEEP)' in page_source
    assert 'hover=(colors.PIPE_ACTION_HOVER, colors.PIPE_DARK)' in page_source
    assert 'pressed=(colors.PIPE_ACTION_PRESSED, colors.PIPE_DEEP)' in page_source
    assert "_surface_pixel" in widget_source
    assert "return fill" in widget_source
    assert "return border" in widget_source
    assert "radius=7" in page_source
    assert "horizontal_padding=16" in page_source
    assert "vertical_padding=7" in page_source


def test_pipe_hybrid_naval_button_pilot_preserves_three_action_levels() -> None:
    """Pipe alone uses solid-primary, neutral-secondary, and soft-formula controls."""
    page_source = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")
    colors_source = (ROOT / "ui/theme/colors.py").read_text(encoding="utf-8")

    assert 'PIPE_ACTION_HOVER = "#00E6E6"' in colors_source
    assert 'PIPE_ACTION_PRESSED = "#00BFC4"' in colors_source
    assert 'normal=(colors.CARD_SURFACE, colors.STRONG_BORDER)' in page_source
    assert 'normal=(colors.FORMULA_SOFT, colors.FORMULA)' in page_source
    assert "focus_border=colors.FORMULA" in page_source
    assert "horizontal_padding=15" in page_source
    assert "vertical_padding=7" in page_source


def test_pipe_formula_toggle_uses_only_the_optional_tertiary_factory() -> None:
    """Only Pipe receives the outlined Formula toggle; other pages keep defaults."""
    pipe_source = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")
    formula_source = (ROOT / "ui/widgets/formula_view.py").read_text(encoding="utf-8")

    assert "self._create_formula_toggle" in pipe_source
    assert 'style="PipeRoundedFormula.TButton"' in pipe_source
    assert "toggle_button_factory" in formula_source
    assert 'style="Secondary.TButton"' in formula_source


def test_pipe_hybrid_primary_uses_compact_padding_and_dark_cyan_text() -> None:
    """The solid cyan primary action keeps dark text and controlled dimensions."""
    styles_source = (ROOT / "ui/theme/styles.py").read_text(encoding="utf-8")
    page_source = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")
    widget_source = (ROOT / "ui/widgets/rounded_button.py").read_text(encoding="utf-8")

    assert 'foreground=colors.PIPE_DARK' in styles_source
    assert 'foreground=colors.ON_ACCENT' not in styles_source.split(
        '"PipeRoundedPrimary.TButton"', 1
    )[1].split('"PipeRoundedNeutral.TButton"', 1)[0]
    assert "radius=7" in page_source
    assert "horizontal_padding=16" in page_source
    assert "horizontal_padding=15" in page_source
    assert "vertical_padding=7" in page_source
    assert "def _content_surface_dimensions" in widget_source
    assert "def _surface_dimensions_from_content" in widget_source
    assert "max(20, content_height + (vertical_padding * 2))" in widget_source
    assert "height = max(self.winfo_height(), self.winfo_reqheight(), 36)" not in widget_source


def test_pipe_cyan_token_does_not_replace_other_module_or_action_semantics() -> None:
    """The vivid Pipe identity stays isolated from Formula and semantic actions."""
    colors_source = (ROOT / "ui/theme/colors.py").read_text(encoding="utf-8")
    styles_source = (ROOT / "ui/theme/styles.py").read_text(encoding="utf-8")

    assert 'PIPE = "#00FFFF"' in colors_source
    assert 'FORMULA = "#2600FF"' in colors_source
    assert 'SUCTION = "#2600FF"' in colors_source
    assert 'TRANSFER = "#F47A16"' in colors_source
    assert 'DISCHARGE = "#1265D8"' in colors_source
    for action_style in ("RoundedAdd.TButton", "RoundedEdit.TButton", "RoundedDelete.TButton"):
        assert action_style in styles_source


def test_module_rollout_uses_distinct_outlined_palettes_and_semantic_actions() -> None:
    """Module actions reuse rounded surfaces without changing shell controls."""
    rounded_source = (ROOT / "ui/widgets/rounded_button.py").read_text(encoding="utf-8")
    transfer = (ROOT / "ui/pages/transfer_pump_page.py").read_text(encoding="utf-8")
    discharge = (ROOT / "ui/pages/discharge_head_loss_page.py").read_text(encoding="utf-8")
    suction = (ROOT / "ui/pages/suction_npsh_page.py").read_text(encoding="utf-8")

    for palette in ("TRANSFER_PRIMARY_PALETTE", "DISCHARGE_PRIMARY_PALETTE", "SUCTION_PRIMARY_PALETTE"):
        assert palette in rounded_source
    for source, style in ((transfer, "TransferRoundedPrimary.TButton"), (discharge, "DischargeRoundedPrimary.TButton"), (suction, "SuctionRoundedPrimary.TButton")):
        assert style in source
        assert "RoundedFormula.TButton" in source
    for style in ("RoundedAdd.TButton", "RoundedEdit.TButton", "RoundedDelete.TButton", "RoundedNeutral.TButton"):
        assert style in transfer or style in discharge or style in suction


def test_suction_identity_uses_approved_blue_violet_without_recoloring_formula() -> None:
    """Suction adopts its new identity while tertiary Formula remains semantic."""
    rounded_source = (ROOT / "ui/widgets/rounded_button.py").read_text(encoding="utf-8")
    colors_source = (ROOT / "ui/theme/colors.py").read_text(encoding="utf-8")

    assert 'SUCTION = "#2600FF"' in colors_source
    assert 'FORMULA = "#2600FF"' in colors_source
    suction_palette = rounded_source.split("SUCTION_PRIMARY_PALETTE", 1)[1].split("ADD_BUTTON_PALETTE", 1)[0]
    assert '"#2600FF"' in suction_palette
    assert '"#7C3AED"' not in suction_palette


def test_pipe_button_prototype_is_not_a_global_button_migration() -> None:
    """Only Pipe’s established actions receive the prototype styles."""
    source = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")

    assert 'style="PipeRoundedPrimary.TButton"' in source
    assert 'style="PipeRoundedNeutral.TButton"' in source
    assert "command=self._calculate_diameter" in source
    assert "command=self._calculate_wall" in source
    assert "command=self._clear_user_state" in source
