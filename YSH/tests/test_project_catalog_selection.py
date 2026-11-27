"""Real new-project/catalog selections, explicit module overrides and frozen identity."""
from uuid import uuid4
import json
import pytest
from .test_fire_phase5cd_navigation import application,shell
from .test_project_engineering_context import chosen
from ._tk_geometry import settle_geometry
from engineering.catalog_seeds import identity


def choose(form,name,value):
    form.variables[name].set(next(label for label,record in form.choices[name].items() if record==value))
    if name=='material':form._material_changed()


def new_context(w):
    assert w._create_project('Linked selections '+str(uuid4()),'','','fuel')
    c=w._engineering_context_controller;c.apply(chosen(c.catalog))
    return c


@pytest.mark.parametrize('size',[(1100,700),(1440,900)])
def test_real_new_fuel_project_collects_and_persists_catalog_choices(shell,monkeypatch,size):
    import ui.main_window as main
    from ui.dialogs.new_project_dialog import NewProjectDialog
    w=shell;root=w._root;root.deiconify();root.geometry(f'{size[0]}x{size[1]}');root.update()
    catalog=w._engineering_context_controller.catalog
    f76=next(r for r in catalog.fluid_records if r.code=='F76')
    callback_errors=[]
    def factory(*args,**kwargs):
        dialog=NewProjectDialog(*args,**kwargs)
        dialog._name_entry.insert(0,'Initial context '+str(uuid4()))
        dialog._family_choice.choice.current(0);dialog._refresh_fluids()
        assert {r.id for r in dialog._fluid_records.values() if r}=={r.id for r in catalog.project_fluids('fuel')}
        dialog._fluid_choice.set(next(label for label,r in dialog._fluid_records.items() if r and r.id==f76.id))
        root.update_idletasks()
        assert dialog._dialog.winfo_reqheight()<=size[1]
        def submit():
            try:dialog._submit()
            except BaseException as error:
                callback_errors.append(error);dialog._cancel()
        root.after(0,submit)
        return dialog
    monkeypatch.setattr(main.messagebox,'showerror',lambda *a,**k:pytest.fail('New-project flow failed: '+str(a)))
    monkeypatch.setitem(w._open_new_project.__func__.__globals__,'NewProjectDialog',factory)
    w._open_new_project()
    assert not callback_errors,callback_errors
    assert w._active_project and w._system_context.fluid.id==f76.id
    assert w._system_context.surface_profile_id is None
    assert w._system_context.material_id is None and w._system_context.rule_set_id is None
    assert w._system_context.service=='' and w._system_context.line_type==''
    c=w._engineering_context_controller
    for module in ('discharge_head_loss','suction_npsh'):
        assert c.read(module,'kinematic_viscosity')==3
        assert 'absolute_roughness' not in c.links[module]
        panel=w._pages[module]._engineering_panel
        assert panel.fluid_box.get()==f76.name_tr
        assert str(panel.fluid_box['state'])=='disabled'
    assert c.read('suction_npsh','density')==838
    assert '838' in w._pages['discharge_head_loss']._engineering_panel.summary['text']
    project=w._active_project;w._project_persistence_service.close();w._active_project=None
    w._activate_project(project);root.update()
    assert w._system_context.fluid.id==f76.id and w._system_context.service==''
    assert w._system_context.surface_profile_id is None and w._system_context.rule_set_id is None
    assert w._locked_project_family()=='fuel'


def test_explicit_module_fluid_override_preserves_project_and_manual_values(shell):
    w=shell;c=new_context(w);page=w._pages['suction_npsh']
    page._fields['density'].set('850')
    project_context=w._system_context
    c.open_module_context('suction_npsh');dialog=c._module_dialogs['suction_npsh'];form=dialog.selection
    f44=next(r for r in c.catalog.fluid_records if r.code=='F44')
    choose(form,'fluid',f44.id)
    c.set_module_context('suction_npsh',form.value());dialog.destroy()
    assert w._system_context==project_context
    assert c.context_for('suction_npsh').fluid.id==f44.id
    assert c.context_for('discharge_head_loss').fluid.code=='F76'
    assert c.read('suction_npsh','density')==850
    assert c.links['suction_npsh']['density'].reference['default_value']==816.5
    assert c.links['suction_npsh']['density'].status=='OVERRIDE'
    assert '850' in page._engineering_panel.summary['text']
    assert c.links['suction_npsh']['kinematic_viscosity'].reference['default_value'] is None
    assert json.loads(w._system_context.engineering_defaults_json)=={}
    with pytest.raises(ValueError,match='project context'):c.action('suction_npsh','density','project')
    assert w._save_project()
    project=w._active_project;w._active_project=None;w._project_persistence_service.close();w._activate_project(project)
    assert c.context_for('suction_npsh').fluid.id==f44.id
    assert c.read('suction_npsh','density')==850
    c.use_project_context('suction_npsh')
    assert c.context_for('suction_npsh').fluid.code=='F76'
    assert c.read('suction_npsh','density')==850  # Returning does not overwrite manual experimentation.


@pytest.mark.parametrize('language',['tr','en'])
@pytest.mark.parametrize('size',[(1100,700),(1440,900)])
def test_catalog_material_service_identity_and_panel_geometry(shell,language,size):
    from ui.dialogs.project_engineering_context import ProjectEngineeringContextDialog
    w=shell;c=new_context(w);root=w._root;old=w._localization.language
    try:
        w._localization.set_language(language);root.deiconify();root.geometry(f'{size[0]}x{size[1]}');root.update()
        dialog=ProjectEngineeringContextDialog(w)
        form=dialog.selection
        assert form.labels['fluid']['text']==w._translate('engineering.select.fluid')
        assert form.labels['service']['text']==w._translate('engineering.select.service')
        assert len(form.choices['material'])>5
        choose(form,'material','HDPE')
        assert form.value().surface_profile_id==identity('surface:HDPE_NEW')
        # A surface profile never fabricates validated yield strength.
        assert form.value().material_id==w._system_context.material_id
        dialog.window.destroy()
        for module in ('pipe_design','discharge_head_loss','suction_npsh'):
            viewport=w._page_host._page_keys[module];w._page_host.select(viewport);viewport.canvas.yview_moveto(0)
            panel=w._pages[module]._engineering_panel;settle_geometry(root,panel)
            assert set(panel.material_box['values'])=={r.material_name for r in c.catalog.surface_records if 'Cu-Ni' not in r.material_name}
            assert panel.winfo_rootx()>=viewport.canvas.winfo_rootx()
            assert panel.winfo_rootx()+panel.winfo_width()<=viewport.canvas.winfo_rootx()+viewport.canvas.winfo_width()
            assert not w._pages[module]._engineering_context_label.winfo_ismapped()
            if module!='pipe_design':assert not w._pages[module]._warning_fluid_box.winfo_ismapped()
            else:assert w._pages[module]._material_label['text']==w._translate('engineering.strength_material')
    finally:w._localization.set_language(old)


def test_module_material_and_fluid_are_frozen_in_formula_basis(shell,monkeypatch):
    w=shell;c=new_context(w);module='discharge_head_loss';page=w._pages[module]
    c.set_module_context(module,chosen(c.catalog,fuel='F44',surface='STAINLESS_NEW'))
    for key,value in {'d':'100','q':'25','l':'10','h':'5','nu':'4'}.items():page._fields[key].set(value)
    monkeypatch.setattr('ui.main_window.messagebox.showerror',lambda *a,**k:pytest.fail('Capture failed'))
    page._calculate();assert page._last_result
    snapshot=page._pdf_snapshot;basis=json.loads(snapshot.formula_steps[0].engineering_basis_json)
    assert snapshot.context.fluid.code=='F44'
    assert not any('EVERLLENCE_DIESEL_FUEL' in f.code for f in c.findings(module,3))
    assert 'F-44' in basis['fluid'] and basis['surface_condition']=='NEW_CLEAN'
    assert basis['context_scope']=='OVERRIDE' and w._system_context.fluid.code=='F76'
    frozen=snapshot.evidence_json
    c.use_project_context(module)
    assert snapshot.evidence_json==frozen and not w._pdf_is_current(page)


def test_unchanged_identity_is_not_a_context_override(shell):
    w=shell;c=new_context(w)
    c.set_module_context('discharge_head_loss',w._system_context)
    assert 'discharge_head_loss' not in c.module_contexts
    page=w._pages['discharge_head_loss'];page._fields['nu'].set('4')
    assert c.links['discharge_head_loss']['kinematic_viscosity'].status=='OVERRIDE'
    assert 'discharge_head_loss' not in c.module_contexts
    assert json.loads(w._system_context.engineering_defaults_json)=={}
