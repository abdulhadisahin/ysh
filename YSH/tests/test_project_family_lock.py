"""V2.1 family persistence and real-shell navigation contracts."""
from copy import deepcopy
from uuid import uuid4

import pytest

from core.project_family import project_family
from engineering.validation import ValidationError
from i18n.translator import Translator
from ui.workspace_navigation import WorkspaceNavigation
from .test_project_persistence_workflow import _service
from .test_fire_phase5cd_navigation import application, shell
from ._tk_geometry import settle_geometry


@pytest.mark.parametrize('family', ['fuel', 'fire'])
def test_family_persisted_at_creation_and_across_service_restart(tmp_path, family):
    service = _service(tmp_path)
    project = service.create_project('New', system_family=family)
    assert not service.is_dirty
    service.close()  # No ordinary Save before close.
    restarted = _service(tmp_path)
    _, state = restarted.open(project.id)
    assert project_family(state) == family
    state['pipe_design'] = {'fields': {'q': '25'}}
    state['fire_workspace'] = {'opaque': 'unchanged'}
    state['system_context'] = {'opaque': 'unchanged'}
    restarted.save(state)
    restarted.save({'schema_version': 1, 'pipe_design': state['pipe_design']})
    restored = _service(tmp_path).open(project.id)[1]
    assert project_family(restored) == family
    assert restored['fire_workspace'] == state['fire_workspace']
    assert restored['system_context'] == state['system_context']
    assert restored['pipe_design'] == state['pipe_design']


@pytest.mark.parametrize('family', ['fuel', 'fire'])
def test_persistence_rejects_family_change_without_overwrite(tmp_path, family):
    service = _service(tmp_path)
    project = service.create_project('Locked', system_family=family)
    before = service.open(project.id)[1]
    changed = deepcopy(before)
    changed['navigation']['active_system_family'] = 'fire' if family == 'fuel' else 'fuel'
    with pytest.raises(ValidationError, match='project_family_locked'):
        service.save(changed)
    assert service.open(project.id)[1] == before


@pytest.mark.parametrize('navigation,expected', [
    (None, 'fuel'), ({}, 'fuel'),
    ({'version': 1, 'active_system_family': 'fire'}, 'fire'),
    ({'version': 2, 'active_system_family': 'fire'}, 'fire'),
])
def test_legacy_uses_stored_family_without_inferring_from_cached_pages(tmp_path, navigation, expected):
    service = _service(tmp_path)
    project = service._projects.create_project('Legacy')
    state = {'schema_version': 1, 'fire_workspace': {'cached': True},
             'system_context': {'system': {'code': 'FIRE'}}}
    if navigation is not None:
        state['navigation'] = navigation
    service._states.save(project.id, state)
    before = deepcopy(state)
    _, loaded = service.open(project.id)
    assert project_family(loaded) == expected
    assert WorkspaceNavigation.from_workspace(loaded).active_system_family == expected
    assert loaded == before  # Opening never rewrites historical or opaque data.
    service.save(loaded)
    assert service.active_system_family == expected


def test_invalid_creation_and_failed_initial_save_preserve_active_project(tmp_path, monkeypatch):
    service = _service(tmp_path)
    old = service.create_project('Existing', system_family='fire')
    with pytest.raises(ValueError):
        service.create_project('Invalid', system_family='both')
    def fail(*args):
        raise OSError('storage unavailable')
    monkeypatch.setattr(service._states, 'save', fail)
    with pytest.raises(OSError):
        service.create_project('Incomplete', system_family='fuel')
    assert service.active_project == old
    assert [p.id for p in service.get_all_projects()] == [old.id]


@pytest.mark.parametrize('family', ['fuel', 'fire'])
@pytest.mark.parametrize('size', [(1100, 700), (1440, 900)])
def test_project_navigation_lock_and_context_indicator(shell, family, size):
    w = shell
    root = w._root
    root.deiconify()
    root.geometry(f'{size[0]}x{size[1]}')
    # Creation choice is authoritative even when the opposite family is displayed.
    other = 'fire' if family == 'fuel' else 'fuel'
    w._show_family(other)
    assert w._create_project('Family ' + str(uuid4()), '', '', family)
    settle_geometry(root, w._project_family_indicator)
    assert w._family == family
    assert str(w._family_selector['state']) == 'disabled'
    assert w._project_family_indicator.winfo_ismapped()
    for language in ('tr', 'en'):
        original = w._translate
        try:
            w._translate = Translator(language).translate
            w._refresh_family_selector()
            text = w._project_family_indicator['text']
            assert w._active_project.name in text
            assert w._translate('project.family.' + family) in text
        finally:
            w._translate = original
            w._refresh_family_selector()
    before = w._export_all_page_states()
    w._show_family(other)
    w._family_selector.current(0 if other == 'fuel' else 1)
    w._select_family()
    root.update()
    assert w._family == family
    assert w._export_all_page_states() == before
    assert w._page_host.winfo_ismapped() == (family == 'fuel')
    assert w._fire_workspace.winfo_ismapped() == (family == 'fire')
    indicator = w._project_family_indicator
    assert indicator.winfo_rootx() + indicator.winfo_width() <= root.winfo_rootx() + root.winfo_width()
    visible = w._page_host if family == 'fuel' else w._fire_workspace
    assert indicator.winfo_rooty() + indicator.winfo_height() <= visible.winfo_rooty()
    project = w._active_project
    w._save_project()
    w._close_project()
    assert str(w._family_selector['state']) == 'readonly'
    assert not indicator.grid_info()
    w._activate_project(project)
    assert w._family == family
    assert str(w._family_selector['state']) == 'disabled'


@pytest.mark.parametrize('dialog_name', ['NewProjectDialog', 'SaveProjectAsDialog'])
@pytest.mark.parametrize('language', ['tr', 'en'])
def test_creation_dialog_requires_explicit_family(shell, monkeypatch, dialog_name, language):
    from ui.dialogs.new_project_dialog import NewProjectDialog
    from ui.dialogs.save_project_as_dialog import SaveProjectAsDialog
    import ui.widgets.project_family_choice as choice_module
    w = shell
    w._root.deiconify()
    w._root.update()
    errors = []
    monkeypatch.setattr(choice_module.messagebox, 'showerror', lambda *a, **kw: errors.append(a))
    cls = NewProjectDialog if dialog_name == 'NewProjectDialog' else SaveProjectAsDialog
    dialog = cls(w._root, Translator(language).translate)
    try:
        name = dialog._name_entry if dialog_name == 'NewProjectDialog' else dialog._name
        name.insert(0, 'Explicit')
        assert dialog._family_choice.choice.current() == -1
        dialog._submit()
        assert dialog.result is None and len(errors) == 1
        dialog._family_choice.choice.current(1)
        dialog.refresh_texts()
        assert dialog._family_choice.choice.current() == 1
        dialog._submit()
        assert dialog.result == ('Explicit', '', '', 'fire')
    finally:
        if dialog._dialog.winfo_exists():
            dialog._cancel()


@pytest.mark.parametrize('active_family', [None, 'fuel', 'fire'])
def test_save_as_explicit_without_project_and_inherited_when_active(shell, monkeypatch, active_family):
    import sys
    w = shell
    module = sys.modules[type(w).__module__]
    if active_family:
        assert w._create_project('Original ' + str(uuid4()), '', '', active_family)
    before = {k: p.export_state() for k, p in w._pages.items()}
    chosen = 'fire' if active_family != 'fire' else 'fuel'
    expected = active_family or chosen
    class Dialog:
        def __init__(self, *args, locked_family):
            assert locked_family == active_family
        def show(self):
            return ('Copy ' + str(uuid4()), '', '', chosen)
    monkeypatch.setattr(module, 'SaveProjectAsDialog', Dialog)
    w._save_project_as()
    assert w._family == expected
    assert w._project_persistence_service.active_system_family == expected
    assert {k: p.export_state() for k, p in w._pages.items()} == before


def test_save_as_dialog_displays_inherited_family_without_editing(shell):
    from ui.dialogs.save_project_as_dialog import SaveProjectAsDialog
    shell._root.deiconify()
    shell._root.update()
    dialog = SaveProjectAsDialog(shell._root, locked_family='fire')
    try:
        assert str(dialog._family_choice.choice['state']) == 'disabled'
        assert dialog._family_choice.selected() == 'fire'
    finally:
        dialog._cancel()


def test_failed_save_as_preserves_active_project_family_and_unsaved_state(shell, monkeypatch):
    import sys
    w = shell
    assert w._create_project('Original ' + str(uuid4()), '', '', 'fire')
    old = w._active_project
    service = w._project_persistence_service
    service.mark_dirty()
    before = w._export_all_page_states()
    module = sys.modules[type(w).__module__]
    class Dialog:
        def __init__(self, *a, **kw):
            pass
        def show(self):
            return ('Failed Copy ' + str(uuid4()), '', '', 'fire')
    monkeypatch.setattr(module, 'SaveProjectAsDialog', Dialog)
    errors = []
    monkeypatch.setattr(module.messagebox, 'showerror', lambda *a, **kw: errors.append(a))
    def fail(state):
        raise OSError('storage unavailable')
    monkeypatch.setattr(service, 'save', fail)
    w._save_project_as()
    assert errors
    assert w._active_project == service.active_project == old
    assert service.active_system_family == 'fire' and service.is_dirty
    assert w._export_all_page_states() == before
    assert all(not p.name.startswith('Failed Copy ') for p in service.get_all_projects())


def test_state_load_cannot_bypass_family_lock(shell):
    w = shell
    assert w._create_project('Locked ' + str(uuid4()), '', '', 'fire')
    before = w._export_all_page_states()
    other = deepcopy(before)
    other['navigation']['active_system_family'] = 'fuel'
    with pytest.raises(ValidationError, match='project_family_locked'):
        w._load_all_page_states(other)
    assert w._export_all_page_states() == before
    w._clear_all_pages()
    assert w._family == 'fire'
    assert w._navigation.active_system_family == 'fire'


@pytest.mark.parametrize('family', ['fuel', 'fire'])
@pytest.mark.parametrize('navigation', [None, {}, {'version': 1},
                                       {'version': 1, 'active_system_family': 'both'}])
def test_save_cannot_erase_persisted_family(tmp_path, family, navigation):
    service = _service(tmp_path)
    project = service.create_project('Locked', system_family=family)
    before = service.open(project.id)[1]
    with pytest.raises(ValidationError, match='project_family_locked'):
        service.save({'schema_version': 1, 'navigation': navigation})
    assert service.open(project.id)[1] == before
