"""Display-independent tests for MainWindow active-project state."""

from __future__ import annotations

from core.project import Project
import ui.main_window as main_window_module
from ui.dialogs.open_project_dialog import OpenProjectDialog
from ui.main_window import MainWindow


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
        self.states: dict[str, str] = {}

    def entryconfigure(self, label: str, state: str) -> None:
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
    assert window._root.title_value == "YSH"
    assert window._project_summary.was_cleared
    assert window._file_menu.states["Close Project"] == "disabled"
    assert window._status_bar.message == "Project closed"


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

    def create_dialog(parent: object, service: object) -> _ResultDialog:
        """Create a result dialog that returns the selected project."""
        return _ResultDialog(parent, service, project)

    monkeypatch.setattr(main_window_module, "OpenProjectDialog", create_dialog)

    window._open_project()

    assert window._active_project == project
    assert window._root.title_value == "YSH - Opened Project"
    assert window._project_summary.project == project
    assert window._file_menu.states["Close Project"] == "normal"
    assert window._status_bar.message == "Project opened successfully"
