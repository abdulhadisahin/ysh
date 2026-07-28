"""Display-independent tests for MainWindow active-project state."""

from __future__ import annotations

from core.project import Project
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
