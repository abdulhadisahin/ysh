"""TTK calculation page for fuel-transfer pump capacity estimates."""

from __future__ import annotations

import tkinter as tk
import logging
from collections.abc import Callable, Sequence
from tkinter import messagebox, ttk
from uuid import UUID

from core.pump_reference import PumpReference
from engineering.precision import format_engineering_value
from engineering.input_parsing import parse_engineering_float
from engineering.validation import ValidationError, ValidationIssue
from i18n.translator import Translator
from i18n.validation import render_validation_issue
from services.transfer_pump_service import TransferPumpService
from ui.dialogs.pump_reference_dialog import PumpReferenceDialog
from ui.widgets.scrollable_treeview import ScrollableTreeview
from ui.widgets.formula_view import FormulaReferencePanel, FormulaSection
from ui.widgets.rounded_button import ADD_BUTTON_PALETTE, DELETE_BUTTON_PALETTE, EDIT_BUTTON_PALETTE, FORMULA_BUTTON_PALETTE, NEUTRAL_BUTTON_PALETTE, TRANSFER_PRIMARY_PALETTE, create_rounded_button
from ui.widgets.transfer_pump_chart import TransferPumpChart, TransferPumpChartModel
from ui.widgets.cards import (
    CalculationCard,
    InputCard,
    ResultCard,
    ResultMetric,
    SectionHeader,
)


class TransferPumpPage(ttk.LabelFrame):
    """Display editable ship references and a project-independent estimate."""

    def __init__(
        self,
        parent: tk.Misc,
        service: TransferPumpService,
        constant_service: object,
        translate: Callable[[str], str] | None = None,
    ) -> None:
        """Build the enabled fuel-transfer-pump calculation page."""
        self._translate = translate or Translator().translate
        super().__init__(parent, text=self._translate("page.transfer.tab"), padding=12)
        self._service = service
        self._constants = constant_service
        self._capacity = tk.StringVar()
        self._reference_search = tk.StringVar()
        self._status_messages: list[ValidationIssue] = [
            ValidationIssue("insufficient_reference_ships")
        ]
        self._message = tk.StringVar(value="")
        self._estimate_capacity_summary = tk.StringVar(value="—")
        self._emptying_time_summary = tk.StringVar(value="—")
        self._dirty_callback: object | None = None
        self._suppress_dirty = True
        self._build()
        self.refresh()
        self._suppress_dirty = False
        self._capacity.trace_add("write", self._invalidate_estimate)
        self._reference_search.trace_add("write", lambda *_: self.refresh())

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self._header = SectionHeader(
            self,
            self._translate("page.transfer.title"),
            self._translate("page.transfer.description"),
        )
        self._header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        upper = ttk.Frame(self)
        upper.grid(row=1, column=0, sticky="nsew")
        self._upper = upper
        upper.columnconfigure(0, weight=3)
        upper.columnconfigure(1, weight=2)

        self._references_card = InputCard(
            upper,
            self._translate("section.reference_vessels"),
        )
        references = self._references_card
        references.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        references.columnconfigure(0, weight=1)
        toolbar = ttk.Frame(references)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self._search_label = ttk.Label(toolbar, text=self._translate("field.search_references"))
        self._search_label.pack(side="left")
        ttk.Entry(toolbar, textvariable=self._reference_search, width=28).pack(
            side="left", padx=(6, 0)
        )
        self._tree_container = ScrollableTreeview(
            references,
            columns=("name", "fuel", "pump", "source"),
            show="headings",
            height=5,
        )
        self._tree = self._tree_container.tree
        self._tree.configure(style="Transfer.Treeview")
        for key, label in (
            ("name", self._translate("field.ship_name")),
            ("fuel", self._translate("chart.fuel_capacity")),
            ("pump", self._translate("chart.pump_capacity")),
            ("source", self._translate("field.source")),
        ):
            self._tree.heading(key, text=label)
            self._tree.column(key, width=150)
        self._tree_container.grid(row=1, column=0, sticky="nsew")
        self._tree.bind("<Double-1>", self._edit)
        self._tree.bind("<Return>", self._edit)
        self._tree.bind("<Delete>", self._delete)
        self._reference_actions = ttk.Frame(references)
        self._reference_actions.grid(row=2, column=0, sticky="w", pady=(8, 0))
        self._add_button = create_rounded_button(self._reference_actions, self._translate("common.add"), self._add, style="RoundedAdd.TButton", palette=ADD_BUTTON_PALETTE)
        self._edit_button = create_rounded_button(self._reference_actions, self._translate("common.edit"), self._edit, style="RoundedEdit.TButton", palette=EDIT_BUTTON_PALETTE)
        self._delete_button = create_rounded_button(self._reference_actions, self._translate("common.delete"), self._delete, style="RoundedDelete.TButton", palette=DELETE_BUTTON_PALETTE)
        self._reference_action_buttons = (self._add_button, self._edit_button, self._delete_button)
        for column, button in enumerate(self._reference_action_buttons):
            button.grid(row=0, column=column, sticky="w", padx=(0 if column == 0 else 8, 0))

        prediction_column = ttk.Frame(upper)
        self._prediction_column = prediction_column
        prediction_column.grid(row=0, column=1, sticky="nsew")
        prediction_column.columnconfigure(0, weight=1)
        self._estimate_card = InputCard(
            prediction_column,
            self._translate("section.new_vessel"),
        )
        estimate = self._estimate_card
        estimate.grid(row=0, column=0, sticky="ew")
        self._capacity_label = ttk.Label(estimate, text=self._translate("chart.fuel_capacity"))
        self._capacity_label.grid(row=0, column=0, sticky="w")
        ttk.Entry(estimate, textvariable=self._capacity, width=16).grid(
            row=0, column=1, sticky="w", padx=(8, 0)
        )
        self._estimate_actions = ttk.Frame(estimate)
        self._estimate_actions.grid(row=0, column=2, columnspan=2, sticky="w", padx=(8, 0))
        self._calculate_button = create_rounded_button(self._estimate_actions, self._translate("calculation.calculate"), self._calculate, style="TransferRoundedPrimary.TButton", palette=TRANSFER_PRIMARY_PALETTE, primary=True)
        self._clear_button = create_rounded_button(self._estimate_actions, self._translate("common.clear"), self._clear, style="RoundedNeutral.TButton", palette=NEUTRAL_BUTTON_PALETTE)
        self._estimate_action_buttons = (self._calculate_button, self._clear_button)
        for column, button in enumerate(self._estimate_action_buttons):
            button.grid(row=0, column=column, sticky="w", padx=(0 if column == 0 else 8, 0))

        self._results_card = ResultCard(
            prediction_column,
            self._translate("section.estimate_results"),
        )
        results = self._results_card
        results.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        results.columnconfigure(0, weight=1)
        self._pump_result_metric = ResultMetric(
            results,
            self._translate("result.predicted_pump_capacity"),
            self._estimate_capacity_summary,
            "m³/h",
            normal_style_prefix="TransferResultMetric",
        )
        self._pump_result_metric.grid(row=0, column=0, sticky="ew")
        self._emptying_result_metric = ResultMetric(
            results,
            self._translate("result.full_tank_discharge_time"),
            self._emptying_time_summary,
            "h",
            normal_style_prefix="TransferSecondaryMetric",
        )
        self._emptying_result_metric.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self._chart = TransferPumpChart(self, translate=self._translate)
        self._chart.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self._model_card = CalculationCard(
            self,
            self._translate("section.regression_summary"),
        )
        model = self._model_card
        model.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(model, textvariable=self._message, wraplength=800).grid(
            row=0, column=0, sticky="w"
        )
        self._formula_panel = FormulaReferencePanel(self, self._formula_sections, self._translate, self._create_formula_toggle)
        self._formula_panel.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        self._responsive_layout_mode = ""
        self._upper.bind("<Configure>", self._on_upper_configure, add="+")
        self._reference_actions.bind("<Configure>", self._on_action_configure, add="+")
        self._estimate_actions.bind("<Configure>", self._on_action_configure, add="+")
        self.after_idle(self._reflow_layout)

    @staticmethod
    def _create_formula_toggle(parent: tk.Misc, text: str, command: Callable[[], None]) -> ttk.Button:
        """Create the Transfer-only rounded tertiary Formula toggle."""
        return create_rounded_button(parent, text, command, style="RoundedFormula.TButton", palette=FORMULA_BUTTON_PALETTE)

    def refresh_texts(self) -> None:
        """Refresh Transfer Pump text while retaining references and regression state."""
        self.configure(text=self._translate("page.transfer.tab"))
        self._header.set_content(self._translate("page.transfer.title"), self._translate("page.transfer.description"))
        self._references_card.configure(text=self._translate("section.reference_vessels"))
        self._search_label.configure(text=self._translate("field.search_references"))
        self._tree.heading("name", text=self._translate("field.ship_name"))
        self._tree.heading("fuel", text=self._translate("chart.fuel_capacity"))
        self._tree.heading("pump", text=self._translate("chart.pump_capacity"))
        self._tree.heading("source", text=self._translate("field.source"))
        self._add_button.configure(text=self._translate("common.add"))
        self._edit_button.configure(text=self._translate("common.edit"))
        self._delete_button.configure(text=self._translate("common.delete"))
        self._estimate_card.configure(text=self._translate("section.new_vessel"))
        self._capacity_label.configure(text=self._translate("chart.fuel_capacity"))
        self._calculate_button.configure(text=self._translate("calculation.calculate"))
        self._clear_button.configure(text=self._translate("common.clear"))
        self._model_card.configure(text=self._translate("section.regression_summary"))
        self._results_card.configure(text=self._translate("section.estimate_results"))
        self._pump_result_metric.set_label(
            self._translate("result.predicted_pump_capacity")
        )
        self._emptying_result_metric.set_label(
            self._translate("result.full_tank_discharge_time")
        )
        self._chart.set_translate(self._translate)
        self._render_status()
        self._render_estimate()
        self._formula_panel.refresh_texts()
        self.after_idle(self._reflow_layout)

    def _on_upper_configure(self, event: tk.Event[tk.Misc]) -> None:
        """Reflow the reference and prediction workspace for the usable width."""
        self._reflow_layout(event.width)

    def _reflow_layout(self, available_width: int | None = None) -> None:
        """Choose a requested-width layout before cards are allowed to compress."""
        width = available_width or self._upper.winfo_width()
        if width <= 1:
            return
        references_width = self._references_card.winfo_reqwidth()
        prediction_width = self._prediction_column.winfo_reqwidth()
        prediction_pair_width = (
            self._estimate_card.winfo_reqwidth()
            + self._results_card.winfo_reqwidth()
            + 12
        )
        wide_width = references_width + prediction_width + 10
        two_column_width = max(references_width, prediction_pair_width)
        content_width = max(1, width - 12)
        mode = (
            "wide"
            if content_width >= wide_width
            else "two_column"
            if content_width >= two_column_width
            else "stacked"
        )
        if mode == self._responsive_layout_mode:
            return
        self._responsive_layout_mode = mode
        self._apply_responsive_layout(mode)

    def _apply_responsive_layout(self, mode: str) -> None:
        """Arrange the existing cards without recreating controls or chart data."""
        for column in range(2):
            self._upper.columnconfigure(column, weight=0)
            self._prediction_column.columnconfigure(column, weight=0)
        if mode == "wide":
            self._upper.columnconfigure(0, weight=3)
            self._upper.columnconfigure(1, weight=2)
            self._references_card.grid_configure(
                row=0, column=0, columnspan=1, padx=(0, 10), pady=0
            )
            self._prediction_column.grid_configure(
                row=0, column=1, columnspan=1, padx=0, pady=0
            )
            self._prediction_column.columnconfigure(0, weight=1)
            self._estimate_card.grid_configure(
                row=0, column=0, columnspan=1, padx=0, pady=0
            )
            self._results_card.grid_configure(
                row=1, column=0, columnspan=1, padx=0, pady=(10, 0)
            )
        elif mode == "two_column":
            self._upper.columnconfigure(0, weight=1)
            self._upper.columnconfigure(1, weight=1)
            self._references_card.grid_configure(
                row=0, column=0, columnspan=2, padx=0, pady=0
            )
            self._prediction_column.grid_configure(
                row=1, column=0, columnspan=2, padx=0, pady=(10, 0)
            )
            self._prediction_column.columnconfigure(0, weight=1)
            self._prediction_column.columnconfigure(1, weight=1)
            self._estimate_card.grid_configure(
                row=0, column=0, columnspan=1, padx=(0, 6), pady=0
            )
            self._results_card.grid_configure(
                row=0, column=1, columnspan=1, padx=(6, 0), pady=0
            )
        else:
            self._upper.columnconfigure(0, weight=1)
            self._references_card.grid_configure(
                row=0, column=0, columnspan=1, padx=0, pady=0
            )
            self._prediction_column.grid_configure(
                row=1, column=0, columnspan=1, padx=0, pady=(10, 0)
            )
            self._prediction_column.columnconfigure(0, weight=1)
            self._estimate_card.grid_configure(
                row=0, column=0, columnspan=1, padx=0, pady=0
            )
            self._results_card.grid_configure(
                row=1, column=0, columnspan=1, padx=0, pady=(10, 0)
            )
        self.after_idle(self._reflow_action_buttons)

    def _on_action_configure(self, _event: tk.Event[tk.Misc]) -> None:
        """Ensure translated CRUD and estimate actions are never clipped."""
        self._reflow_action_buttons()

    def _reflow_action_buttons(self) -> None:
        """Use rows until requested button widths require a compact stack."""
        self._reflow_button_group(
            self._reference_actions, self._reference_action_buttons
        )
        self._reflow_button_group(
            self._estimate_actions, self._estimate_action_buttons
        )

    @staticmethod
    def _reflow_button_group(
        container: ttk.Frame, buttons: tuple[ttk.Button, ...]
    ) -> None:
        """Re-grid one action group while retaining original button callbacks."""
        width = container.winfo_width()
        if width <= 1:
            return
        required = sum(button.winfo_reqwidth() for button in buttons) + 8 * (
            len(buttons) - 1
        )
        stacked = width < required
        for index, button in enumerate(buttons):
            if stacked:
                button.grid_configure(
                    row=index,
                    column=0,
                    padx=0,
                    pady=(0 if index == 0 else 6, 0),
                    sticky="w",
                )
            else:
                button.grid_configure(
                    row=0,
                    column=index,
                    padx=(0 if index == 0 else 8, 0),
                    pady=0,
                    sticky="w",
                )

    def set_dirty_callback(self, callback: object) -> None:
        """Register a future optional-project dirty callback."""
        self._dirty_callback = callback

    def _mark_dirty(self) -> None:
        """Report a user-owned estimate change when persistence is active."""
        if not self._suppress_dirty and callable(self._dirty_callback):
            self._dirty_callback()

    def _invalidate_estimate(self, *_args: object) -> None:
        """Discard a stale estimate after the proposed fuel capacity changes."""
        if not self._suppress_dirty:
            self.__dict__.pop("_estimate_result", None)
            self.__dict__.pop("_estimate_capacity_m3", None)
            self._clear_estimate_summary()
            self._set_model_status()
            self._mark_dirty()
            self._refresh_chart()
            self._refresh_formula_panel()

    def export_state(self) -> dict[str, object]:
        """Return project-specific input state without rendered status text."""
        return {"capacity": self._capacity.get()}

    def load_state(self, state: dict[str, object]) -> None:
        """Restore saved estimate input and informational message."""
        self._suppress_dirty = True
        try:
            self._capacity.set(str(state.get("capacity", "")))
            self.__dict__.pop("_estimate_result", None)
            self.__dict__.pop("_estimate_capacity_m3", None)
            self._clear_estimate_summary()
            self.refresh()
        finally:
            self._suppress_dirty = False

    def clear_state(self) -> None:
        """Clear only the current estimate while preserving reference ships."""
        self._suppress_dirty = True
        try:
            self._clear()
        finally:
            self._suppress_dirty = False

    def refresh(self) -> None:
        """Reload service-backed reference records without direct SQL."""
        selected = self._tree.selection()
        for item in self._tree.get_children():
            self._tree.delete(item)
        query = self._reference_search.get().casefold().strip()
        all_records = self._service._references.get_all_references()
        records = [
            record
            for record in all_records
            if not query or query in record.ship_name.casefold()
        ]
        for item in records:
            self._tree.insert("", "end", iid=str(item.id), values=(item.ship_name, item.fuel_capacity_m3, item.pump_capacity_m3h, item.source))
        if selected and self._tree.exists(selected[0]):
            self._tree.selection_set(selected[0])
        model_result=self._service.get_regression_model()
        self._model_result=model_result
        if not model_result.is_successful or model_result.regression_model is None:
            self._set_semantic_messages(model_result.errors)
        else:
            self._set_model_ready_status(model_result.regression_model)
        self._refresh_chart(all_records)
        if hasattr(self, "_formula_panel"):
            self._refresh_formula_panel()

    def _add(self) -> None:
        """Open the service-backed reference dialog in add mode."""
        if PumpReferenceDialog(self, self._service._references).show() is not None:
            self.__dict__.pop("_estimate_result", None)
            self.__dict__.pop("_estimate_capacity_m3", None)
            self._clear_estimate_summary()
            self.refresh()
            self._mark_dirty()

    def _edit(self, event: object | None = None) -> str:
        """Edit the selected row through the shared keyboard/button path."""
        del event
        selected = self._tree.selection()
        if not selected:
            return "break"
        try:
            item = self._service._references.get_reference(UUID(selected[0]))
        except (LookupError, ValueError):
            logging.getLogger(__name__).exception("Transfer-pump reference lookup failed")
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate("validation.unexpected_error"),
                parent=self,
            )
            return "break"
        if PumpReferenceDialog(self, self._service._references, item).show() is not None:
            self.__dict__.pop("_estimate_result", None)
            self.__dict__.pop("_estimate_capacity_m3", None)
            self._clear_estimate_summary()
            self.refresh()
            self._mark_dirty()
        return "break"

    def _delete(self, event: object | None = None) -> str:
        """Confirm and delete the selected reference through one shared path."""
        del event
        selected = self._tree.selection()
        if selected and messagebox.askyesno(
            self._translate("dialog.delete_pump_reference"),
            self._translate("confirm.delete_pump_reference"),
            parent=self,
        ):
            self._service._references.delete_reference(UUID(selected[0]))
            self.__dict__.pop("_estimate_result", None)
            self.__dict__.pop("_estimate_capacity_m3", None)
            self.refresh()
            self._mark_dirty()
        return "break"

    @staticmethod
    def format_hours_minutes(hours: float) -> str:
        """Format decimal hours with rounded carried minutes."""
        whole = int(hours)
        minutes = round((hours - whole) * 60)
        if minutes == 60:
            whole += 1
            minutes = 0
        return f"{whole} h {minutes} min"

    def _calculate(self) -> None:
        """Validate and calculate one authoritative transfer-pump estimate."""
        try:
            capacity = parse_engineering_float(
                self._capacity.get(),
                field_name="New ship fuel capacity",
                field_key="field.fuel_capacity",
            )
            assert capacity is not None
            if capacity <= 0:
                raise ValidationError(
                    ValidationIssue("greater_than_zero", "field.fuel_capacity")
                )
            result = self._service.calculate(capacity)
        except ValidationError as error:
            self._set_semantic_messages([error.issue])
            return
        except Exception:
            logging.getLogger(__name__).exception("Transfer-pump estimate failed")
            self._set_semantic_messages([ValidationIssue("unexpected_error")])
            return
        if not result.is_successful:
            self._set_semantic_messages(result.errors)
            return
        model = result.regression_model
        self._estimate_result=result
        self._estimate_capacity_m3=capacity
        assert model is not None
        self._set_estimate_ready_status(model, result)
        self._render_estimate()
        self._mark_dirty()
        self._refresh_chart()
        self._refresh_formula_panel()

    def _formula_sections(self) -> list[FormulaSection]:
        """Display the available model and optional latest estimate substitution."""
        model_result=getattr(self,"_model_result",None)
        sections = [
            FormulaSection("FORMULA", "Qpump = m × Vfuel + b\nm = Σ((Vfuel − V̄fuel)(Qpump − Q̄pump)) / Σ(Vfuel − V̄fuel)²\nb = Q̄pump − m × V̄fuel", "1. LINEAR REGRESSION MODEL", "formula"),
            FormulaSection("VARIABLES", f"Qpump | {self._translate('result.estimated_pump_capacity')} | m³/h\nVfuel | {self._translate('field.fuel_capacity')} | m³\nm | {self._translate('formula.regression_slope')} | {self._translate('formula.regression_slope_unit')}\nb | {self._translate('formula.regression_intercept')} | m³/h", "1. LINEAR REGRESSION MODEL", "variables"),
            FormulaSection("CURRENT SUBSTITUTION", self._translate("message.available_after_calculation"), "1. LINEAR REGRESSION MODEL", "substitution"),
            FormulaSection("RESULT", self._translate("message.available_after_calculation"), "1. LINEAR REGRESSION MODEL", "result"),
            FormulaSection("NOTE", self._translate("formula.regression_model_note"), "1. LINEAR REGRESSION MODEL", "note"),
            FormulaSection("FORMULA", "Qpump = m × Vfuel + b", "2. PREDICTED PUMP CAPACITY", "formula"),
            FormulaSection("VARIABLES", f"Qpump | {self._translate('result.estimated_pump_capacity')} | m³/h\nVfuel | {self._translate('field.fuel_capacity')} | m³", "2. PREDICTED PUMP CAPACITY", "variables"),
            FormulaSection("CURRENT SUBSTITUTION", self._translate("message.available_after_calculation"), "2. PREDICTED PUMP CAPACITY", "substitution"),
            FormulaSection("RESULT", self._translate("message.available_after_calculation"), "2. PREDICTED PUMP CAPACITY", "result"),
            FormulaSection("FORMULA", "t = Vfuel / Qpump", "3. EMPTYING TIME", "formula"),
            FormulaSection("VARIABLES", f"t | {self._translate('result.estimated_emptying_time')} | h\nVfuel | {self._translate('field.fuel_capacity')} | m³\nQpump | {self._translate('field.pump_capacity')} | m³/h", "3. EMPTYING TIME", "variables"),
            FormulaSection("CURRENT SUBSTITUTION", self._translate("message.available_after_calculation"), "3. EMPTYING TIME", "substitution"),
            FormulaSection("RESULT", self._translate("message.available_after_calculation"), "3. EMPTYING TIME", "result"),
        ]
        if model_result is None or model_result.regression_model is None:
            sections.append(FormulaSection("MODEL INFORMATION", self._translate("transfer.formula.model_unavailable"), "1. LINEAR REGRESSION MODEL", "note"))
            return sections
        model=model_result.regression_model
        places = int(self._constants.get_constant("display_decimal_places").value)
        sections[2] = FormulaSection("CURRENT SUBSTITUTION", f"m = {model.slope:.{places}f}\nb = {model.intercept:.{places}f}", "1. LINEAR REGRESSION MODEL", "substitution")
        sections[3] = FormulaSection("RESULT", f"R² = {model.r_squared:.{places}f}", "1. LINEAR REGRESSION MODEL", "result")
        sections.append(FormulaSection("MODEL INFORMATION", f"{self._translate('formula.regression_slope')} m = {model.slope:.{places}f}\n{self._translate('formula.regression_intercept')} b = {model.intercept:.{places}f}\nR² = {model.r_squared:.{places}f}", "1. LINEAR REGRESSION MODEL", "note"))
        estimate=getattr(self,"_estimate_result",None)
        if estimate is not None and estimate.is_successful:
            sections[7] = FormulaSection("CURRENT SUBSTITUTION", f"Vfuel = {self._capacity.get()} m³\nQpump = ({model.slope:.{places}f}) × ({self._capacity.get()}) + ({model.intercept:.{places}f})", "2. PREDICTED PUMP CAPACITY", "substitution")
            sections[8] = FormulaSection("RESULT", f"{self._translate('result.estimated_pump_capacity')} = {estimate.predicted_pump_capacity_m3h:.{places}f} m³/h", "2. PREDICTED PUMP CAPACITY", "result")
            sections[11] = FormulaSection("CURRENT SUBSTITUTION", f"t = {self._capacity.get()} / {estimate.predicted_pump_capacity_m3h:.{places}f}", "3. EMPTYING TIME", "substitution")
            sections[12] = FormulaSection("RESULT", f"{self._translate('result.estimated_emptying_time')} = {estimate.estimated_emptying_time_hours:.{places}f} h", "3. EMPTYING TIME", "result")
        return sections

    def _clear(self) -> None:
        """Clear estimate input and result text."""
        self.__dict__.pop("_estimate_result", None)
        self.__dict__.pop("_estimate_capacity_m3", None)
        self._clear_estimate_summary()
        self._capacity.set("")
        self._set_model_status()
        self._mark_dirty()
        self._refresh_chart()
        self._refresh_formula_panel()

    def _refresh_chart(self, records: Sequence[PumpReference] | None = None) -> None:
        """Render authoritative references, model, and optional current prediction."""
        references = (
            self._service._references.get_all_references()
            if records is None
            else records
        )
        model_result = getattr(self, "_model_result", None)
        regression_model = (
            model_result.regression_model
            if model_result is not None and model_result.is_successful
            else None
        )
        chart_model = TransferPumpChartModel.from_authoritative(
            references,
            regression_model,
            getattr(self, "_estimate_result", None),
            getattr(self, "_estimate_capacity_m3", None),
        )
        self._chart.render(chart_model)

    def _refresh_formula_panel(self) -> None:
        """Update an expanded formula reference after state changes."""
        if self._formula_panel.expanded:
            self._formula_panel.refresh()

    def _clear_estimate_summary(self) -> None:
        """Clear transient result presentation without touching reference data."""
        self._estimate_capacity_summary.set("—")
        self._emptying_time_summary.set("—")

    def _render_estimate(self) -> None:
        """Render stored estimate data in the currently active language."""
        result = getattr(self, "_estimate_result", None)
        if result is None or not result.is_successful:
            return
        places = int(self._constants.get_constant("display_decimal_places").value)
        model = result.regression_model
        self._estimate_capacity_summary.set(
            format_engineering_value(result.predicted_pump_capacity_m3h, places)
        )
        self._emptying_time_summary.set(
            format_engineering_value(result.estimated_emptying_time_hours, places)
        )

    def _set_semantic_messages(self, messages: Sequence[ValidationIssue]) -> None:
        """Store semantic status messages and render them with the active translator."""
        self._status_messages = list(messages)
        self._render_status()

    def _render_status(self) -> None:
        """Render stored status codes without recalculating the regression model."""
        if not self._status_messages:
            self._message.set(self._translate("message.ready"))
            return
        self._message.set(
            "; ".join(self._render_semantic_message(message) for message in self._status_messages)
        )

    def _render_semantic_message(self, message: ValidationIssue) -> str:
        """Render either a transfer status or a validation issue on demand."""
        if message.code.startswith("transfer.status."):
            return self._translate(message.code, **dict(message.params or {}))
        return render_validation_issue(message, self._translator_proxy())

    def _set_model_status(self) -> None:
        """Restore semantic model status after clearing a transient estimate."""
        model_result = getattr(self, "_model_result", None)
        if model_result is None or model_result.regression_model is None:
            self._set_semantic_messages(
                model_result.errors
                if model_result is not None and model_result.errors
                else [ValidationIssue("insufficient_reference_ships")]
            )
            return
        self._set_model_ready_status(model_result.regression_model)

    def _set_model_ready_status(self, model: object) -> None:
        """Store formatted numeric model parameters beneath one stable status code."""
        self._set_semantic_messages([
            ValidationIssue("transfer.status.model_ready", params=self._model_status_params(model))
        ])

    def _set_estimate_ready_status(self, model: object, result: object) -> None:
        """Store the estimate status and any semantic model warnings."""
        parameters = self._model_status_params(model)
        parameters.update({
            "predicted_capacity": format_engineering_value(
                getattr(result, "predicted_pump_capacity_m3h"), self._display_places()
            ),
            "emptying_time": format_engineering_value(
                getattr(result, "estimated_emptying_time_hours"), self._display_places()
            ),
        })
        self._set_semantic_messages([
            ValidationIssue("transfer.status.estimate_ready", params=parameters),
            *getattr(result, "warnings", []),
        ])

    def _model_status_params(self, model: object) -> dict[str, object]:
        """Format authoritative model values without changing their stored precision."""
        places = self._display_places()
        return {
            "reference_count": getattr(model, "reference_count"),
            "slope": format_engineering_value(getattr(model, "slope"), places),
            "intercept": format_engineering_value(getattr(model, "intercept"), places),
            "r_squared": format_engineering_value(getattr(model, "r_squared"), places),
            "minimum_capacity": format_engineering_value(
                getattr(model, "minimum_reference_capacity_m3"), places
            ),
            "maximum_capacity": format_engineering_value(
                getattr(model, "maximum_reference_capacity_m3"), places
            ),
        }

    def _display_places(self) -> int:
        """Return the current library-controlled display precision."""
        return int(self._constants.get_constant("display_decimal_places").value)

    def _translator_proxy(self) -> object:
        """Expose the page translation callable to the shared issue renderer."""
        return type("TranslatorProxy", (), {"translate": self._translate})()
