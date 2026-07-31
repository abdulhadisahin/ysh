"""Display-independent tests for YSH application startup lifecycle behavior."""

from __future__ import annotations

import app as application_module
from app import YSHApplication


class _FakeMainWindow:
    """Records startup lifecycle calls without creating a Tkinter window."""

    instance: _FakeMainWindow | None = None

    def __init__(
        self,
        root: object,
        project_service: object,
        on_close: object,
    ) -> None:
        """Store startup dependencies for lifecycle verification."""
        self.root = root
        self.project_service = project_service
        self.on_close = on_close
        _FakeMainWindow.instance = self


class _FakeRoot:
    """Records the application-owned Tk mainloop without creating a display."""

    def __init__(self) -> None:
        """Create a root with no mainloop call recorded."""
        self.mainloop_called = False

    def mainloop(self) -> None:
        """Record application entry into the Tkinter event loop."""
        self.mainloop_called = True


def test_application_run_initializes_then_runs_main_window(
    monkeypatch: object,
) -> None:
    """Application startup initializes dependencies before running one main window."""
    application = YSHApplication.__new__(YSHApplication)
    application._project_service = object()
    application._main_window = None
    application._root = None
    initialized = False

    def initialize_application() -> None:
        """Record completion of application initialization."""
        nonlocal initialized
        initialized = True

    monkeypatch.setattr(application, "_initialize_application", initialize_application)
    monkeypatch.setattr(application_module, "MainWindow", _FakeMainWindow)
    monkeypatch.setattr(application_module.tk, "Tk", _FakeRoot)

    application.run()

    assert initialized
    assert _FakeMainWindow.instance is not None
    assert _FakeMainWindow.instance.root is application._root
    assert application._root.mainloop_called
