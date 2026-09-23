"""Keep Tkinter importable when a host Tcl probe is unavailable.

The YSH spec explicitly collects the validated Tcl/Tk runtime directories into
PyInstaller's required onedir destinations. Therefore the standard hook's host
probe must not erase the pure-Python ``tkinter`` package search path.
"""

from __future__ import annotations


def pre_find_module_path(_hook_api: object) -> None:
    """Retain normal Tkinter module discovery for the explicit YSH runtime."""
