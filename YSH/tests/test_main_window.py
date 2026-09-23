"""Display-independent tests for MainWindow active-project state."""

from __future__ import annotations

from core.project import Project
import ui.main_window as main_window_module
from ui.dialogs.open_project_dialog import OpenProjectDialog
from ui.main_window import FILE_MENU_INDEX, MainWindow


class _FakeRoot:
    """Records title changes without creating a graphical window."""

    def __init__(self) -> None:
        """Create an empty title-change record."""
        self.title_value = ""

    def title(self, value: str) -> None:
        """Record the supplied window title."""
        self.title_value = value


class _FakeProjectSummary:
    """Records whether the active-project summary was cleared."""

    def __init__(self) -> None:
        """Create a summary with no clear operation recorded."""
        self.was_cleared = False
        self.project: Project | None = None

    def set_project(self, project: Project) -> None:
        """Record the project supplied for display."""
        self.project = project

    def clear(self) -> None:
        """Record that the summary was cleared."""
        self.was_cleared = True


class _FakeMenu:
    """Records state updates for the File menu."""

    def __init__(self) -> None:
        """Create an empty menu-state record."""
        self.states: dict[int, str] = {}

    def entryconfigure(self, label: int, state: str) -> None:
        """Record the state applied to a menu entry."""
        self.states[label] = state


class _FakeStatusBar:
    """Records status-bar messages without requiring a Tkinter display."""

    def __init__(self) -> None:
        """Create an empty status-message record."""
        self.message = ""

    def set_message(self, message: str) -> None:
        """Record the supplied status message."""
        self.message = message


class _DummyWidget:
    """Minimal widget stub that supports common layout methods."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Store constructor arguments for inspection by tests."""
        self.args = args
        self.kwargs = kwargs

    def pack(self, *args: object, **kwargs: object) -> None:
        """Accept pack calls without side effects."""

    def grid(self, *args: object, **kwargs: object) -> None:
        """Accept grid calls without side effects."""

    def columnconfigure(self, *args: object, **kwargs: object) -> None:
        """Accept columnconfigure calls without side effects."""

    def rowconfigure(self, *args: object, **kwargs: object) -> None:
        """Accept rowconfigure calls without side effects."""

    def configure(self, *args: object, **kwargs: object) -> None:
        """Accept configure calls without side effects."""


class _DummyTreeview(_DummyWidget):
    """Stores inserted rows so the window can refresh projects."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize an empty treeview stub."""
        super().__init__(*args, **kwargs)
        self._rows: list[tuple[object, ...]] = []

    def heading(self, *args: object, **kwargs: object) -> None:
        """Accept heading configuration calls."""

    def column(self, *args: object, **kwargs: object) -> None:
        """Accept column configuration calls."""

    def bind(self, *args: object, **kwargs: object) -> None:
        """Accept event bindings without a graphical display."""

    def insert(self, *args: object, **kwargs: object) -> None:
        """Store a row entry for later inspection."""
        self._rows.append(args)

    def get_children(self) -> tuple[object, ...]:
        """Return stored row identifiers."""
        return tuple(str(row[2]) for row in self._rows if len(row) > 2)

    def delete(self, item_id: object) -> None:
        """Remove a stored row by identifier."""
        self._rows = [row for row in self._rows if str(row[2]) != str(item_id)]


class _FakeDialogWindow:
    """Records lifecycle calls made by the Open Project dialog."""

    def __init__(self) -> None:
        """Create a dialog window with no lifecycle calls recorded."""
        self.was_released = False
        self.was_destroyed = False

    def grab_release(self) -> None:
        """Record release of the dialog grab."""
        self.was_released = True

    def destroy(self) -> None:
        """Record destruction of the dialog window."""
        self.was_destroyed = True


class _FakeProjectTree:
    """Returns one selected project identifier without a Tkinter display."""

    def __init__(self, project: Project) -> None:
        """Create a tree containing the supplied selected project."""
        self._project = project

    def selection(self) -> tuple[str]:
        """Return the selected project row identifier."""
        return (str(self._project.id),)


class _FakeProjectService:
    """Returns a known project through the service retrieval interface."""

    def __init__(self, project: Project) -> None:
        """Create a service fixture for the supplied project."""
        self._project = project

    def get_project(self, project_id: object) -> Project:
        """Return the known project after verifying its identifier."""
        assert project_id == self._project.id
        return self._project


class _ResultDialog:
    """Returns a preselected project through the Open Project dialog contract."""

    def __init__(self, parent: object, service: object, project: Project) -> None:
        """Capture the dialog dependencies and configured result."""
        self.parent = parent
        self.service = service
        self._project = project

    def show(self) -> Project:
        """Return the configured selected project."""
        return self._project


def test_main_window_closes_active_project_without_display() -> None:
    """Closing an active project resets state and presentation collaborators."""
    window = MainWindow.__new__(MainWindow)
    window._active_project = Project(name="Active Project")
    window._root = _FakeRoot()
    window._project_summary = _FakeProjectSummary()
    window._file_menu = _FakeMenu()
    window._status_bar = _FakeStatusBar()

    window._close_project()

    assert window._active_project is None
    assert window._root.title_value == "YSH — Fuel System Engineering"
    assert window._project_summary.was_cleared
    assert window._file_menu.states[FILE_MENU_INDEX["close"]] == "disabled"
    assert window._status_bar.message == "Project closed"


def test_main_window_initializes_projects_tree(monkeypatch: object) -> None:
    """Creating the window registers the projects tree used by refresh operations."""

    class _FakeProjectService:
        def list_projects(self) -> list[Project]:
            return []

    class _FakeMenuBar(_DummyWidget):
        def add_command(self, *args: object, **kwargs: object) -> None:
            return None

        def add_separator(self, *args: object, **kwargs: object) -> None:
            return None

        def add_cascade(self, *args: object, **kwargs: object) -> None:
            return None

    class _DummyScrollableTreeview(_DummyWidget):
        """Expose a fake Treeview through the reusable container contract."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            self.tree = _DummyTreeview(*args, **kwargs)

    class _DummyStringVar:
        """Provide the project-search variable API without a Tk display."""

        def __init__(self, value: str = "") -> None:
            self.value = value

        def get(self) -> str:
            return self.value

        def trace_add(self, *args: object) -> None:
            del args

    class _TestRoot(_FakeRoot):
        def __init__(self) -> None:
            self.title_value = ""
            self.menu = None
            self.geometry_value = None
            self.minsize_value = None

        def configure(self, **kwargs: object) -> None:
            if "menu" in kwargs:
                self.menu = kwargs["menu"]

        def geometry(self, value: str) -> None:
            self.geometry_value = value

        def minsize(self, width: int, height: int) -> None:
            self.minsize_value = (width, height)

        def protocol(self, *args: object, **kwargs: object) -> None:
            return None

        def iconname(self, *args: object, **kwargs: object) -> None:
            return None

        def columnconfigure(self, *args: object, **kwargs: object) -> None:
            return None

        def rowconfigure(self, *args: object, **kwargs: object) -> None:
            return None

    fake_root = _TestRoot()

    monkeypatch.setattr(main_window_module, "tk", type("TkStub", (), {
        "Menu": _FakeMenuBar,
        "Misc": object,
        "StringVar": _DummyStringVar,
    }))
    monkeypatch.setattr(main_window_module.ttk, "Entry", _DummyWidget)
    monkeypatch.setattr(main_window_module.ttk, "Frame", _DummyWidget)
    monkeypatch.setattr(main_window_module.ttk, "LabelFrame", _DummyWidget)
    monkeypatch.setattr(main_window_module.ttk, "Button", _DummyWidget)
    monkeypatch.setattr(main_window_module.ttk, "Label", _DummyWidget)
    monkeypatch.setattr(main_window_module.ttk, "Treeview", _DummyTreeview)
    monkeypatch.setattr(
        main_window_module,
        "create_rounded_button",
        lambda *args, **kwargs: _DummyWidget(*args, **kwargs),
    )
    monkeypatch.setattr(main_window_module, "ProjectSummary", lambda *args, **kwargs: _DummyWidget(*args, **kwargs))
    monkeypatch.setattr(main_window_module, "StatusBar", lambda *args, **kwargs: _DummyWidget(*args, **kwargs))
    monkeypatch.setattr(main_window_module, "ScrollablePageHost", lambda *args, **kwargs: _DummyWidget(*args, **kwargs))
    monkeypatch.setattr(main_window_module, "ScrollableTreeview", _DummyScrollableTreeview)
    monkeypatch.setattr(main_window_module, "OpenProjectDialog", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window_module, "NewProjectDialog", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window_module, "MaterialLibraryDialog", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window_module, "PipeSizeLibraryDialog", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_window_module, "ConstantsLibraryDialog", lambda *args, **kwargs: None)

    window = MainWindow(
        root=fake_root,
        project_service=_FakeProjectService(),
        on_close=lambda: None,
    )

    assert hasattr(window, "_projects_tree")
    assert window._projects_tree is not None


def test_open_project_dialog_sets_result_before_closing() -> None:
    """Selecting a row sets the dialog result through its shared open path."""
    project = Project(name="Openable Project")
    dialog = OpenProjectDialog.__new__(OpenProjectDialog)
    dialog._project_service = _FakeProjectService(project)
    dialog._projects_tree = _FakeProjectTree(project)
    dialog._dialog = _FakeDialogWindow()
    dialog.result = None

    dialog._open_selected()

    assert dialog.result == project
    assert dialog._dialog.was_released
    assert dialog._dialog.was_destroyed


def test_main_window_activates_dialog_result(monkeypatch: object) -> None:
    """A dialog result activates the selected project in the main window."""
    project = Project(name="Opened Project")
    window = MainWindow.__new__(MainWindow)
    window._root = _FakeRoot()
    window._project_summary = _FakeProjectSummary()
    window._file_menu = _FakeMenu()
    window._status_bar = _FakeStatusBar()
    window._project_service = object()
    window._active_project = None

    def create_dialog(
        parent: object,
        service: object,
        translate: object,
        localization_owner: object,
    ) -> _ResultDialog:
        """Create a result dialog that returns the selected project."""
        del translate, localization_owner
        return _ResultDialog(parent, service, project)

    monkeypatch.setattr(main_window_module, "OpenProjectDialog", create_dialog)

    window._open_project()

    assert window._active_project == project
    assert window._root.title_value == "YSH — Fuel System Engineering — Opened Project"
    assert window._project_summary.project == project
    assert window._file_menu.states[FILE_MENU_INDEX["close"]] == "normal"
    assert window._status_bar.message == "Project opened successfully"


def test_refresh_projects_preserves_active_workspace_state() -> None:
    """Refresh reloads metadata only and does not alter an active project."""
    project = Project(name="Refresh Project")

    class _Persistence:
        def get_all_projects(self) -> list[Project]:
            return [project]

    window = MainWindow.__new__(MainWindow)
    window._project_persistence_service = _Persistence()
    window._project_service = object()
    window._projects_tree = _DummyTreeview()
    window._active_project = project
    window._pages = {}

    window._refresh_projects()

    assert window._active_project == project
    assert len(window._projects_tree._rows) == 1


def test_create_project_clears_pages_then_activates_persistence_project() -> None:
    """The New Project handler clears all pages and activates a clean project."""
    project = Project(name="New Project")

    class _Persistence:
        is_dirty = False

        def create_project(self, *args: object) -> Project:
            return project

        def open(self, project_id: object) -> tuple[Project, dict[str, object]]:
            assert project_id == project.id
            return project, {"schema_version": 1}

        def get_all_projects(self) -> list[Project]:
            return [project]

    class _Page:
        def __init__(self) -> None:
            self.cleared = False

        def clear_state(self) -> None:
            self.cleared = True

        def load_state(self, state: dict[str, object]) -> None:
            assert state == {}

        def export_state(self) -> dict[str, object]:
            return {}

    page = _Page()
    window = MainWindow.__new__(MainWindow)
    window._project_persistence_service = _Persistence()
    window._project_service = object()
    window._active_project = None
    window._pages = {"pipe_design": page}
    window._projects_tree = _DummyTreeview()
    window._root = _FakeRoot()
    window._project_summary = _FakeProjectSummary()
    window._file_menu = _FakeMenu()
    window._status_bar = _FakeStatusBar()

    assert window._create_project("New Project", "", "") is True
    assert page.cleared is True
    assert window._active_project == project
    assert window._root.title_value == "YSH — Fuel System Engineering — New Project"


def test_empty_project_activation_clears_existing_page_values() -> None:
    """Opening a valid project with no state starts from clean page defaults."""
    project = Project(name="Empty Project")

    class _Persistence:
        def has_saved_state(self, project_id: object) -> bool:
            assert project_id == project.id
            return False

        def open(self, project_id: object) -> tuple[Project, dict[str, object]]:
            assert project_id == project.id
            return project, {"schema_version": 1}

    class _Page:
        def __init__(self) -> None:
            self.cleared = False

        def clear_state(self) -> None:
            self.cleared = True

        def export_state(self) -> dict[str, object]:
            return {"previous": "A"}

    page = _Page()
    window = MainWindow.__new__(MainWindow)
    window._project_persistence_service = _Persistence()
    window._active_project = Project(name="Project A")
    window._pages = {"pipe_design": page}
    window._root = _FakeRoot()
    window._project_summary = _FakeProjectSummary()
    window._file_menu = _FakeMenu()
    window._status_bar = _FakeStatusBar()

    window._activate_project(project)

    assert page.cleared is True
    assert window._active_project == project
