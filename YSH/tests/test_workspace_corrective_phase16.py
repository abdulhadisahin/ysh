"""Non-pixel contracts for the shared workspace and on-demand explanations."""
from pathlib import Path

import pytest


from ui.widgets.formula_view import FormulaReferencePanel

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize('page', [
    'pipe_design_page', 'discharge_head_loss_page',
    'suction_npsh_page', 'transfer_pump_page',
])
def test_modules_keep_typed_formula_provider_and_compact_entry(page):
    source = (ROOT / f'ui/pages/{page}.py').read_text(encoding='utf-8')
    assert 'separate_window=True' in source
    assert 'step_provider=self._formula_steps' in source
    assert 'self.watermark_surfaces = ' not in source


def test_historical_view_opens_frozen_provider_on_explicit_action():
    source = (ROOT / 'ui/dialogs/calculation_history.py').read_text(encoding='utf-8')
    assert 'step_provider=lambda:snapshot.formula_steps' in source
    assert 'separate_window=True' in source
    assert 'module_key=snapshot.module_code.value, historical=True' in source
    assert 'panel.toggle()' not in source


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
