"""Non-pixel contracts for the shared workspace and on-demand explanations."""
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from ui.widgets.formula_view import FormulaReferencePanel
from ui.widgets.workspace_watermark import WorkspaceWatermark, watermark_size

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize('page', [
    'pipe_design_page', 'discharge_head_loss_page',
    'suction_npsh_page', 'transfer_pump_page',
])
def test_modules_keep_typed_formula_provider_and_compact_entry(page):
    source = (ROOT / f'ui/pages/{page}.py').read_text(encoding='utf-8')
    assert 'separate_window=True' in source
    assert 'step_provider=self._formula_steps' in source
    assert 'self.watermark_surfaces = ' in source


@pytest.mark.parametrize('viewport', [(0, 0), (-1, 100), (100, -1), (8, 8), (24, 24)])
def test_no_artwork_for_unusable_surface(viewport):
    assert watermark_size((600, 300), viewport) == (0, 0)


def test_historical_view_retains_inline_frozen_provider():
    source = (ROOT / 'ui/dialogs/calculation_history.py').read_text(encoding='utf-8')
    assert 'step_provider=lambda:snapshot.formula_steps' in source
    assert 'separate_window=True' not in source


def test_live_view_is_lazy_and_closes_reopens_without_duplicates(monkeypatch):
    import ui.widgets.formula_view as module
    import ui.widgets.scrollable_frame as scrolling
    created = []

    class Widget:
        def __init__(self, *args, **kwargs):
            self.options = kwargs
            self.content = object()
            self.destroyed = False
        def configure(self, **kwargs): self.options.update(kwargs)
        def grid(self, **kwargs): pass
        def pack(self, **kwargs): pass
        def title(self, text): self.options['title'] = text
        def transient(self, parent): pass
        def geometry(self, value): pass
        def minsize(self, *args): pass
        def protocol(self, name, callback): self.close = callback
        def set_wheel_active(self, value): self.active = value
        def destroy(self): self.destroyed = True

    def create_dialog(*args):
        dialog = Widget()
        created.append(dialog)
        return dialog

    monkeypatch.setattr(module.ttk.Frame, '__init__', lambda *a, **k: None)
    monkeypatch.setattr(FormulaReferencePanel, 'columnconfigure', lambda *a, **k: None)
    monkeypatch.setattr(FormulaReferencePanel, 'winfo_toplevel', lambda self: object())
    monkeypatch.setattr(FormulaReferencePanel, '_create_content', lambda *a: Widget())
    monkeypatch.setattr(module.tk, 'Toplevel', create_dialog)
    monkeypatch.setattr(scrolling, 'ScrollableFrame', Widget)
    rendered = []
    monkeypatch.setattr(FormulaReferencePanel, 'refresh', lambda self: rendered.append(self._content))
    panel = FormulaReferencePanel(object(), lambda: [], toggle_button_factory=lambda *a: Widget(),
                                  step_provider=lambda: (), separate_window=True)
    assert not created and panel._content is None and not panel.expanded
    panel.toggle()
    assert len(created) == 1 and panel.expanded and len(rendered) == 1
    created[0].close()
    assert created[0].destroyed and not panel.expanded and panel._content is None
    panel.toggle()
    assert len(created) == 2 and panel.expanded
    panel.toggle()
    assert created[1].destroyed and not panel.expanded


def test_shared_surface_render_cache_reuses_bounded_aspect_fit(tmp_path, monkeypatch):
    import ui.widgets.workspace_watermark as module
    path = tmp_path / 'logo.png'
    Image.new('RGBA', (600, 300), (0, 20, 40, 255)).save(path)
    renders = []
    monkeypatch.setattr(module.ImageTk, 'PhotoImage', lambda image, **kw: renders.append(image.copy()) or image)
    state = SimpleNamespace(width=300, height=200)
    renderer = WorkspaceWatermark.__new__(WorkspaceWatermark)
    renderer.master = SimpleNamespace(winfo_width=lambda: state.width, winfo_height=lambda: state.height)
    renderer._source_path = path
    renderer._source = None
    renderer._image_cache = {}
    renderer._active_size = (0, 0)
    renderer.configure = lambda **kw: None
    renderer._refresh_image()
    assert renders[0].getchannel('A').getextrema() == (31, 31)
    assert renders[0].width <= state.width - 24
    assert renders[0].height <= state.height - 24
    state.width += 1
    renderer._refresh_image()
    assert len(renders) == 1
    for width in range(320, 800, 32):
        state.width = width
        state.height = width
        renderer._refresh_image()
    assert len(renderer._image_cache) <= renderer.CACHE_LIMIT
    assert renderer._source.size == (600, 300)


def test_shared_surface_resize_events_are_coalesced():
    renderer = WorkspaceWatermark.__new__(WorkspaceWatermark)
    renderer._pending = None
    scheduled = []
    renderer.after_idle = lambda callback: scheduled.append(callback) or 'pending'
    renderer._on_parent_configure(None)
    renderer._on_parent_configure(None)
    assert len(scheduled) == 1
