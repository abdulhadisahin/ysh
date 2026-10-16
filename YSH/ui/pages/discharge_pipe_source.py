"""Shared pipe source choices; discovery is independent of applied hydraulic values."""
from __future__ import annotations

from collections.abc import Callable
import logging
import tkinter as tk
from tkinter import ttk
from uuid import UUID

from engineering.pipe_design.rules import DesignStatus
from engineering.pipe_design.transfer import PipeInputMode, PipeLinkStatus
from engineering.pipe_design.v2_models import PipeSelection
from engineering.validation import ValidationError
from i18n.validation import render_validation_issue
from services.discharge_workflow import DischargeWorkflow
from ui.formatting import format_user_number


class DischargePipeSourcePanel(ttk.LabelFrame):
    """Expose explicit source/mode decisions and separate link notices from warnings."""

    def __init__(self, parent: tk.Misc, workflow: DischargeWorkflow,
                 translate: Callable[[str], str], changed: Callable[[bool], None]) -> None:
        """Build mode/source choices and explicit update/keep decisions for either owner."""
        super().__init__(parent, padding=8)
        self.workflow = workflow
        self._translate = translate
        self._changed = changed
        self.source_factory: Callable[[PipeSelection | None], PipeSelection] | None = None
        self._selected_id: UUID | None = None
        self._pending_link = False
        self._source_ids: list[UUID] = []
        self._mode = tk.StringVar()
        self._source = tk.StringVar()
        self._status = tk.StringVar()
        self._details = tk.StringVar()
        self._error = tk.StringVar()
        self._mode_box = ttk.Combobox(self, textvariable=self._mode, state="readonly", width=32)
        self._mode_box.grid(row=0, column=0, sticky="w", padx=(0, 8), pady=3)
        self._mode_box.bind("<<ComboboxSelected>>", self._choose_mode)
        self._source_box = ttk.Combobox(self, textvariable=self._source, state="readonly", width=48)
        self._source_box.grid(row=1, column=0, columnspan=2, sticky="ew", pady=3)
        self._source_box.bind("<<ComboboxSelected>>", self._choose_source)
        self._buttons: dict[str, ttk.Button] = {}
        for column, (key, command) in enumerate((
            ("update", self._update), ("keep", self._keep),
        )):
            button = ttk.Button(self, command=command)
            button.grid(row=2, column=column, sticky="w", padx=(0, 8), pady=3)
            self._buttons[key] = button
        ttk.Label(self, textvariable=self._status, wraplength=600).grid(
            row=0, column=1, columnspan=3, sticky="w")
        ttk.Label(self, textvariable=self._details, wraplength=720).grid(
            row=3, column=0, columnspan=4, sticky="w")
        ttk.Label(self, textvariable=self._error, wraplength=720).grid(
            row=4, column=0, columnspan=4, sticky="w")
        self.columnconfigure(1, weight=1)
        self.refresh_texts()

    def refresh_texts(self) -> None:
        """Translate status/mode without changing source, snapshots or calculations."""
        self.configure(text=self._translate("discharge.pipe.section"))
        self._mode_box.configure(values=(self._translate("discharge.pipe.manual"),
                                        self._translate("discharge.pipe.linked")))
        for key, button in self._buttons.items():
            button.configure(text=self._translate(f"discharge.pipe.{key}"))
        self.render()

    def render(self) -> None:
        """Render applied metadata, retaining historical details when stale/missing."""
        state = self.workflow.pipe_input
        self._mode_box.current(1 if state.mode is PipeInputMode.LINKED or getattr(self, "_pending_link", False) else 0)
        sources = self.workflow.available_sources()
        self._source_ids = [s.selection_id for s in sources]
        if (self._selected_id not in self._source_ids and state.snapshot
                and state.snapshot.source_selection_id in self._source_ids):
            self._selected_id = state.snapshot.source_selection_id
        labels = [self._label(s, index) for index, s in enumerate(sources, 1)]
        self._source_box.configure(values=labels)
        if self._selected_id in self._source_ids:
            self._source_box.current(self._source_ids.index(self._selected_id))
        else:
            self._selected_id = None
            self._source.set("")
        status = self._translate(f"discharge.pipe.status.{state.status.value}")
        if state.kept_current:
            status += " · " + self._translate("discharge.pipe.kept")
        self._status.set(status)
        snapshot = state.snapshot
        details = self._translate("discharge.pipe.help" if sources else "discharge.pipe.no_available")
        if snapshot:
            values = snapshot.values
            details = (f"{values.standard_code or '—'} · {values.nominal_diameter or '—'} · "
                f"NPS {values.nps or '—'} · Schedule {values.schedule or '—'} · "
                f"OD {self._number(values.outside_diameter_mm)} mm · "
                f"t {self._number(values.wall_thickness_mm)} mm · "
                f"Di {format_user_number(values.actual_internal_diameter_mm)} mm · "
                f"Q {format_user_number(values.flow_rate_m3_h)} m³/h · "
                f"{self._translate('discharge.pipe.revision')} {snapshot.source_revision}")
            if snapshot.upstream_status is not DesignStatus.SUCCESS:
                details += " · " + self._translate("discharge.pipe.provisional")
        self._details.set(details)
        current = self.workflow.source(snapshot.source_selection_id) if snapshot else None
        self._buttons["update"].configure(state="normal" if current and current.selection_id in self._source_ids else "disabled")
        self._buttons["keep"].configure(state="disabled" if state.status in (
            PipeLinkStatus.MANUAL, PipeLinkStatus.LINKED_SYNCED) else "normal")
        if "publish" in self._buttons:  # Legacy internal adapters/tests only.
            self._buttons["publish"].configure(state="normal" if self.source_factory else "disabled")
        selected = self.workflow.source(self._selected_id) if self._selected_id else None
        if "link" in self._buttons:
            self._buttons["link"].configure(state="normal" if selected and selected.selected_pipe else "disabled")

    @staticmethod
    def _number(value: float | None) -> str:
        return format_user_number(value) if value is not None else "—"

    def reset_choice(self) -> None:
        """Clear transient source-choice intent at project/page boundaries."""
        self._pending_link = False
        self._selected_id = None
        self._error.set("")
        self.render()

    def _label(self, source: PipeSelection, index: int) -> str:
        diameter = source.actual_internal_diameter_mm
        value = format_user_number(diameter) if diameter is not None else "—"
        return (f"{index}. {source.selected_standard_code or '—'} · "
                f"{source.nominal_diameter or '—'} · Di {value} mm · "
                f"Q {format_user_number(source.flow_rate_m3_h)} m³/h · "
                f"{self._translate('discharge.pipe.revision')} {source.revision}")

    def _choose_source(self, _event: object = None) -> None:
        index = self._source_box.current()
        self._selected_id = self._source_ids[index] if index >= 0 else None
        if getattr(self, "_pending_link", False) or self.workflow.pipe_fields_readonly:
            self._link()  # A visible user choice is an explicit apply action.
        else:
            self.render()

    def _choose_mode(self, _event: object = None) -> None:
        if self._mode_box.current() == 1:
            sources = self.workflow.available_sources()
            if not sources:
                self._pending_link = False
                self._error.set(self._translate("discharge.pipe.no_available"))
                self.render()
                return
            if self._selected_id not in {s.selection_id for s in sources}:
                self._selected_id = sources[0].selection_id if len(sources) == 1 else None
            if self._selected_id is None:
                self._pending_link = True
                self._error.set(self._translate("discharge.pipe.select_source"))
                self.render()
            else:
                self._link()
        elif self.workflow.pipe_fields_readonly:
            self._pending_link = False
            self.workflow.manual()
            self._finish(True)
        else:
            self._pending_link = False
            self.render()

    def _link(self) -> None:
        if self._selected_id is None:
            self._error.set(self._translate("discharge.pipe.select_source"))
            self.render()
            return
        try:
            self.workflow.link(self._selected_id)
            self._pending_link = False
            self._finish(True)
        except ValueError:
            self._error.set(self._translate("discharge.pipe.unavailable"))
            self.render()

    def _publish(self) -> None:
        if self.source_factory is None:
            return
        try:
            previous = self.workflow.source(self._selected_id) if self._selected_id else None
            selection = self.source_factory(previous)
            self.workflow.publish(selection)
            self._selected_id = selection.selection_id
            self._finish(False)
        except ValidationError as error:
            proxy = type("TranslatorProxy", (), {"translate": self._translate})()
            self._error.set(render_validation_issue(error.issue, proxy))
        except Exception:
            logging.getLogger(__name__).exception("Unable to prepare discharge pipe source")
            self._error.set(self._translate("validation.unexpected_error"))

    def _update(self) -> None:
        self.workflow.update()
        self._finish(True)

    def _keep(self) -> None:
        self.workflow.keep_current()
        self._finish(False)

    def _finish(self, inputs_changed: bool) -> None:
        self._error.set("")
        self.render()
        self._changed(inputs_changed)


# The old name remains an import-compatible alias for Phase 8 integrations.
PipeSourcePanel = DischargePipeSourcePanel
