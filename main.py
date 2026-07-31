"""Primary executable entry point for the YSH desktop application."""

from __future__ import annotations

import sys
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import messagebox


def _configure_application_path() -> None:
    """Make the YSH application package directory importable from the repository."""
    application_directory = Path(__file__).resolve().parent / "YSH"
    application_path = str(application_directory)
    if application_path not in sys.path:
        sys.path.insert(0, application_path)


def main() -> None:
    """Configure imports, create the application, and run its lifecycle."""
    print("START: main.py")
    _configure_application_path()
    try:
        from app import YSHApplication

        application = YSHApplication()
        print("START: application created")
        application.run()
    except Exception as error:
        traceback.print_exc()
        _show_startup_error(error)
        raise


def _show_startup_error(error: Exception) -> None:
    """Show a startup error dialog when a graphical display is available."""
    error_root: tk.Tk | None = None
    try:
        error_root = tk.Tk()
        error_root.withdraw()
        messagebox.showerror("YSH Startup Error", str(error), parent=error_root)
    except tk.TclError:
        return
    finally:
        if error_root is not None:
            error_root.destroy()


if __name__ == "__main__":
    main()
