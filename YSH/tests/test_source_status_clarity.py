"""Shared source wording and presentation consume existing workflow flags only."""
from dataclasses import replace
from uuid import uuid4
import pytest

from i18n.translator import Translator
from ui.widgets.source_status import source_text, source_style
from .test_fire_phase5cd_navigation import application, shell
from .test_fire_phase5_live_ui import live
from .test_fire_phase6_library import library
from .test_fire_phase6a_ui import linked_view
from .test_discharge_v2_phase8 import source
from engineering.fire.library import FireParameter
from engineering.pipe_design.transfer import revise_selection


@pytest.mark.parametrize('normal,override,stale,expected',[
    ('Fire.Source.Error.TLabel',True,True,'Fire.Source.Error.TLabel'),
    ('Fire.Source.Warning.TLabel',True,False,'Fire.Source.Warning.TLabel'),
    ('Info.TLabel',False,True,'SourceStatus.Stale.Info.TLabel'),
    ('Fire.Source.Verified.TLabel',True,False,'SourceStatus.Override.Fire.Source.Verified.TLabel'),
    ('Fire.Source.Muted.TLabel',False,False,'Fire.Source.Muted.TLabel'),
])
def test_status_emphasis_preserves_source_warning_priority(normal,override,stale,expected):
    assert source_style(object(),normal,override=override,stale=stale)==expected


@pytest.mark.parametrize('language',['tr','en'])
def test_one_vocabulary_without_internal_codes(language):
    tr=Translator(language).translate
    assert tr('message.manual_source')==tr('source.state.manual')==tr('fire.library.mode.manual')
    assert tr('message.material_source')==tr('source.state.library')
    assert tr('fire.library.mode.override')==tr('source.state.override')
    assert tr('fire.library.stale')==tr('source.state.stale')
    assert tr('fire.value.LINKED_STALE')==tr('discharge.pipe.status.LINKED_STALE')
    manual=source_text(tr,'manual')
    assert tr('source.state.override') not in manual
    current=source_text(tr,'library',linked=True)
    stale=source_text(tr,'library',linked=True,override=True,stale=True)
    assert tr('source.state.current') in current
    assert tr('source.state.current') not in stale.split(' · ')
    assert tr('source.state.stale') in stale and tr('source.state.override') in stale
    assert 'LINKED_' not in stale and 'SOURCE_' not in stale


@pytest.mark.parametrize('language',['tr','en'])
def test_library_override_stale_and_keep_have_distinct_native_status(live,library,language):
    root,page,_,_=live
    view,panel,item=linked_view(page,library,'foam','application_density_lpm_m2',FireParameter.APPLICATION_RATE,5)
    view.tr=Translator(language).translate;view.refresh_texts()
    label=panel.summaries['application_density_lpm_m2']
    assert not label.source_override and not label.source_stale
    view.variables['application_density_lpm_m2'].set('6')
    assert label.source_override and 'SourceStatus.Override.' in label.cget('style')
    service,_=library;values=service.form_values('fire_foam_rate',item);values['value']=7
    service.save('fire_foam_rate',values,item.id);panel.refresh()
    assert label.source_stale and 'SourceStatus.Stale.' in label.cget('style')
    applied=page.model.library_inputs.links['application_density_lpm_m2']
    panel.action('application_density_lpm_m2','keep')
    assert page.model.library_inputs.links['application_density_lpm_m2']==applied
    assert label.source_stale and 'SourceStatus.Stale.' in label.cget('style')
    panel.action('application_density_lpm_m2','update')
    assert not label.source_stale and label.source_override
    assert view.variables['application_density_lpm_m2'].get()=='6'
    panel.action('application_density_lpm_m2','manual')
    view.meta_vars['application_density_lpm_m2']['recommended'].set('')
    assert not label.source_override


def test_hw_source_choices_hide_ids_and_preserve_identity_on_reordering(live,monkeypatch):
    root,page,_,_=live;view=page.views['hw']
    first=replace(source(),selection_id=uuid4());second=replace(first,selection_id=uuid4())
    choices=[first,second]
    monkeypatch.setattr(page.sources,'available',lambda:tuple(choices))
    view.sync();labels=tuple(view.source_choices_pipe)
    assert len(labels)==2 and labels[0]!=labels[1]
    for label in labels:
        for item in choices:
            assert str(item.selection_id) not in label and str(item.selection_id)[:8] not in label
    view.source_var.set(labels[1]);before=page.model.pipe
    choices.reverse();view.sync()
    assert view.source_choices_pipe[view.source_var.get()].selection_id==second.selection_id
    assert page.model.pipe==before


@pytest.mark.parametrize('language',['tr','en'])
def test_fuel_link_current_stale_keep_update_wording(shell,language):
    from .test_ui_consistency_phase7 import review_language
    w=shell;root=w._root;old=w._localization.language
    try:
        review_language(w,language);root.deiconify();w._show_family('fuel',dirty=False)
        tr=Translator(language).translate
        for key in ('pipe_design','discharge_head_loss','suction_npsh'):
            page=w._pages[key]
            selector=page._roughness_source_box if key=='suction_npsh' else page._source_box
            assert tuple(map(str,selector.cget('values')))==(tr('source.state.library'),tr('source.state.manual'))
        design=w._pages['transfer_pump']._design_panel
        design._fields['volume'].set('100');design._fields['target_time'].set('2');design.calculate()
        assert tr('result.source_manual') in design._status.get()
        for key in ('discharge_head_loss','suction_npsh'):
            page=w._pages[key];panel=page._pipe_source_panel;workflow=panel.workflow
            item=replace(source(),selection_id=uuid4());workflow.publish(item);workflow.link(item.selection_id);panel.render()
            assert tr('source.state.current') in panel._status.get()
            applied=workflow.pipe_input.snapshot
            workflow.publish(revise_selection(item,replace(item,flow_rate_m3_h=21)));panel.render()
            assert workflow.pipe_input.snapshot==applied
            assert tr('source.state.stale') in panel._status.get()
            assert str(panel._status_label.cget('style')).startswith('SourceStatus.Stale.')
            panel._buttons['keep'].invoke();panel.render()
            assert workflow.pipe_input.snapshot==applied
            assert tr('source.state.stale') in panel._status.get()
            panel._buttons['update'].invoke();panel.render()
            assert tr('source.state.current') in panel._status.get()
            assert not str(panel._status_label.cget('style')).startswith('SourceStatus.Stale.')
    finally:w._localization.set_language(old)
