"""Display-independent contracts for V3-F shell branding refinement."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    """Read a shell presentation source file."""
    return (ROOT / path).read_text(encoding="utf-8")


def test_brand_lockup_uses_a_compact_white_logo_plate() -> None:
    """The approved logo remains a compact part of the header identity lockup."""
    window = _source("ui/main_window.py")
    styles = _source("ui/theme/styles.py")

    assert 'style="HeaderLogoPlate.TFrame"' in window
    assert "padding=(SM // 2, SM // 2)" in window
    assert 'logo_plate.pack(side="left", padx=(0, 6))' in window
    assert 'self._header_title.pack(side="left", pady=(0, 1))' in window
    assert 'self._header_subtitle.pack(side="left", padx=(SM, 0), pady=(2, 0))' in window
    assert 'background=colors.CARD_SURFACE' in styles
    assert 'bordercolor=colors.DIVIDER' in styles


def test_decorative_ships_remain_proportional_and_responsive() -> None:
    """Naval artwork stays subordinate and hides before it can obstruct controls."""
    window = _source("ui/main_window.py")

    for fragment in (
        "maximum_width=260",
        "maximum_height=76",
        "maximum_width=216",
        "maximum_height=82",
        "dimensions = (140, 44)",
        "dimensions = (200, 60)",
        "dimensions = (260, 76)",
        "image.subsample(scale, scale)",
        "if event.width < 900:",
        "if event.height < 680:",
    ):
        assert fragment in window


def test_header_keeps_navy_command_hosts_and_packaged_asset_references() -> None:
    """Brand polish cannot alter the accepted header button or resource architecture."""
    window = _source("ui/main_window.py")

    assert "outside_background=colors.NAVY" in window
    assert "ysh_logo_path()" in window
    assert "ysh_ship_top_right_path()" in window
    assert "ysh_ship_bottom_left_path()" in window
    assert "self._header_logo_image" in window
    assert "self._header_ship_image" in window
    assert "self._sidebar_ship_image" in window
