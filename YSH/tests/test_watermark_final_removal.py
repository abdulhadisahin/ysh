"""Watermark removal contracts preserve existing geometry, events and shared module composition."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from ui.widgets.scrollable_frame import ScrollableFrame
from ui.widgets.scrollable_page_host import ScrollablePageHost

ROOT = Path(__file__).parents[1]
MODULES = ('pipe_design', 'transfer_pump', 'discharge_head_loss', 'suction_npsh')
PAGES = ('pipe_design_page', 'transfer_pump_page', 'discharge_head_loss_page', 'suction_npsh_page')


class Widget:
    """Record layout operations without opening Tk or inventing pixel expectations."""
    def __init__(self, parent: object, **kwargs: object) -> None:
        self.parent = parent
        self.options = dict(kwargs)
        self.bindings: dict[str, object] = {}
        self.items: list[tuple[str, dict[str, object]]] = []

    def configure(self, **kwargs: object) -> None:
        """Record only explicit widget configuration."""
        self.options.update(kwargs)

    def grid(self, **kwargs: object) -> None:
        """Record the existing viewport/scrollbar grid cells."""
        self.cell = kwargs

    def pack(self, **kwargs: object) -> None:
        """Record normal page packing without reserved decorative space."""
        self.packing = kwargs

    def bind(self, sequence: str, callback: object) -> None:
        """Record the existing input routes only."""
        self.bindings[sequence] = callback

    def set(self, *args: object) -> None:
        """Represent a scrollbar command without creating events."""

    def yview(self, *args: object) -> tuple[float, float]:
        """Represent a stable scroll viewport."""
        return (0, 1)

    def create_window(self, coordinates: tuple[int, int], **kwargs: object) -> int:
        """The content window is the sole canvas item."""
        self.items.append(('window', kwargs))
        return 1


@pytest.mark.parametrize('width,height', [(1, 1), (24, 24), (220, 500), (320, 240), (640, 480),
                                         (800, 600), (1000, 700), (1200, 700), (1700, 1000), (2560, 1440)])
def test_scroll_viewport_has_only_original_layout_and_event_routes(monkeypatch, width: int, height: int) -> None:
    """All viewport sizes retain two original columns, one content window and native wheel routes."""
    import ui.widgets.scrollable_frame as module
    base = module.ttk.Frame
    monkeypatch.setattr(base, '__init__', lambda self, parent, **kw: setattr(self, 'frame_options', kw))
    columns, rows = [], []
    monkeypatch.setattr(ScrollableFrame, 'columnconfigure', lambda self, index, **kw: columns.append((index, kw)))
    monkeypatch.setattr(ScrollableFrame, 'rowconfigure', lambda self, index, **kw: rows.append((index, kw)))
    monkeypatch.setattr(module.tk, 'Canvas', Widget)
    monkeypatch.setattr(module.ttk, 'Scrollbar', Widget)
    monkeypatch.setattr(module.ttk, 'Frame', Widget)
    frame = ScrollableFrame(object(), width=width, height=height)
    assert frame.frame_options == {'width': width, 'height': height}
    assert columns == [(0, {'weight': 1})] and rows == [(0, {'weight': 1})]
    assert frame.canvas.cell == {'row': 0, 'column': 0, 'sticky': 'nsew'}
    assert frame.scrollbar.cell == {'row': 0, 'column': 1, 'sticky': 'ns'}
    assert len(frame.canvas.items) == 1 and frame.canvas.items[0][0] == 'window'
    assert set(frame.canvas.bindings) == {'<Configure>', '<MouseWheel>', '<Prior>', '<Next>', '<Home>', '<End>'}
    assert set(frame.content.bindings) == {'<Configure>'}
    assert not hasattr(frame, '_background_watermark')
    assert 'takefocus' not in frame.canvas.options


@pytest.mark.parametrize('key', MODULES)
@pytest.mark.parametrize('viewport', [(320, 240), (1200, 700), (1700, 1000)])
def test_all_modules_use_unchanged_page_factory_without_decoration(monkeypatch, key: str, viewport: tuple[int, int]) -> None:
    """No module requests an asset, decoration helper or special placement on construction."""
    import ui.widgets.scrollable_page_host as module
    created = []
    class Host(Widget):
        def __init__(self, parent: object) -> None:
            super().__init__(parent, width=viewport[0], height=viewport[1])
            self.content = Widget(self)
            created.append(self)
    monkeypatch.setattr(module, 'ScrollableFrame', Host)
    notebook = ScrollablePageHost.__new__(ScrollablePageHost)
    notebook._hosts, notebook._page_hosts, notebook._page_keys = {}, {}, {}
    tabs, callbacks = [], []
    notebook.add = lambda host, **kw: tabs.append((host, kw))
    notebook.after_idle = lambda callback: callbacks.append(callback)
    page = notebook.add_scrollable_page('Module', Widget, key)
    assert len(created) == 1 and page.parent is created[0].content
    assert page.packing == {'fill': 'x', 'expand': True}
    assert tabs == [(created[0], {'text': 'Module'})]
    assert notebook._page_keys[key] is created[0]
    assert len(callbacks) == 2  # Existing tab activation/theme callbacks only.
    assert not hasattr(created[0], '_background_watermark')


@pytest.mark.parametrize('page', PAGES)
def test_each_module_keeps_controls_and_formula_entry_without_watermark(page: str) -> None:
    """Removal does not redesign module controls or retain per-page positioning hacks."""
    source = (ROOT / f'ui/pages/{page}.py').read_text(encoding='utf-8')
    assert 'watermark_surfaces' not in source
    assert 'FormulaReferencePanel' in source and 'separate_window=True' in source
    assert 'RoundedImageButton' in source or 'create_rounded_button' in source


def test_dead_renderer_cache_focus_handlers_and_polling_are_removed() -> None:
    """No watermark widget, image cache, resampling, event binding or timer remains."""
    assert not (ROOT / 'ui/widgets/workspace_watermark.py').exists()
    for name in ('scrollable_frame', 'scrollable_page_host'):
        source = (ROOT / f'ui/widgets/{name}.py').read_text(encoding='utf-8')
        assert 'watermark' not in source.lower()
        assert 'ImageTk' not in source and 'Image.open' not in source
        assert 'after(' not in source


def test_normal_branding_and_pdf_header_assets_remain_available() -> None:
    """Workspace removal preserves canonical assets, shell branding and PDF resources."""
    from ui.assets import d243_main_logo_path, d243_watermark_logo_path, d243_small_logo_path
    assert d243_watermark_logo_path().is_file()
    assert d243_main_logo_path().is_file() and d243_small_logo_path().is_file()
    assert 'd243_small_logo_path' in (ROOT / 'reporting/renderer.py').read_text(encoding='utf-8')
