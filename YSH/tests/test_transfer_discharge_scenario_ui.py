"""Native inputs, invalidation, isolation, persistence and scenario geometry."""
from uuid import uuid4
import pytest
from .test_fire_phase5cd_navigation import application,shell
from ._tk_geometry import settle_geometry


def page_and_scenario(w):
    assert w._create_project('Scenario '+str(uuid4()),'','','fuel')
    page=w._transfer_pump_page
    return page,page._discharge_115


def test_scenario_is_explicit_not_total_capacity_or_required_design_flow(shell):
    page,scenario=page_and_scenario(shell)
    page._capacity.set('5000')
    design=page._design_panel
    design._fields['volume'].set('240');design._fields['target_time'].set('12');design._fields['pump_capacity'].set('80')
    design.calculate()
    original=design._last_result
    assert original.required_flow_m3_h==20
    assert scenario.export_state()=={'volume':'','nominal':''}
    scenario.fields['volume'].set('230');scenario.fields['nominal'].set('100')
    scenario.calculate()
    assert scenario.result.scenario_flow_m3_h==pytest.approx(115)
    assert scenario.result.duration_h==pytest.approx(2)
    assert scenario.flow.get()=='115,00' and scenario.duration.get()=='2,00'
    assert design._last_result is original
    assert page._capacity.get()=='5000'
    scenario.fields['volume'].set('460')
    assert scenario.result is None and scenario.duration.get()=='—'
    scenario.calculate();assert scenario.result.duration_h==pytest.approx(4)
    scenario.fields['nominal'].set('200')
    assert scenario.result is None and scenario.flow.get()=='—'
    scenario.clear()
    assert scenario.export_state()=={'volume':'','nominal':''}
    assert design._last_result is original


@pytest.mark.parametrize('field,text',[('volume',''),('volume','0'),('volume','bad'),('nominal',''),('nominal','-1'),('nominal','inf')])
def test_invalid_scenario_does_not_replace_existing_transfer_result(shell,field,text):
    page,scenario=page_and_scenario(shell)
    scenario.fields['volume'].set('230');scenario.fields['nominal'].set('100');scenario.calculate()
    assert scenario.result
    scenario.fields[field].set(text)
    assert scenario.result is None
    scenario.calculate()
    assert scenario.result is None and scenario.message.get()
    assert scenario.labels[field]['text'] in scenario.message.get()
    assert scenario.flow.get()==scenario.duration.get()=='—'


@pytest.mark.parametrize('size',['1100x700','1440x900'])
def test_project_roundtrip_and_geometry(shell,size):
    w=shell;page,scenario=page_and_scenario(w)
    scenario.fields['volume'].set('230,0');scenario.fields['nominal'].set('100,0');scenario.calculate()
    assert w._save_project()
    project=w._active_project
    assert w._create_project('Other scenario '+str(uuid4()),'','','fuel')
    assert scenario.export_state()=={'volume':'','nominal':''}
    assert w._activate_project(project)
    assert scenario.export_state()=={'volume':'230,0','nominal':'100,0'}
    assert scenario.result is None
    scenario.calculate();assert scenario.result.duration_h==pytest.approx(2)
    w._root.deiconify();w._root.geometry(size)
    w._page_host.select(w._page_host._page_keys['transfer_pump'])
    settle_geometry(w._root,scenario,scenario.result_card)
    assert scenario.winfo_ismapped()
    right=w._root.winfo_rootx()+w._root.winfo_width()
    for widget in (scenario.result_card,scenario.calculate_button,scenario.entries['nominal']):
        assert widget.winfo_rootx()+widget.winfo_width()<=right
