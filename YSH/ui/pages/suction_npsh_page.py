"""Tkinter page for suction-line loss and ENPY/NPSH calculations."""

from __future__ import annotations

import tkinter as tk
import logging
from collections.abc import Callable
from tkinter import messagebox, ttk
from uuid import UUID, uuid4

from core.local_loss_item import LocalLossItem
from engineering.input_parsing import parse_engineering_float
from engineering.validation import ValidationError, ValidationIssue
from i18n.translator import Translator
from i18n.validation import render_validation_issue
from ui.dialogs.local_loss_item_dialog import LocalLossItemDialog
from ui.widgets.scrollable_treeview import ScrollableTreeview
from ui.widgets.formula_view import FormulaReferencePanel, FormulaSection
from ui.widgets.rounded_button import ADD_BUTTON_PALETTE, CLEAR_ALL_BUTTON_PALETTE, DELETE_BUTTON_PALETTE, EDIT_BUTTON_PALETTE, FORMULA_BUTTON_PALETTE, NEUTRAL_BUTTON_PALETTE, SUCTION_PRIMARY_PALETTE, create_rounded_button
from ui.widgets.cards import CalculationCard, InputCard, ResultCard, ResultMetric, SectionHeader


class SuctionNPSHPage(ttk.Frame):
    """Collect suction inputs and delegate every calculation to the service."""

    def __init__(
        self,
        parent: tk.Misc,
        service: object,
        materials: object,
        constants: object,
        translate: Callable[[str], str] | None = None,
    ) -> None:
        """Create a calculation-first suction NPSH page."""
        self._translate = translate or Translator().translate
        super().__init__(parent, padding=12)
        self._service = service
        self._materials = materials
        self._constants = constants
        self._items: dict[str, LocalLossItem] = {}
        self._material_ids: dict[str, UUID] = {}
        self._fields = {
            key: tk.StringVar()
            for key in (
                "diameter", "flow", "viscosity", "length", "roughness",
                "pressure", "vapour", "density", "height", "required",
            )
        }
        self._viscosity_unit = tk.StringVar(value="cSt")
        self._roughness_source_mode = "material"
        self._roughness_source = tk.StringVar(value=self._translate("message.material_source"))
        self._material = tk.StringVar()
        self._pressure_unit = tk.StringVar(value="bar")
        self._vapour_unit = tk.StringVar(value="bar")
        self._loss_status_messages: list[ValidationIssue] = []
        self._enpy_status_messages: list[ValidationIssue] = []
        self._message = tk.StringVar(value="")
        self._result = tk.StringVar()
        self._suction_loss_summary = tk.StringVar(value="—")
        self._enpy_summary = tk.StringVar(value="—")
        self._k_total_summary = tk.StringVar(value="—")
        self._detail_values = {
            key: tk.StringVar(value="—")
            for key in (
                "flow_velocity", "reynolds_number", "flow_regime",
                "relative_roughness", "friction_factor", "pipe_loss",
                "local_loss", "k_total", "suction_pressure_head",
                "vapour_pressure_head", "npsh_margin",
            )
        }
        self._formula = tk.StringVar()
        self._dirty_callback: object | None = None
        self._suppress_dirty = True
        self._build()
        self._load_materials()
        self._set_roughness_source()
        for key in ("diameter", "flow", "viscosity", "length", "roughness"):
            self._fields[key].trace_add("write", self._invalidate_hydraulics)
        for key in ("pressure", "vapour", "density", "height", "required"):
            self._fields[key].trace_add("write", self._invalidate_enpy)
        for variable in (
            *self._fields.values(), self._viscosity_unit, self._roughness_source,
            self._material, self._pressure_unit, self._vapour_unit,
        ):
            variable.trace_add("write", self._mark_dirty)
        self._suppress_dirty = False

    def _build(self) -> None:
        """Create the Suction/ENPY workflow with a measured responsive upper layout."""
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self._header = SectionHeader(self, self._translate("page.suction.title"), self._translate("page.suction.description"))
        self._header.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        self._fluid_card = InputCard(self, self._translate("section.suction_inputs"))
        fluid = self._fluid_card
        fluid.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        for row, (key, label, suffix) in enumerate((
            ("diameter", "field.pipe_inside_diameter", " D, mm"),
            ("flow", "field.flow_rate", " Q, m³/h"),
            ("viscosity", "field.kinematic_viscosity", ""),
            ("length", "field.pipe_length", " L, m"),
        )):
            label_widget = ttk.Label(fluid, text=f"{self._translate(label)}{suffix}")
            label_widget.grid(row=row, column=0, sticky="w", pady=3)
            setattr(self, f"_field_label_{key}", (label_widget, label, suffix))
            ttk.Entry(fluid, textvariable=self._fields[key], width=22).grid(
                row=row, column=1, sticky="w", padx=(12, 0), pady=3
            )
        self._viscosity_box = ttk.Combobox(
            fluid, textvariable=self._viscosity_unit, values=("cSt", "m²/s"),
            state="readonly", width=10,
        )
        self._viscosity_box.grid(row=2, column=2, sticky="w", padx=8)
        self._viscosity_box.bind("<<ComboboxSelected>>", self._invalidate_hydraulics)
        self._roughness_source_label = ttk.Label(fluid, text=self._translate("field.roughness_source"))
        self._roughness_source_label.grid(row=4, column=0, sticky="w", pady=(10, 3))
        self._roughness_source_box = ttk.Combobox(
            fluid, textvariable=self._roughness_source,
            values=("Material Library", "Manual"), state="readonly", width=18,
        )
        self._roughness_source_box.grid(row=4, column=1, sticky="w", padx=(12, 0), pady=(10, 3))
        self._roughness_source_box.bind("<<ComboboxSelected>>", self._select_roughness_source)
        self._material_label = ttk.Label(fluid, text=self._translate("field.material"))
        self._material_label.grid(row=5, column=0, sticky="w", pady=3)
        self._material_box = ttk.Combobox(fluid, textvariable=self._material, state="readonly", width=34)
        self._material_box.grid(row=5, column=1, columnspan=2, sticky="w", padx=(12, 0), pady=3)
        self._material_box.bind("<<ComboboxSelected>>", self._load_selected_roughness)
        self._active_roughness_label = ttk.Label(fluid, text=f"{self._translate('field.active_roughness')}, mm")
        self._active_roughness_label.grid(row=6, column=0, sticky="w", pady=3)
        self._roughness_entry = ttk.Entry(fluid, textvariable=self._fields["roughness"], width=22)
        self._roughness_entry.grid(row=6, column=1, sticky="w", padx=(12, 0), pady=3)

        self._losses_card = InputCard(self, self._translate("section.local_losses"))
        losses = self._losses_card
        losses.grid(row=1, column=1, sticky="nsew", padx=6)
        losses.columnconfigure(0, weight=1)
        self._tree_container = ScrollableTreeview(losses, columns=("component", "quantity", "k", "total"), show="headings", height=5)
        self._tree = self._tree_container.tree
        self._tree.configure(style="Suction.Treeview")
        for column, label, width in (("component", self._translate("table.component"), 250), ("quantity", self._translate("table.quantity"), 80), ("k", "K", 100), ("total", self._translate("table.quantity_times_k"), 120)):
            self._tree.heading(column, text=label)
            self._tree.column(column, width=width, anchor="w")
        self._tree_container.grid(row=0, column=0, columnspan=4, sticky="nsew")
        self._tree.bind("<Double-1>", self._edit_loss)
        self._tree.bind("<Return>", self._edit_loss)
        self._tree.bind("<Delete>", self._delete_loss)
        self._loss_buttons = []
        for column, text_key, command, style, palette in ((0, "common.add", self._add_loss, "RoundedAdd.TButton", ADD_BUTTON_PALETTE), (1, "common.edit", self._edit_loss, "RoundedEdit.TButton", EDIT_BUTTON_PALETTE), (2, "common.delete", self._delete_loss, "RoundedDelete.TButton", DELETE_BUTTON_PALETTE), (3, "action.clear_all", self._clear_losses, "RoundedClearAll.TButton", CLEAR_ALL_BUTTON_PALETTE)):
            button = create_rounded_button(losses, self._translate(text_key), command, style=style, palette=palette)
            button.grid(row=1, column=column, padx=(0, 8), pady=(8, 0), sticky="w")
            self._loss_buttons.append((button, text_key))
        ttk.Label(losses, text="ΣK", style="ResultMetricLabel.TLabel").grid(
            row=2, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Label(losses, textvariable=self._k_total_summary, style="ResultMetricValue.TLabel").grid(
            row=2, column=1, sticky="w", pady=(8, 0)
        )

        self._enpy_card = InputCard(self, self._translate("section.enpy_inputs"))
        enpy = self._enpy_card
        enpy.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        self._enpy_card.configure(text=self._translate("section.enpy_calculation"))
        for row, (key, label, suffix) in enumerate((
            ("pressure", "field.suction_pressure", " PE"), ("vapour", "field.vapour_pressure", " Pb"),
            ("density", "field.fluid_density", " ρ, kg/m³"), ("height", "field.static_suction_height", " HEgeo, m"),
            ("required", "field.npsh_required", ", m (optional)"),
        )):
            label_widget = ttk.Label(enpy, text=f"{self._translate(label)}{suffix}")
            label_widget.grid(row=row, column=0, sticky="w", pady=3)
            setattr(self, f"_field_label_{key}", (label_widget, label, suffix))
            ttk.Entry(enpy, textvariable=self._fields[key], width=22).grid(row=row, column=1, sticky="w", padx=(12, 0), pady=3)
        for row, variable in ((0, self._pressure_unit), (1, self._vapour_unit)):
            box = ttk.Combobox(enpy, textvariable=variable, values=("Pa", "kPa", "bar"), state="readonly", width=10)
            box.grid(row=row, column=2, sticky="w", padx=8)
            box.bind("<<ComboboxSelected>>", self._invalidate_enpy)
        self._pressure_note = ttk.Label(
            enpy,
            text=self._translate("suction.pressure_note"),
            wraplength=720,
        )
        self._pressure_note.grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 0))

        self._results_card = ResultCard(self, self._translate("section.suction_results"))
        results = self._results_card
        results.grid(row=1, column=2, sticky="nsew", padx=(6, 0))
        self._enpy_metric = ResultMetric(results, self._translate("result.available_npsh"), self._enpy_summary, "m", normal_style_prefix="SuctionResultMetric")
        self._enpy_metric.grid(row=0, column=0, sticky="ew")
        self._suction_metric = ResultMetric(results, self._translate("result.suction_head_loss"), self._suction_loss_summary, "m", normal_style_prefix="SuctionLossMetric")
        self._suction_metric.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self._details_card = ttk.Frame(results, style="EngineeringDetails.TFrame", padding=(10, 8))
        self._details_card.columnconfigure(0, weight=1)
        self._details_card.columnconfigure(1, weight=1)
        self._details_title = ttk.Label(
            self._details_card,
            text=self._translate("section.calculation_details"),
            style="EngineeringDetailsTitle.TLabel",
        )
        self._details_title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))
        self._detail_labels: list[tuple[ttk.Label, str]] = []
        detail_specs = (
            ("flow_velocity", "result.flow_velocity"),
            ("reynolds_number", "result.reynolds_number"),
            ("flow_regime", "result.flow_regime"),
            ("relative_roughness", "result.relative_roughness"),
            ("friction_factor", "result.friction_factor"),
            ("pipe_loss", "result.pipe_friction_loss"),
            ("local_loss", "result.local_loss"),
            ("k_total", "result.local_loss_coefficient"),
            ("suction_pressure_head", "result.suction_pressure_head"),
            ("vapour_pressure_head", "result.vapour_pressure_head"),
            ("npsh_margin", "result.npsh_margin"),
        )
        for index, (value_key, label_key) in enumerate(detail_specs):
            row = index // 2 + 1
            column = index % 2
            metric = ttk.Frame(self._details_card, style="EngineeringDetails.TFrame")
            metric.grid(row=row, column=column, sticky="ew", padx=(0 if column == 0 else 10, 0), pady=3)
            metric.columnconfigure(1, weight=1)
            label = ttk.Label(metric, text=self._translate(label_key), style="EngineeringDetailsLabel.TLabel")
            label.grid(row=0, column=0, sticky="w")
            ttk.Label(metric, textvariable=self._detail_values[value_key], style="EngineeringDetailsValue.TLabel").grid(row=0, column=1, sticky="e", padx=(8, 0))
            self._detail_labels.append((label, label_key))
        self._details_card.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self._details_card.grid_remove()
        self._result_fallback = ttk.Label(results, textvariable=self._result, style="Info.TLabel", justify="left", wraplength=360)
        self._result_fallback.grid(row=3, column=0, sticky="w", pady=(8, 0))
        self._result_fallback.grid_remove()
        ttk.Label(results, textvariable=self._message, style="Info.TLabel", wraplength=360).grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Label(results, textvariable=self._formula, justify="left", wraplength=360).grid(row=5, column=0, sticky="w", pady=(8, 0))
        self._actions_card = CalculationCard(results, self._translate("common.calculations"))
        actions = self._actions_card
        actions.grid(row=6, column=0, sticky="ew", pady=(10, 0))
        self._calculate_loss_button = create_rounded_button(actions, self._translate("calculation.calculate"), self._calculate_suction_loss, style="SuctionRoundedPrimary.TButton", palette=SUCTION_PRIMARY_PALETTE, primary=True)
        self._calculate_loss_button.grid(row=0, column=0, sticky="w")
        self._calculate_enpy_button = create_rounded_button(actions, self._translate("action.calculate_enpy"), self._calculate_enpy, style="SuctionRoundedPrimary.TButton", palette=SUCTION_PRIMARY_PALETTE, primary=True)
        self._calculate_enpy_button.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self._clear_button = create_rounded_button(actions, self._translate("common.clear"), self._clear, style="RoundedNeutral.TButton", palette=NEUTRAL_BUTTON_PALETTE)
        self._clear_button.grid(row=0, column=2, sticky="w", padx=(8, 0))
        self._formula_panel = FormulaReferencePanel(self, self._formula_sections, self._translate, self._create_formula_toggle)
        self._formula_panel.grid(
            row=3, column=0, columnspan=3, sticky="ew", pady=(12, 0)
        )
        self._responsive_layout_mode = ""
        self.bind("<Configure>", self._on_layout_configure, add="+")
        actions.bind("<Configure>", self._on_actions_configure, add="+")
        self.after_idle(self._reflow_layout)

    @staticmethod
    def _create_formula_toggle(parent: tk.Misc, text: str, command: Callable[[], None]) -> ttk.Button:
        """Create the Suction-only rounded tertiary Formula toggle."""
        return create_rounded_button(parent, text, command, style="RoundedFormula.TButton", palette=FORMULA_BUTTON_PALETTE)

    def _on_layout_configure(self, event: tk.Event[tk.Misc]) -> None:
        """Reflow only after the live page viewport has a meaningful width."""
        self._reflow_layout(event.width)

    def _reflow_layout(self, available_width: int | None = None) -> None:
        """Choose wide, two-column, or stacked cards from requested widget sizes."""
        width = available_width or self.winfo_width()
        if width <= 1:
            return
        fluid = self._fluid_card
        losses = self._losses_card
        results = self._results_card
        enpy = self._enpy_card
        wide_width = sum(
            card.winfo_reqwidth() for card in (fluid, losses, results)
        ) + 24
        two_column_width = max(
            fluid.winfo_reqwidth() + results.winfo_reqwidth() + 12,
            losses.winfo_reqwidth(),
            enpy.winfo_reqwidth(),
        )
        content_width = max(1, width - 24)
        if content_width >= wide_width:
            mode = "wide"
        elif content_width >= two_column_width:
            mode = "two-column"
        else:
            mode = "stacked"
        if self._responsive_layout_mode == mode:
            return
        self._responsive_layout_mode = mode
        self._apply_responsive_layout(mode)

    def _apply_responsive_layout(self, mode: str) -> None:
        """Apply one normal-grid layout without recreating cards or their state."""
        for column in range(3):
            self.columnconfigure(column, minsize=0, weight=0)
        if mode == "wide":
            for column in range(3):
                self.columnconfigure(column, weight=1)
            self._fluid_card.grid_configure(row=1, column=0, columnspan=1, sticky="nsew", padx=(0, 6), pady=0)
            self._losses_card.grid_configure(row=1, column=1, columnspan=1, sticky="nsew", padx=6, pady=0)
            self._results_card.grid_configure(row=1, column=2, columnspan=1, sticky="nsew", padx=(6, 0), pady=0)
            self._enpy_card.grid_configure(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))
            self._formula_panel.grid_configure(row=3, column=0, columnspan=3, sticky="ew", pady=(12, 0))
            return
        if mode == "two-column":
            self.columnconfigure(0, weight=1)
            self.columnconfigure(1, weight=1)
            self._fluid_card.grid_configure(row=1, column=0, columnspan=1, sticky="nsew", padx=(0, 6), pady=0)
            self._results_card.grid_configure(row=1, column=1, columnspan=1, sticky="nsew", padx=(6, 0), pady=0)
            self._losses_card.grid_configure(row=2, column=0, columnspan=2, sticky="nsew", padx=0, pady=(12, 0))
            self._enpy_card.grid_configure(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
            self._formula_panel.grid_configure(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
            return
        self.columnconfigure(0, weight=1)
        self._fluid_card.grid_configure(row=1, column=0, columnspan=1, sticky="ew", padx=0, pady=0)
        self._losses_card.grid_configure(row=2, column=0, columnspan=1, sticky="ew", padx=0, pady=(12, 0))
        self._results_card.grid_configure(row=3, column=0, columnspan=1, sticky="ew", padx=0, pady=(12, 0))
        self._enpy_card.grid_configure(row=4, column=0, columnspan=1, sticky="ew", pady=(12, 0))
        self._formula_panel.grid_configure(row=5, column=0, columnspan=1, sticky="ew", pady=(12, 0))

    def _on_actions_configure(self, event: tk.Event[tk.Misc]) -> None:
        """Keep localized calculation actions inside their card instead of clipping."""
        buttons = (
            self._calculate_loss_button,
            self._calculate_enpy_button,
            self._clear_button,
        )
        required_width = sum(button.winfo_reqwidth() for button in buttons) + 16
        stacked = event.width < required_width
        if getattr(self, "_actions_stacked", None) == stacked:
            return
        self._actions_stacked = stacked
        for row, button in enumerate(buttons):
            if stacked:
                button.grid_configure(row=row, column=0, sticky="w", padx=0, pady=(0 if row == 0 else 6, 0))
            else:
                button.grid_configure(row=0, column=row, sticky="w", padx=(0 if row == 0 else 8, 0), pady=0)

    def refresh_texts(self) -> None:
        """Refresh suction/ENPY labels without altering staged calculation state."""
        manual = self._roughness_source_mode == "manual"
        self._suppress_dirty = True
        try:
            self._roughness_source.set(self._translate(
                "message.manual_source" if manual else "message.material_source"
            ))
        finally:
            self._suppress_dirty = False
        self._header.set_content(self._translate("page.suction.title"), self._translate("page.suction.description"))
        self._fluid_card.configure(text=self._translate("section.suction_inputs"))
        self._losses_card.configure(text=self._translate("section.local_losses"))
        self._enpy_card.configure(text=self._translate("section.enpy_calculation"))
        self._results_card.configure(text=self._translate("section.suction_results"))
        self._actions_card.configure(text=self._translate("common.calculations"))
        for key in ("diameter", "flow", "viscosity", "length", "pressure", "vapour", "density", "height", "required"):
            label, text_key, suffix = getattr(self, f"_field_label_{key}")
            label.configure(text=f"{self._translate(text_key)}{suffix}")
        self._suction_metric.set_label(self._translate("result.suction_head_loss"))
        self._enpy_metric.set_label(self._translate("result.available_npsh"))
        self._roughness_source_label.configure(text=self._translate("field.roughness_source"))
        self._material_label.configure(text=self._translate("field.material"))
        self._active_roughness_label.configure(text=f"{self._translate('field.active_roughness')}, mm")
        self._pressure_note.configure(text=self._translate("suction.pressure_note"))
        self._roughness_source_box.configure(values=(
            self._translate("message.material_source"),
            self._translate("message.manual_source"),
        ))
        self._tree.heading("component", text=self._translate("table.component"))
        self._tree.heading("quantity", text=self._translate("table.quantity"))
        self._tree.heading("total", text=self._translate("table.quantity_times_k"))
        for button, text_key in self._loss_buttons:
            button.configure(text=self._translate(text_key))
        self._calculate_loss_button.configure(text=self._translate("calculation.calculate"))
        self._calculate_enpy_button.configure(text=self._translate("action.calculate_enpy"))
        self._clear_button.configure(text=self._translate("common.clear"))
        self._details_title.configure(text=self._translate("section.calculation_details"))
        for label, key in self._detail_labels:
            label.configure(text=self._translate(key))
        self._render_status()
        self._render_current_results()
        self._formula_panel.refresh_texts()

    def set_dirty_callback(self, callback: object) -> None:
        """Register the optional active-project dirty callback."""
        self._dirty_callback = callback

    def _mark_dirty(self, *_args: object) -> None:
        """Notify the active project only for genuine user-owned changes."""
        if not self._suppress_dirty and callable(self._dirty_callback):
            self._dirty_callback()

    def export_state(self) -> dict[str, object]:
        """Serialize page inputs without storing rendered stage-status text."""
        return {"fields": {key: value.get() for key, value in self._fields.items()}, "viscosity_unit": self._viscosity_unit.get(), "roughness_source": self._roughness_source_mode, "material": self._material.get(), "pressure_unit": self._pressure_unit.get(), "vapour_unit": self._vapour_unit.get(), "items": [{"id": identifier, "name": item.name, "quantity": item.quantity, "k": item.k_coefficient} for identifier, item in self._items.items()], "result": self._result.get(), "formula": self._formula.get(), "hydraulic_valid": hasattr(self, "_last_loss"), "enpy_valid": hasattr(self, "_last_enpy")}

    def load_state(self, state: dict[str, object]) -> None:
        """Restore saved page data without modifying shared materials."""
        self._suppress_dirty = True
        try:
            for key, value in dict(state.get("fields", {})).items():
                if key in self._fields: self._fields[key].set(str(value))
            self._viscosity_unit.set(str(state.get("viscosity_unit", "cSt")));saved_source=str(state.get("roughness_source", "material"));self._roughness_source_mode="manual" if saved_source in {"manual","Manual"} else "material";self._roughness_source.set(self._translate("message.manual_source") if self._roughness_source_mode=="manual" else self._translate("message.material_source"));self._material.set(str(state.get("material", "")));self._pressure_unit.set(str(state.get("pressure_unit", "bar")));self._vapour_unit.set(str(state.get("vapour_unit", "bar")))
            self._items={str(item["id"]):LocalLossItem(str(item["name"]),int(item["quantity"]),float(item["k"])) for item in state.get("items", []) if isinstance(item,dict)};self._refresh_losses();self._set_roughness_source();self._set_status("loss",[]);self._set_status("enpy",[]);self._result.set(str(state.get("result", "")));self._formula.set(str(state.get("formula", "")));self._sync_detail_presentation()
        finally:
            self._suppress_dirty = False

    def clear_state(self) -> None:
        """Clear this page to its normal project-free defaults."""
        self._suppress_dirty = True
        try:
            self._clear()
        finally:
            self._suppress_dirty = False

    def _load_materials(self) -> None:
        self._material_ids.clear()
        labels: list[str] = []
        for material in self._materials.get_all_materials():
            label = f"{material.name} ({material.designation})"
            labels.append(label)
            self._material_ids[label] = material.id
        self._material_box.configure(values=labels)

    def _set_roughness_source(self, _event: object | None = None) -> None:
        manual = self._roughness_source_mode == "manual"
        self._material_box.configure(state="disabled" if manual else "readonly")
        self._roughness_entry.configure(state="normal" if manual else "readonly")
        if manual:
            self._fields["roughness"].set("")
        else:
            self._load_selected_roughness()
        self._invalidate_hydraulics()

    def _select_roughness_source(self, _event: object | None = None) -> None:
        """Map a selected display value to the stable roughness-source state."""
        self._roughness_source_mode = "manual" if self._roughness_source_box.current() == 1 else "material"
        self._set_roughness_source()

    def _load_selected_roughness(self, _event: object | None = None) -> None:
        identifier = self._material_ids.get(self._material.get())
        if identifier is None:
            self._fields["roughness"].set("")
            return
        material = self._materials.get_material(identifier)
        if material.roughness_mm is None:
            self._fields["roughness"].set("")
            self._set_status("loss", [ValidationIssue("material_roughness_missing")])
            return
        self._fields["roughness"].set(str(material.roughness_mm))
        self._invalidate_hydraulics()

    def _refresh_losses(self) -> None:
        for row in self._tree.get_children():
            self._tree.delete(row)
        for identifier, item in self._items.items():
            self._tree.insert("", "end", iid=identifier, values=(item.name, item.quantity, item.k_coefficient, item.subtotal_k))

    def _add_loss(self) -> None:
        item = LocalLossItemDialog(self).show()
        if item is not None:
            self._items[str(uuid4())] = item
            self._refresh_losses()
            self._invalidate_hydraulics()
            self._mark_dirty()

    def _edit_loss(self, _event: object | None = None) -> str:
        selected = self._tree.selection()
        if not selected:
            return "break"
        identifier = selected[0]
        item = LocalLossItemDialog(self, self._items[identifier]).show()
        if item is not None:
            self._items[identifier] = item
            self._refresh_losses()
            self._tree.selection_set(identifier)
            self._invalidate_hydraulics()
            self._mark_dirty()
        return "break"

    def _delete_loss(self, _event: object | None = None) -> str:
        selected = self._tree.selection()
        if selected and messagebox.askyesno(self._translate("dialog.delete_local_loss"), self._translate("confirm.delete_local_loss"), parent=self):
            del self._items[selected[0]]
            self._refresh_losses()
            self._invalidate_hydraulics()
            self._mark_dirty()
        return "break"

    def _clear_losses(self) -> None:
        if self._items and messagebox.askyesno(self._translate("dialog.clear_local_losses"), self._translate("confirm.clear_local_losses"), parent=self):
            self._items.clear()
            self._refresh_losses()
            self._invalidate_hydraulics()
            self._mark_dirty()

    def _calculate_suction_loss(self) -> None:
        """Calculate hydraulics without requiring pressure or NPSH inputs."""
        try:
            labels = {"diameter": "Pipe Inside Diameter (mm)", "flow": "Flow Rate", "viscosity": "Kinematic Viscosity", "length": "Pipe Length", "roughness": "Roughness (mm)"}
            field_keys = {"diameter": "field.pipe_inside_diameter", "flow": "field.flow_rate", "viscosity": "field.kinematic_viscosity", "length": "field.pipe_length", "roughness": "field.roughness"}
            number = lambda name: parse_engineering_float(self._fields[name].get(), field_name=labels[name], field_key=field_keys[name])
            material_id = self._material_ids.get(self._material.get()) if self._using_library_source() else None
            if self._using_library_source() and material_id is None:
                raise ValidationError(ValidationIssue("selection_required", "field.material"))
            if self._using_library_source() and not self._fields["roughness"].get().strip():
                raise ValidationError(ValidationIssue("material_roughness_missing"))
            result = self._service.calculate_suction_loss(number("diameter"), number("flow"), number("viscosity"), self._viscosity_unit.get(), number("length"), None if material_id else number("roughness"), list(self._items.values()), material_id)
        except ValidationError as error:
            self._result.set("")
            self._set_status("loss", [error.issue])
            return
        except Exception:
            logging.getLogger(__name__).exception("Suction-loss calculation failed")
            self._result.set("")
            self._set_status("loss", [ValidationIssue("unexpected_error")])
            return
        self._last_loss = result
        loss = result
        digits = int(self._constants.get_constant("display_decimal_places").value)
        format_value = lambda value: f"{value:.{digits}f}"
        self._suction_loss_summary.set(format_value(loss.total_hydraulic_loss_m))
        self._k_total_summary.set(format_value(loss.local_loss_coefficient_total))
        self._enpy_summary.set("—")
        self._render_current_results()
        self._set_status("loss", loss.warnings)
        self._set_status("enpy", [])
        self._formula.set("")
        self._mark_dirty()
        self._refresh_formula_panel()

    def _calculate_enpy(self) -> None:
        """Calculate ENPY using the current valid suction-line loss only."""
        loss = getattr(self, "_last_loss", None)
        if loss is None:
            self._set_status("enpy", [ValidationIssue("suction_loss_required_for_enpy")])
            return
        try:
            labels = {"pressure": "Suction Pressure (PE)", "vapour": "Vapour Pressure (Pb)", "density": "Fluid Density", "height": "Static Suction Height"}
            field_keys = {"pressure": "field.suction_pressure", "vapour": "field.vapour_pressure", "density": "field.fluid_density", "height": "field.static_suction_height"}
            number = lambda name: parse_engineering_float(self._fields[name].get(), field_name=labels[name], field_key=field_keys[name])
            result = self._service.calculate_enpy(loss.total_hydraulic_loss_m, number("pressure"), self._pressure_unit.get(), number("vapour"), self._vapour_unit.get(), number("density"), number("height"), parse_engineering_float(self._fields["required"].get(), field_name="NPSH Required", allow_empty=True, field_key="field.npsh_required"))
        except ValidationError as error:
            self._set_status("enpy", [error.issue])
            return
        except Exception:
            logging.getLogger(__name__).exception("ENPY calculation failed")
            self._set_status("enpy", [ValidationIssue("unexpected_error")])
            return
        self._last_enpy = result
        digits = int(self._constants.get_constant("display_decimal_places").value)
        format_value = lambda value: f"{value:.{digits}f}"
        self._enpy_summary.set(format_value(result.enpym_available_m))
        self._render_current_results()
        self._set_status("enpy", result.warnings)
        self._formula.set("")
        self._mark_dirty()
        self._refresh_formula_panel()

    def _formula_sections(self) -> list[FormulaSection]:
        """Return static suction/ENPY reference and stored-result substitutions."""
        loss = getattr(self, "_last_loss", None)
        enpy = getattr(self, "_last_enpy", None)
        sections = [
            FormulaSection("FORMULA", f"v = 4Q / (πD²)\nRe = vD / ν\nε = k / D\nf = {self._translate('formula.approved_ysh_moody_result')}\nKtotal = Σ(quantity × K)\nh_local = 6400 × Ktotal × Q² / D⁴\nh_pipe = 6.4 × 10⁶ × f × L × Q² / D⁵\nhe = h_pipe + h_local", "1. SUCTION HYDRAULICS", "formula"),
            FormulaSection("VARIABLES", f"D | {self._translate('field.pipe_inside_diameter')} | mm\nQ | {self._translate('field.flow_rate')} | m³/h\nν | {self._translate('field.kinematic_viscosity')} | m²/s\nL | {self._translate('field.pipe_length')} | m\nk | {self._translate('field.roughness')} | mm\nKtotal | {self._translate('formula.total_local_loss_coefficient')} | −\nhe | {self._translate('result.suction_head_loss')} | m", "1. SUCTION HYDRAULICS", "variables"),
            FormulaSection("CURRENT SUBSTITUTION", self._translate("message.available_after_suction_calculation"), "1. SUCTION HYDRAULICS", "substitution"),
            FormulaSection("RESULT", self._translate("message.available_after_suction_calculation"), "1. SUCTION HYDRAULICS", "result"),
            FormulaSection("FORMULA", f"ENPYm = PE/(ρg) − Pb/(ρg) − HEgeo − he\n{self._translate('result.npsh_margin')} = ENPYm − {self._translate('field.npsh_required')}", "2. ENPY / NPSH AVAILABLE", "formula"),
            FormulaSection("VARIABLES", f"PE | {self._translate('field.suction_pressure')} | Pa\nPb | {self._translate('field.vapour_pressure')} | Pa\nρ | {self._translate('field.fluid_density')} | kg/m³\ng | {self._translate('formula.standard_gravity')} | m/s²\nHEgeo | {self._translate('field.static_suction_height')} | m\nENPYm | {self._translate('result.available_npsh')} | m", "2. ENPY / NPSH AVAILABLE", "variables"),
            FormulaSection("NOTE", self._translate("formula.suction_enpy_note"), "2. ENPY / NPSH AVAILABLE", "note"),
            FormulaSection("CURRENT SUBSTITUTION", self._translate("message.available_after_enpy_calculation"), "2. ENPY / NPSH AVAILABLE", "substitution"),
            FormulaSection("RESULT", self._translate("message.available_after_enpy_calculation"), "2. ENPY / NPSH AVAILABLE", "result"),
        ]
        if loss is not None:
            digits = int(self._constants.get_constant("display_decimal_places").value)
            sections[2] = FormulaSection("CURRENT SUBSTITUTION", f"ν = {loss.metadata['viscosity_m2s']:.{digits}f} m²/s\nRe = {loss.reynolds_number:.{digits}f}\nf = {loss.friction_factor:.{digits}f}\nh_local = {loss.local_loss_m:.{digits}f} m\nh_pipe = {loss.pipe_friction_loss_m:.{digits}f} m", "1. SUCTION HYDRAULICS", "substitution")
            sections[3] = FormulaSection("RESULT", f"{self._translate('result.suction_head_loss')} he = {loss.total_hydraulic_loss_m:.{digits}f} m", "1. SUCTION HYDRAULICS", "result")
        if enpy is not None:
            digits = int(self._constants.get_constant("display_decimal_places").value)
            sections[7] = FormulaSection("CURRENT SUBSTITUTION", f"PE = {enpy.metadata['suction_pressure_pa']:.{digits}f} Pa\nPb = {enpy.metadata['vapour_pressure_pa']:.{digits}f} Pa\nHEgeo = {self._fields['height'].get()} m\nhe = {enpy.suction_loss_m:.{digits}f} m\nENPYm = PE/(ρg) − Pb/(ρg) − HEgeo − he", "2. ENPY / NPSH AVAILABLE", "substitution")
            sections[8] = FormulaSection("RESULT", f"{self._translate('result.available_npsh')} = {enpy.enpym_available_m:.{digits}f} m" + ("" if enpy.npsh_margin_m is None else f"\n{self._translate('result.npsh_margin')} = {enpy.npsh_margin_m:.{digits}f} m"), "2. ENPY / NPSH AVAILABLE", "result")
        return sections

    def _invalidate_hydraulics(self, _event: object | None = None, *_args: object) -> None:
        """Invalidate both calculation stages after a hydraulic input changes."""
        self.__dict__.pop("_last_loss", None);self.__dict__.pop("_last_enpy", None);self.__dict__.pop("_loss_display", None)
        self._result.set("")
        self._suction_loss_summary.set("—")
        self._enpy_summary.set("—")
        self._k_total_summary.set("—")
        for detail_value in self._detail_values.values():
            detail_value.set("—")
        self._sync_detail_presentation()
        self._formula.set("")
        self._set_status("loss", [])
        self._set_status("enpy", [])
        self._mark_dirty()
        self._refresh_formula_panel()

    def _invalidate_enpy(self, _event: object | None = None, *_args: object) -> None:
        """Invalidate ENPY while retaining a still-valid hydraulic result."""
        self.__dict__.pop("_last_enpy", None)
        self._result.set(getattr(self, "_loss_display", ""))
        self._enpy_summary.set("—")
        self._formula.set("")
        self._set_status("enpy", [])
        self._mark_dirty()
        self._refresh_formula_panel()

    def _refresh_formula_panel(self) -> None:
        """Update the expanded inline reference after state changes."""
        if self._formula_panel.expanded:
            self._formula_panel.refresh()

    def _render_current_results(self) -> None:
        """Render stored suction and ENPY results in the active language."""
        loss = getattr(self, "_last_loss", None)
        if loss is None:
            self._sync_detail_presentation()
            return
        digits = int(self._constants.get_constant("display_decimal_places").value)
        value = lambda number: f"{number:.{digits}f}"
        self._detail_values["flow_velocity"].set(f"{value(loss.flow_velocity_m_s)} m/s")
        self._detail_values["reynolds_number"].set(value(loss.reynolds_number))
        self._detail_values["flow_regime"].set(str(loss.flow_regime))
        self._detail_values["relative_roughness"].set(value(loss.relative_roughness))
        self._detail_values["friction_factor"].set(value(loss.friction_factor))
        self._detail_values["pipe_loss"].set(f"{value(loss.pipe_friction_loss_m)} m")
        self._detail_values["local_loss"].set(f"{value(loss.local_loss_m)} m")
        self._detail_values["k_total"].set(value(loss.local_loss_coefficient_total))
        display = "\n".join((
            f"{self._translate('result.flow_velocity')}: {value(loss.flow_velocity_m_s)} m/s    "
            f"{self._translate('result.reynolds_number')}: {value(loss.reynolds_number)}    "
            f"{self._translate('result.flow_regime')}: {loss.flow_regime}",
            f"{self._translate('result.relative_roughness')}: {value(loss.relative_roughness)}    "
            f"{self._translate('result.friction_factor')}: {value(loss.friction_factor)}",
            f"{self._translate('result.pipe_friction_loss')}: {value(loss.pipe_friction_loss_m)} m    "
            f"{self._translate('result.local_loss_coefficient')}: {value(loss.local_loss_coefficient_total)}    "
            f"{self._translate('result.local_loss')}: {value(loss.local_loss_m)} m",
            f"{self._translate('result.suction_head_loss')}: {value(loss.total_hydraulic_loss_m)} m",
        ))
        enpy = getattr(self, "_last_enpy", None)
        if enpy is not None:
            self._detail_values["suction_pressure_head"].set(
                f"{value(enpy.suction_pressure_head_m)} m"
            )
            self._detail_values["vapour_pressure_head"].set(
                f"{value(enpy.vapour_pressure_head_m)} m"
            )
            self._detail_values["npsh_margin"].set(
                "—" if enpy.npsh_margin_m is None else f"{value(enpy.npsh_margin_m)} m"
            )
            display += "\n" + (
                f"{self._translate('result.suction_pressure_head')}: {value(enpy.suction_pressure_head_m)} m    "
                f"{self._translate('result.vapour_pressure_head')}: {value(enpy.vapour_pressure_head_m)} m\n"
                f"{self._translate('result.available_npsh')}: {value(enpy.enpym_available_m)} m"
                + ("" if enpy.npsh_margin_m is None else f"    {self._translate('result.npsh_margin')}: {value(enpy.npsh_margin_m)} m")
            )
        else:
            for key in ("suction_pressure_head", "vapour_pressure_head", "npsh_margin"):
                self._detail_values[key].set("—")
        self._loss_display = display
        self._result.set(display)
        self._sync_detail_presentation()

    def _sync_detail_presentation(self) -> None:
        """Prefer structured live metrics while retaining persisted-text fallback."""
        if getattr(self, "_last_loss", None) is not None:
            self._details_card.grid()
            self._result_fallback.grid_remove()
        elif self._result.get().strip():
            self._details_card.grid_remove()
            self._result_fallback.grid()
        else:
            self._details_card.grid_remove()
            self._result_fallback.grid_remove()

    def _using_library_source(self) -> bool:
        """Return whether the active roughness source is the material library."""
        return self._roughness_source_mode == "material"

    def _clear(self) -> None:
        for field in self._fields.values():
            field.set("")
        self._items.clear()
        self._refresh_losses()
        self._material.set("")
        self._viscosity_unit.set("cSt")
        self._roughness_source_mode = "material"
        self._roughness_source.set(self._translate("message.material_source"))
        self._pressure_unit.set("bar")
        self._vapour_unit.set("bar")
        self._set_roughness_source()
        self._invalidate_hydraulics()
        self._mark_dirty()

    def _set_status(self, stage: str, messages: list[ValidationIssue]) -> None:
        """Store semantic status separately for the hydraulic and ENPY stages."""
        if stage == "loss":
            self._loss_status_messages = list(messages)
        else:
            self._enpy_status_messages = list(messages)
        self._render_status()

    def _render_status(self) -> None:
        """Render current stage status without recalculating either stage."""
        messages = self._enpy_status_messages or self._loss_status_messages
        if not messages:
            self._message.set(self._translate("message.ready"))
            return
        self._message.set(
            "; ".join(
                render_validation_issue(message, self._translator_proxy())
                for message in messages
            )
        )

    def _translator_proxy(self) -> object:
        """Expose the active translator to the shared semantic issue renderer."""
        return type("TranslatorProxy", (), {"translate": self._translate})()
