"""Real project lifecycle plus shell icon/frame contracts without pixel assertions."""
from types import SimpleNamespace

import pytest
from PIL import Image

from i18n.translator import Translator
from repositories.project_repository import ProjectRepository
from repositories.project_state_repository import ProjectStateRepository
from services.project_persistence_service import ProjectPersistenceService
from services.project_service import ProjectService
from ui.main_window import MainWindow
from ui.theme import colors
from ui.assets import action_icon_path
from ui.widgets.asset_loader import AssetImageLoader
from ui.widgets.rounded_button import ADD_BUTTON_PALETTE, DELETE_BUTTON_PALETTE, HEADER_COMMAND_PALETTE
from .test_main_window import _FakeRoot, _FakeProjectSummary, _FakeMenu, _FakeStatusBar, _DummyWidget


class Region:
    """Record geometry visibility independently of repository contents."""
    def __init__(self) -> None:
        self.visible = False

    def grid(self) -> None:
        """Map this region."""
        self.visible = True

    def grid_remove(self) -> None:
        """Unmap this region while retaining its layout."""
        self.visible = False


class Tree:
    """Model native deletion/selection semantics instead of returning canned rows."""
    def __init__(self) -> None:
        self.rows = {}
        self.selected = ()

    def insert(self, parent, position, *, iid, values, tags) -> None:
        """Insert a project identified by its actual persisted UUID."""
        self.rows[iid] = (values, tags)

    def get_children(self) -> tuple:
        """Return visible row identities."""
        return tuple(self.rows)

    def delete(self, identifier) -> None:
        """Delete a row and its native selection."""
        del self.rows[identifier]
        if identifier in self.selected:
            self.selected = ()

    def selection(self) -> tuple:
        """Return current selection."""
        return self.selected

    def selection_set(self, identifier) -> None:
        """Reject attempts to restore a deleted/filtered row."""
        assert identifier in self.rows
        self.selected = (identifier,)

    def exists(self, identifier) -> bool:
        """Resolve exact row identity."""
        return identifier in self.rows

    def focus(self, identifier) -> None:
        """Record focus restoration."""
        self.focused = identifier

    def see(self, identifier) -> None:
        """Record active row scrolling."""
        self.seen = identifier


@pytest.fixture
def shell(project_database, monkeypatch):
    """Use real create/open/delete services with display-only doubles."""
    import ui.main_window as view
    projects = ProjectService(ProjectRepository(project_database))
    window = MainWindow.__new__(MainWindow)
    window._project_service = projects
    window._project_persistence_service = ProjectPersistenceService(projects, ProjectStateRepository(project_database))
    window._active_project = None
    window._projects_tree = Tree()
    window._project_tree_container, window._project_empty_state = Region(), Region()
    window._root, window._project_summary = _FakeRoot(), _FakeProjectSummary()
    window._file_menu, window._status_bar = _FakeMenu(), _FakeStatusBar()
    window._translate = Translator('tr').translate
    window._localization = None
    query = ['']
    window._project_search = SimpleNamespace(get=lambda: query[0], set=lambda value: query.__setitem__(0, value))
    window._pages = {}
    window._clear_all_pages = lambda: None
    window._export_all_page_states = lambda: {}
    window._load_all_page_states = lambda state: None
    monkeypatch.setattr(view.messagebox, 'askyesno', lambda *a, **kw: True)
    monkeypatch.setattr(view.messagebox, 'showerror', lambda *a, **kw: pytest.fail(str(a)))
    window._refresh_projects()
    return window


def create(window, name):
    """Use the actual New Project callback including activation and list refresh."""
    assert window._create_project(name, 'Description', 'Notes')
    return window._active_project


def assert_list(window, projects) -> None:
    """Check contents, geometry and active row as separate state contracts."""
    assert set(window._projects_tree.rows) == {str(project.id) for project in projects}
    assert window._project_tree_container.visible is bool(projects)
    assert window._project_empty_state.visible is not bool(projects)
    if window._active_project is not None:
        assert window._projects_tree.selection() == (str(window._active_project.id),)
        assert window._projects_tree.rows[str(window._active_project.id)][1] == ('active_project',)


@pytest.mark.parametrize('scenario', ['initial', 'first', 'second', 'switch', 'open',
    'refresh', 'delete_one', 'delete_last', 'recreate', 'filtered_new'])
def test_project_list_lifecycle(shell, monkeypatch, scenario) -> None:
    """Cover empty/list transitions, selection, normal callbacks and deleted rows."""
    window = shell
    assert_list(window, [])
    if scenario == 'initial':
        return
    first = create(window, 'First')
    assert_list(window, [first])
    if scenario == 'first':
        return
    second = create(window, 'Second')
    assert_list(window, [first, second])
    if scenario == 'second':
        return
    if scenario == 'switch':
        window._projects_tree.selection_set(str(first.id))
        window._open_selected_project()
        assert window._active_project.id == first.id
        assert_list(window, [first, second])
    elif scenario == 'open':
        import ui.main_window as view
        monkeypatch.setattr(view, 'OpenProjectDialog', lambda *a: SimpleNamespace(show=lambda: first))
        window._open_project()
        assert window._active_project.id == first.id
        assert_list(window, [first, second])
    elif scenario == 'refresh':
        window._refresh_projects()
        window._refresh_projects()
        assert_list(window, [first, second])
        assert window._projects_tree.focused == window._projects_tree.seen == str(second.id)
    elif scenario == 'filtered_new':
        window._project_search.set('No existing or new project matches this')
        window._refresh_projects()
        assert not window._project_tree_container.visible
        third = create(window, 'Third')
        assert window._project_search.get() == ''
        assert_list(window, [first, second, third])
    else:
        window._projects_tree.selection_set(str(first.id))
        window._delete_project()
        assert_list(window, [second])
        if scenario == 'delete_one':
            return
        window._projects_tree.selection_set(str(second.id))
        window._delete_project()
        assert window._active_project is None
        assert_list(window, [])
        if scenario == 'recreate':
            third = create(window, 'Created after empty')
            assert_list(window, [third])


@pytest.mark.parametrize('area', ['header', 'sidebar_add', 'sidebar_delete'])
def test_shell_button_constructors_keep_factory_contract_and_interaction_states(monkeypatch, area) -> None:
    """Call the actual shell factory through the actual rounded-button API."""
    import ui.widgets.rounded_button as buttons
    monkeypatch.setattr(buttons, 'RoundedImageButton', _DummyWidget)
    callback = lambda: None
    parent = object()
    source_palette = DELETE_BUTTON_PALETTE if area == 'sidebar_delete' else ADD_BUTTON_PALETTE
    factory = MainWindow._create_header_button if area == 'header' else MainWindow._create_sidebar_button
    control = factory(parent, 'Visible command', callback, style='RoundedAdd.TButton',
                      palette=source_palette, icon_name='new')
    options = control.kwargs
    assert options['command'] is callback and options['text'] == 'Visible command'
    palette = options['palette']
    background = colors.HEADER_SURFACE if area == 'header' else colors.SIDEBAR_SURFACE
    assert palette.normal == (background, background)
    assert palette.hover != palette.normal and palette.pressed != palette.hover
    assert palette.disabled != palette.normal and palette.focus_border != background
    if area == 'header':
        assert palette is HEADER_COMMAND_PALETTE
        assert options['icon_size'] == 79 and options['square_size'] == 86
        assert options['tooltip_text'] == 'Visible command'
    else:
        assert options['icon_size'] == 40 and options['minimum_height'] == 52
        assert options['horizontal_padding'] == 18 and not options['icon_only']
        assert palette.hover == (colors.DEEP_NAVY, colors.SHELL_CYAN) and palette.focus_border == colors.SHELL_CYAN


def test_new_shell_artwork_is_about_ten_percent_larger_and_undistorted() -> None:
    """Measure approved source alpha bounds, not a pixel-perfect screenshot."""
    with Image.open(action_icon_path('new')) as source:
        fitted = AssetImageLoader._full_asset_safe(source.convert('RGBA'))
    bbox = fitted.getchannel('A').point(lambda a: 255 if a >= 8 else 0).getbbox()
    extent = max(bbox[2] - bbox[0], bbox[3] - bbox[1])
    assert 71 <= extent * 79 / max(fitted.size) <= 73
    assert 35 <= extent * 40 / max(fitted.size) <= 37
    assert 1.09 < 79 / 72 < 1.11 and 1.10 < 40 / 36 < 1.12
    assert 86 > 79 > 0 and 52 >= 40 + 12
    assert len({action_icon_path(name) for name in ('new', 'open', 'save', 'save_as')}) == 4


def test_project_summary_metadata_uses_distinct_rows_and_preserves_full_values(monkeypatch) -> None:
    """Summary growth stays scrollable; label/value pairs must not overlap one cell."""
    import ui.widgets.project_summary as view
    from core.project import Project

    class Label(_DummyWidget):
        """Retain grid positions just as grid_remove/grid restore do in Tk."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.cell = {}

        def grid(self, **kwargs):
            self.cell.update(kwargs)
            self.visible = True

        def grid_remove(self):
            self.visible = False

    class Variable:
        """Hold complete project values without opening a Tcl interpreter."""
        def __init__(self): self.value = ''
        def set(self, value): self.value = value
        def get(self): return self.value

    monkeypatch.setattr(view.ttk.Frame, '__init__', _DummyWidget.__init__)
    monkeypatch.setattr(view.ttk.Frame, 'columnconfigure', _DummyWidget.columnconfigure)
    monkeypatch.setattr(view.ttk, 'Label', Label)
    monkeypatch.setattr(view.tk, 'StringVar', Variable)
    summary = view.ProjectSummary(object(), Translator('tr').translate)
    project = Project(name='Long project', description='A' * 10000, notes='B' * 10000)
    summary.set_project(project)
    assert summary._values['description'].get() == project.description
    assert summary._values['notes'].get() == project.notes
    cells = [(label.cell['row'], label.cell['column'])
             for label in (*summary._field_labels.values(), *summary._value_labels.values())]
    assert len(set(cells)) == 10
    assert all(label.visible for label in summary._value_labels.values())
    summary.clear()
    assert all(not label.visible for label in summary._value_labels.values())
