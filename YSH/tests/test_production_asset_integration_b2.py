"""Production-asset contracts for the Phase 9UI-B2 shared UI integration."""

from __future__ import annotations

from pathlib import Path

from ui.assets import (
    ACTION_ICON_FILENAMES,
    STATUS_ICON_FILENAMES,
    action_icon_path,
    d243_main_logo_path,
    status_icon_path,
)
from ui.widgets import asset_loader


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_production_asset_manifest_is_complete_and_resolves_from_package_resources() -> None:
    assert len(ACTION_ICON_FILENAMES) == 16
    assert len(STATUS_ICON_FILENAMES) == 8
    assets = _source("ui/assets.py")
    for asset_name in (
        "BTN_YENI", "BTN_AC", "BTN_KAYDET", "BTN_FARKLI_KAYDET", "BTN_SIL",
        "BTN_YENILE", "BTN_HESAPLA", "BTN_TEMIZLE", "BTN_EKLE", "BTN_DUZENLE",
        "BTN_HAKKINDA", "BTN_FORMULU_GOSTER", "BTN_PROJE", "BTN_KUTUPHANE",
        "BTN_GRAFIK", "BTN_UYARI", "STATUS_HAZIR", "STATUS_BILGI", "STATUS_UYARI",
        "STATUS_KRITIK", "STATUS_HATA", "STATUS_BASARILI", "STATUS_KAYDEDILDI",
        "STATUS_ISLEMDE",
    ):
        assert asset_name in assets
    assert sorted(path.name for path in (ROOT / "resources" / "branding").iterdir()) == [
        "d243_logo.ico",
        "d243_logo_main.png",
        "d243_logo_medium.png",
        "d243_logo_small.png",
        "d243_logo_watermark.png",
    ]
    assert all((ROOT / "resources" / "icons" / "actions" / name).is_file() for name in ACTION_ICON_FILENAMES.values())
    assert all((ROOT / "resources" / "icons" / "status" / name).is_file() for name in STATUS_ICON_FILENAMES.values())
    assert d243_main_logo_path() == ROOT / "resources" / "branding" / "d243_logo_main.png"
    assert action_icon_path("calculate").is_file()  # type: ignore[union-attr]
    assert status_icon_path("critical").is_file()  # type: ignore[union-attr]


def test_shared_loader_and_button_keep_native_text_with_optional_production_icons() -> None:
    loader = _source("ui/widgets/asset_loader.py")
    button = _source("ui/widgets/rounded_button.py")

    assert "Image.Resampling.LANCZOS" in loader
    assert "ImageTk.PhotoImage" in loader
    assert "icon_name: str | None" in button
    assert "action_icon_path(self._icon_name)" in button
    assert "self._icon_text" in button
    assert "_composite_icon" in button


def test_asset_loader_renders_representative_logo_action_and_status_assets(monkeypatch: object) -> None:
    """Production PNGs flow through the shared loader without needing a display."""
    class _Photo:
        def __init__(self, image: object, master: object) -> None:
            del master
            self._size = image.size  # type: ignore[attr-defined]

        def width(self) -> int:
            return self._size[0]

        def height(self) -> int:
            return self._size[1]

    class _Master:
        tk = object()

    monkeypatch.setattr(asset_loader.ImageTk, "PhotoImage", _Photo)  # type: ignore[union-attr]
    asset_loader.AssetImageLoader._cache.clear()
    master = _Master()
    for path, size in (
        (d243_main_logo_path(), 180),
        (action_icon_path("calculate"), 34),
        (status_icon_path("warning"), 22),
    ):
        loaded = asset_loader.AssetImageLoader.load(master, path, size)
        assert loaded is not None
        assert loaded.rendered.width() <= size
        assert loaded.rendered.height() <= size


def test_shell_transfer_and_warning_surfaces_use_logical_asset_names() -> None:
    shell = _source("ui/main_window.py")
    transfer = _source("ui/pages/transfer_pump_page.py")
    components = _source("ui/widgets/engineering_components.py")
    warnings = _source("ui/widgets/engineering_warning_panel.py")
    host = _source("ui/widgets/scrollable_page_host.py")

    for icon_name in ('icon_name="new"', 'icon_name="open"', 'icon_name="save"', 'icon_name="save_as"', 'icon_name="about"'):
        assert icon_name in shell
    for icon_name in ('icon_name="calculate"', 'icon_name="clear"', 'icon_name="add"', 'icon_name="edit"', 'icon_name="delete"', 'icon_name="formula"'):
        assert icon_name in transfer
    assert "self._reference_actions = TableToolbar(references)" in transfer
    assert "status_icon_path(state)" in components
    assert '"error" if error else "critical" if critical else "warning"' in warnings
    assert "WorkspaceWatermark" not in host
