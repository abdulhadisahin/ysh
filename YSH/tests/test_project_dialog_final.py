"""Final creation fields and module-derived line function preserve old data."""
from dataclasses import replace
from uuid import uuid4

import pytest

from i18n.translator import Translator
from ui.widgets.engineering_page_context import rule_summary
from .test_fire_phase5cd_navigation import application,shell
from .test_project_engineering_context import chosen,catalog
from .test_project_persistence_workflow import _service


@pytest.mark.parametrize('family',['fuel','fire'])
def test_description_is_optional_and_new_notes_are_empty(shell,family):
    from ui.dialogs.new_project_dialog import NewProjectDialog
    root=shell._root;root.deiconify();root.update()
    dialog=NewProjectDialog(root,shell._translate,shell)
    try:
        dialog._name_entry.insert(0,'Optional description')
        dialog._family_choice.choice.current(0 if family=='fuel' else 1)
        dialog._submit()
        assert dialog.result==('Optional description','','',family)
        assert not hasattr(dialog,'_notes_text')
    finally:
        if dialog._dialog.winfo_exists():dialog._cancel()


def test_existing_description_notes_and_context_are_not_merged_or_overwritten(tmp_path):
    service=_service(tmp_path)
    old=service.create_project('Historical project','Original description','Separate historical notes')
    state={'schema_version':1,'legacy_data':{'notes':'Legacy payload notes'}}
    service.save(state);service.close()
    service.create_project('New project','New optional description','')
    service.save({'schema_version':1})
    restored,payload=service.open(old.id)
    assert restored.description=='Original description'
    assert restored.notes=='Separate historical notes'
    assert payload['legacy_data']==state['legacy_data']
    service.save({'schema_version':1,**payload});service.close()
    restored,_=service.open(old.id)
    assert (restored.description,restored.notes)==('Original description','Separate historical notes')


@pytest.mark.parametrize('module,line,opposite',[
    ('discharge_head_loss','DELIVERY','SUCTION'),('suction_npsh','SUCTION','DELIVERY')])
def test_module_editor_has_no_redundant_selectors_and_rules_use_module_line(shell,module,line,opposite):
    window=shell
    assert window._create_project('Automatic line '+str(uuid4()),'','','fuel')
    controller=window._engineering_context_controller
    context=chosen(controller.catalog,line=opposite).changed(service='DIESEL_FUEL_'+opposite)
    controller.apply(context)
    controller.open_module_context(module)
    dialog=controller._module_dialogs[module]
    try:
        form=dialog.selection
        assert set(form.boxes)=={'fluid','material','surface','profile'}
        assert 'service' not in form.variables and 'line_type' not in form.variables
        assert form.value()==context  # Hidden historical classification is preserved.
        rules=controller.catalog.matching_rules(form.value(),'fuel',module)
        assert 'EVERLLENCE_DIESEL_FUEL_'+line in {r.code for r in rules}
        assert 'EVERLLENCE_DIESEL_FUEL_'+opposite not in {r.code for r in rules}
        rule=next(r for r in rules if r.code=='EVERLLENCE_DIESEL_FUEL_'+line)
        assert (rule.recommended_min,rule.recommended_max)==((1.5,2.) if line=='DELIVERY' else (.5,1.))
        panel=window._pages[module]._engineering_panel
        assert window._translate('engineering.line.'+line) in panel.rules['text']
        assert rule.source_authority in panel.rules['text'] and rule.source_document in panel.rules['text']
        assert window._system_context==context
    finally:dialog.destroy()


@pytest.mark.parametrize('language',['tr','en'])
def test_recorded_limits_source_edition_and_scope_are_shown_without_invention(catalog,language):
    tr=Translator(language).translate
    rule=next(r for r in catalog.rule_records if r.code=='TL_FFS_SUCTION')
    text=rule_summary(rule,tr)
    assert str(rule.hard_max) in text and rule.unit in text
    assert rule.source_authority in text and rule.source_document in text
    assert rule.source_edition=='July 2019' and rule.source_edition in text
    assert rule.source_clause in text
    assert tr('engineering.scope.TL_FFS') in text
    without=replace(rule,source_edition='',source_clause='',applicability='')
    missing=rule_summary(without,tr)
    assert 'July 2019' not in missing and rule.source_clause not in missing
    assert tr('engineering.scope_unrecorded') in missing


def test_verified_line_rule_and_applicability_gates_remain_intact(catalog):
    context=chosen(catalog,line='SUCTION',scope='TEST_SCOPE')
    source=next(r for r in catalog.rule_records if r.code=='EVERLLENCE_DIESEL_FUEL_DELIVERY')
    synthetic=replace(source,code='TEST_ONLY_VERIFIED_DELIVERY',verification='VERIFIED',
        applicability='TEST_SCOPE',source_document='TEST ONLY source',source_edition='TEST revision A')
    catalog.rule_records=(*catalog.rule_records,synthetic)
    assert synthetic in catalog.matching_rules(context,'fuel','discharge_head_loss')
    assert synthetic not in catalog.matching_rules(context,'fuel','suction_npsh')
    assert synthetic not in catalog.matching_rules(context.changed(applicability_scope=''),'fuel','discharge_head_loss')
    assert source.recommended_min==synthetic.recommended_min and source.recommended_max==synthetic.recommended_max
