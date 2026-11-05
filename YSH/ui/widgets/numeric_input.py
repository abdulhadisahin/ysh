"""Explicit compact numeric controls; retain native ttk behavior and styles."""
from tkinter import ttk
from ui.theme.spacing import NUMERIC_INPUT_WIDTH, SM


def numeric_entry(parent, **options):
    """Create a native Entry with shared numeric sizing, without parsing its value."""
    entry = ttk.Entry(parent, width=NUMERIC_INPUT_WIDTH, **options)
    entry.numeric_width_class = "compact"
    return entry


def numeric_pair(parent, *, unit, unit_style="", **options):
    """Keep a numerical field and its unit together even in mixed-width grids."""
    pair = ttk.Frame(parent)
    entry = numeric_entry(pair, **options)
    entry.pack(side="left")
    label = ttk.Label(pair, text=unit, style=unit_style)
    label.pack(side="left", padx=(SM, 0))
    return pair, entry
