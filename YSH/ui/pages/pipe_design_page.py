"""TTK page for Version 1 pipe design."""
from __future__ import annotations
import math
import tkinter as tk
from uuid import UUID
from collections.abc import Callable
from tkinter import ttk
from engineering.pipe_design.models import PipeDiameterInput, WallThicknessInput
from engineering.input_parsing import parse_engineering_float
from engineering.precision import format_engineering_value
from i18n.translator import Translator
from i18n.validation import render_validation_issue
from engineering.validation import ValidationError, ValidationIssue
from services.pipe_design_service import PipeDesignService
from ui.widgets.formula_view import FormulaReferencePanel, FormulaSection
from ui.widgets.rounded_button import RoundedButtonPalette, RoundedImageButton
from ui.widgets.cards import (
    CalculationCard,
    InputCard,
    ResultCard,
    SectionHeader,
    SurfaceCard,
)
from ui.theme import colors
from ui.theme.spacing import MD, SM


_DN_WARNING_TRANSLATION_KEYS = {
    "no_suitable_dn": "pipe.warning.no_suitable_dn",
    "pipe_size_library_empty": "pipe.warning.pipe_size_library_empty",
}

_PIPE_BUTTON_PALETTE = RoundedButtonPalette(
    normal=(colors.PIPE, colors.PIPE_DEEP),
    hover=(colors.PIPE_ACTION_HOVER, colors.PIPE_DARK),
    pressed=(colors.PIPE_ACTION_PRESSED, colors.PIPE_DEEP),
    disabled=(colors.PIPE_DISABLED, colors.STRONG_BORDER),
    focus_border=colors.PIPE_DEEP,
)
_PIPE_NEUTRAL_BUTTON_PALETTE = RoundedButtonPalette(
    normal=(colors.CARD_SURFACE, colors.STRONG_BORDER),
    hover=(colors.SECONDARY_SURFACE, colors.STRONG_BORDER),
    pressed=("#E4EAF2", colors.BORDER),
    disabled=(colors.SECONDARY_SURFACE, colors.BORDER),
    focus_border=colors.NAVY,
)
_PIPE_FORMULA_BUTTON_PALETTE = RoundedButtonPalette(
    normal=(colors.FORMULA_SOFT, colors.FORMULA),
    hover=("#E8E4FF", colors.FORMULA),
    pressed=("#DCD6FF", "#1E00CC"),
    disabled=("#F1EFF5", "#D8D0E4"),
    focus_border=colors.FORMULA,
)
_PIPE_RECOMMENDED_BUTTON_PALETTE = RoundedButtonPalette(
    normal=(colors.CARD_SURFACE, colors.PIPE_BORDER),
    hover=(colors.PIPE_SOFT, colors.PIPE_DARK),
    pressed=(colors.PIPE_PRESSED_SOFT, colors.PIPE_DARK),
    disabled=(colors.SECONDARY_SURFACE, colors.BORDER),
    focus_border=colors.PIPE_DARK,
)


class PipeDesignPage(ttk.Frame):
    """Displays the pipe-diameter and wall-thickness workflow."""
    def __init__(
        self,
        parent: tk.Misc,
        service: PipeDesignService,
        translate: Callable[[str], str] | None = None,
    ) -> None:
        """Build a service-backed calculation page."""
        self._translate = translate or Translator().translate
        super().__init__(parent, style="PipePage.TFrame", padding=12)
        self._service = service
        self._message = tk.StringVar(value=self._t("message.ready"))
        self._diameter_summary = tk.StringVar(value="—")
        self._diameter_value = tk.StringVar(value="—")
        self._diameter_dn = tk.StringVar(value="—")
        self._recommended_outside_diameter = tk.StringVar(value="—")
        self._wall_summary = tk.StringVar(
            value=self._t("message.no_current_wall_calculation")
        )
        self._wall_value = tk.StringVar(value="—")
        self._wall_supporting = tk.StringVar(value="—")
        self._wall_allowable = tk.StringVar(value="—")
        self._wall_base = tk.StringVar(value="—")
        self._wall_bend = tk.StringVar(value="—")
        self._fields = {key: tk.StringVar() for key in ("q","v","da","pc","rp","sf","wf","c","r")}
        self._bend = tk.BooleanVar()
        self._source = tk.StringVar(value=self._t("message.material_source"))
        self._material = tk.StringVar()
        self._material_ids: dict[str, UUID] = {}
        self._diameter_result: dict[str, object] = {}
        self._diameter_warning_codes: list[str] = []
        self._wall_result: dict[str, object] = {}
        self._formula_text = ""
        self._manual_da_override = False
        self._display_places = 6
        self._dirty_callback: Callable[[], None] | None = None
        self._suppress_dirty = True
        self._widgets: list[tk.Misc] = []
        self._load_defaults()
        self._build()
        self._load_materials()
        self._set_source_mode()
        self.set_workspace_enabled(True)
        self._suppress_dirty = False
        for variable in (*self._fields.values(), self._bend, self._source, self._material):
            variable.trace_add("write", self._on_change)
        self._fields["da"].trace_add("write", self._on_outside_diameter_change)
    def set_dirty_callback(self, callback: Callable[[], None]) -> None:
        """Register the workspace callback used for genuine user edits."""
        self._dirty_callback=callback
    def _on_change(self,*_args:object)->None:
        if not self._suppress_dirty:
            self._diameter_result = {}
            self._diameter_warning_codes = []
            self._wall_result = {}
            self._formula_text = ""
            self._message.set(self._t("message.ready"))
            self._update_diameter_summary()
            self._update_wall_summary()
            if hasattr(self, "_formula_panel"):
                self._refresh_formula_panel()
            if self._dirty_callback is not None:self._dirty_callback()

    def _on_outside_diameter_change(self, *_args: object) -> None:
        """Track a genuine current-calculation outside-diameter override."""
        if not self._suppress_dirty:
            self._manual_da_override = True
    def _set_widget_state(self, widget: tk.Misc, state: str) -> None:
        """Apply a Tk state to a widget and its descendants when supported."""
        try:
            widget.configure(state=state)
        except (AttributeError, tk.TclError):
            pass

        try:
            for child in widget.winfo_children():
                self._set_widget_state(child, state)
        except Exception:
            pass

    def set_workspace_enabled(self, enabled: bool) -> None:
        """Enable or disable the calculation page for project ownership."""
        state = "normal" if enabled else "disabled"
        for widget in getattr(self, "_widgets", []):
            self._set_widget_state(widget, state)
    def export_state(self)->dict[str,object]:
        """Return every page-owned input, selection, result, and display state."""
        material_id = self._material_ids.get(self._material.get())
        return {
            "fields": {key: value.get() for key, value in self._fields.items()},
            "bend_enabled": self._bend.get(),
            "source_mode": self._source.get(),
            "material_id": None if material_id is None else str(material_id),
            "material_label": self._material.get(),
            "manual_outside_diameter_override": self._manual_da_override,
            "diameter_result": dict(self._diameter_result),
            "wall_result": dict(self._wall_result),
            "message": self._message.get(),
            "formula_text": self._formula_text,
            "display_decimal_places": self._display_places,
        }
    def load_state(self,state:dict[str,object])->None:
        """Restore saved page state without marking the workspace dirty."""
        self._suppress_dirty=True
        try:
            fields=state.get("fields",{})
            if isinstance(fields,dict):
                for key,value in fields.items():
                    if key in self._fields:self._fields[key].set(str(value))
            self._bend.set(bool(state.get("bend_enabled",False)))
            self._source.set(str(state.get("source_mode", "Material Library")))
            self._diameter_result = dict(state.get("diameter_result", {}))
            self._diameter_warning_codes = self._warning_codes_from_result()
            self._wall_result = dict(state.get("wall_result", {}))
            self._manual_da_override = bool(state.get("manual_outside_diameter_override", False))
            self._display_places = int(state.get("display_decimal_places", 6))
            saved_id = state.get("material_id")
            selected = ""
            if isinstance(saved_id, str):
                selected = next((label for label, identifier in self._material_ids.items() if str(identifier) == saved_id), "")
            self._material.set(selected)
            self._set_source_mode(reset_value=False)
            if self._source.get() == "Material Library" and selected:
                self._load_selected_material()
            self._formula_text = str(state.get("formula_text", ""))
            self._message.set(str(state.get("message", "Ready")))
        finally:self._suppress_dirty=False
        self._update_diameter_summary()
        self._update_wall_summary()
        self._refresh_diameter_warning_message()
        self._refresh_formula_panel()
    def clear_state(self)->None:
        """Clear project-specific values and reload saved engineering defaults."""
        self._suppress_dirty=True
        try:
            for field in self._fields.values():field.set("")
            self._bend.set(False);self._source.set(self._t("message.material_source"));self._material.set("");self._message.set(self._t("message.ready"));self._diameter_result={};self._diameter_warning_codes=[];self._wall_result={};self._formula_text="";self._manual_da_override=False;self._load_defaults();self._set_source_mode()
        finally:self._suppress_dirty=False
        self._update_diameter_summary()
        self._update_wall_summary()

    def _clear_user_state(self) -> None:
        """Clear user values while retaining default constants and reporting dirtiness."""
        self.clear_state()
        self._on_change()
    def _load_defaults(self) -> None:
        """Load saved library constants into current-calculation UI fields."""
        try:
            values = self._service.get_current_constants()
            self._fields["pc"].set(str(values["design_pressure_bar"]))
            self._fields["sf"].set(str(values["safety_factor"]))
            self._fields["wf"].set(str(values["weld_factor"]))
            self._fields["c"].set(str(values["corrosion_allowance_mm"]))
            self._display_places = int(values["display_decimal_places"])
        except ValueError as error:
            self._message.set(f"Error: {error}")
    def _build(self) -> None:
        """Compose the two-stage Pipe workflow from frame-based engineering surfaces."""
        self.columnconfigure(0, weight=1)
        self._header = SectionHeader(
            self,
            self._translate("page.pipe.title"),
            self._translate("page.pipe.description"),
        )
        self._header.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        inputs = ttk.Frame(self, style="PipePage.TFrame")
        inputs.grid(row=1, column=0, sticky="ew")
        self._layout_container = inputs
        inputs.columnconfigure(0, minsize=420, weight=6)
        inputs.columnconfigure(1, minsize=300, weight=4)

        self._diameter_inputs = SurfaceCard(
            inputs,
            self._translate("section.pipe_diameter_inputs"),
            style="PipeInputCard.TFrame",
            title_style="PipeInputCardTitle.TLabel",
            content_style="PipeInputCardContent.TFrame",
        )
        diameter_inputs = self._diameter_inputs
        self._diameter_inputs.columnconfigure(0, weight=1)
        diameter_inputs.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        diameter_form = diameter_inputs.content
        self._diameter_form = diameter_form
        diameter_form.columnconfigure(1, weight=1)

        self._diameter_result_card = SurfaceCard(
            inputs,
            self._translate("result.calculated_diameter"),
            style="PipeResultCard.TFrame",
            title_style="PipeResultCardTitle.TLabel",
            content_style="PipeResultCardContent.TFrame",
            accent_style="PipeResultAccent.TFrame",
            padding=(10, 8),
        )
        diameter_result = self._diameter_result_card
        self._diameter_result_card.columnconfigure(0, weight=1)
        diameter_result.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        diameter_metrics = diameter_result.content
        diameter_metrics.columnconfigure(0, weight=0)
        diameter_metrics.columnconfigure(1, weight=0)
        self._diameter_metric_label = ttk.Label(
            diameter_metrics,
            text=self._translate("result.calculated_diameter"),
            style="PipeMetricLabel.TLabel",
        )
        self._diameter_metric_label.grid(row=0, column=0, sticky="w")
        self._diameter_metric_value = ttk.Label(
            diameter_metrics,
            textvariable=self._diameter_value,
            style="PipeMetricValue.TLabel",
        )
        self._diameter_metric_value.grid(row=1, column=0, sticky="w")
        self._diameter_unit_label = ttk.Label(
            diameter_metrics,
            text="mm",
            style="PipeMetricUnit.TLabel",
        )
        self._diameter_unit_label.grid(row=1, column=1, sticky="sw", padx=(SM, 0))
        self._diameter_dn_label = ttk.Label(
            diameter_metrics,
            text=self._translate("result.recommended_nominal_size"),
            style="PipeMetricLabel.TLabel",
        )
        self._diameter_dn_label.grid(row=2, column=0, sticky="w", pady=(8, 0))
        self._diameter_dn_value = ttk.Label(
            diameter_metrics,
            textvariable=self._diameter_dn,
            style="PipeSupportingValue.TLabel",
        )
        self._diameter_dn_value.grid(row=3, column=0, sticky="w")
        self._recommended_outside_label = ttk.Label(
            diameter_metrics,
            text=self._translate("field.pipe_outside_diameter"),
            style="PipeMetricLabel.TLabel",
        )
        self._recommended_outside_label.grid(row=4, column=0, sticky="w", pady=(SM, 0))
        self._recommended_outside_value = ttk.Label(
            diameter_metrics,
            textvariable=self._recommended_outside_diameter,
            style="PipeSupportingValue.TLabel",
        )
        self._recommended_outside_value.grid(row=5, column=0, sticky="w")
        self._use_recommended_pipe_button = RoundedImageButton(
            diameter_metrics,
            text=self._translate("action.use_recommended_pipe"),
            command=self._use_recommended_pipe,
            style="PipeRoundedNeutral.TButton",
            palette=_PIPE_RECOMMENDED_BUTTON_PALETTE,
            radius=7,
            horizontal_padding=14,
            vertical_padding=7,
            state="disabled",
        )
        self._use_recommended_pipe_button.grid(row=6, column=0, sticky="w", pady=(SM, 0))

        self._wall_inputs = SurfaceCard(
            inputs,
            self._translate("section.wall_thickness_inputs"),
            style="PipeInputCard.TFrame",
            title_style="PipeInputCardTitle.TLabel",
            content_style="PipeInputCardContent.TFrame",
        )
        wall_inputs = self._wall_inputs
        self._wall_inputs.columnconfigure(0, weight=1)
        wall_inputs.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        wall_form = wall_inputs.content
        self._wall_form = wall_form
        for column in range(4):
            wall_form.columnconfigure(column, weight=0)
        wall_form.grid_anchor("w")

        material_group = ttk.Frame(wall_form, style="PipeGroup.TFrame")
        design_group = ttk.Frame(wall_form, style="PipeGroup.TFrame")
        allowance_group = ttk.Frame(wall_form, style="PipeGroup.TFrame")
        self._wall_groups = (material_group, design_group, allowance_group)
        for column, group in enumerate(
            (material_group, design_group, allowance_group)
        ):
            group.grid(row=0, column=column, sticky="nsew", padx=(0, SM))
            group.columnconfigure(1, weight=1)

        self._wall_group_labels = [
            ttk.Label(
                group,
                text=self._translate(key),
                style="PipeGroupTitle.TLabel",
            )
            for group, key in zip(
                (material_group, design_group, allowance_group),
                (
                    "pipe.group.material_pipe",
                    "pipe.group.design_conditions",
                    "pipe.group.allowances_bend",
                ),
            )
        ]
        for label in self._wall_group_labels:
            label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, SM))

        labels = (
            (material_group, "da", "field.pipe_outside_diameter", " da (mm)", 1),
            (material_group, "pc", "field.design_pressure", " pc (bar)", 2),
            (material_group, "rp", "field.yield_strength", " (MPa)", 3),
            (design_group, "sf", "field.safety_factor", "", 1),
            (design_group, "wf", "field.weld_factor", " (w)", 2),
            (allowance_group, "c", "field.corrosion_allowance", " c (mm)", 1),
            (allowance_group, "r", "field.bend_radius", " R (mm)", 2),
        )
        self._field_labels: dict[str, tuple[ttk.Label, str, str]] = {}
        for parent, key, label_key, suffix, target_row in labels:
            label = ttk.Label(
                parent,
                text=f"{self._translate(label_key)}{suffix}",
                style="PipeField.TLabel",
            )
            label.grid(row=target_row, column=0, sticky="w", pady=3)
            self._field_labels[key] = (label, label_key, suffix)
            entry = ttk.Entry(parent, textvariable=self._fields[key], width=15)
            entry.grid(row=target_row, column=1, padx=(SM, 0), pady=3, sticky="w")
            self._widgets.append(entry)
            if key == "rp":
                self._rp_entry = entry

        for target_row, key, label_key, suffix in (
            (1, "q", "field.flow_rate", " Q (m³/h)"),
            (2, "v", "field.design_velocity", " V (m/s)"),
        ):
            label = ttk.Label(
                diameter_form,
                text=f"{self._translate(label_key)}{suffix}",
                style="PipeField.TLabel",
            )
            label.grid(row=target_row, column=0, sticky="w", pady=3)
            self._field_labels[key] = (label, label_key, suffix)
            entry = ttk.Entry(diameter_form, textvariable=self._fields[key], width=16)
            entry.grid(row=target_row, column=1, padx=(SM, 0), pady=3, sticky="w")
            self._widgets.append(entry)

        self._source_label = ttk.Label(
            allowance_group,
            text=self._translate("field.rp_source"),
            style="PipeField.TLabel",
        )
        self._source_label.grid(row=3, column=0, sticky="w", pady=3)
        self._source_box = ttk.Combobox(allowance_group, textvariable=self._source, values=("Material Library", "Manual"), state="readonly", width=16)
        self._source_box.grid(row=3, column=1, sticky="w", padx=(SM, 0), pady=3)
        self._source_box.bind("<<ComboboxSelected>>", lambda _: self._set_source_mode())
        self._material_label = ttk.Label(
            allowance_group,
            text=self._translate("field.material"),
            style="PipeField.TLabel",
        )
        self._material_label.grid(row=4, column=0, sticky="w", pady=3)
        self._material_box = ttk.Combobox(allowance_group, textvariable=self._material, state="readonly", width=20)
        self._material_box.grid(row=4, column=1, sticky="w", padx=(SM, 0), pady=3)
        self._material_box.bind("<<ComboboxSelected>>", lambda _: self._load_selected_material())

        self._bend_check = ttk.Checkbutton(
            allowance_group,
            text=self._translate("result.bend_allowance"),
            variable=self._bend,
        )
        bend_check = self._bend_check
        bend_check.grid(row=5, column=0, columnspan=2, sticky="w", pady=(SM, 0))
        self._widgets.append(bend_check)

        self._diameter_button = RoundedImageButton(
            diameter_form,
            text=self._translate("calculation.calculate_diameter"),
            command=self._calculate_diameter,
            style="PipeRoundedPrimary.TButton",
            palette=_PIPE_BUTTON_PALETTE,
            radius=7,
            horizontal_padding=16,
            vertical_padding=7,
        )
        diameter_button = self._diameter_button
        diameter_button.grid(row=3, column=0, columnspan=2, sticky="w", pady=(MD, 0))
        self._widgets.append(diameter_button)

        action_row = ttk.Frame(wall_form, style="PipeInputCardContent.TFrame")
        self._wall_action_row = action_row
        action_row.grid(row=1, column=0, columnspan=3, sticky="w", pady=(MD, 0))
        self._wall_button = RoundedImageButton(
            action_row,
            text=self._translate("calculation.calculate_wall_thickness"),
            command=self._calculate_wall,
            style="PipeRoundedPrimary.TButton",
            palette=_PIPE_BUTTON_PALETTE,
            radius=7,
            horizontal_padding=16,
            vertical_padding=7,
        )
        wall_button = self._wall_button
        wall_button.pack(side="left")
        self._widgets.append(wall_button)
        self._clear_button = RoundedImageButton(
            action_row,
            text=self._translate("common.clear"),
            command=self._clear_user_state,
            style="PipeRoundedNeutral.TButton",
            palette=_PIPE_NEUTRAL_BUTTON_PALETTE,
            radius=7,
            horizontal_padding=15,
            vertical_padding=7,
        )
        clear_button = self._clear_button
        clear_button.pack(side="left", padx=(SM, 0))
        self._widgets.append(clear_button)

        self._wall_result_card = SurfaceCard(
            wall_form,
            self._translate("result.required_wall_thickness"),
            style="PipeResultCard.TFrame",
            title_style="PipeResultCardTitle.TLabel",
            content_style="PipeResultCardContent.TFrame",
            accent_style="PipeResultAccent.TFrame",
            padding=(10, 8),
        )
        wall_result = self._wall_result_card
        self._wall_result_card.grid(row=0, column=3, sticky="nsew")
        wall_metrics = wall_result.content
        wall_metrics.columnconfigure(0, weight=0)
        wall_metrics.columnconfigure(1, weight=0)
        self._wall_metric_label = ttk.Label(wall_metrics, text=self._translate("result.required_wall_thickness"), style="PipeMetricLabel.TLabel")
        self._wall_metric_label.grid(row=0, column=0, sticky="w")
        self._wall_metric_value = ttk.Label(wall_metrics, textvariable=self._wall_value, style="PipeMetricValue.TLabel")
        self._wall_metric_value.grid(row=1, column=0, sticky="w")
        self._wall_unit_label = ttk.Label(wall_metrics, text="mm", style="PipeMetricUnit.TLabel")
        self._wall_unit_label.grid(row=1, column=1, sticky="sw", padx=(SM, 0))
        self._wall_supporting_labels: list[ttk.Label] = []
        for row, key, value in (
            (2, "result.allowable_stress", self._wall_allowable),
            (3, "result.base_wall_thickness", self._wall_base),
            (4, "result.bend_allowance", self._wall_bend),
        ):
            label = ttk.Label(wall_metrics, text=self._translate(key), style="PipeMetricLabel.TLabel")
            label.grid(row=row, column=0, sticky="w", pady=(SM if row == 2 else 2, 0))
            ttk.Label(wall_metrics, textvariable=value, style="PipeSupportingValue.TLabel").grid(row=row, column=1, sticky="e", padx=(MD, 0))
            self._wall_supporting_labels.append(label)

        message_label = ttk.Label(self, textvariable=self._message, wraplength=650)
        message_label.grid(row=2, column=0, sticky="w", pady=(8, 0))
        self._widgets.append(message_label)
        self._formula_panel = FormulaReferencePanel(
            self,
            self._formula_sections,
            self._translate,
            self._create_formula_toggle,
        )
        self._formula_panel.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        self._responsive_layout_mode = ""
        self._layout_container.bind("<Configure>", self._on_layout_configure, add="+")
        self.after_idle(self._reflow_layout)

    @staticmethod
    def _create_formula_toggle(
        parent: tk.Misc,
        text: str,
        command: Callable[[], None],
    ) -> RoundedImageButton:
        """Create the Pipe-only tertiary formula action without changing its command."""
        return RoundedImageButton(
            parent,
            text=text,
            command=command,
            style="PipeRoundedFormula.TButton",
            palette=_PIPE_FORMULA_BUTTON_PALETTE,
            radius=7,
            horizontal_padding=15,
            vertical_padding=7,
        )

    def _on_layout_configure(self, event: tk.Event[tk.Misc]) -> None:
        """Reflow only when the live viewport can no longer fit the current cards."""
        self._reflow_layout(event.width)

    def _reflow_layout(self, available_width: int | None = None) -> None:
        """Select a content-measured Pipe layout without shrinking engineering controls."""
        width = available_width or self._layout_container.winfo_width()
        if width <= 1:
            return
        self._reflow_diameter_cards(width)
        self._reflow_wall_workspace(width)

    def _reflow_diameter_cards(self, available_width: int) -> None:
        """Stack the paired diameter cards only when their requested widths require it."""
        required_width = (
            self._diameter_inputs.winfo_reqwidth()
            + self._diameter_result_card.winfo_reqwidth()
            + SM
        )
        stacked = available_width < required_width
        mode = "diameter-stacked" if stacked else "diameter-wide"
        if getattr(self, "_diameter_layout_mode", "") == mode:
            return
        self._diameter_layout_mode = mode
        if stacked:
            self._layout_container.columnconfigure(0, minsize=0, weight=1)
            self._layout_container.columnconfigure(1, minsize=0, weight=0)
            self._diameter_inputs.grid_configure(
                row=0, column=0, columnspan=2, sticky="ew", padx=(0, 0)
            )
            self._diameter_result_card.grid_configure(
                row=1,
                column=0,
                columnspan=2,
                sticky="ew",
                padx=(0, 0),
                pady=(SM, 0),
            )
            self._wall_inputs.grid_configure(
                row=2, column=0, columnspan=2, sticky="ew", pady=(SM, 0)
            )
            return
        self._layout_container.columnconfigure(0, minsize=420, weight=6)
        self._layout_container.columnconfigure(1, minsize=300, weight=4)
        self._diameter_inputs.grid_configure(
            row=0, column=0, columnspan=1, sticky="nsew", padx=(0, SM // 2)
        )
        self._diameter_result_card.grid_configure(
            row=0, column=1, columnspan=1, sticky="nsew", padx=(SM // 2, 0), pady=0
        )
        self._wall_inputs.grid_configure(
            row=1, column=0, columnspan=2, sticky="ew", pady=(MD, 0)
        )

    def _reflow_wall_workspace(self, available_width: int) -> None:
        """Reflow compact wall groups from four columns to two columns or one stack."""
        material, design, allowances = self._wall_groups
        result = self._wall_result_card
        wide_width = sum(
            widget.winfo_reqwidth()
            for widget in (material, design, allowances, result)
        ) + (SM * 3)
        two_column_width = max(
            material.winfo_reqwidth(), design.winfo_reqwidth()
        ) + max(allowances.winfo_reqwidth(), result.winfo_reqwidth()) + SM
        content_width = max(1, available_width - (MD * 2))
        if content_width >= wide_width:
            mode = "wall-wide"
        elif content_width >= two_column_width:
            mode = "wall-two-column"
        else:
            mode = "wall-stacked"
        if getattr(self, "_wall_layout_mode", "") == mode:
            return
        self._wall_layout_mode = mode
        for column in range(4):
            self._wall_form.columnconfigure(column, minsize=0, weight=0)
        if mode == "wall-wide":
            material.grid_configure(row=0, column=0, sticky="nw", padx=(0, SM))
            design.grid_configure(row=0, column=1, sticky="nw", padx=(0, SM))
            allowances.grid_configure(row=0, column=2, sticky="nw", padx=(0, SM))
            result.grid_configure(row=0, column=3, sticky="nw", padx=0)
            self._wall_action_row.grid_configure(
                row=1, column=0, columnspan=3, sticky="w", pady=(MD, 0)
            )
            return
        if mode == "wall-two-column":
            material.grid_configure(row=0, column=0, sticky="nw", padx=(0, SM))
            design.grid_configure(row=0, column=1, sticky="nw", padx=0)
            allowances.grid_configure(row=1, column=0, sticky="nw", padx=(0, SM), pady=(SM, 0))
            result.grid_configure(row=1, column=1, sticky="nw", padx=0, pady=(SM, 0))
            self._wall_action_row.grid_configure(
                row=2, column=0, columnspan=2, sticky="w", pady=(MD, 0)
            )
            return
        material.grid_configure(row=0, column=0, sticky="nw", padx=0)
        design.grid_configure(row=1, column=0, sticky="nw", padx=0, pady=(SM, 0))
        allowances.grid_configure(row=2, column=0, sticky="nw", padx=0, pady=(SM, 0))
        result.grid_configure(row=3, column=0, sticky="nw", padx=0, pady=(SM, 0))
        self._wall_action_row.grid_configure(
            row=4, column=0, columnspan=1, sticky="w", pady=(MD, 0)
        )

    def refresh_texts(self) -> None:
        """Refresh Pipe Design labels without recreating inputs or result state."""
        self._header.set_content(self._translate("page.pipe.title"), self._translate("page.pipe.description"))
        self._diameter_inputs.set_title(self._translate("section.pipe_diameter_inputs"))
        self._wall_inputs.set_title(self._translate("section.wall_thickness_inputs"))
        for label, key in zip(self._wall_group_labels, ("pipe.group.material_pipe", "pipe.group.design_conditions", "pipe.group.allowances_bend")): label.configure(text=self._translate(key))
        for label, key, suffix in self._field_labels.values():
            label.configure(text=f"{self._translate(key)}{suffix}")
        self._bend_check.configure(text=self._translate("result.bend_allowance"))
        self._diameter_button.configure(text=self._translate("calculation.calculate_diameter"))
        self._wall_button.configure(text=self._translate("calculation.calculate_wall_thickness"))
        self._clear_button.configure(text=self._translate("common.clear"))
        self._diameter_result_card.set_title(self._translate("result.calculated_diameter"))
        self._wall_result_card.set_title(self._translate("result.required_wall_thickness"))
        self._diameter_metric_label.configure(text=self._translate("result.calculated_diameter"))
        self._diameter_dn_label.configure(text=self._translate("result.recommended_nominal_size"))
        self._recommended_outside_label.configure(
            text=self._translate("field.pipe_outside_diameter")
        )
        self._use_recommended_pipe_button.configure(
            text=self._translate("action.use_recommended_pipe")
        )
        self._wall_metric_label.configure(text=self._translate("result.required_wall_thickness"))
        for label, key in zip(
            self._wall_supporting_labels,
            (
                "result.allowable_stress",
                "result.base_wall_thickness",
                "result.bend_allowance",
            ),
        ):
            label.configure(text=self._translate(key))
        self._source_label.configure(text=self._translate("field.rp_source"))
        self._material_label.configure(text=self._translate("field.material"))
        self._source_box.configure(values=(
            self._translate("message.material_source"),
            self._translate("message.manual_source"),
        ))
        was_manual = self._source.get() in {"Manual", self._translate("message.manual_source")}
        self._suppress_dirty = True
        try:
            self._source.set(self._translate(
                "message.manual_source" if was_manual else "message.material_source"
            ))
        finally:
            self._suppress_dirty = False
        self._update_diameter_summary()
        self._update_wall_summary()
        self._refresh_diameter_warning_message()
        self._formula_panel.refresh_texts()
    def _load_materials(self) -> None:
        """Load material labels while retaining UUID identity separately."""
        labels=[]
        for material in self._service.get_all_materials():
            label=f"{material.name} ({material.designation})"
            labels.append(label);self._material_ids[label]=material.id
        self._material_box.configure(values=labels)
    def _set_source_mode(self, reset_value: bool = True) -> None:
        """Toggle source controls without modifying any library record."""
        manual=self._source.get() in {"Manual", self._translate("message.manual_source")}
        self._material_box.configure(state="disabled" if manual else "readonly")
        self._rp_entry.configure(state="normal" if manual else "readonly")
        if reset_value:
            self._fields["rp"].set("")
            self._message.set(self._t("message.ready"))
    def _load_selected_material(self) -> None:
        """Load the selected material yield strength into a readonly field."""
        material_id=self._material_ids.get(self._material.get())
        if material_id is None:return
        material=self._service.get_material(material_id)
        if material.yield_strength_mpa is None:
            self._fields["rp"].set("");self._message.set(self._translate("validation.material_yield_missing"));return
        self._fields["rp"].set(str(material.yield_strength_mpa));self._message.set(self._translate("message.ready"))
    def _number(self, key: str) -> float:
        """Parse one page field using centralized decimal normalization."""
        labels = {
            "q": "Flow Rate", "v": "Design Velocity", "da": "Outside Diameter",
            "pc": "Design Pressure (bar)", "rp": "Yield Strength Rp0.2 (MPa)",
            "sf": "Safety Factor", "wf": "Weld Factor", "c": "Corrosion Allowance",
            "r": "Bend Radius",
        }
        field_keys = {
            "q": "field.flow_rate", "v": "field.design_velocity",
            "da": "field.pipe_outside_diameter", "pc": "field.design_pressure",
            "rp": "field.yield_strength", "sf": "field.safety_factor",
            "wf": "field.weld_factor", "c": "field.corrosion_allowance",
            "r": "field.bend_radius",
        }
        value = parse_engineering_float(self._fields[key].get(), field_name=labels[key], field_key=field_keys[key])
        assert value is not None
        return value

    def _calculate_diameter(self)->None:
        """Calculate operation 1 without validating wall-thickness fields."""
        try:
            result=self._service.calculate(diameter=PipeDiameterInput(self._number("q"),self._number("v")))
            if result.errors:
                self._diameter_result = {}
                self._diameter_warning_codes = []
                self._update_diameter_summary()
                self._message.set(self._t("validation.unexpected_error"));return
            assert result.diameter is not None
            self._diameter_result = result.diameter.to_dict()
            self._diameter_warning_codes = self._warning_codes_from_result()
            self._update_diameter_summary()
            self._refresh_diameter_warning_message()
            self._refresh_formula_panel()
        except ValidationError as error:
            self._diameter_result = {}
            self._diameter_warning_codes = []
            self._update_diameter_summary()
            self._message.set(render_validation_issue(error.issue, self._translator_proxy()))
        except ValueError:
            self._diameter_result = {}
            self._diameter_warning_codes = []
            self._update_diameter_summary()
            self._message.set(self._t("validation.unexpected_error"))

    def _calculate_wall(self)->None:
        """Calculate operation 2 without requiring operation 1 inputs."""
        try:
            material_id=self._material_ids.get(self._material.get()) if self._using_library_source() else None
            if self._using_library_source() and material_id is None:raise ValidationError(ValidationIssue("selection_required", "field.material"))
            result=self._service.calculate(wall=WallThicknessInput(self._number("da"),self._number("pc"),self._number("rp"),self._number("sf"),self._number("wf"),self._number("c"),self._bend.get(),self._number("r") if self._bend.get() else None),material_id=material_id)
            if result.errors:
                self._message.set(self._t("validation.unexpected_error"))
                return
            assert result.wall_thickness is not None
            self._wall_result = result.wall_thickness.to_dict()
            self._update_wall_summary()
            self._message.set(f"Wall: {format_engineering_value(result.wall_thickness.final_wall_thickness_mm, self._display_places)} mm")
            self._refresh_formula_panel()
        except ValidationError as error:self._message.set(render_validation_issue(error.issue, self._translator_proxy()))
        except ValueError as error:self._message.set(f"Error: {error}")

    def _use_recommended_pipe(self) -> None:
        """Explicitly transfer only the recommended record's authoritative outside diameter."""
        diameter = self._recommended_outside_diameter_value()
        if diameter is None:
            return
        self._suppress_dirty = True
        try:
            self._fields["da"].set(str(diameter))
            self._manual_da_override = False
        finally:
            self._suppress_dirty = False
        if self._dirty_callback is not None:
            self._dirty_callback()

    def _recommended_outside_diameter_value(self) -> float | None:
        """Return the persisted library value only when the recommendation is current."""
        value = self._diameter_result.get("recommended_outside_diameter_mm")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return float(value) if math.isfinite(value) and value > 0 else None

    def _formula_sections(self) -> list[FormulaSection]:
        """Return static pipe reference plus any stored current calculation audit."""
        sections: list[FormulaSection] = [
            FormulaSection("FORMULA", "Qm³/s = Qm³/h / 3600\nD = √((4 × Qm³/s) / (π × V))", "1. PIPE DIAMETER", "formula"),
            FormulaSection("VARIABLES", f"D | {self._translate('result.calculated_diameter')} | mm\nQ | {self._translate('field.flow_rate')} | m³/h\nV | {self._translate('field.design_velocity')} | m/s\nπ | {self._translate('formula.mathematical_constant')} | −", "1. PIPE DIAMETER", "variables"),
            FormulaSection("CURRENT SUBSTITUTION", self._translate("message.available_after_calculation"), "1. PIPE DIAMETER", "substitution"),
            FormulaSection("RESULT", self._translate("message.available_after_calculation"), "1. PIPE DIAMETER", "result"),
            FormulaSection("FORMULA", "σallow = Rp0.2 / B", "2. ALLOWABLE STRESS", "formula"),
            FormulaSection("VARIABLES", f"σallow | {self._translate('result.allowable_stress')} | MPa\nRp0.2 | {self._translate('field.yield_strength')} | MPa\nB | {self._translate('field.safety_factor')} | −", "2. ALLOWABLE STRESS", "variables"),
            FormulaSection("CURRENT SUBSTITUTION", self._translate("message.available_after_wall_thickness_calculation"), "2. ALLOWABLE STRESS", "substitution"),
            FormulaSection("RESULT", self._translate("message.available_after_wall_thickness_calculation"), "2. ALLOWABLE STRESS", "result"),
            FormulaSection("FORMULA", "s0 = (da × pc) / ((20 × σallow × w) + pc)", "3. BASE WALL THICKNESS", "formula"),
            FormulaSection("VARIABLES", f"s0 | {self._translate('result.base_wall_thickness')} | mm\nda | {self._translate('field.pipe_outside_diameter')} | mm\npc | {self._translate('field.design_pressure')} | bar\nw | {self._translate('field.weld_factor')} | −", "3. BASE WALL THICKNESS", "variables"),
            FormulaSection("CURRENT SUBSTITUTION", self._translate("message.available_after_wall_thickness_calculation"), "3. BASE WALL THICKNESS", "substitution"),
            FormulaSection("RESULT", self._translate("message.available_after_wall_thickness_calculation"), "3. BASE WALL THICKNESS", "result"),
            FormulaSection("FORMULA", "b = 0.4 × (da / R) × s0", "4. BEND ALLOWANCE", "formula"),
            FormulaSection("VARIABLES", f"b | {self._translate('result.bend_allowance')} | mm\nR | {self._translate('field.bend_radius')} | mm\ns0 | {self._translate('result.base_wall_thickness')} | mm", "4. BEND ALLOWANCE", "variables"),
            FormulaSection("CURRENT SUBSTITUTION", self._translate("message.available_after_wall_thickness_calculation"), "4. BEND ALLOWANCE", "substitution"),
            FormulaSection("RESULT", self._translate("message.available_after_wall_thickness_calculation"), "4. BEND ALLOWANCE", "result"),
            FormulaSection("FORMULA", "s = s0 + c + b", "5. REQUIRED WALL THICKNESS", "formula"),
            FormulaSection("VARIABLES", f"s | {self._translate('result.required_wall_thickness')} | mm\nc | {self._translate('field.corrosion_allowance')} | mm\nb | {self._translate('result.bend_allowance')} | mm", "5. REQUIRED WALL THICKNESS", "variables"),
            FormulaSection("CURRENT SUBSTITUTION", self._translate("message.available_after_wall_thickness_calculation"), "5. REQUIRED WALL THICKNESS", "substitution"),
            FormulaSection("RESULT", self._translate("message.available_after_wall_thickness_calculation"), "5. REQUIRED WALL THICKNESS", "result"),
        ]
        if self._diameter_result:
            result = self._diameter_result
            sections[2] = FormulaSection("CURRENT SUBSTITUTION", f"Q = {self._fields['q'].get()} m³/h\nV = {self._fields['v'].get()} m/s\nD = √((4 × (Q / 3600)) / (π × V))", "1. PIPE DIAMETER", "substitution")
            sections[3] = FormulaSection("RESULT", f"{self._translate('result.calculated_diameter')} = {format_engineering_value(float(result['diameter_mm']), self._display_places)} mm", "1. PIPE DIAMETER", "result")
            if result.get("recommended_dn"):
                sections.append(FormulaSection("PIPE SIZE RECOMMENDATION", f"{self._translate('result.recommended_nominal_size')} = {result['recommended_dn']}\n{self._translate('formula.pipe_size_recommendation_note')}\n{self._translate('field.pipe_outside_diameter')} = {result.get('recommended_outside_diameter_mm')} mm", "PIPE SIZE RECOMMENDATION", "note"))
        if self._wall_result:
            result = self._wall_result
            substitution = f"σallow = {result['allowable_stress_mpa']:.{self._display_places}f} MPa\ns0 = {result['base_wall_thickness_mm']:.{self._display_places}f} mm\nb = {result['bend_allowance_mm']:.{self._display_places}f} mm\nc = {result['corrosion_allowance_mm']:.{self._display_places}f} mm"
            sections[6] = FormulaSection("CURRENT SUBSTITUTION", substitution, "2. ALLOWABLE STRESS", "substitution")
            sections[7] = FormulaSection("RESULT", f"{self._translate('result.allowable_stress')} = {result['allowable_stress_mpa']:.{self._display_places}f} MPa", "2. ALLOWABLE STRESS", "result")
            sections[10] = FormulaSection("CURRENT SUBSTITUTION", substitution, "3. BASE WALL THICKNESS", "substitution")
            sections[11] = FormulaSection("RESULT", f"{self._translate('result.base_wall_thickness')} s0 = {result['base_wall_thickness_mm']:.{self._display_places}f} mm", "3. BASE WALL THICKNESS", "result")
            sections[14] = FormulaSection("CURRENT SUBSTITUTION", f"b = {result['bend_allowance_mm']:.{self._display_places}f} mm", "4. BEND ALLOWANCE", "substitution")
            sections[15] = FormulaSection("RESULT", f"{self._translate('result.bend_allowance')} b = {result['bend_allowance_mm']:.{self._display_places}f} mm", "4. BEND ALLOWANCE", "result")
            sections[18] = FormulaSection("CURRENT SUBSTITUTION", substitution, "5. REQUIRED WALL THICKNESS", "substitution")
            sections[19] = FormulaSection("RESULT", f"{self._translate('result.required_wall_thickness')} = {result['final_wall_thickness_mm']:.{self._display_places}f} mm", "5. REQUIRED WALL THICKNESS", "result")
        return sections

    def _refresh_formula_panel(self) -> None:
        """Update an expanded formula reference after result-state changes."""
        if self._formula_panel.expanded:
            self._formula_panel.refresh()

    def _update_wall_summary(self) -> None:
        """Render wall details from the stored authoritative wall result only."""
        if not self._wall_result:
            self._wall_summary.set("—")
            self._wall_value.set("—")
            self._wall_supporting.set("—")
            self._wall_allowable.set("—")
            self._wall_base.set("—")
            self._wall_bend.set("—")
            return
        result = self._wall_result
        self._wall_value.set(
            f"{result['final_wall_thickness_mm']:.{self._display_places}f}"
        )
        self._wall_allowable.set(
            f"{result['allowable_stress_mpa']:.{self._display_places}f} MPa"
        )
        self._wall_base.set(
            f"{result['base_wall_thickness_mm']:.{self._display_places}f} mm"
        )
        self._wall_bend.set(
            f"{result['bend_allowance_mm']:.{self._display_places}f} mm"
        )
        self._wall_supporting.set(
            f"{self._t('result.allowable_stress')}: {result['allowable_stress_mpa']:.{self._display_places}f} MPa\n{self._t('result.base_wall_thickness')}: {result['base_wall_thickness_mm']:.{self._display_places}f} mm\n{self._t('result.bend_allowance')}: {result['bend_allowance_mm']:.{self._display_places}f} mm"
        )
        self._wall_summary.set(
            f"{self._t('result.allowable_stress')}: {result['allowable_stress_mpa']:.{self._display_places}f} MPa\n"
            f"{self._t('result.base_wall_thickness')}: {result['base_wall_thickness_mm']:.{self._display_places}f} mm\n"
            f"{self._t('result.bend_allowance')}: {result['bend_allowance_mm']:.{self._display_places}f} mm\n"
            f"{result['final_wall_thickness_mm']:.{self._display_places}f} mm\n"
            f"{self._t('result.allowable_stress')}: {result['allowable_stress_mpa']:.{self._display_places}f} MPa\n"
            f"{self._t('result.base_wall_thickness')}: {result['base_wall_thickness_mm']:.{self._display_places}f} mm\n"
            f"{self._t('result.bend_allowance')}: {result['bend_allowance_mm']:.{self._display_places}f} mm"
        )

    def _update_diameter_summary(self) -> None:
        """Render the stored library recommendation without duplicating DN state."""
        if not self._diameter_result:
            self._diameter_summary.set("—");getattr(self, "_diameter_value", self._diameter_summary).set("—");getattr(self, "_diameter_dn", self._diameter_summary).set("—");getattr(self, "_recommended_outside_diameter", self._diameter_summary).set("—")
            button = getattr(self, "_use_recommended_pipe_button", None)
            if button is not None: button.configure(state="disabled")
            return
        diameter = format_engineering_value(
            float(self._diameter_result["diameter_mm"]), self._display_places
        )
        recommended_dn = self._diameter_result.get("recommended_dn")
        getattr(self, "_diameter_value", self._diameter_summary).set(diameter)
        getattr(self, "_diameter_dn", self._diameter_summary).set(recommended_dn if isinstance(recommended_dn, str) and recommended_dn else "—")
        recommended_outside = self._recommended_outside_diameter_value()
        getattr(self, "_recommended_outside_diameter", self._diameter_summary).set(
            "—" if recommended_outside is None else f"{format_engineering_value(recommended_outside, self._display_places)} mm"
        )
        button = getattr(self, "_use_recommended_pipe_button", None)
        if button is not None:
            button.configure(state="normal" if recommended_outside is not None else "disabled")
        if isinstance(recommended_dn, str) and recommended_dn:
            recommendation = f"{self._t('result.recommended_nominal_size')}: {recommended_dn}"
        else:
            recommendation = self._render_diameter_warning_message()
        self._diameter_summary.set(f"{diameter} mm\n{recommendation}")

    def _warning_codes_from_result(self) -> list[str]:
        """Return persisted DN warning codes from the current diameter result."""
        warnings = self._diameter_result.get("warnings", [])
        return [warning for warning in warnings if isinstance(warning, str)] if isinstance(warnings, list) else []

    def _render_diameter_warning_message(self) -> str:
        """Render the current semantic DN warning state with the active language."""
        if not self._diameter_warning_codes:
            return self._t("pipe.warning.recommendation_unavailable")
        return "; ".join(
            self._t(
                _DN_WARNING_TRANSLATION_KEYS.get(
                    warning_code,
                    "pipe.warning.recommendation_unavailable",
                )
            )
            for warning_code in self._diameter_warning_codes
        )

    def _refresh_diameter_warning_message(self) -> None:
        """Refresh a visible DN warning without recalculating the diameter."""
        if self._diameter_warning_codes:
            self._message.set(self._render_diameter_warning_message())

    def _t(self, key: str) -> str:
        """Resolve localized display text while supporting display-only test doubles."""
        return getattr(self, "_translate", Translator().translate)(key)

    def _translator_proxy(self) -> object:
        """Expose the page's active translation callable to the shared renderer."""
        return type("TranslatorProxy", (), {"translate": self._translate})()

    def _using_library_source(self) -> bool:
        """Return whether the source selector represents the library mode."""
        return self._source.get() not in {
            "Manual", self._translate("message.manual_source"), "manual"
        }
