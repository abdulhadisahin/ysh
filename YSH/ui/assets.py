"""Local-only asset locations reserved for future approved YSH artwork."""

from __future__ import annotations

from pathlib import Path

from YSH.paths import ApplicationPaths


ASSET_DIRECTORY = Path(__file__).resolve().parent / "assets"
LOGO_SYMBOL_PATH = ASSET_DIRECTORY / "logo_symbol.png"
SIDEBAR_SHIP_PATH = ASSET_DIRECTORY / "sidebar_ship.png"
TAB_ICON_PATHS = {
    "pipe_design": ASSET_DIRECTORY / "tab_pipe.png",
    "transfer_pump": ASSET_DIRECTORY / "tab_transfer.png",
    "discharge_head_loss": ASSET_DIRECTORY / "tab_discharge.png",
    "suction_npsh": ASSET_DIRECTORY / "tab_suction.png",
}
BRANDING_RESOURCE_DIRECTORY = "resources"
YSH_LOGO_FILENAME = "ysh_logo.png"
YSH_ICON_FILENAME = "ysh.ico"
YSH_SHIP_TOP_RIGHT_FILENAME = "ysh_ship_top_right.png"
YSH_SHIP_BOTTOM_LEFT_FILENAME = "ysh_ship_bottom_left.png"


def local_asset_path(path: Path) -> Path | None:
    """Return an existing packaged-local asset, never downloading a resource."""
    return path if path.is_file() else None


def branding_asset_path(
    filename: str,
    resource_root: Path | None = None,
) -> Path | None:
    """Return an approved branding asset from source or frozen resources."""
    root = resource_root or ApplicationPaths().resource_root
    return local_asset_path(root / BRANDING_RESOURCE_DIRECTORY / filename)


def ysh_logo_path(resource_root: Path | None = None) -> Path | None:
    """Return the approved YSH header-logo path when available."""
    return branding_asset_path(YSH_LOGO_FILENAME, resource_root)


def ysh_icon_path(resource_root: Path | None = None) -> Path | None:
    """Return the approved YSH Windows icon path when available."""
    return branding_asset_path(YSH_ICON_FILENAME, resource_root)


def ysh_ship_top_right_path(resource_root: Path | None = None) -> Path | None:
    """Return the optional approved upper-shell marine artwork path."""
    return branding_asset_path(YSH_SHIP_TOP_RIGHT_FILENAME, resource_root)


def ysh_ship_bottom_left_path(resource_root: Path | None = None) -> Path | None:
    """Return the optional approved sidebar marine artwork path."""
    return branding_asset_path(YSH_SHIP_BOTTOM_LEFT_FILENAME, resource_root)
