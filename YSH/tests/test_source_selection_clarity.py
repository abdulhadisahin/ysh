"""Applied source vs candidate visibility; existing update/keep contracts are frozen."""
from dataclasses import replace
from uuid import uuid4
import pytest

from i18n.translator import Translator
from engineering.fire.library import FireParameter
from .test_fire_phase5_live_ui import live
from .test_fire_phase6_library import library
from .test_fire_phase6a_ui import linked_view, visible
from .test_fire_phase5cd_navigation import application, shell
from .test_discharge_v2_phase8 import source
from engineering.pipe_design.transfer import revise_selection
from ui.widgets.source_status import library_source_name


@pytest.mark.parametrize('language',['tr','en'])
def test_library_applied_name_context_target_and_explicit_update(live,library,language):
    root,page,_,_=live
    view,panel,item=linked_view(page,library,'foam','application_density_lpm_m2',FireParameter.APPLICATION_RATE,5)
    view.tr=Translator(language).translate;view.refresh_texts();name='application_density_lpm_m2'
    label=panel.summaries[name]
    assert item.source.document in label.cget('text') and item.context in label.cget('text')
    assert view.tr(view.spec[name][0]) in label.cget('text')
    assert view.tr('selection.applied') in label.cget('text')
    assert label.cget('text').count(item.source.document)==1
    assert not visible(panel.buttons[name]['update']) and not visible(panel.buttons[name]['keep'])
    panel.boxes[name].current(0);panel.sync()
    preview=panel.choice_hints[name]._text
    assert item.context in preview and view.tr(view.spec[name][0]) in preview
    assert view.tr('fire.library.use') in preview
    applied=page.model.library_inputs.links[name]
    original=view.variables[name].get()
    service,_=library;values=service.form_values('fire_foam_rate',item);values['value']=7
    service.save('fire_foam_rate',values,item.id);panel.refresh()
    assert page.model.library_inputs.links[name]==applied
    assert view.variables[name].get()==original
    assert view.tr('selection.new_revision',revision=2) in label.cget('text')
    assert visible(panel.buttons[name]['update']) and visible(panel.buttons[name]['keep'])
    assert panel.action_hints[(name,'update')]._text==view.tr('selection.library_update')
    assert panel.action_hints[(name,'keep')]._text==view.tr('selection.keep')
    panel.action(name,'keep')
    assert page.model.library_inputs.links[name]==applied and view.variables[name].get()==original
    assert label.source_stale
    panel.action(name,'update')
    assert page.model.library_inputs.links[name].revision==2 and view.variables[name].get()==original
    assert page.model.library_inputs.links[name].value==7 and label.source_override
    assert not visible(panel.buttons[name]['update']) and not visible(panel.buttons[name]['keep'])
    for text in (label.cget('text'),preview,*panel.boxes[name].cget('values')):
        assert str(item.id) not in text and str(item.id)[:8] not in text


def test_library_summary_name_is_compact_without_changing_record(library):
    from .test_fire_phase6_library import record
    item=record(library)
    long=replace(item,context='A'*120,source=replace(item.source,document='B'*120))
    name=library_source_name(long,Translator('tr').translate)
    assert len(name)<=99 and '…' in name and '\n' not in name
    assert long.context=='A'*120 and long.source.document=='B'*120


@pytest.mark.parametrize('language',['tr','en'])
def test_hw_applied_source_and_update_keep_visibility(live,language):
    from .test_fire_phase5_live_ui import selection
    root,page,_,_=live;view=page.views['hw']
    view.tr=Translator(language).translate;view.refresh_texts()
    buttons={key.rsplit('.',1)[-1]:button for button,key in view.link_buttons}
    assert not visible(buttons['update']) and not visible(buttons['keep'])
    item=selection();page.sources.publish(item);view.sync();view.pipe_action('link')
    assert not visible(buttons['update']) and not visible(buttons['keep'])
    assert view.tr('selection.applied') in view.pipe_status.cget('text')
    assert 'Di ' in view.pipe_status.cget('text') and 'Q ' in view.pipe_status.cget('text')
    applied=page.model.pipe.snapshot
    updated=revise_selection(item,replace(item,flow_rate_m3_h=item.flow_rate_m3_h+1))
    page.sources.publish(updated);page.model.observe(updated);view.sync()
    assert page.model.pipe.snapshot==applied
    assert visible(buttons['update']) and visible(buttons['keep'])
    assert view._pipe_action_hints['update']._text==view.tr('selection.pipe_update')
    assert view._pipe_action_hints['keep']._text==view.tr('selection.keep')
    view.pipe_action('keep')
    assert page.model.pipe.snapshot==applied and visible(buttons['keep'])
    view.pipe_action('update')
    assert page.model.pipe.snapshot.source_revision==updated.revision
    assert not visible(buttons['update']) and not visible(buttons['keep'])
    assert str(item.selection_id) not in view.pipe_status.cget('text')


@pytest.mark.parametrize('language',['tr','en'])
def test_pipe_summary_feeds_and_stale_applied_revision(shell,language):
    from .test_ui_consistency_phase7 import review_language
    w=shell;root=w._root;old=w._localization.language
    try:
        review_language(w,language);root.deiconify();w._show_family('fuel',dirty=False)
        tr=Translator(language).translate
        for key in ('discharge_head_loss','suction_npsh'):
            panel=w._pages[key]._pipe_source_panel;flow=panel.workflow
            item=replace(source(),selection_id=uuid4());flow.publish(item);flow.link(item.selection_id);panel.render()
            assert tr('selection.values') in panel._details.get()
            assert 'Di ' in panel._details.get() and 'Q ' in panel._details.get()
            assert 'NPS ' not in panel._details.get() and 'OD ' not in panel._details.get()
            assert panel._action_hints['update']._text==tr('selection.pipe_update')
            assert panel._action_hints['keep']._text==tr('selection.keep')
            before=flow.pipe_input.snapshot
            flow.publish(revise_selection(item,replace(item,flow_rate_m3_h=21)));panel.render()
            assert flow.pipe_input.snapshot==before
            assert tr('selection.applied') in panel._details.get()
            assert tr('discharge.pipe.revision')+' 1' in panel._details.get()
            assert panel._buttons['update'].grid_info() and panel._buttons['keep'].grid_info()
            assert str(item.selection_id) not in panel._details.get()
            assert all(str(item.selection_id)[:8] not in value for value in panel._source_box.cget('values'))
    finally:w._localization.set_language(old)
