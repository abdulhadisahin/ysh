"""Five-field project creation uses classified catalog identities, not values."""
from dataclasses import replace
from uuid import uuid4

import pytest

from engineering.catalog import FluidSpecification
from repositories.v2_models import Fluid
from services.engineering_catalog_service import EngineeringCatalogService
from i18n.translator import Translator
from .test_fire_phase5cd_navigation import application,shell


def test_catalog_filters_by_explicit_groups_and_never_writes(library_database):
    catalog=EngineeringCatalogService(library_database)
    with library_database.connection() as connection:before=tuple(connection.iterdump())
    fuel={r.code for r in catalog.project_fluids('fuel')}
    assert {'F76','F44','DMA','DMZ','DMB','RMA_20','RME_180','RMG_380','RMK_500'}==fuel
    assert not fuel & {'WATER','SEAWATER','CONTROL_AIR','STARTING_AIR','LUBE_OIL'}
    assert {r.code for r in catalog.project_fluids('fire')}=={'WATER'}
    assert catalog.project_fluids(None)==() and catalog.project_fluids('unknown')==()
    with library_database.connection() as connection:assert tuple(connection.iterdump())==before


def test_display_names_do_not_determine_compatibility_and_unknowns_are_excluded(library_database):
    catalog=EngineeringCatalogService(library_database)
    classified=catalog.fluid_repository.create(Fluid(code='SYNTHETIC',name_tr='Fresh Water / Starting Air'))
    unknown=catalog.fluid_repository.create(Fluid(code='UNKNOWN',name_tr='MGO Fuel'))
    catalog.properties.create(FluidSpecification(code='SYNTHETIC_DENSITY',fluid_id=classified.id,
        name='TEST ONLY',fluid_group='DIESEL_FUEL',property_name='density',unit='kg/m³'))
    catalog.reload()
    assert classified in catalog.project_fluids('fuel')
    assert classified not in catalog.project_fluids('fire')
    assert unknown not in catalog.project_fluids('fuel')


def test_temperature_variants_preserve_one_fluid_identity_and_all_metadata(library_database):
    catalog=EngineeringCatalogService(library_database)
    water=next(r for r in catalog.fluid_records if r.code=='WATER')
    reference=next(r for r in catalog.property_records if r.fluid_id==water.id)
    variant=catalog.properties.create(replace(reference,id=uuid4(),code='TEST_WATER_TEMPERATURE_VARIANT',
        reference_temperature_c=5,source_document='TEST ONLY temperature variant',is_factory=False))
    catalog.reload();before=catalog.property_records
    assert catalog.project_fluids('fire')==(water,)
    assert catalog.property_records==before
    assert catalog.properties.get(reference.id)==reference
    assert catalog.properties.get(variant.id)==variant
    assert variant.fluid_id==reference.fluid_id and variant.source_document!=reference.source_document


def test_conflicting_fluid_classifications_are_not_guessed(library_database):
    catalog=EngineeringCatalogService(library_database)
    fuel=next(r for r in catalog.fluid_records if r.code=='F76')
    record=next(r for r in catalog.property_records if r.fluid_id==fuel.id)
    catalog.property_records=(*catalog.property_records,replace(record,fluid_group='FRESH_WATER'))
    assert fuel not in catalog.project_fluids('fuel')
    assert fuel not in catalog.project_fluids('fire')


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


@pytest.mark.parametrize('language',['tr','en'])
@pytest.mark.parametrize('size',[(1100,700),(1440,900)])
def test_new_dialog_has_only_five_fields_one_system_and_filtered_fluids(shell,language,size):
    from ui.dialogs.new_project_dialog import NewProjectDialog
    window=shell;root=window._root;root.deiconify();root.geometry(f'{size[0]}x{size[1]}');root.update()
    tr=Translator(language).translate
    dialog=NewProjectDialog(root,tr,window)
    try:
        widgets=tuple(descendants(dialog._dialog))
        labels=[str(w.cget('text')) for w in widgets if w.winfo_class()=='TLabel']
        assert labels==[tr('project.name')+':',tr('project.description')+':',tr('project.notes')+':',
                        'Sistem' if language=='tr' else 'System',tr('engineering.fluid')]
        assert len([w for w in widgets if w.winfo_class()=='TCombobox'])==2
        assert not hasattr(dialog,'_engineering_selection')
        assert tuple(dialog._family_choice.choice['values'])==(tr('project.family.fuel'),tr('project.family.fire'))
        assert dialog._family_choice.choice.current()==-1
        dialog._family_choice.choice.current(0);dialog._family_choice.choice.event_generate('<<ComboboxSelected>>')
        root.update()
        assert 'F76' in {r.code for r in dialog._fluid_records.values() if r}
        assert not {r.code for r in dialog._fluid_records.values() if r}&{'WATER','SEAWATER','CONTROL_AIR','STARTING_AIR'}
        label=next(label for label,r in dialog._fluid_records.items() if r and r.code=='F76')
        dialog._fluid_choice.set(label);dialog.refresh_texts()
        assert dialog._fluid_choice.get()==label
        dialog._family_choice.choice.current(1);dialog._family_choice.choice.event_generate('<<ComboboxSelected>>')
        root.update()
        assert {r.code for r in dialog._fluid_records.values() if r}=={'WATER'}
        assert dialog._fluid_records[dialog._fluid_choice.get()] is None
        assert dialog._dialog.winfo_reqwidth()<=size[0] and dialog._dialog.winfo_reqheight()<=size[1]
    finally:dialog._cancel()


@pytest.mark.parametrize('code',['WATER',None])
def test_fire_new_project_save_reopen_preserves_only_selected_fluid(shell,monkeypatch,code):
    from ui.dialogs.new_project_dialog import NewProjectDialog
    window=shell;root=window._root;root.deiconify();root.update()
    errors=[]
    def factory(*args,**kwargs):
        dialog=NewProjectDialog(*args,**kwargs)
        dialog._name_entry.insert(0,'Simple Fire '+str(uuid4()))
        dialog._description_text.insert('1.0','Description')
        dialog._notes_text.insert('1.0','Notes')
        dialog._family_choice.choice.current(1);dialog._refresh_fluids()
        if code:
            dialog._fluid_choice.set(next(label for label,r in dialog._fluid_records.items() if r and r.code==code))
        def submit():
            try:dialog._submit()
            except BaseException as error:errors.append(error);dialog._cancel()
        root.after(0,submit)
        return dialog
    monkeypatch.setitem(window._open_new_project.__func__.__globals__,'NewProjectDialog',factory)
    window._open_new_project()
    assert not errors
    assert window._active_project and window._locked_project_family()=='fire'
    context=window._system_context
    assert (context.fluid.code if context.fluid else None)==code
    assert context.material_id is None and context.surface_profile_id is None and context.rule_set_id is None
    assert context.service=='' and context.line_type=='' and context.engineering_defaults_json=='{}'
    project=window._active_project
    assert project.description=='Description' and project.notes=='Notes'
    window._project_persistence_service.close();window._active_project=None
    window._activate_project(project);root.update()
    assert window._system_context==context
    assert window._locked_project_family()=='fire'
    window._show_family('fuel',dirty=False)
    assert window._family=='fire'
