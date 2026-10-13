"""Display-independent contracts for V3-F shell branding refinement."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    """Read a shell presentation source file."""
    return (ROOT / path).read_text(encoding="utf-8")


def test_brand_lockup_uses_a_transparent_emblem_on_the_navy_shell() -> None:
    """The approved emblem no longer sits on a white rectangular backing plate."""
    window = _source("ui/main_window.py")
    styles = _source("ui/theme/styles.py")

    assert 'logo_plate = ttk.Frame(parent, style="HeaderLogoPlate.TFrame")' in window
    assert 'logo_plate.pack(side="left", padx=(0, MD))' in window
    assert 'brand_text.pack(side="left")' in window
    assert 'self._header_title.pack(anchor="w")' in window
    assert 'self._header_subtitle.pack(anchor="w", pady=(2, 0))' in window
    assert 'background=colors.NAVY' in styles
    assert 'bordercolor=colors.NAVY' in styles
    assert 'background=colors.CARD_SURFACE' not in styles.split('"HeaderLogoPlate.TFrame"', 1)[1].split('"Ribbon.TFrame"', 1)[0]


def test_shell_removes_temporary_ship_art_before_the_d243_emblem_is_supplied() -> None:
    """The final D243 shell reserves branding space rather than showing placeholders."""
    window = _source("ui/main_window.py")

    assert "d243_main_logo_path" in window
    assert "legacy decorative ship art is not part of this shell" in window
    assert "ysh_ship_top_right_path()," not in window


def test_header_keeps_navy_command_hosts_and_packaged_asset_references() -> None:
    """Brand polish cannot alter the accepted header button or resource architecture."""
    window = _source("ui/main_window.py")

    assert "outside_background=colors.NAVY" in window
    assert "d243_main_logo_path()" in window
    assert "HEADER_LOGO_TARGET_SIZE = 180" in window
    assert "AssetImageLoader.load" in window
    assert "self._header_logo_source_image" in window
    assert "self._header_logo_image" in window
