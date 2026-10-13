"""Contracts for the Phase 9UI shared presentation foundation and Transfer pilot."""

from __future__ import annotations

from pathlib import Path

from ui.assets import action_icon_path, status_icon_path


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_asset_registry_resolves_only_real_packaged_branding_and_optional_icons() -> None:
    """Missing approved icon sets fall back safely instead of creating substitute artwork."""
    assets = _source("ui/assets.py")

    assert "ACTION_ICON_FILENAMES" in assets
    assert "STATUS_ICON_FILENAMES" in assets
    assert "def action_icon_path" in assets
    assert "def status_icon_path" in assets
    assert action_icon_path("calculate") == ROOT / "resources" / "icons" / "actions" / "btn_hesapla.png"
    assert status_icon_path("warning") == ROOT / "resources" / "icons" / "status" / "status_uyari.png"


def test_asset_loader_centralizes_tk_image_caching_and_aspect_safe_scaling() -> None:
    """Pages rely on one loader rather than scattering PhotoImage calls."""
    loader = _source("ui/widgets/asset_loader.py")
    window = _source("ui/main_window.py")

    assert "class AssetImageLoader" in loader
    assert "_cache" in loader
    assert "Image.Resampling.LANCZOS" in loader
    assert "AssetImageLoader.load" in window
    assert "d243_main_logo_path" in window


def test_shared_components_cover_card_metrics_tables_and_status_presentation() -> None:
    """The design system owns reusable desktop primitives rather than page-local copies."""
    cards = _source("ui/widgets/cards.py")
    components = _source("ui/widgets/engineering_components.py")
    styles = _source("ui/theme/styles.py")

    for component in ("SurfaceCard", "InputCard", "ResultCard", "ResultMetric", "SectionHeader"):
        assert f"class {component}" in cards
    for component in ("TableToolbar", "TechnicalTable", "EmptyState", "StatusBadge"):
        assert f"class {component}" in components
    for style_name in ("TableToolbar.TFrame", "EmptyState.TFrame", "StatusWarning.TLabel"):
        assert style_name in styles


def test_transfer_pilot_uses_shared_table_components_without_regression_changes() -> None:
    """Transfer is the first staged user of the new component vocabulary."""
    transfer = _source("ui/pages/transfer_pump_page.py")

    assert "from ui.widgets.engineering_components import TableToolbar, TechnicalTable" in transfer
    assert "toolbar = TableToolbar(references)" in transfer
    assert "self._tree_container = TechnicalTable(" in transfer
    assert "TransferPumpChart" in transfer
    assert "FormulaReferencePanel" in transfer
    assert "FUEL_DENSITY_T_PER_M3" in transfer
