"""Optional project context selectors; no property injection or calculation calls."""
from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import ttk

from engineering.system_context import SystemContext
from services.system_context_service import SystemContextService


class SystemContextPanel(ttk.LabelFrame):
    """Keep system, circuit and fluid as separate, clearable selections."""

    def __init__(self, parent: tk.Misc, service: SystemContextService,
                 translate: Callable[[str], str], changed: Callable[[SystemContext], None], *,
                 compact: bool = False) -> None:
        """Build a nonblocking, project-owned context strip."""
        super().__init__(parent, padding=8)
        self._service, self._translate, self._changed = service, translate, changed
        self._context = SystemContext()
        self._compact = compact
        self._values = {key: tk.StringVar() for key in ("system", "circuit", "fluid")}
        self._labels, self._selectors, self._choices = {}, {}, {}
        for column, key in enumerate(self._values):
            self.columnconfigure(column * 2 + 1 if compact else column, weight=1)
            self._labels[key] = ttk.Label(self)
            self._labels[key].grid(row=0, column=column * 2 if compact else column,
                                   sticky="w", padx=(0, 8) if compact else 0, pady=0 if compact else (0, 4))
            combo = ttk.Combobox(self, textvariable=self._values[key], state="readonly", width=24)
            combo.grid(row=0 if compact else 1, column=column * 2 + 1 if compact else column,
                       sticky="ew", padx=(0, 12))
            combo.bind("<<ComboboxSelected>>", self._select)
            self._selectors[key] = combo
        self._status = ttk.Label(self, wraplength=900, justify="left")
        self._status.grid(row=1 if compact else 2, column=0, columnspan=6 if compact else 3,
                          sticky="w", pady=(4, 0))
        self._module_notice = ""
        self.refresh_texts()

    def set_service(self, service: SystemContextService) -> None:
        """Attach configured master-data repositories without changing selected IDs."""
        self._service = service
        self.refresh_texts()

    def load(self, context: SystemContext) -> None:
        """Display saved context without dirty events, substitutions or calculations."""
        self._context = context
        self.refresh_texts()

    def set_module_notice(self, notice: str) -> None:
        """Expose disabled module reasons outside disabled navigation controls."""
        self._module_notice = notice
        self._render_status()

    def refresh_texts(self) -> None:
        """Localize and render cached small catalogs; no repeated property lookups."""
        tr = self._translate
        self.configure(text=tr("context.title"))
        rows = {"system": self._service.systems(),
                "circuit": self._service.circuits(self._context.system_id),
                "fluid": self._service.fluids()}
        for key in self._values:
            self._labels[key].configure(text=tr("context.profile" if key == "system" else f"context.{key}"))
            choices = {tr(f"context.none.{key}"): None}
            for row in rows[key]:
                language = getattr(getattr(tr, "__self__", None), "language", "en")
                name = row.name_en if language == "en" else row.name_tr
                choices[f"{name or row.name_tr} [{row.code}]"] = row.id
            saved = getattr(self._context, key)
            selected = next((name for name, identity in choices.items() if saved and identity == saved.id), None)
            if saved and selected is None:
                selected = f"{saved.name_tr} [{saved.code}] — {tr('context.source_missing')}"
                choices[selected] = saved.id
            self._choices[key] = choices
            self._selectors[key].configure(values=tuple(choices))
            self._values[key].set(selected or next(iter(choices)))
        self._render_status()

    def _render_status(self) -> None:
        messages = [self._translate(f"context.{issue.field}") + ": " + self._translate(issue.reason_key)
                    for issue in self._service.issues(self._context)]
        if self._context.system is None:
            messages.append(self._translate("context.legacy"))
        if self._module_notice:
            messages.append(self._module_notice)
        self._status.configure(text="\n".join(messages))

    def _select(self, _event: object = None) -> None:
        try:
            ids = {f"{key}_id": self._choices[key][var.get()] for key, var in self._values.items()}
            context = self._service.select(self._context, **ids)
        except ValueError:
            self._status.configure(text=self._translate("context.invalid_selection"))
            return
        if context != self._context:
            self._context = context
            self.refresh_texts()
            self._changed(context)
