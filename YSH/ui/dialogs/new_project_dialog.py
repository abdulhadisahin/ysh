"""TTK dialog for creating a new project."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from i18n.translator import Translator
from ui.widgets.project_family_choice import ProjectFamilyChoice
from ui.theme.spacing import LG, MD, SM
from core.project_family import FAMILY_KEYS


class NewProjectDialog:
    """Collect project metadata and return it to the caller synchronously."""

    def __init__(
        self,
        parent: tk.Misc,
        translate: Callable[[str], str] | None = None,
        localization_owner: object | None = None,
    ) -> None:
        """Create and display a modal dialog for a new project."""
        self._translate = translate or Translator().translate
        self._localization_owner = localization_owner
        self.engineering_context=None
        self.result: tuple[str, str, str, str] | None = None
        self._dialog = tk.Toplevel(parent)
        self._dialog.title(self._translate("menu.file.new_project"))
        self._dialog.transient(parent)
        self._dialog.resizable(False, False)
        self._dialog.protocol("WM_DELETE_WINDOW", self._cancel)
        self._create_widgets()
        self._dialog.grab_set()
        self._dialog.wait_visibility()
        self._dialog.lift()
        self._name_entry.focus_set()
        self._dialog.bind("<Return>", self._submit)
        self._dialog.bind("<Control-Return>", self._submit)
        self._dialog.bind("<Escape>", self._cancel)
        if localization_owner is not None:
            register = getattr(localization_owner, "register_localizable", None)
            if callable(register):
                register(self)

    def show(self) -> tuple[str, str, str, str] | None:
        """Wait for completion and return normalized metadata or ``None``."""
        self._dialog.wait_window()
        return self.result

    def _create_widgets(self) -> None:
        content = ttk.Frame(self._dialog, style="Dialog.TFrame", padding=LG)
        content.grid(row=0, column=0, sticky="nsew")
        content.columnconfigure(1, weight=1)

        self._name_label = ttk.Label(content, text="")
        self._name_label.grid(
            row=0,
            column=0,
            sticky="w",
        )
        self._name_entry = ttk.Entry(content, width=54)
        self._name_entry.grid(row=0, column=1, sticky="ew", padx=(MD, 0))

        self._family_choice = ProjectFamilyChoice(content, self._translate,label_key='project.system')
        self._family_choice.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(MD, 0))
        controller=getattr(self._localization_owner,'_engineering_context_controller',None)
        self._catalog=controller.catalog if controller is not None else None
        self._fluid_records={}
        self._fluid_label=ttk.Label(content,text='')
        self._fluid_label.grid(row=2,column=0,sticky='w',pady=(SM,0))
        self._fluid_choice=ttk.Combobox(content,state='disabled',width=36)
        self._fluid_choice.grid(row=2,column=1,sticky='ew',padx=(MD,0),pady=(SM,0))
        self._family_choice.choice.bind('<<ComboboxSelected>>',self._refresh_fluids,add='+')
        self._description_label = ttk.Label(content, text="")
        self._description_label.grid(row=3,column=0,sticky='nw',pady=(MD,0))
        self._description_text = tk.Text(content,width=54,height=4,wrap='word')
        self._description_text.grid(row=3,column=1,sticky='ew',padx=(MD,0),pady=(MD,0))
        actions = ttk.Frame(content)
        actions.grid(row=4, column=1, sticky="e", pady=(LG, 0))
        self._cancel_button = ttk.Button(actions, command=self._cancel, style="Neutral.TButton")
        self._cancel_button.pack(
            side="left"
        )
        self._submit_button = ttk.Button(actions, command=self._submit, style="Success.TButton")
        self._submit_button.pack(
            side="left",
            padx=(SM, 0),
        )
        self.refresh_texts()

    def _refresh_fluids(self,event=None):
        selected=self._fluid_records.get(self._fluid_choice.get())
        index=self._family_choice.choice.current()
        family=tuple(FAMILY_KEYS)[index] if 0 <= index < len(FAMILY_KEYS) else None
        records=self._catalog.project_fluids(family) if self._catalog is not None else ()
        self._fluid_records={self._translate('engineering.none'):None}
        for fluid in records:
            label=self._translate('engineering.fluid.seawater') if family=='seawater' else fluid.name_tr
            if label in self._fluid_records:label+=' · '+fluid.code
            self._fluid_records[label]=fluid
        if family == 'seawater':
            # Classification selects the existing canonical seawater identity only.
            canonical=next((r for r in records if r.code=='SEAWATER'),None)
            selected=canonical or (records[0] if len(records)==1 else None)
            self._fluid_records={label:fluid for label,fluid in self._fluid_records.items()
                                 if fluid is not None and selected is not None and fluid.id==selected.id}
        self._fluid_choice.configure(values=tuple(self._fluid_records),state='readonly' if records else 'disabled')
        self._fluid_choice.set(next((label for label,fluid in self._fluid_records.items()
                                    if selected is not None and fluid is not None and fluid.id==selected.id),
                                   self._translate('engineering.none')))
        if family == 'seawater':self._fluid_choice.configure(state='disabled')

    def refresh_texts(self) -> None:
        """Refresh this open dialog without altering entered project metadata."""
        self._dialog.title(self._translate("menu.file.new_project"))
        self._name_label.configure(text=f"{self._translate('project.name')}:")
        self._description_label.configure(text=self._translate('project.description_optional'))
        self._family_choice.refresh_texts()
        self._fluid_label.configure(text=self._translate('engineering.fluid'))
        self._refresh_fluids()
        self._cancel_button.configure(text=self._translate("common.cancel"))
        self._submit_button.configure(text=self._translate("common.save"))

    def _submit(self, event: tk.Event[tk.Misc] | None = None) -> str:
        """Validate and submit the entered project details."""
        name = self._name_entry.get().strip()
        if not name:
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate("validation.required", field_name=self._translate("field.project_name")),
                parent=self._dialog,
            )
            self._name_entry.focus_set()
            return "break"
        description = self._description_text.get("1.0", "end-1c").strip()
        # New projects have one optional description; historical notes are
        # untouched by this creation-only dialog and the four-value API stays.
        notes = ''
        family = self._family_choice.selected()
        if family is None:
            return "break"
        # Never retain an old cross-family selection after a system change.
        self._refresh_fluids()
        fluid=self._fluid_records.get(self._fluid_choice.get())
        if family == 'seawater' and fluid is None:
            messagebox.showerror(self._translate('dialog.error'),self._translate('seawater.fluid_required'),parent=self._dialog)
            return 'break'
        if fluid is not None:
            from engineering.system_context import SystemContext,ContextReference
            self.engineering_context=SystemContext().changed(fluid=ContextReference(
                id=fluid.id,code=fluid.code,name_tr=fluid.name_tr,name_en=fluid.name_en))
            if family == 'seawater':
                from services.system_context_service import DEFAULT_SYSTEMS, reference
                system=next(row for row in DEFAULT_SYSTEMS if row.code=='SEA_WATER')
                self.engineering_context=self.engineering_context.changed(system=reference(system))
        self.result = (name, description, notes, family)
        self._dialog.grab_release()
        self._destroy()
        return "break"

    def _cancel(self, event: tk.Event[tk.Misc] | None = None) -> str:
        """Close the dialog without submitting project details."""
        self._dialog.grab_release()
        self._destroy()
        return "break"

    def _destroy(self) -> None:
        """Unregister then destroy the dialog exactly once."""
        if self._localization_owner is not None:
            unregister = getattr(self._localization_owner, "unregister_localizable", None)
            if callable(unregister):
                unregister(self)
        self._dialog.destroy()
