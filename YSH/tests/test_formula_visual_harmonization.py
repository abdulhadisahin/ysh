"""Non-pixel Formula View chrome, selection and frozen evidence contracts."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from engineering.formula.models import FormulaCheck, CheckStatus, FormulaStep, SelectionReason
from engineering.provenance import SourceReference, SourceType, VerificationStatus, EngineeringValue, OverridePolicy
from i18n.messages_tr import MESSAGES as TR
from i18n.messages_en import MESSAGES as EN
from ui.theme.formula_visuals import IDENTITIES, identity, configure_formula_visuals
from ui.widgets.formula_view import FormulaReferencePanel, active_step_id
from ui.widgets.formula_steps import step_sections, verification_style, source_summary, source_rows, StepSection
from .test_pipe_visual_pilot import Style

ROOT = Path(__file__).parents[1]


def example():
    source = SourceReference(source_type=SourceType.USER_INPUT, verification_status=VerificationStatus.USER_SUPPLIED)
    from engineering.formula.common import variable
    return FormulaStep(step_id='frozen', title_key='formula2.result', formula_text='s = s0 + c',
        result_symbol='s', result_value=1.23456789, result_unit='mm', display_order=0,
        variables=(variable('c', 1, 'mm'),),
        used_values=(EngineeringValue(used_value=1, recommended_value=.5, unit='mm', source=source, symbol='c',
            override_policy=OverridePolicy.SUGGESTED, override_reason='Kullanıcı tercihi'),),
        sources=(source,), selection_reason=SelectionReason.USER_INPUT,
        substitution='s = 0,23456789 + 1', check=FormulaCheck(status=CheckStatus.NOT_CONFIGURED))


@pytest.mark.parametrize('key', IDENTITIES)
def test_module_identity_reaches_view_and_preserves_master_colors(key):
    style = Style(); configure_formula_visuals(style)
    prefix, accent, dark, soft, label = identity(key)
    assert TR[label] and EN[label]
    assert style.configurations[prefix+'Accent.TFrame']['background'] == accent
    assert style.configurations[prefix+'Result.TLabel']['foreground'] == dark
    assert style.configurations[prefix+'Header.TFrame']['background'] == soft
    page = (ROOT/f'ui/pages/{key}_page.py').read_text(encoding='utf-8')
    assert f'module_key="{key}"' in page
    assert all(name.startswith('FV') for name in style.configurations)


@pytest.mark.parametrize('status,role', [
    (VerificationStatus.VERIFIED,'Verified'), (VerificationStatus.PARTIALLY_VERIFIED,'Warning'),
    (VerificationStatus.USER_SUPPLIED,'Info'), (VerificationStatus.UNVERIFIED,'Warning'),
    (VerificationStatus.DEPRECATED,'Error'), (None,'Muted'),
])
def test_verification_tint_follows_recorded_status_only(status, role):
    src = SourceReference(source_type=SourceType.PIPE_STANDARD, verification_status=status)
    region = StepSection('source',rows=source_rows(src,TR.__getitem__))
    assert verification_style(region,TR.__getitem__) == 'FV'+role+'.TLabel'


def test_long_source_metadata_cannot_hide_verification_summary():
    src = SourceReference(source_type=SourceType.PIPE_STANDARD, document='Long document '*100,
        verification_status=VerificationStatus.UNVERIFIED)
    region = StepSection('source',rows=source_rows(src,TR.__getitem__))
    summary = source_summary(region,TR.__getitem__)
    assert summary.startswith(TR['formula2.verification_status.UNVERIFIED'])
    assert len(summary)<180
    assert any('Long document' in value for label,value in region.rows)


def test_all_eight_sections_and_precision_survive_presentation():
    step = example()
    sections = step_sections(step,TR.__getitem__)
    assert [s.key for s in sections] == ['formula','variables','used_values','reason','source','substitution','result','check']
    assert step.result_value == 1.23456789
    assert 'Önerilen' in next(s.text for s in sections if s.key=='reason')
    assert next(s.text for s in sections if s.key=='check') == TR['formula2.check.NOT_CONFIGURED']


def test_selection_retains_identity_and_does_not_mutate_steps():
    first = example(); second = replace(first,step_id='second')
    assert active_step_id((first,second),'second') == 'second'
    assert active_step_id((first,), 'removed') == first.step_id
    assert active_step_id((), 'removed') is None
    calls=[]
    owner=SimpleNamespace(_steps=(first,second),_active_step_id=first.step_id,refresh=lambda:calls.append('render'))
    FormulaReferencePanel._select_step(owner,1)
    assert owner._active_step_id=='second' and calls==['render']
    FormulaReferencePanel._select_step(owner,2)
    assert calls==['render'] and first.result_value==second.result_value==1.23456789


def test_unrelated_page_refresh_keeps_open_disclosures_and_selection():
    """Equal frozen data must not destroy active controls during a deferred reflow."""
    step = example()
    def destroyed():
        raise AssertionError('Unchanged content must remain mounted')
    owner = SimpleNamespace(_content=SimpleNamespace(winfo_children=destroyed),
        _content_available=lambda:True, _step_provider=lambda:(step,),
        _active_step_id=step.step_id, _rendered_signature=((step,), step.step_id))
    FormulaReferencePanel.refresh(owner)
    assert owner._active_step_id == step.step_id


def test_unavailable_result_drops_destroyed_step_controls(monkeypatch):
    """A failed empirical estimate must show empty state, never retained design controls."""
    import ui.widgets.formula_view as view
    class Empty:
        def __init__(self,*args,**kwargs): pass
        def grid(self,**kwargs): pass
    monkeypatch.setattr(view,'EmptyState',Empty)
    owner=SimpleNamespace(_content=SimpleNamespace(winfo_children=lambda:[]),
        _content_available=lambda:False, _step_provider=lambda:(_ for _ in ()).throw(AssertionError()),
        _steps=(example(),), _disclosures=[object()], _step_regions={'result':[object()]},
        _formula_strips=[], _equation_images=[], _formula_asset_images=[], _section_marker_images=[])
    FormulaReferencePanel.refresh(owner)
    assert owner._steps==() and owner._disclosures==[] and owner._step_regions=={}


def test_historical_wiring_is_snapshot_only_and_visibly_readonly():
    source=(ROOT/'ui/dialogs/calculation_history.py').read_text(encoding='utf-8')
    assert 'step_provider=lambda:snapshot.formula_steps' in source
    assert 'module_key=snapshot.module_code.value, historical=True' in source
    assert 'Geçmiş Kayıt' in TR['formula.visual.historical'] and 'Salt Okunur' in TR['formula.visual.historical']


def test_turkish_chrome_is_localized_and_only_selected_step_renders():
    for key in ('formula.view_title','formula.visual.previous','formula.visual.next','formula.visual.historical'):
        assert TR[key] and EN[key]
        assert not any(word in TR[key] for word in ('History','Read only','Previous','Next','Formula View'))
    source=(ROOT/'ui/widgets/formula_view.py').read_text(encoding='utf-8')
    assert 'render_step(self, selected, 1)' in source
    assert 'self._step_selector.current(index)' in source
    assert 'self._previous.configure(state=' in source and 'self._next.configure(state=' in source
    assert 'watermark' not in source.lower()
    renderer=(ROOT/'ui/widgets/formula_steps.py').read_text(encoding='utf-8')
    assert "section.details or section.key == 'source'" in renderer
    assert 'step_asset_names(step)' in renderer and 'QUARANTINED_ASSETS' in renderer
