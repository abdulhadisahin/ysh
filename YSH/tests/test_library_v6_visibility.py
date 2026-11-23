"""Existing v6 catalog is discoverable through native Library/project entry points."""
from uuid import uuid4
import pytest
from .test_fire_phase5cd_navigation import application,shell
from .test_project_engineering_context import chosen
from ._tk_geometry import settle_geometry
from services.library_catalog import VISIBLE_CATEGORIES as CATEGORIES


def labels(widget):
    result=[]
    for child in widget.winfo_children():
        try:result.append(str(child.cget('text')))
        except Exception:pass
        result.extend(labels(child))
    return result


def open_library(w,category):
    w._open_engineering_library(category)
    window=w._library_window
    window.deiconify();w._root.update()
    return window


@pytest.mark.parametrize('language',['tr','en'])
def test_visible_catalog_navigation_fluid_details_and_distinct_rules(shell,language):
    w=shell;root=w._root;root.deiconify();old=w._localization.language
    w._localization.set_language(language)
    window=open_library(w,'fluids')
    try:
        window.geometry('1100x700');settle_geometry(root,window,window._navigation)
        for group in ('materials','fluids','pipes','engineering_rules','constants','corrosion'):
            assert window._navigation.exists('group:'+group)
        assert all(window._navigation.exists(c.code) for c in CATEGORIES)
        assert window._navigation.item('group:engineering_rules','text')==w._translate('library2.group.engineering_rules')
        fluid=next(r for r in window._controller.records if r.code=='F76')
        window._tree.selection_set(str(fluid.id));window._select_record();root.update()
        text='\n'.join(labels(window._body))
        assert 'MIL-DTL-16884R' in text
        for value in ('800','876','838','1,70','4,30','3,00'):assert value in text
        assert w._translate('engineering.method.DERIVED_MIDPOINT') in text
        assert w._translate('engineering.property.density') in text
        assert w._translate('engineering.property.kinematic_viscosity') in text
        f44=next(r for r in window._controller.records if r.code=='F44')
        window._tree.selection_set(str(f44.id));window._select_record();root.update()
        f44_text='\n'.join(labels(window._body))
        assert 'MIL-DTL-5624X' in f44_text and '-20' in f44_text
        assert w._translate('engineering.method.SOURCE_REQUIRED') in f44_text
        assert str(window._buttons['edit']['state'])=='disabled'
        window._navigation.selection_set('group:engineering_rules');window._choose_navigation();root.update()
        assert window._controller.category=='engineering_rules'
        rules={r.code:r for r in window._controller.records}
        assert len(rules)==23
        for code in ('D243_FUEL_MAX','EVERLLENCE_DIESEL_FUEL_DELIVERY','TL_FFS_DELIVERY','BALLAST','BILGE'):
            row=window._tree.item(str(rules[code].id),'values')
            assert row[0]==rules[code].name
        d243=window._tree.item(str(rules['D243_FUEL_MAX'].id),'values')
        assert '7' in d243[1] and d243[3]=='D243'
        assert window._tree.item(str(rules['TL_FFS_DELIVERY'].id),'values')[3]=='Türk Loydu'
        assert window._tree.item(str(rules['BALLAST'].id),'values')[1]==w._translate('engineering.status.SOURCE_REQUIRED')
        window.show_category('material_surfaces');root.update()
        assert len(window._controller.records)==10
        surface=next(r for r in window._controller.records if r.code=='CARBON_NEW')
        values=window._tree.item(str(surface.id),'values')
        assert 'mm' in values[1] and values[2]=='Carbon Steel' and values[3]=='NEW_COMMERCIAL'
        assert w._translate('engineering.property.absolute_roughness')==window._tree.heading('value','text')
    finally:
        window.destroy();w._localization.set_language(old)


def test_menu_context_inheritance_reopen_and_readonly_browsing(shell):
    from repositories.fluid_repository import FluidRepository
    from repositories.v2_models import Fluid
    w=shell;c=w._engineering_context_controller
    fluid=FluidRepository(c.catalog.rules._database).create(Fluid(code='USER_'+uuid4().hex,name_tr='User retained record'))
    assert w._create_project('Catalog access '+str(uuid4()),'','','fuel')
    assert w._project_menu.entrycget(2,'label')==w._translate('context.open_editor')
    before=set(w._root.winfo_children());w._project_menu.invoke(2);w._root.update()
    dialogs=[x for x in w._root.winfo_children() if x not in before]
    assert any(x.winfo_class()=='Toplevel' and x.title()==w._translate('engineering.context_title') for x in dialogs)
    for x in dialogs:x.destroy()
    c.apply(chosen(c.catalog))
    assert c.read('discharge_head_loss','kinematic_viscosity')==3
    assert c.read('discharge_head_loss','absolute_roughness')==.045
    page=w._pages['discharge_head_loss'];page._fields['k'].set('.1')
    c.apply(w._system_context.changed(service='DIESEL_FUEL_DELIVERY'))
    assert c.read('discharge_head_loss','absolute_roughness')==.1
    database=c.catalog.rules._database
    def counts():
        with database.connection() as conn:
            return {t:conn.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('fluids','fluid_specifications','material_surfaces','engineering_rules','sources','fluid_properties','material_properties')}
    initial=counts()
    for _ in range(2):
        # Menu entries reuse the accepted workspace, never seed or copy records.
        w._library_menu.invoke(4);window=w._library_window;w._root.update()
        assert window._controller.category=='fluids'
        assert fluid in window._controller.records
        w._library_menu.invoke(5);assert window._controller.category=='engineering_rules'
        window.destroy()
    assert counts()==initial
    assert initial['fluid_properties']==initial['material_properties']==initial['sources']==0
    source=__import__('pathlib').Path(__file__).parents[1]/'ui/dialogs/engineering_library_workspace.py'
    assert 'NATO F-76' not in source.read_text(encoding='utf-8')
