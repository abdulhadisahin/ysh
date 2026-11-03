"""Real Fire and shared Library widgets with explicit synthetic reference data."""
from types import SimpleNamespace

import pytest

from engineering.fire.library import FireParameter
from engineering.fire.enums import FireSourceStatus
from i18n.translator import Translator
from ui.dialogs.engineering_library_workspace import EngineeringLibraryWorkspace
from .test_fire_phase6_library import library, record
from .test_fire_phase5_live_ui import live, fill_view


def test_empty_library_keeps_manual_fields_blank_and_source_required(live,library):
    _,page,_,_=live;service,_=library;page._library_provider=lambda:service
    view=page.views['foam'];panel=view.library_panel;panel.refresh()
    assert all(v.get()=='' for v in view.variables.values())
    assert all('—' in label['text'] and view.tr('fire.ui.source.SOURCE_REQUIRED') in label['text'] for label in panel.summaries.values())
    assert not page.model.library_inputs.links


def test_multiple_matches_require_selection_then_override_stale_keep_update(live,library):
    root,page,saved,_=live;service,_=library;page._library_provider=lambda:service
    first=record(library);record(library,value=7)
    view=page.views['foam'];panel=view.library_panel
    fill_view(view,('210','','30','3'));panel.context.set('TEST_ONLY');panel.refresh()
    box=panel.boxes['application_density_lpm_m2']
    assert len(box['values'])==2 and box.get()==''
    assert view.variables['application_density_lpm_m2'].get()==''
    panel.action('application_density_lpm_m2','use')
    assert not page.model.library_inputs.links
    box.set(next(key for key,value in panel.choices['application_density_lpm_m2'].items() if value.id==first.id))
    panel.action('application_density_lpm_m2','use');view.calculate()
    assert page.model.results['foam'].domain_result.foam_concentrate_volume_l==945
    view.variables['application_density_lpm_m2'].set('6')
    view.meta_vars['application_density_lpm_m2']['reason'].set('TEST_ONLY project override');view.calculate()
    result=page.model.results['foam'];snapshot=page.model.snapshots['foam']
    assert result.domain_result.solution_flow_lpm==1260
    values=service.form_values('fire_foam_rate',first);values['value']=8;service.save('fire_foam_rate',values,first.id)
    page.refresh_library()
    assert page.model.results['foam'] is result and page.model.snapshots['foam'] is snapshot
    assert view.tr('fire.library.stale') in panel.summaries['application_density_lpm_m2']['text']
    panel.action('application_density_lpm_m2','keep')
    assert page.model.results['foam'] is result and page.model.library_inputs.links['application_density_lpm_m2'].revision==1
    panel.action('application_density_lpm_m2','update')
    assert view.variables['application_density_lpm_m2'].get()=='6'
    assert page.model.library_inputs.links['application_density_lpm_m2'].revision==2
    view.calculate();assert page.model.results['foam'].domain_result.solution_flow_lpm==1260
    assert saved[-2].to_json()==snapshot.to_json()


def test_concentration_library_percent_and_single_low_value_warning(live,library):
    _,page,_,_=live;service,_=library;page._library_provider=lambda:service
    record(library,FireParameter.CONCENTRATION,.03)
    view=page.views['foam'];panel=view.library_panel
    fill_view(view,('210','5','30',''));panel.context.set('TEST_ONLY');panel.refresh()
    panel.boxes['foam_fraction'].current(0);panel.action('foam_fraction','use')
    assert float(view.variables['foam_fraction'].get())==3
    view.variables['foam_fraction'].set('6');view.meta_vars['foam_fraction']['reason'].set('TEST_ONLY concentrate override');view.calculate()
    assert page.model.results['foam'].domain_result.input.foam_fraction==.06
    view.variables['foam_fraction'].set('0,03')
    assert len(view.clarifications)==1 and not view.concentration_help.grid_info()
    assert view.variables['foam_fraction'].get()=='0,03'


@pytest.mark.parametrize('language',['tr','en'])
def test_shared_library_editor_has_no_duplicate_family_and_saves_valid_source(live,library,language):
    root,_,_,_=live;service,source=library
    owner=SimpleNamespace(register_localizable=lambda *_:None,unregister_localizable=lambda *_:None)
    tr=Translator(language).translate
    window=EngineeringLibraryWorkspace(root,service,tr,owner,'fire_foam_rate')
    try:
        window._new()
        assert not {'system_family','system_type','family'}.intersection(window._edit_vars)
        assert window._controller.draft['unit']=='L/(min·m²)'
        assert tr('library2.field.context') in ('Uygulanabilirlik / Alt sistem (isteğe bağlı)','Applicability / Subsystem (optional)')
        window._edit_vars['value'].set('5')
        window._edit_vars['context'].set('TEST_ONLY')
        window._edit_vars['applicability'].set('TEST_ONLY source scope')
        for field,target in (('source_id',source.id),('source_status',FireSourceStatus.SOURCE_VERIFIED_CONTEXT_DEPENDENT)):
            window._edit_vars[field].set(next(label for label,value in window._edit_choices[field].items() if value==target))
        window._save()
        assert len(service.list_records('fire_foam_rate'))==1
        assert service.list_records('fire_foam_rate')[0].system_family=='fire'
    finally:
        window.destroy()


@pytest.mark.parametrize('size',[(1100,700),(1280,800),(1440,900),(1700,1000)])
@pytest.mark.parametrize('language',['tr','en'])
def test_source_controls_fit_four_sizes(live,library,size,language):
    root,page,_,_=live;service,_=library;page._library_provider=lambda:service
    page.tr=Translator(language).translate
    root.deiconify();root.geometry(f'{size[0]}x{size[1]}')
    page.pack_forget();page.place(x=300,y=150,width=size[0]-320,height=size[1]-180)
    for kind in ('foam','hw'):
        view=page.views[kind];view.tr=page.tr;view.refresh_texts()
        page.host.select(page.host._page_keys[kind]);view.library_panel.details.toggle();root.update()
        canvas=page.host._page_keys[kind].canvas;edge=canvas.winfo_rootx()+canvas.winfo_width()
        widgets=list(view.library_panel.boxes.values())+[view.library_panel.context_entry]
        for widget in widgets:
            assert widget.winfo_rootx()+widget.winfo_width()<=edge+2
        for label in view.library_panel.summaries.values():
            assert label.winfo_rootx()+label.winfo_width()<=edge+2
        assert all(label['wraplength']>0 for label in view.library_panel.summaries.values())
        view.library_panel.details.toggle()


@pytest.mark.parametrize('size',[(1100,700),(1280,800),(1440,900),(1700,1000)])
def test_fire_library_category_and_editor_fit_shared_window(live,library,size):
    from tkinter import ttk, font
    root,_,_,_=live;service,_=library
    owner=SimpleNamespace(register_localizable=lambda *_:None,unregister_localizable=lambda *_:None)
    window=EngineeringLibraryWorkspace(root,service,Translator('tr').translate,owner,'fire_foam_rate')
    try:
        window.geometry(f'{size[0]}x{size[1]}');window.update()
        assert window._navigation.exists('group:fire')
        nav=window._navigation
        face=font.Font(root=window,font=ttk.Style(window).lookup('LibraryNav.Treeview','font') or 'TkDefaultFont')
        for code in ('fire_foam_rate','fire_foam_duration','fire_foam_concentration','fire_hw'):
            assert face.measure(nav.item(code,'text'))+32<=int(nav.column('#0','width'))
        window._new();window.update()
        for entry in window._body.winfo_children():
            if entry.winfo_class() in ('TEntry','TCombobox'):
                assert entry.winfo_x()+entry.winfo_width()<=window._body.winfo_width()+2
    finally:window.destroy()
