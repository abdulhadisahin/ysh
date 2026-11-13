"""Exercise real constructors/factory signatures without a display or Tk root."""
import ast
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from i18n.translator import Translator
from ui.pages.transfer_pump_design import TransferPumpDesignPanel
from ui.widgets.rounded_button import create_rounded_button
from .test_main_window import _DummyWidget


@pytest.mark.parametrize('language', ['tr', 'en'])
def test_design_panel_constructor_uses_real_button_factory(monkeypatch, language: str) -> None:
    """Only native widgets are replaced; missing factory keywords still raise TypeError."""
    import ui.pages.transfer_pump_design as page
    import ui.widgets.rounded_button as buttons
    import ui.widgets.calculation_presentation as presentation

    class Widget(_DummyWidget):
        """Reuse the existing layout double while retaining configured button options."""
        def configure(self, **kwargs: object) -> None:
            """Record localized captions and styles for constructor assertions."""
            self.kwargs.update(kwargs)

        master = None

        def winfo_children(self):
            return ()

        def set_label(self, text: str) -> None:
            """Accept the result metric's normal caption update."""
            self.kwargs['label'] = text

    class Variable:
        """Keep constructor variables independent of Tcl's default root."""
        def __init__(self, value: str = '') -> None:
            self.value = value
            self.traces = []

        def get(self) -> str:
            """Return the current raw input/display value."""
            return self.value

        def set(self, value: str) -> None:
            """Update display state without invoking a Tcl interpreter."""
            self.value = value

        def trace_add(self, mode: str, callback: object) -> None:
            """Retain the actual constructor's invalidation registrations."""
            self.traces.append((mode, callback))

    def frame_init(self, *args: object, **kwargs: object) -> None:
        _DummyWidget.__init__(self, *args, **kwargs)
        self.tk = SimpleNamespace()

    monkeypatch.setattr(page.ttk.Frame, '__init__', frame_init)
    monkeypatch.setattr(page.ttk.Frame, 'columnconfigure', _DummyWidget.columnconfigure)
    for name in ('Label', 'Entry'):
        monkeypatch.setattr(page.ttk, name, Widget)
    for name in ('InputCard', 'ResultCard', 'ResultMetric'):
        monkeypatch.setattr(page, name, Widget)
    monkeypatch.setattr(page.tk, 'StringVar', Variable)
    monkeypatch.setattr(buttons, 'RoundedImageButton', Widget)
    monkeypatch.setattr(presentation, 'RoundedImageButton', Widget)
    monkeypatch.setattr(presentation.ttk, 'Style', lambda *args: SimpleNamespace(configure=lambda *a, **k: None))
    monkeypatch.setattr(page, 'numeric_pair', lambda parent, **options: (Widget(parent), Widget(parent, **options)))
    assert page.create_rounded_button is presentation.calculation_button
    panel = TransferPumpDesignPanel(object(), object(), Translator(language).translate, lambda: None)
    assert panel._calculate.kwargs['style'] == 'Calculation.TransferRoundedPrimary.TButton'
    assert panel._clear.kwargs['style'] == 'Calculation.RoundedNeutral.TButton'
    assert panel._calculate.kwargs['palette'] is buttons.TRANSFER_PRIMARY_PALETTE
    assert panel._clear.kwargs['palette'] is buttons.NEUTRAL_BUTTON_PALETTE
    assert panel._calculate.kwargs['icon_name'] == 'calculate'
    assert panel._clear.kwargs['icon_name'] == 'clear'
    assert panel._calculate.kwargs['command'] == panel.calculate
    assert panel._clear.kwargs['command'] == panel.clear
    assert panel._calculate.kwargs['text'] == Translator(language).translate('calculation.calculate')
    assert panel._calculate.kwargs['minimum_height'] == presentation.PRIMARY_HEIGHT
    assert panel._clear.kwargs['minimum_height'] == presentation.SECONDARY_HEIGHT
    # Exercise the wrapper's dynamic forwarding branch against the real factory.
    icon = page.create_rounded_button(object(), 'Icon', lambda: None, icon_only=True,
        style='HeaderCommand.TButton', palette=buttons.TRANSFER_PRIMARY_PALETTE)
    assert icon.kwargs['icon_only'] is True
    assert panel._flow.get() == panel._time.get() == '—'
    assert all(len(variable.traces) == 1 for variable in panel._fields.values())


def test_all_project_rounded_button_calls_bind_current_signature() -> None:
    """Audit every production call, including imported aliases, for stale helper arguments."""
    signature = inspect.signature(create_rounded_button)
    failures = []
    checked = []
    for path in Path(__file__).parents[1].rglob('*.py'):
        if 'tests' in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
        names = {'create_rounded_button'}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                names.update(alias.asname or alias.name for alias in node.names
                             if alias.name == 'create_rounded_button')
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            is_helper = (isinstance(node.func, ast.Name) and node.func.id in names or
                         isinstance(node.func, ast.Attribute) and node.func.attr == 'create_rounded_button')
            if not is_helper:
                continue
            location = f'{path.relative_to(Path(__file__).parents[1])}:{node.lineno}'
            # Dynamic argument forwarding needs an explicit review rather than silently escaping this audit.
            assert not any(isinstance(arg, ast.Starred) for arg in node.args), location
            if any(keyword.arg is None for keyword in node.keywords):
                # The shared presentation wrapper is the single reviewed forwarding
                # boundary; its real factory branch is exercised above in both languages.
                assert path.name == 'calculation_presentation.py', location
                assert [keyword.value.id for keyword in node.keywords if keyword.arg is None] == ['options'], location
                forwarded={'style':'TButton', 'palette':object()}
                forwarded.update({keyword.arg: object() for keyword in node.keywords if keyword.arg is not None})
                signature.bind(*[object() for _ in node.args], **forwarded)
                checked.append(location)
                continue
            checked.append(location)
            try:
                signature.bind(*[object() for _ in node.args],
                               **{keyword.arg: object() for keyword in node.keywords})
            except TypeError as error:
                failures.append(f'{location}: {error}')
    assert checked, 'No factory call sites were audited'
    assert not failures, '\n'.join(failures)
