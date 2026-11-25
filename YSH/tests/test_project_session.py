"""Last-project preferences restore saved state, never unsaved edits."""
from uuid import uuid4

import pytest

from core.user_settings import UserSettings
from i18n.manager import LanguagePreferenceStore
from .test_fire_phase5cd_navigation import application


def test_application_restores_before_mainloop(monkeypatch, tmp_path):
    import YSH.app as module
    from YSH.paths import ApplicationPaths
    from .test_application_lifecycle import _FakeMainWindow, _FakeRoot
    events = []
    class Window(_FakeMainWindow):
        def restore_project_session(self, store):
            assert not self.root.mainloop_called
            assert store.path == tmp_path / 'YSH' / 'data' / 'settings.json'
            events.append('restore')
    app = module.YSHApplication.__new__(module.YSHApplication)
    app._project_service = object()
    app._paths = ApplicationPaths(local_app_data=tmp_path)
    app._main_window = app._root = None
    monkeypatch.setattr(app, '_initialize_application', lambda: None)
    monkeypatch.setattr(module, 'MainWindow', Window)
    monkeypatch.setattr(module.tk, 'Tk', _FakeRoot)
    app.run()
    assert events == ['restore']
    assert app._root.mainloop_called


def test_settings_merge_and_invalid_file(tmp_path):
    store = UserSettings(tmp_path / 'settings.json')
    assert store.session() == {}
    identity = uuid4()
    store.update(unknown={'keep': True})
    store.remember(identity, 'hw')
    LanguagePreferenceStore(store.path).save('tr')
    assert store.read()['unknown'] == {'keep': True}
    assert store.session() == {'last_project_id': str(identity), 'tabs': {str(identity): 'hw'}}
    store.path.write_text('{broken', encoding='utf-8')
    assert store.session() == {}


@pytest.mark.parametrize('family,module', [('fuel','suction_npsh'), ('fire','hw'), ('seawater','discharge_head_loss')])
def test_restore_saved_project_and_independent_tab(application, tmp_path, monkeypatch, family, module):
    window = application._main_window
    persistence = window._project_persistence_service
    persistence.close()
    window._active_project = None
    window._clear_all_pages()
    project = persistence.create_project('Session ' + family, system_family=family)
    window._activate_project(project)
    window._save_project()
    saved = persistence.open(project.id)[1]
    store = UserSettings(tmp_path / 'settings.json')
    store.remember(project.id, module)
    persistence.close()
    window._active_project = None
    window._clear_all_pages()
    window._session_restore_attempted = False
    calls = []
    original = persistence.open
    def opened(identity):
        calls.append(identity)
        return original(identity)
    monkeypatch.setattr(persistence, 'open', opened)
    monkeypatch.setattr(persistence, 'save', lambda *_: pytest.fail('Unexpected automatic save'))
    window.restore_project_session(store)
    window._root.update()
    window.restore_project_session(store)
    assert calls == [project.id]
    assert window._active_project.id == project.id
    assert window._family == family
    assert window._navigation.last_active_module_by_family[family] == module
    assert original(project.id)[1] == saved
    assert not persistence.is_dirty


@pytest.mark.parametrize('identity', [None, 'not-a-uuid', str(uuid4())])
def test_missing_project_has_no_fallback(application, tmp_path, monkeypatch, identity):
    window = application._main_window
    window._project_persistence_service.close()
    window._active_project = None
    window._clear_all_pages()
    window._session_restore_attempted = False
    store = UserSettings(tmp_path / 'settings.json')
    if identity:
        store.remember(identity)
    monkeypatch.setattr('ui.main_window.messagebox.showerror', lambda *_args, **_kw: pytest.fail('Unexpected dialog'))
    window.restore_project_session(store)
    assert window._active_project is None
    assert window._project_persistence_service.active_project is None


def test_corrupt_workspace_is_quiet_and_manual_switch_commits_only_success(application, tmp_path, monkeypatch):
    window = application._main_window
    service = window._project_persistence_service
    service.close()
    window._active_project = None
    window._clear_all_pages()
    first = service.create_project('Session corrupt')
    store = UserSettings(tmp_path / 'settings.json')
    store.remember(first.id, 'transfer_pump')
    service.close()
    window._session_restore_attempted = False
    original = service.open
    def broken(_identity):
        raise ValueError('Corrupt workspace')
    with monkeypatch.context() as patch:
        patch.setattr(service, 'open', broken)
        patch.setattr('ui.main_window.messagebox.showerror', lambda *_args, **_kw: pytest.fail('Unexpected dialog'))
        window.restore_project_session(store)
    assert window._active_project is None
    assert service.active_project is None
    assert not window._session_loading
    second = service.create_project('Session manual switch')
    assert window._activate_project(second)
    assert store.session()['last_project_id'] == str(second.id)
    host = window._page_host
    host.select(host._page_keys['discharge_head_loss'])
    window._root.update()
    assert store.session()['tabs'][str(second.id)] == 'discharge_head_loss'
    assert not service.is_dirty
    with monkeypatch.context() as patch:
        patch.setattr(service, 'open', broken)
        assert window._activate_project(first, quiet=True) is False
    assert store.session()['last_project_id'] == str(second.id)
    assert window._active_project.id == second.id
    assert original(second.id)[0].id == second.id
