"""Master visual propagation contracts without pixel-perfect screenshot assertions."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from i18n.messages_tr import MESSAGES as TR
from i18n.messages_en import MESSAGES as EN
from ui.theme import colors
from ui.theme.module_visuals import MODULES, configure_module_visuals
from ui.widgets.rounded_button import (
    TRANSFER_PRIMARY_PALETTE, DISCHARGE_PRIMARY_PALETTE, SUCTION_PRIMARY_PALETTE,
)
from .test_pipe_visual_pilot import Style

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize('key,palette', [
    ('transfer_pump', TRANSFER_PRIMARY_PALETTE),
    ('discharge_head_loss', DISCHARGE_PRIMARY_PALETTE),
    ('suction_npsh', SUCTION_PRIMARY_PALETTE),
])
def test_module_card_controls_result_and_action_share_one_identity(key, palette):
    """White inputs, tinted results and focus use one centralized module palette."""
    style = Style()
    configure_module_visuals(style)
    prefix, accent, dark, soft, secondary = MODULES[key]
    assert style.configurations[prefix+'InputCard.TLabelframe']['background'] == colors.WHITE
    assert style.configurations[prefix+'ResultCard.TLabelframe']['background'] == soft
    assert style.configurations[prefix+'ResultMetricValue.TLabel']['foreground'] == dark
    assert style.configurations[prefix+'ResultMetricValue.TLabel']['font'][1] > style.configurations[secondary+'Value.TLabel']['font'][1]
    assert style.maps[prefix+'.TEntry']['bordercolor'] == [('focus', accent)]
    assert palette.normal == (dark, accent) and palette.focus_border == accent
    assert not any(name.startswith(('Pipe', 'Library', 'Formula', 'Warning', 'Critical')) for name in style.configurations)


@pytest.mark.parametrize('key', MODULES)
def test_pages_opt_in_without_inline_formula_or_watermark(key):
    """Existing semantic groups, formula separation and snapshot action remain."""
    source = (ROOT / f'ui/pages/{key}_page.py').read_text(encoding='utf-8')
    assert f'apply_module_visuals(self, "{key}")' in source
    assert 'separate_window=True' in source
    assert 'watermark' not in source.lower()
    assert 'pipe_pilot' not in source
    main = (ROOT / 'ui/main_window.py').read_text(encoding='utf-8')
    assert 'page._formula_panel.configure_post_tools(' in main
    assert 'page._pdf_button=page._formula_panel._pdf_button' in main
    assert 'save_snapshot_pdf(self._root,target._pdf_snapshot)' in main.replace(' ', '')
    assert 'if MainWindow._pdf_is_current(target) else None' in main


@pytest.mark.parametrize('key', [
    'transfer.design.volume.label', 'transfer.design.target_time.label',
    'transfer.design.pump_capacity.label', 'field.npsh_required_optional',
])
def test_field_captions_have_turkish_and_english_resources(key):
    """Separate unit columns do not introduce English into the default UI."""
    assert TR[key] and EN[key]
    assert 'optional' not in TR[key]


def test_presentation_walker_preserves_variables_commands_states_and_excluded_components(monkeypatch):
    """Exercise actual traversal: engineering controls remain the same objects."""
    import ui.widgets.module_visuals as module

    class Widget:
        def __init__(self, children=(), **options):
            self.children, self.options = list(children), options
        def configure(self, **options):
            self.options.update(options)
        def cget(self, key):
            return self.options.get(key, '')
        def winfo_children(self):
            return self.children

    types = {name: type(name, (Widget,), {}) for name in (
        'Entry', 'Combobox', 'Label', 'Frame', 'InformationCard', 'ResultCard',
        'ResultMetric', 'SectionHeader', 'FormulaReferencePanel', 'EngineeringWarningPanel')}
    for name in ('Entry', 'Combobox', 'Label', 'Frame'):
        monkeypatch.setattr(module.ttk, name, types[name])
    for name in types.keys() - {'Entry', 'Combobox', 'Label', 'Frame'}:
        monkeypatch.setattr(module, name, types[name])
    variable, callback = object(), lambda: None
    entry = types['Entry'](textvariable=variable, state='readonly')
    combo = types['Combobox'](textvariable=variable, state='disabled')
    severity = types['Label'](style='Warning.TLabel')
    untouched = [types[name]([types['Entry']()]) for name in
                 ('FormulaReferencePanel', 'EngineeringWarningPanel', 'ResultMetric')]
    source = Widget([combo], command=callback)
    page = Widget([types['InformationCard']([entry, severity]), source, *untouched])
    page._pipe_source_panel = source
    module.apply_module_visuals(page, 'discharge_head_loss')
    assert entry.options == dict(textvariable=variable, state='readonly', style='Discharge.TEntry')
    assert combo.options == dict(textvariable=variable, state='disabled', style='Discharge.TCombobox')
    assert source.options['command'] is callback
    assert source.options['style'] == 'DischargeInputCard.TLabelframe'
    assert severity.options['style'] == 'Warning.TLabel'
    assert all(child.children[0].options == {} for child in untouched)


def test_transfer_methods_and_hydraulic_stages_remain_separate():
    """The visual system cannot merge methodology or introduce automatic link writes."""
    transfer = (ROOT/'ui/pages/transfer_pump_page.py').read_text(encoding='utf-8')
    for marker in ('TransferPumpMode.DESIGN', '_method_box', '_method_explanation', '_show_calculation_mode'):
        assert marker in transfer
    for filename in ('discharge_head_loss_page', 'suction_npsh_page'):
        source = (ROOT/f'ui/pages/{filename}.py').read_text(encoding='utf-8')
        assert '_pipe_source_panel' in source and '_workflow' in source
    suction = (ROOT/'ui/pages/suction_npsh_page.py').read_text(encoding='utf-8')
    assert '_calculate_suction_loss' in suction and '_calculate_enpy' in suction
    assert 'normal_style_prefix="SuctionResultMetric"' in suction
    assert 'result.npsh_margin' in suction
