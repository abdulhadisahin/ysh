"""Informational, non-selectable Türk Loydu Table 8.9 reference dialog."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from engineering.turk_loydu_table_8_9 import TABLE_8_9_FOOTNOTE, TABLE_8_9_ROWS


class TurkLoyduTable89Dialog:
    """Displays immutable reference values and never changes calculation state."""

    def __init__(self, parent: tk.Misc) -> None:
        dialog = self._dialog = tk.Toplevel(parent)
        dialog.title("Türk Loydu Tablo 8.9 — A ve B Katsayıları")
        dialog.transient(parent)
        body = ttk.Frame(dialog, padding=12)
        body.pack(fill="both", expand=True)
        headings = ("Malzeme", "Sınıf I — A", "Sınıf I — B", "Sınıf II/III — A", "Sınıf II/III — B")
        tree = ttk.Treeview(body, columns=tuple(range(5)), show="headings", selectmode="none", height=6)
        for index, heading in enumerate(headings):
            tree.heading(index, text=heading)
            tree.column(index, width=260 if index == 0 else 110, anchor="w" if index == 0 else "center")
        for row in TABLE_8_9_ROWS:
            tree.insert("", "end", values=(row.material, row.class_i_a, row.class_i_b, row.class_ii_iii_a, row.class_ii_iii_b))
        tree.pack(fill="both", expand=True)
        ttk.Label(body, text=TABLE_8_9_FOOTNOTE, wraplength=780).pack(anchor="w", pady=(10, 0))
        ttk.Label(body, text="Kaynak: Türk Loydu, Bölüm 8, Tablo 8.9.").pack(anchor="w", pady=(4, 0))
        ttk.Button(body, text="Kapat", command=dialog.destroy).pack(anchor="e", pady=(10, 0))
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
