"""Primary executable entry point for the YSH desktop application."""

from __future__ import annotations

import sys
import traceback
import logging
from pathlib import Path


def _configure_application_path() -> None:
    """Make the YSH application package directory importable from the repository."""
    application_directory = Path(__file__).resolve().parent / "YSH"
    application_path = str(application_directory)
    if application_path not in sys.path:
        sys.path.insert(0, application_path)


_configure_application_path()
from YSH.app import YSHApplication


def main() -> None:
    """Configure imports, create the application, and run its lifecycle."""
    try:
        application = YSHApplication()
        application.run()
    except Exception:
        logging.getLogger(__name__).exception("Uncaught YSH startup exception")
        traceback.print_exc()
        try:
            from tkinter import messagebox
            messagebox.showerror("YSH startup error", "YSH could not start. See %LOCALAPPDATA%\\YSH\\logs\\ysh.log.")
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
