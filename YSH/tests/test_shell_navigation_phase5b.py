"""Contracts for the Phase 5B shell and calculation navigation presentation."""

from __future__ import annotations

from pathlib import Path

from ui.theme import colors
from ui.assets import ASSET_DIRECTORY, local_asset_path
from i18n.messages_en import MESSAGES
from i18n.messages_tr import MESSAGES as TR_MESSAGES


ROOT = Path(__file__).resolve().parents[1]


def test_calculation_tabs_have_stable_semantic_page_colors() -> None:
    """The tab band owns one approved accent token per calculation page."""
    source = (ROOT / "ui/widgets/scrollable_page_host.py").read_text(encoding="utf-8")
    assert colors.PIPE == "#00FFFF"
    assert colors.TRANSFER == "#F47A16"
    assert colors.DISCHARGE == "#1265D8"
    assert colors.SUCTION == "#2600FF"
    for page_key in ("pipe_design", "transfer_pump", "discharge_head_loss", "suction_npsh"):
        assert page_key in source
    assert "YSH.TNotebook" in source
    assert "selected_foreground = colors.ON_ACCENT" in source
    assert 'background=[("selected", accent)' in source
    assert 'foreground=[("selected", selected_foreground)' in source


def test_command_ribbon_is_embedded_in_the_unified_navy_header() -> None:
    """The ribbon remains a stable shell command area within the navy header."""
    source = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8")

    assert 'toolbar = ttk.Frame(header, style="Ribbon.TFrame"' in source
    assert 'toolbar.grid(row=1, column=0, columnspan=2, sticky="ew")' in source
    assert 'workspace.grid(row=1, column=0, sticky="nsew")' in source


def test_ribbon_contains_only_approved_shell_commands() -> None:
    """Calculation actions remain page-owned rather than becoming global ribbon actions."""
    source = (ROOT / "ui/main_window.py").read_text(encoding="utf-8")
    for callback in (
        "self._open_new_project", "self._open_project", "self._save_project",
        "self._save_project_as", "self._open_material_library",
        "self._open_pipe_size_library", "self._open_constants_library",
        "self._show_about",
    ):
        assert callback in source
    assert "_toolbar_calculate" not in source
    assert "_toolbar_formula" not in source


def test_shell_uses_local_asset_hooks_without_network_dependencies() -> None:
    """Logo, ship, and tab artwork resolve only from packaged-local paths."""
    source = (ROOT / "ui/assets.py").read_text(encoding="utf-8")
    assert "LOGO_SYMBOL_PATH" in source
    assert "SIDEBAR_SHIP_PATH" in source
    assert "TAB_ICON_PATHS" in source
    assert "http" not in source


def test_identity_text_and_optional_asset_hooks_are_safe() -> None:
    """Identity strings localize while missing optional imagery remains harmless."""
    assert MESSAGES["app.title"] == "YSH"
    assert MESSAGES["app.subtitle"] == "Fuel System Engineering"
    assert MESSAGES["app.workspace"] == "Engineering Calculation Workspace"
    assert TR_MESSAGES["app.title"] == "D243"
    assert TR_MESSAGES["app.subtitle"] == "Boru ve Tulumba Boyutlandırma Programı"
    assert TR_MESSAGES["app.workspace"] == "Mühendislik Hesaplama Çalışma Alanı"
    assert local_asset_path(ASSET_DIRECTORY / "missing-approved-logo.png") is None


def test_unified_header_uses_the_approved_ship_without_a_workspace_slogan() -> None:
    """The approved ship replaces the removed workspace slogan in the header."""
    source = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8")

    assert "ysh_ship_top_right_path()" in source
    assert "maximum_width=260" in source
    assert "maximum_height=76" in source
    assert "self._header_ship_source_image" in source
    assert "self._resize_header_ship" in source
    assert "self._header_workspace" not in source


def test_window_identity_uses_localized_product_title() -> None:
    """The native title reflects the product identity, not a developer path."""
    source = (ROOT / "ui/main_window.py").read_text(encoding="utf-8")
    assert "def _window_title" in source
    assert "PRODUCT_FULL_NAME" in source
    assert "C:\\\\Users" not in source


def test_header_logo_keeps_a_strong_tkinter_image_reference() -> None:
    """The optional header symbol cannot disappear after widget construction."""
    source = (ROOT / "ui/main_window.py").read_text(encoding="utf-8")
    assert "self._header_logo_image" in source
    assert "tk.PhotoImage" in source
    assert "ysh_logo_path" in source
    assert "HeaderLogoPlate.TFrame" in source
    assert "HeaderLogoPlate.TLabel" in source
    assert "padding=(SM // 2, SM // 2)" in source


def test_header_rounded_commands_match_the_navy_shell_at_outer_corners() -> None:
    """Ribbon buttons set their outside pixels to the shared header background."""
    shell_source = (ROOT / "ui/main_window.py").read_text(encoding="utf-8")
    button_source = (ROOT / "ui/widgets/rounded_button.py").read_text(encoding="utf-8")

    assert "def _create_header_button" in shell_source
    assert "outside_background=colors.NAVY" in shell_source
    assert "outside_background: str | None = None" in button_source
    assert "self._outside_background or fill" in button_source
    assert "if self._outside_background is None:" in button_source
    assert "def _surface_aware_style" in button_source
    assert "background=outside_background" in button_source
    assert "Surface{color_key}.{base_style}" in button_source


def test_sidebar_rounded_commands_match_their_neutral_panel_at_outer_corners() -> None:
    """Project actions use the sidebar token without affecting page buttons."""
    shell_source = (ROOT / "ui/main_window.py").read_text(encoding="utf-8")

    assert "def _create_sidebar_button" in shell_source
    assert "outside_background=colors.SIDEBAR_SURFACE" in shell_source
    for action in (
        "self._sidebar_new",
        "self._sidebar_open",
        "self._sidebar_save",
        "self._sidebar_delete",
        "self._sidebar_refresh",
    ):
        action_statement = shell_source.split(f"{action} = ", 1)[1].split("\n", 1)[0]
        assert "self._create_sidebar_button" in action_statement
    assert "outside_background=colors.NAVY" in shell_source


def test_header_button_host_styles_are_derived_for_all_command_groups() -> None:
    """Ribbon host footprints inherit navy instead of a native light button fill."""
    shell_source = (ROOT / "ui/main_window.py").read_text(encoding="utf-8")

    for control in (
        "_toolbar_new",
        "_toolbar_open",
        "_toolbar_save",
        "_toolbar_save_as",
        "_toolbar_materials",
        "_toolbar_pipe_sizes",
        "_toolbar_constants",
        "_toolbar_about",
    ):
        statement = shell_source.split(f"self.{control} = ", 1)[1].split("\n", 1)[0]
        assert "self._create_header_button" in statement


def test_command_group_structures_share_the_authoritative_navy_surface() -> None:
    """No near-navy intermediate frame can show through between ribbon actions."""
    styles_source = (ROOT / "ui/theme/styles.py").read_text(encoding="utf-8")

    command_group_block = styles_source.split('"CommandGroup.TFrame"', 1)[1].split(
        'style.configure("Sidebar.TFrame"', 1
    )[0]
    assert command_group_block.count("background=colors.NAVY") >= 3


def test_optional_naval_artwork_is_scoped_and_keeps_strong_references() -> None:
    """Keep decorative ships optional, constrained, and free of absolute placement."""
    source = (ROOT / "ui/main_window.py").read_text(encoding="utf-8")

    assert "ysh_ship_top_right_path" in source
    assert "ysh_ship_bottom_left_path" in source
    assert "self._header_ship_image" in source
    assert "self._sidebar_ship_image" in source
    assert "_update_header_artwork_visibility" in source
    assert "_update_sidebar_artwork_visibility" in source
    assert ".grid_remove()" in source
    assert ".place(" not in source
