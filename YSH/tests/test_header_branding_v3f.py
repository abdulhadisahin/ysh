"""Display-independent contracts for V3-F shell branding refinement."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    """Read a shell presentation source file."""
    return (ROOT / path).read_text(encoding="utf-8")


def test_brand_lockup_moves_to_sidebar_without_large_header_text() -> None:
    """The approved compact emblem belongs to the Project panel."""
    window = _source("ui/main_window.py")
    styles = _source("ui/theme/styles.py")

    assert 'self._add_sidebar_logo(self._sidebar_brand)' in window
    assert 'self._header_title' not in window
    assert 'self._header_subtitle' not in window
    assert 'style="SidebarLogo.TLabel"' in window
    assert 'background=colors.NAVY' in styles
    assert 'bordercolor=colors.HEADER_SURFACE' in styles
    assert 'background=colors.CARD_SURFACE' not in styles.split('"HeaderLogoPlate.TFrame"', 1)[1].split('"Ribbon.TFrame"', 1)[0]


def test_shell_reuses_ship_decoration_without_replacing_sidebar_emblem() -> None:
    """The accepted ship is decorative while the emblem stays in the sidebar."""
    window = _source("ui/main_window.py")

    assert "d243_main_logo_path" in window
    assert "Branding belongs to the Project panel" in window
    assert "ysh_ship_top_right_path()," in window
    assert "self._header_ship_label.place(" in window


def test_header_keeps_shell_command_hosts_and_packaged_asset_references() -> None:
    """Brand polish cannot alter the accepted header button or resource architecture."""
    window = _source("ui/main_window.py")

    assert "outside_background=colors.HEADER_SURFACE" in window
    assert "d243_main_logo_path()" in window
    assert "SIDEBAR_LOGO_TARGET_SIZE = 176" in window
    assert "AssetImageLoader.load" in window
    assert "self._sidebar_logo_source_image" in window
    assert "self._sidebar_logo_image" in window
