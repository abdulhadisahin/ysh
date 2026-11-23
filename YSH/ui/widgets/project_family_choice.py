"""Explicit localized family choice for project creation and Save As."""
from tkinter import ttk, messagebox
from core.project_family import FAMILY_KEYS
from ui.theme.spacing import MD


class ProjectFamilyChoice(ttk.Frame):
    def __init__(self, parent, translate, *, locked_family=None, label_key='project.family'):
        super().__init__(parent)
        self.tr = translate
        self.locked_family = locked_family
        self.label_key = label_key
        self.columnconfigure(1, weight=1)
        self.label = ttk.Label(self)
        self.label.grid(row=0, column=0, sticky='w', padx=(0, MD))
        self.choice = ttk.Combobox(self, state='readonly', width=30)
        self.choice.grid(row=0, column=1, sticky='ew')
        self.refresh_texts()
        if locked_family is not None:
            self.choice.current(tuple(FAMILY_KEYS).index(locked_family))
            self.choice.configure(state='disabled')

    def refresh_texts(self):
        index = self.choice.current()
        self.label.configure(text=self.tr(self.label_key))
        self.choice.configure(values=tuple(self.tr(k) for k in FAMILY_KEYS.values()))
        if index >= 0:
            self.choice.current(index)

    def selected(self):
        if self.locked_family is not None:
            return self.locked_family
        index = self.choice.current()
        if index < 0:
            messagebox.showerror(self.tr('dialog.error'),
                                 self.tr('validation.project_family_required'),
                                 parent=self.winfo_toplevel())
            self.choice.focus_set()
            return None
        return tuple(FAMILY_KEYS)[index]
