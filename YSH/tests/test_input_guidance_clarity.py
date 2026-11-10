"""Focused localized guidance and empty-state geometry, without calculation edits."""
import pytest

from i18n.messages_tr import MESSAGES as TR
from i18n.messages_en import MESSAGES as EN
from .test_fire_phase5cd_navigation import application, shell
from .test_ui_consistency_phase7 import review_language, descendants, assert_horizontal_bounds


@pytest.mark.parametrize('catalogue',[TR,EN],ids=['tr','en'])
def test_guidance_catalogues_are_complete_short_and_user_facing(catalogue):
    keys={key for key in TR if key.startswith('guidance.')}
    assert keys=={key for key in EN if key.startswith('guidance.')}
    assert len(keys)>=20
    for key in keys:
        text=catalogue[key]
        assert text and text!=key and len(text)<=120
        assert '\n' not in text and 'UUID' not in text and 'SOURCE_' not in text
    assert '3' in catalogue['fire.ui.percent_help']


@pytest.mark.parametrize('size',[(1100,700),(1440,900)])
@pytest.mark.parametrize('language',['tr','en'])
def test_helpers_empty_messages_and_geometry(shell,size,language):
    w=shell;root=w._root;old=w._localization.language
    catalogue=TR if language=='tr' else EN
    try:
        review_language(w,language);root.deiconify();root.geometry(f'{size[0]}x{size[1]}');root.update()
        tested=set()
        for family in ('fuel','fire'):
            w._show_family(family,dirty=False);root.update()
            host=w._page_host if family=='fuel' else w._fire_workspace.host
            for key,viewport in host._page_keys.items():
                host.select(viewport);viewport.canvas.yview_moveto(0);root.update()
                page=w._pages[key] if family=='fuel' else w._fire_workspace.views[key]
                hinted=[]
                for owner in (page,*descendants(page)):
                    hinted.extend(getattr(owner,'_guidance_widgets',()))
                assert hinted,key
                for widget,text_key in hinted:
                    tooltip=widget._guidance_tooltip
                    assert tooltip._text==catalogue[text_key]
                    before=(id(tooltip),widget.bind('<Enter>'))
                    page.refresh_texts();root.update()
                    assert (id(widget._guidance_tooltip),widget.bind('<Enter>'))==before
                widget=next(widget for widget,_ in hinted if widget.winfo_ismapped())
                tooltip=widget._guidance_tooltip
                tooltip._hide();tooltip._show();root.update()
                window=tooltip._window
                assert window is not None and window.winfo_viewable()
                assert window.winfo_children()[0].cget('text')==tooltip._text
                assert window.winfo_rootx()>=root.winfo_rootx()
                assert window.winfo_rootx()+window.winfo_width()<=root.winfo_rootx()+root.winfo_width()
                assert window.winfo_rooty()+window.winfo_height()<=root.winfo_rooty()+root.winfo_height()
                tooltip._hide();root.update()
                if key=='pipe_design':
                    assert page._pipe_result_empty_state._body.cget('text')==catalogue['guidance.empty.pipe']
                    assert page._wall_empty_result.cget('text')==catalogue['guidance.empty.pipe_wall']
                elif key=='transfer_pump':
                    assert page._result_empty_state._body.cget('text')==catalogue['guidance.empty.transfer_empirical']
                    assert page._design_panel._empty_result.cget('text')==catalogue['guidance.empty.transfer_design']
                    assert page._design_panel._labels['pump_capacity'].cget('text')==catalogue['transfer.design.pump_capacity.label']
                    assert page._design_panel._labels['pump_capacity']._guidance_tooltip._text==catalogue['guidance.optional_capacity']
                elif key=='discharge_head_loss':
                    assert page._result_empty_state._body.cget('text')==catalogue['guidance.empty.discharge']
                elif key=='suction_npsh':
                    assert page._result_empty_state._body.cget('text')==catalogue['guidance.empty.suction']
                    assert page._field_label_required[0]._guidance_tooltip._text==catalogue['guidance.optional_npshr']
                else:
                    assert page.empty_result.cget('text')==catalogue['guidance.empty.'+key]
                    if key=='foam':assert page.concentration_help.cget('text')==catalogue['fire.ui.percent_help']
                assert_horizontal_bounds(descendants(page),viewport.canvas)
                tested.add(key)
        assert len(tested)==6
    finally:w._localization.set_language(old)
