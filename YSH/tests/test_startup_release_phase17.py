"""Release contracts for deferred chart imports and complete frozen resources."""
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

from ui.widgets.transfer_pump_chart import TransferPumpChart, TransferPumpChartModel
from ui import assets
from PIL import Image

ROOT = Path(__file__).parents[2]


def test_application_import_does_not_load_matplotlib_or_lazy_windows() -> None:
    """A fresh interpreter verifies the import boundary independent of pytest imports."""
    result = subprocess.run([
        sys.executable, '-c',
        'import sys; import main; '
        'assert "matplotlib" not in sys.modules; '
        'assert "ui.dialogs.calculation_history" not in sys.modules; '
        'assert "ui.dialogs.engineering_library_workspace" not in sys.modules',
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_hidden_chart_retains_latest_model_without_creating_canvas() -> None:
    """Startup and hidden-page refreshes store data without rendering Matplotlib."""
    chart = SimpleNamespace(winfo_ismapped=lambda: False)
    first = TransferPumpChartModel((), (), None, None, None, None)
    second = TransferPumpChartModel((), (), None, 1, 2, 3)
    TransferPumpChart.render(chart, first)
    TransferPumpChart.render(chart, second)
    assert chart._last_model is second


def test_chart_map_renders_latest_stored_model() -> None:
    """The visibility boundary restores existing chart behavior using current data."""
    calls = []
    model = TransferPumpChartModel((), (), None, None, None, None)
    chart = SimpleNamespace(_last_model=model, render=calls.append)
    TransferPumpChart._on_map(chart)
    assert calls == [model]
    chart._last_model = None
    TransferPumpChart._on_map(chart)
    assert calls == [model]


def test_existing_canvas_is_reused_without_import_or_reconstruction() -> None:
    """Mapping or resizing an already rendered chart cannot create a second canvas."""
    existing = object()
    chart = SimpleNamespace(_canvas=existing)
    TransferPumpChart._ensure_canvas(chart)
    assert chart._canvas is existing


def test_all_dynamic_resource_maps_resolve_packaged_files() -> None:
    """Dynamic names remain part of the complete resources payload."""
    for mapping, loader in (
        (assets.ACTION_ICON_FILENAMES, assets.action_icon_path),
        (assets.LIBRARY_CATEGORY_ICON_FILENAMES, assets.action_icon_path),
        (assets.STATUS_ICON_FILENAMES, assets.status_icon_path),
        (assets.FORMULA_ASSET_FILENAMES, assets.formula_asset_path),
    ):
        for key in mapping:
            path = loader(key)
            assert path is not None and path.is_file(), key


def test_release_uses_runtime_hook_resources_and_excludes_build_probe() -> None:
    """The optional checker shares the payload but is absent from the release COLLECT."""
    source = (ROOT / 'build/ysh.spec').read_text(encoding='utf-8')
    assert 'collect_all' not in source
    assert 'name="D243"' in source
    assert 'console=False' in source
    assert '"init.tcl"' in source and '"tk.tcl"' in source
    assert 'D243-package-probe' not in source.split('COLLECT(', 1)[1]
    assert '"tests" not in module_path.parts' in source
    assert 'branding_resources' in source


def test_build_script_stops_before_zip_when_frozen_probe_fails() -> None:
    """A build success alone cannot produce a release archive."""
    source = (ROOT / 'build/build_exe.ps1').read_text(encoding='utf-8')
    assert source.index('Frozen package probe failed') < source.index('Compress-Archive')
    assert 'Get-FileHash' in source
    assert '$env:TCL_LIBRARY = $oldTcl' in source
    assert '$env:TK_LIBRARY = $oldTk' in source


def test_asset_loader_uploads_only_target_rendition_and_runs_selected_fit(tmp_path, monkeypatch) -> None:
    """Unused transforms and full-resolution Tk copies must not tax every button."""
    import ui.widgets.asset_loader as module
    path = tmp_path / 'synthetic.png'
    Image.new('RGBA', (800, 400), (20, 30, 40, 255)).save(path)
    uploads = []
    monkeypatch.setattr(module.ImageTk, 'PhotoImage', lambda image, **kw: uploads.append(image.copy()) or image)
    monkeypatch.setattr(module.AssetImageLoader, '_cache', {})
    def unused(*args, **kwargs):
        raise AssertionError('Unselected transform evaluated')
    for name in ('_visible_content', '_glyph_content', '_full_asset_safe', '_silhouette_safe'):
        monkeypatch.setattr(module.AssetImageLoader, name, unused)
    master = SimpleNamespace(tk=object())
    loaded = module.AssetImageLoader.load(master, path, 80)
    assert len(uploads) == 1 and uploads[0].size == (80, 40)
    assert loaded.source is loaded.rendered
    assert module.AssetImageLoader.load(master, path, 80) is loaded
    assert len(uploads) == 1
