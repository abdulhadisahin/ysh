"""Native material selectors and warning colours at the two accepted sizes."""
from uuid import uuid4
import pytest
from .test_fire_phase5cd_navigation import application, shell
from ._tk_geometry import settle_geometry


@pytest.mark.parametrize('size',['1100x700','1440x900'])
def test_material_roughness_controls_restore_and_fit(shell,size):
    w=shell
    assert w._create_project('Roughness '+str(uuid4()),'','','fuel')
    w._root.deiconify();w._root.geometry(size)
    for module,source_name,field in [('discharge_head_loss','_source_box','k'),('suction_npsh','_roughness_source_box','roughness')]:
        page=w._pages[module]
        w._page_host.select(w._page_host._page_keys[module])
        w._engineering_context_controller.refresh_labels()
        source=getattr(page,source_name)
        source.current(0)
        if module=='discharge_head_loss':page._select_source_mode()
        else:page._select_roughness_source()
        label=next(iter(page._material_ids))
        page._material.set(label);page._load_selected_roughness()
        material=page._materials.get_material(page._material_ids[label])
        assert float(page._fields[field].get())==material.roughness_mm
        assert str(page._roughness_entry['state'])=='readonly'
        settle_geometry(w._root,page,source,page._material_box,page._roughness_entry)
        for widget in (source,page._material_box,page._roughness_entry):
            assert widget.winfo_ismapped()
            assert widget.winfo_rootx()+widget.winfo_width()<=w._root.winfo_rootx()+w._root.winfo_width()
        assert source['values'][0]=='Standart'
        if module=='discharge_head_loss':
            for key,value in dict(d='100',q='20',nu='4',l='10',h='2').items():page._fields[key].set(value)
            page._calculate()
            assert page._last_result.input.roughness_mm==material.roughness_mm
        else:
            for key,value in dict(diameter='100',flow='20',viscosity='4',length='10').items():page._fields[key].set(value)
            page._calculate_suction_loss()
            assert page._last_loss.input.roughness_mm==material.roughness_mm
        standard=page.export_state()
        source.current(1)
        if module=='discharge_head_loss':page._select_source_mode()
        else:page._select_roughness_source()
        page._fields[field].set('.123')
        manual=page.export_state()
        assert str(page._roughness_entry['state'])=='normal'
        page.load_state(standard)
        assert float(page._fields[field].get())==material.roughness_mm
        page.load_state(manual)
        assert float(page._fields[field].get())==.123
    state=w._export_all_page_states()
    w._project_persistence_service.save(state)
    project=w._active_project
    assert w._activate_project(project)
    assert w._pages['discharge_head_loss']._fields['k'].get()=='.123'
    assert w._pages['suction_npsh']._fields['roughness'].get()=='.123'


def test_historical_warning_styles_are_actually_used(shell):
    from engineering.catalog_seeds import d243_rule
    from engineering.rule_evaluation import evaluate_rule
    from ui.widgets.engineering_components import StatusBadge
    panel=shell._pages['pipe_design']._warning_panel
    for velocity,style in [(7.1,'EngineeringWarningTitle.TLabel'),(8.,'EngineeringCriticalWarningTitle.TLabel'),(99.,'EngineeringBlackWarningTitle.TLabel')]:
        panel.set_findings(evaluate_rule(d243_rule(),velocity))
        badge=next(w for w in panel.winfo_children() if isinstance(w,StatusBadge))
        assert badge['style']==style
    panel.set_findings(())
    assert not panel.winfo_children()


def test_pipe_direct_stress_nominal_result_and_saved_basis(shell):
    w=shell
    assert w._create_project('Wall scope '+str(uuid4()),'','','seawater')
    page=w._pages['pipe_design']
    materials=page._service._materials
    from engineering.pipe_design.wall_standards import cuni_wall_material
    alloy=cuni_wall_material()
    assert alloy in page._service.get_all_materials(system_family='seawater')
    stainless=materials.create_material(name='Stainless test',designation='316L',yield_strength_mpa=200.,roughness_mm=.045)
    page._load_materials()
    page._source_box.current(0);page._set_source_mode()
    page._material.set(next(label for label,identity in page._material_ids.items() if identity==alloy.id))
    page._load_selected_material()
    for key,value in {'da':'159','pc':'8','sf':'1.8','wf':'1','c':'.5','temperature':'50'}.items():page._fields[key].set(value)
    page._calculate_wall()
    assert page._wall_result, page._message.get()
    assert page._wall_result['allowable_stress_mpa']==68
    assert '8.7' in page._wall_standard_text.get()
    assert 'nominal' in page._wall_standard_text.get()
    assert '50' in page._wall_standard_text.get()
    state=page.export_state()
    assert state['source_mode']=='Kütüphane'  # Stored legacy identity, not the new label.
    page.clear_state();page.load_state(state)
    assert page._wall_result['allowable_stress_mpa']==68
    stress=next(s for s in page._formula_steps() if s.step_id=='pipe.stress')
    assert stress.formula_text=='σallow = 68 MPa'
    page._fields['temperature'].set('100')
    assert not page._wall_result
    page._calculate_wall()
    assert not page._wall_result
    assert '75' in page._message.get()
    page._material.set(next(label for label,identity in page._material_ids.items() if identity==stainless.id))
    page._load_selected_material();page._fields['da'].set('168.3');page._fields['temperature'].set('')
    page._calculate_wall()
    assert page._wall_result, page._message.get()
    assert page._wall_result['allowable_stress_mpa']==200/1.8
    assert page._wall_result['selected_standard_wall_thickness_mm']==2.6
    assert 'ISO 4200:1991' in page._wall_standard_text.get()
    assert '8.6' in page._wall_standard_text.get()
    w._page_host.select(w._page_host._page_keys['pipe_design'])
    for size in ('1100x700','1440x900'):
        w._root.deiconify();w._root.geometry(size)
        settle_geometry(w._root,page,page._wall_result_card,page._standard_wall_value)
        assert page._standard_wall_value.winfo_rootx()>page._wall_metric_value.winfo_rootx()
        assert page._standard_wall_details.winfo_rootx()+page._standard_wall_details.winfo_width()<=w._root.winfo_rootx()+w._root.winfo_width()
