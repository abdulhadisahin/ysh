"""Presentation follows the locked family; old engineering metadata stays intact."""
from uuid import uuid4
import pytest

from services.engineering_catalog_service import EngineeringCatalogService
from services.system_context_service import DEFAULT_SYSTEMS, reference
from repositories.v2_models import Circuit
from engineering.system_context import SystemContext
from ui.widgets.engineering_selection import EngineeringSelectionForm
from .test_fire_phase5cd_navigation import application, shell
from .test_project_engineering_context import chosen
from ._tk_geometry import settle_geometry


@pytest.mark.parametrize('family',['fuel','fire','seawater'])
@pytest.mark.parametrize('size',['1100x700','1440x900'])
def test_locked_identity_hides_legacy_fuel_and_preserves_page_data(shell,family,size):
    w=shell;root=w._root;root.deiconify();root.geometry(size)
    assert w._create_project('Pipe identity '+str(uuid4()),'','',''+family)
    page=w._pipe_design_page
    assert not hasattr(page,'_line_role_box') and not hasattr(page,'_line_role_label')
    assert not hasattr(page,'_circuit_box')
    page._select_line_role('SUCTION')
    page._fields['c'].set('0.73')
    before=page.export_state()
    w._refresh_family_selector()
    assert page.export_state()==before
    assert page._project_circuit_display.get()==w._translate('project.family.'+family)
    if family=='seawater':assert 'Yakıt' not in page._project_circuit_display.get()
    project=w._active_project
    assert w._save_project()
    w._project_persistence_service.close();w._active_project=None
    w._activate_project(project);root.update()
    assert page.export_state()['line_role']=='SUCTION'
    assert page._fields['c'].get()=='0.73'
    assert page._project_circuit_display.get()==w._translate('project.family.'+family)
    if family!='fire':
        tab=w._page_host._page_keys['pipe_design'];w._page_host.select(tab);tab.canvas.yview_moveto(0)
        settle_geometry(root,page._project_circuit_label)
        label=page._project_circuit_label
        assert label.winfo_rootx()+label.winfo_width()<=root.winfo_rootx()+root.winfo_width()


def test_only_valid_circuit_from_locked_system_is_displayed(shell):
    w=shell
    assert w._create_project('Circuit validation '+str(uuid4()),'','','seawater')
    from repositories.v2_models import System
    service=w._system_context_service
    system=System(code='SEA_WATER',name_tr='Deniz Suyu')
    service._system_repository.create(system)
    circuit=service._circuit_repository.create(Circuit(system_id=system.id,code='TEST_SEA',name_tr='Yardımcı Deniz Suyu'))
    service.reload()
    w._apply_system_context(SystemContext(system=reference(system),circuit=reference(circuit)))
    assert 'Yardımcı Deniz Suyu' in w._pipe_design_page._project_circuit_display.get()
    fuel=next(s for s in DEFAULT_SYSTEMS if s.code=='FUEL')
    w._apply_system_context(SystemContext(system=reference(fuel),circuit=reference(circuit)))
    assert w._pipe_design_page._project_circuit_display.get()=='Yardımcı Deniz Suyu'


@pytest.mark.parametrize('module',[None,'pipe_design','discharge_head_loss','suction_npsh'])
def test_context_forms_do_not_ask_line_function_but_preserve_it(shell,module):
    w=shell;context=SystemContext(line_type='DELIVERY',service='SEA_WATER_COOLING')
    form=EngineeringSelectionForm(w._root,w._engineering_context_controller.catalog,w._translate,context,module=module)
    try:
        assert 'line_type' not in form.variables
        assert form.value().line_type=='DELIVERY'
        assert form.value().service=='SEA_WATER_COOLING'
    finally:form.destroy()


def test_unknown_pipe_function_does_not_acquire_directional_criteria(library_database):
    catalog=EngineeringCatalogService(library_database)
    context=chosen(catalog,fuel='SEAWATER',line='')
    assert not any(r.line_type for r in catalog.matching_rules(context,'seawater','pipe_design'))
    assert any(r.line_type=='SUCTION' for r in catalog.matching_rules(context,'seawater','suction_npsh'))
    assert any(r.line_type=='DELIVERY' for r in catalog.matching_rules(context,'seawater','discharge_head_loss'))
