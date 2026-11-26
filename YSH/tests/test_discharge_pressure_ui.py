"""One existing density input feeds a read-only pressure equivalent."""
from uuid import uuid4
from tkinter import ttk
import pytest
from .test_fire_phase5cd_navigation import application,shell
from ._tk_geometry import settle_geometry


def prepare(w):
    assert w._create_project('Pressure '+str(uuid4()),'','','fuel')
    page=w._pages['discharge_head_loss']
    page._source_mode='manual';page._source.set(w._translate('message.manual_source'));page._set_source_mode(reset_value=False)
    for key,value in dict(d='100',q='20',nu='4',l='10',k='.015',h='0').items():page._fields[key].set(value)
    page._calculate()
    page._fields['h'].set(str(9.43-page._last_result.total_hydraulic_loss_m))
    page._calculate()
    return page,page._pressure_panel


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def test_upper_density_is_the_only_input_and_943m_gives_077bar(shell):
    page,panel=prepare(shell)
    result=page._last_result
    assert result.system_head_m==pytest.approx(9.43)
    assert panel.pressure_bar is None
    page._fields['fluid_density'].set('830')
    assert page._last_result is result
    assert panel.used_density==830
    assert panel.pressure_bar==pytest.approx(.76781889)
    assert panel.value.get()=='0,77 bar'
    assert not any(isinstance(w,(ttk.Entry,ttk.Combobox)) for w in descendants(panel))
    entries=[w for w in descendants(page) if isinstance(w,ttk.Entry) and str(w.cget('textvariable'))==str(page._fields['fluid_density'])]
    assert len(entries)==1
    assert page._engineering_panel.density_label['text']=='Yoğunluk [kg/m³]'
    for bad in ('','0','-1','nan','inf','bad'):
        page._fields['fluid_density'].set(bad)
        assert panel.pressure_bar is None and panel.value.get()=='—' and panel.reason.get()
        assert page._last_result is result
    page._calculate()
    assert page._last_result and panel.pressure_bar is None
    page._fields['fluid_density'].set('1000')
    assert panel.pressure_bar==1000*9.81*page._last_result.system_head_m/100000
    page._clear()
    assert panel.pressure_bar is None and panel.value.get()=='—'


def test_catalog_and_manual_values_use_the_same_field_and_fluid_changes_clear(shell):
    from .test_hydraulic_fluid_selection_ui import sea
    w=shell;c,f=sea(w);page=w._pages['discharge_head_loss'];panel=page._pressure_panel
    c.select_fluid('discharge_head_loss',f.id,20,35,.101325)
    page._source_mode='manual';page._set_source_mode(reset_value=False)
    for key,value in dict(d='100',q='20',nu='1.05',l='10',k='.015',h='2').items():page._fields[key].set(value)
    page._calculate()
    assert float(page._fields['fluid_density'].get())==1024.9
    assert panel.used_density==1024.9
    assert panel.pressure_bar==1024.9*9.81*page._last_result.system_head_m/100000
    context=w._system_context
    result=page._last_result
    page._fields['fluid_density'].set('830')
    assert panel.used_density==830 and page._last_result is result
    assert w._system_context==context
    page._engineering_panel.conditions['temperature'].set('40')
    assert panel.pressure_bar is None
    page.refresh_texts();assert panel.pressure_bar is None
    page._calculate()
    assert page._fields['fluid_density'].get()=='830'
    assert panel.used_density==830
    c.action('discharge_head_loss','density','reference')
    assert panel.used_density==1018.3
    assert panel.pressure_bar==1018.3*9.81*page._last_result.system_head_m/100000


@pytest.mark.parametrize('size',['1100x700','1440x900'])
@pytest.mark.parametrize('old_mode',[None,'standard','manual'])
def test_old_project_keeps_upper_density_and_ignores_lower_legacy_value(shell,size,old_mode):
    w=shell;page,panel=prepare(w)
    page._fields['fluid_density'].set('830,0')
    state=w._export_all_page_states()
    if old_mode is None:state['discharge_head_loss'].pop('pressure',None)
    else:state['discharge_head_loss']['pressure']={'mode':old_mode,'manual_density':'999'}
    w._project_persistence_service.save(state)
    project=w._active_project
    assert w._create_project('Other pressure '+str(uuid4()),'','','fuel')
    assert page._fields['fluid_density'].get()==''
    assert w._activate_project(project)
    assert page._fields['fluid_density'].get()=='830,0'
    assert panel.pressure_bar is None
    page._calculate()
    assert panel.used_density==830 and panel.value.get()=='0,77 bar'
    if old_mode:assert page.export_state()['pressure']=={'mode':old_mode,'manual_density':'999'}
    w._root.deiconify();w._root.geometry(size)
    w._page_host.select(w._page_host._page_keys['discharge_head_loss'])
    settle_geometry(w._root,page._results_card,panel)
    assert panel.winfo_ismapped()
    assert panel.winfo_rootx()>page._system_metric.winfo_rootx()
    assert panel.winfo_rootx()+panel.winfo_width()<=w._root.winfo_rootx()+w._root.winfo_width()
