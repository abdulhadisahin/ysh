"""TTK page for Version 1 pipe design."""
from __future__ import annotations
import math
import tkinter as tk
from uuid import UUID
from collections.abc import Callable
from tkinter import ttk
from engineering.pipe_design.models import PipeDiameterInput, WallThicknessInput
from engineering.input_parsing import parse_engineering_float
from core.bend_radius import (
    BEND_RADIUS_MODES,
    DEFAULT_BEND_RADIUS_MODE,
    automatic_bend_radius_mm,
    bend_radius_mode,
)
from core.engineering_context import LINE_ROLES, warning_fluid_for_circuit
from engineering.warning_rules import evaluate_velocity
from ui.formatting import format_user_number
from i18n.translator import Translator
from i18n.validation import render_validation_issue
from engineering.validation import ValidationError, ValidationIssue
from services.pipe_design_service import PipeDesignService
from services.pipe_size_service import PipeSizeService
from ui.widgets.formula_view import FormulaReferencePanel, FormulaSection
from ui.widgets.engineering_warning_panel import EngineeringWarningPanel
from ui.widgets.rounded_button import RoundedButtonPalette, RoundedImageButton
from ui.dialogs.turk_loydu_table_8_9_dialog import TurkLoyduTable89Dialog
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
    "selected_standard_empty": "pipe.warning.selected_standard_empty",
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
        self._diameter_standard = tk.StringVar(value="—")
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
        self._bend_mode = tk.StringVar(value=DEFAULT_BEND_RADIUS_MODE)
        self._bend_mode_labels: dict[str, str] = {}
        self._bend_mode_codes: dict[str, str] = {}
        self._manual_bend_radius_mm = ""
        self._last_bend_mode = DEFAULT_BEND_RADIUS_MODE
        self._source = tk.StringVar(value=self._t("message.material_source"))
        self._material = tk.StringVar()
        self._circuit = tk.StringVar()
        self._line_role = tk.StringVar(value=self._t("message.select"))
        self._line_role_codes: dict[str, str] = {}
        self._circuit_codes: dict[str, str] = {}
        self._circuit_defaults: dict[str, float] = {}
        self._circuit_names: dict[str, str] = {}
        self._circuit_default_c = tk.StringVar(value="—")
        self._circuit_used_c = tk.StringVar(value="—")
        self._corrosion_allowance_override = False
        self._pipe_standard = tk.StringVar()
        self._pipe_standard_codes: dict[str, str] = {}
        self._pipe_standard_names: dict[str, str] = {}
        self._material_ids: dict[str, UUID] = {}
        self._diameter_result: dict[str, object] = {}
        self._diameter_warning_velocity_m_s: float | None = None
        self._diameter_warning_codes: list[str] = []
        self._engineering_findings = ()
        self._wall_result: dict[str, object] = {}
        self._formula_text = ""
        self._manual_da_override = False
        self._display_places = 2
        self._dirty_callback: Callable[[], None] | None = None
        self._suppress_dirty = True
        self._widgets: list[tk.Misc] = []
        # Keep a visible, parseable engineering default even if library-default
        # loading is temporarily unavailable during page construction.
        self._fields["wf"].set(format_user_number(1.0))
        self._fields["sf"].set(format_user_number(1.8))
        self._load_defaults()
        self._build()
        self._load_line_roles()
        self._load_bend_modes()
        self._load_pipe_standards()
        self._load_circuits()
        self._load_materials()
        self._set_source_mode()
        self.set_workspace_enabled(True)
        self._suppress_dirty = False
        for variable in (self._fields["q"], self._fields["v"], self._pipe_standard):
            variable.trace_add("write", self._on_part1_change)
        for variable in (
            self._fields["da"], self._fields["pc"], self._fields["rp"],
            self._fields["sf"], self._fields["wf"], self._fields["c"],
            self._fields["r"], self._bend, self._source, self._material,
            self._circuit, self._bend_mode,
        ):
            variable.trace_add("write", self._on_part2_change)
        self._fields["da"].trace_add("write", self._on_outside_diameter_change)
        self._fields["c"].trace_add("write", self._on_corrosion_allowance_change)
        self._fields["r"].trace_add("write", self._on_bend_radius_change)
    def set_dirty_callback(self, callback: Callable[[], None]) -> None:
        """Register the workspace callback used for genuine user edits."""
        self._dirty_callback=callback
    def _mark_dirty(self) -> None:
        if self._dirty_callback is not None:
            self._dirty_callback()

    def _on_part1_change(self,*_args:object)->None:
        if not self._suppress_dirty:
            self._diameter_result = {}
            self._diameter_warning_velocity_m_s = None
            self._diameter_warning_codes = []
            self._engineering_findings = ()
            if hasattr(self, "_warning_panel"):
                self._warning_panel.set_findings(())
            self._formula_text = ""
            self._message.set(self._t("message.ready"))
            self._update_diameter_summary()
            if hasattr(self, "_formula_panel"):
                self._refresh_formula_panel()
            self._mark_dirty()

    def _on_part2_change(self,*_args:object)->None:
        if not self._suppress_dirty:
            self._wall_result = {}
            self._formula_text = ""
            self._message.set(self._t("message.ready"))
            self._update_wall_summary()
            if hasattr(self, "_formula_panel"):
                self._refresh_formula_panel()
            self._mark_dirty()

    def _on_outside_diameter_change(self, *_args: object) -> None:
        """Track a genuine current-calculation outside-diameter override."""
        if not self._suppress_dirty:
            self._manual_da_override = True
            self._refresh_automatic_bend_radius()

    def _on_bend_radius_change(self, *_args: object) -> None:
        """Retain only a Manual R entry as a manual bend-radius value."""
        if not self._suppress_dirty and self._selected_bend_mode_code() == "MANUAL":
            self._manual_bend_radius_mm = self._fields["r"].get()

    def _on_corrosion_allowance_change(self, *_args: object) -> None:
        """Keep a manual c entry local to the current calculation."""
        if not self._suppress_dirty:
            self._corrosion_allowance_override = True
            self._update_circuit_summary()
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
            "pipe_standard_code": self._selected_pipe_standard_code(),
            "circuit_code": self._selected_circuit_code(),
            "line_role": self._selected_line_role_code(),
            "corrosion_allowance_manual_override": self._corrosion_allowance_override,
            "bend_enabled": self._bend.get(),
            "bend_mode": self._selected_bend_mode_code(),
            "manual_bend_radius_mm": self._manual_bend_radius_mm,
            "source_mode": self._source.get(),
            "material_id": None if material_id is None else str(material_id),
            "material_label": self._material.get(),
            "manual_outside_diameter_override": self._manual_da_override,
            "diameter_result": dict(self._diameter_result),
            "diameter_warning_velocity_m_s": self._diameter_warning_velocity_m_s,
            "wall_result": dict(self._wall_result),
            "message": self._message.get(),
            "formula_text": self._formula_text,
            "display_decimal_places": self._display_places,
        }
    def load_state(self,state:dict[str,object])->None:
        """Restore saved page state without marking the workspace dirty."""
        standard_missing = False
        circuit_missing = False
        self._suppress_dirty=True
        try:
            fields=state.get("fields",{})
            if isinstance(fields,dict):
                for key,value in fields.items():
                    if key in self._fields:self._fields[key].set(str(value))
            self._bend.set(bool(state.get("bend_enabled",False)))
            self._select_bend_mode(
                state.get("bend_mode") if isinstance(state.get("bend_mode"), str) else None,
                preserve_manual=False,
            )
            saved_manual_radius = state.get("manual_bend_radius_mm")
            self._manual_bend_radius_mm = (
                str(saved_manual_radius) if isinstance(saved_manual_radius, (str, int, float)) else ""
            )
            if self._selected_bend_mode_code() == "MANUAL":
                self._fields["r"].set(self._manual_bend_radius_mm or self._fields["r"].get())
            else:
                self._refresh_automatic_bend_radius()
            saved_standard = state.get("pipe_standard_code")
            standard_missing = isinstance(saved_standard, str) and bool(saved_standard.strip()) and not self._select_pipe_standard(saved_standard)
            if not isinstance(saved_standard, str) or not saved_standard.strip():
                self._select_pipe_standard(None)
            saved_circuit = state.get("circuit_code")
            circuit_missing = isinstance(saved_circuit, str) and bool(saved_circuit.strip()) and not self._select_circuit(saved_circuit, apply_default=False)
            if not isinstance(saved_circuit, str) or not saved_circuit.strip():
                self._select_circuit(None, apply_default=False)
            self._select_line_role(state.get("line_role") if isinstance(state.get("line_role"), str) else None)
            self._corrosion_allowance_override = bool(state.get("corrosion_allowance_manual_override", False))
            self._source.set(str(state.get("source_mode", "Material Library")))
            self._diameter_result = dict(state.get("diameter_result", {}))
            saved_velocity = state.get("diameter_warning_velocity_m_s")
            self._diameter_warning_velocity_m_s = float(saved_velocity) if isinstance(saved_velocity, (int, float)) and not isinstance(saved_velocity, bool) else None
            self._diameter_warning_codes = self._warning_codes_from_result()
            self._wall_result = dict(state.get("wall_result", {}))
            self._manual_da_override = bool(state.get("manual_outside_diameter_override", False))
            self._display_places = 2
            saved_id = state.get("material_id")
            selected = ""
            if isinstance(saved_id, str):
                selected = next((label for label, identifier in self._material_ids.items() if str(identifier) == saved_id), "")
            self._material.set(selected)
            self._set_source_mode(reset_value=False)
            if self._source.get() == "Material Library" and selected:
                self._load_selected_material()
            self._formula_text = str(state.get("formula_text", ""))
            self._message.set(
                self._t("validation.circuit_not_found") if circuit_missing else self._t("validation.pipe_standard_not_found")
                if standard_missing or circuit_missing
                else str(state.get("message", "Ready"))
            )
        finally:self._suppress_dirty=False
        self._update_diameter_summary()
        self._update_wall_summary()
        self._refresh_diameter_warning_message()
        self._evaluate_velocity_warning()
        self._refresh_formula_panel()
    def clear_state(self)->None:
        """Clear project-specific values and reload saved engineering defaults."""
        self._suppress_dirty=True
        try:
            for field in self._fields.values():field.set("")
            self._select_pipe_standard(None)
            self._select_circuit(None)
            self._select_line_role(None)
            self._bend.set(False);self._select_bend_mode(None, preserve_manual=False);self._manual_bend_radius_mm="";self._source.set(self._t("message.material_source"));self._material.set("");self._message.set(self._t("message.ready"));self._diameter_result={};self._diameter_warning_velocity_m_s=None;self._diameter_warning_codes=[];self._wall_result={};self._formula_text="";self._manual_da_override=False;self._corrosion_allowance_override=False;self._load_defaults();self._set_source_mode()
        finally:self._suppress_dirty=False
        self._update_diameter_summary()
        self._update_wall_summary()
        self._update_circuit_summary()

    def _clear_user_state(self) -> None:
        """Clear user values while retaining default constants and reporting dirtiness."""
        self.clear_state()
        self._mark_dirty()
    def _load_defaults(self) -> None:
        """Load saved library constants into current-calculation UI fields."""
        try:
            values = self._service.get_current_constants()
            self._fields["pc"].set(str(values["design_pressure_bar"]))
            self._fields["sf"].set(format_user_number(values["safety_factor"]))
            self._fields["wf"].set(format_user_number(values["weld_factor"]))
            self._fields["c"].set(str(values["corrosion_allowance_mm"]))
            self._display_places = 2
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
        self._diameter_standard_label = ttk.Label(
            diameter_metrics,
            text=self._translate("field.pipe_standard"),
            style="PipeMetricLabel.TLabel",
        )
        self._diameter_standard_label.grid(row=2, column=0, sticky="w", pady=(8, 0))
        self._diameter_standard_value = ttk.Label(
            diameter_metrics,
            textvariable=self._diameter_standard,
            style="PipeSupportingValue.TLabel",
        )
        self._diameter_standard_value.grid(row=3, column=0, sticky="w")
        self._diameter_dn_label = ttk.Label(
            diameter_metrics,
            text=self._translate("result.recommended_nominal_size"),
            style="PipeMetricLabel.TLabel",
        )
        self._diameter_dn_label.grid(row=4, column=0, sticky="w", pady=(8, 0))
        self._diameter_dn_value = ttk.Label(
            diameter_metrics,
            textvariable=self._diameter_dn,
            style="PipeSupportingValue.TLabel",
        )
        self._diameter_dn_value.grid(row=5, column=0, sticky="w")
        self._recommended_outside_label = ttk.Label(
            diameter_metrics,
            text=self._translate("field.pipe_outside_diameter"),
            style="PipeMetricLabel.TLabel",
        )
        self._recommended_outside_label.grid(row=6, column=0, sticky="w", pady=(SM, 0))
        self._recommended_outside_value = ttk.Label(
            diameter_metrics,
            textvariable=self._recommended_outside_diameter,
            style="PipeSupportingValue.TLabel",
        )
        self._recommended_outside_value.grid(row=7, column=0, sticky="w")
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
        self._use_recommended_pipe_button.grid(row=8, column=0, sticky="w", pady=(SM, 0))

        self._wall_inputs = SurfaceCard(
            inputs,
            self._translate("section.wall_thickness_inputs"),
            style="PipeInputCard.TFrame",
            title_style="PipeInputCardTitle.TLabel",
            content_style="PipeInputCardContent.TFrame",
        )
        wall_inputs = self._wall_inputs
        self._wall_inputs.columnconfigure(0, weight=1)
        wall_inputs.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
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
            (allowance_group, "c", "field.corrosion_allowance", " c (mm)", 2),
            (allowance_group, "r", "field.bend_radius_value", " R (mm)", 4),
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
            if key == "r":
                self._bend_radius_entry = entry

        self._bend_mode_label = ttk.Label(
            allowance_group,
            text=self._translate("field.bend_radius"),
            style="PipeField.TLabel",
        )
        self._bend_mode_label.grid(row=3, column=0, sticky="w", pady=3)
        self._bend_mode_box = ttk.Combobox(
            allowance_group, textvariable=self._bend_mode, state="readonly", width=16
        )
        self._bend_mode_box.grid(row=3, column=1, sticky="w", padx=(SM, 0), pady=3)
        self._bend_mode_box.bind("<<ComboboxSelected>>", self._on_bend_mode_selected)
        self._widgets.append(self._bend_mode_box)
        self._bend_convention_label = ttk.Label(
            allowance_group,
            text=self._translate("pipe.bend_radius_convention"),
            style="PipeField.TLabel",
            wraplength=250,
        )
        self._bend_convention_label.grid(row=5, column=0, columnspan=2, sticky="w", pady=(2, SM))

        self._circuit_label = ttk.Label(
            allowance_group, text=self._translate("field.circuit"), style="PipeField.TLabel"
        )
        self._circuit_label.grid(row=1, column=0, sticky="w", pady=3)
        self._circuit_box = ttk.Combobox(
            allowance_group, textvariable=self._circuit, state="readonly", width=20
        )
        self._circuit_box.grid(row=1, column=1, sticky="w", padx=(SM, 0), pady=3)
        self._circuit_box.bind("<<ComboboxSelected>>", self._on_circuit_selected)
        self._widgets.append(self._circuit_box)
        self._line_role_label = ttk.Label(allowance_group, text=self._translate("field.line_role"), style="PipeField.TLabel")
        self._line_role_label.grid(row=12, column=0, sticky="w", pady=(SM, 3))
        self._line_role_box = ttk.Combobox(allowance_group, textvariable=self._line_role, state="readonly", width=20)
        self._line_role_box.grid(row=12, column=1, sticky="w", padx=(SM, 0), pady=(SM, 3))
        self._line_role_box.bind("<<ComboboxSelected>>", self._on_line_role_selected)
        self._widgets.append(self._line_role_box)

        self._pipe_standard_label = ttk.Label(
            diameter_form,
            text=self._translate("field.pipe_standard"),
            style="PipeField.TLabel",
        )
        self._pipe_standard_label.grid(row=1, column=0, sticky="w", pady=3)
        self._pipe_standard_box = ttk.Combobox(
            diameter_form,
            textvariable=self._pipe_standard,
            state="readonly",
            width=24,
        )
        self._pipe_standard_box.grid(row=1, column=1, padx=(SM, 0), pady=3, sticky="w")
        self._pipe_standard_box.bind("<<ComboboxSelected>>", self._on_pipe_standard_selected)
        self._widgets.append(self._pipe_standard_box)

        for target_row, key, label_key, suffix in (
            (2, "q", "field.flow_rate", " Q (m³/h)"),
            (3, "v", "field.design_velocity", " V (m/s)"),
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
        self._source_label.grid(row=6, column=0, sticky="w", pady=3)
        self._source_box = ttk.Combobox(allowance_group, textvariable=self._source, values=("Material Library", "Manual"), state="readonly", width=16)
        self._source_box.grid(row=6, column=1, sticky="w", padx=(SM, 0), pady=3)
        self._source_box.bind("<<ComboboxSelected>>", lambda _: self._set_source_mode())
        self._material_label = ttk.Label(
            allowance_group,
            text=self._translate("field.material"),
            style="PipeField.TLabel",
        )
        self._material_label.grid(row=7, column=0, sticky="w", pady=3)
        self._material_box = ttk.Combobox(allowance_group, textvariable=self._material, state="readonly", width=20)
        self._material_box.grid(row=7, column=1, sticky="w", padx=(SM, 0), pady=3)
        self._material_box.bind("<<ComboboxSelected>>", lambda _: self._load_selected_material())

        self._bend_check = ttk.Checkbutton(
            allowance_group,
            text=self._translate("result.bend_allowance"),
            variable=self._bend,
        )
        bend_check = self._bend_check
        bend_check.grid(row=8, column=0, columnspan=2, sticky="w", pady=(SM, 0))
        self._widgets.append(bend_check)

        self._table_89_button = ttk.Button(
            allowance_group, text="Türk Loydu Tablo 8.9", command=self._open_table_8_9
        )
        self._table_89_button.grid(row=11, column=0, columnspan=2, sticky="w", pady=(SM, 0))
        self._widgets.append(self._table_89_button)

        self._circuit_default_label = ttk.Label(allowance_group, text=self._translate("result.default_corrosion_allowance"), style="PipeField.TLabel")
        self._circuit_default_label.grid(row=9, column=0, sticky="w", pady=(SM, 0))
        ttk.Label(allowance_group, textvariable=self._circuit_default_c, style="PipeSupportingValue.TLabel").grid(row=9, column=1, sticky="w", padx=(SM, 0), pady=(SM, 0))
        self._circuit_used_label = ttk.Label(allowance_group, text=self._translate("result.used_corrosion_allowance"), style="PipeField.TLabel")
        self._circuit_used_label.grid(row=10, column=0, sticky="w", pady=2)
        ttk.Label(allowance_group, textvariable=self._circuit_used_c, style="PipeSupportingValue.TLabel").grid(row=10, column=1, sticky="w", padx=(SM, 0), pady=2)

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
        diameter_button.grid(row=4, column=0, columnspan=2, sticky="w", pady=(MD, 0))
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
        self._warning_panel = EngineeringWarningPanel(inputs, self._translate)
        self._warning_panel.grid(row=1, column=1, sticky="ew", padx=(SM // 2, 0), pady=(SM, 0))
        self._warning_panel.set_findings(())
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

    def _open_table_8_9(self) -> None:
        """Open an informational reference only; do not mutate inputs or state."""
        TurkLoyduTable89Dialog(self)

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
            self._warning_panel.grid_configure(row=2, column=0, columnspan=2, sticky="ew", padx=0, pady=(SM, 0))
            self._wall_inputs.grid_configure(row=3, column=0, columnspan=2, sticky="ew", pady=(SM, 0))
            return
        self._layout_container.columnconfigure(0, minsize=420, weight=6)
        self._layout_container.columnconfigure(1, minsize=300, weight=4)
        self._diameter_inputs.grid_configure(
            row=0, column=0, columnspan=1, sticky="nsew", padx=(0, SM // 2)
        )
        self._diameter_result_card.grid_configure(
            row=0, column=1, columnspan=1, sticky="nsew", padx=(SM // 2, 0), pady=0
        )
        self._warning_panel.grid_configure(row=1, column=1, columnspan=1, sticky="ew", padx=(SM // 2, 0), pady=(SM, 0))
        self._wall_inputs.grid_configure(
            row=2, column=0, columnspan=2, sticky="ew", pady=(MD, 0)
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
        self._bend_mode_label.configure(text=self._translate("field.bend_radius"))
        self._bend_convention_label.configure(text=self._translate("pipe.bend_radius_convention"))
        self._diameter_button.configure(text=self._translate("calculation.calculate_diameter"))
        self._wall_button.configure(text=self._translate("calculation.calculate_wall_thickness"))
        self._clear_button.configure(text=self._translate("common.clear"))
        self._diameter_result_card.set_title(self._translate("result.calculated_diameter"))
        self._wall_result_card.set_title(self._translate("result.required_wall_thickness"))
        self._diameter_metric_label.configure(text=self._translate("result.calculated_diameter"))
        self._pipe_standard_label.configure(text=self._translate("field.pipe_standard"))
        self._diameter_standard_label.configure(text=self._translate("field.pipe_standard"))
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
        self._circuit_label.configure(text=self._translate("field.circuit"))
        self._line_role_label.configure(text=self._translate("field.line_role"))
        self._circuit_default_label.configure(text=self._translate("result.default_corrosion_allowance"))
        self._circuit_used_label.configure(text=self._translate("result.used_corrosion_allowance"))
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
        bend_code = self._selected_bend_mode_code()
        self._suppress_dirty = True
        try:
            self._load_bend_modes()
            self._select_bend_mode(bend_code, preserve_manual=False)
        finally:
            self._suppress_dirty = False
        self._update_diameter_summary()
        self._update_wall_summary()
        self._update_circuit_summary()
        self._load_line_roles()
        self._warning_panel.refresh_texts()
        self._evaluate_velocity_warning()
        self._refresh_diameter_warning_message()
        self._formula_panel.refresh_texts()

    def _load_bend_modes(self) -> None:
        """Expose stable D243 bend-mode codes through localized visible labels."""
        current = self._selected_bend_mode_code()
        self._bend_mode_labels.clear()
        self._bend_mode_codes.clear()
        for mode in BEND_RADIUS_MODES:
            label = self._translate(f"pipe.bend_mode.{mode.code}")
            self._bend_mode_labels[mode.code] = label
            self._bend_mode_codes[label] = mode.code
        self._bend_mode_box.configure(values=list(self._bend_mode_codes))
        self._select_bend_mode(current, preserve_manual=False)

    def _selected_bend_mode_code(self) -> str:
        """Resolve the visible selector value to its persistence-safe mode code."""
        selected = getattr(self, "_bend_mode", None)
        if selected is None:
            return DEFAULT_BEND_RADIUS_MODE
        value = selected.get()
        return getattr(self, "_bend_mode_codes", {}).get(value, value if value in {mode.code for mode in BEND_RADIUS_MODES} else DEFAULT_BEND_RADIUS_MODE)

    def _selected_bend_mode_label(self) -> str:
        mode = bend_radius_mode(self._selected_bend_mode_code())
        return getattr(self, "_bend_mode_labels", {}).get(mode.code, mode.label)

    def _select_bend_mode(self, code: str | None, *, preserve_manual: bool = True) -> None:
        """Set a mode and apply its deterministic R ownership rule."""
        mode = bend_radius_mode(code)
        previous = bend_radius_mode(getattr(self, "_last_bend_mode", DEFAULT_BEND_RADIUS_MODE))
        if preserve_manual and mode.is_manual and not previous.is_manual:
            self._manual_bend_radius_mm = self._fields["r"].get()
        self._bend_mode.set(getattr(self, "_bend_mode_labels", {}).get(mode.code, mode.code))
        self._last_bend_mode = mode.code
        entry = getattr(self, "_bend_radius_entry", None)
        if entry is not None:
            entry.configure(state="normal" if mode.is_manual else "readonly")
        if mode.is_manual:
            if self._manual_bend_radius_mm:
                self._fields["r"].set(self._manual_bend_radius_mm)
        else:
            self._refresh_automatic_bend_radius()

    def _on_bend_mode_selected(self, _event: object | None = None) -> None:
        """Change the active R source without calculating wall thickness."""
        self._select_bend_mode(self._selected_bend_mode_code())

    def _refresh_automatic_bend_radius(self) -> None:
        """Refresh a read-only automatic R from the current authoritative da."""
        if self._selected_bend_mode_code() == "MANUAL" or "r" not in self._fields:
            return
        try:
            da = self._number("da")
            radius = automatic_bend_radius_mm(self._selected_bend_mode_code(), da)
        except (ValidationError, ValueError):
            radius = None
        self._suppress_dirty = True
        try:
            self._fields["r"].set("" if radius is None else format_user_number(radius))
        finally:
            self._suppress_dirty = False

    def _load_pipe_standards(self) -> None:
        """Load active, human-readable standard names without exposing internal codes."""
        labels: list[str] = []
        self._pipe_standard_codes.clear()
        self._pipe_standard_names.clear()
        for standard in self._service.get_available_pipe_standards():
            label = standard.display_name
            if label in self._pipe_standard_codes:
                label = f"{label} ({standard.source})"
            labels.append(label)
            self._pipe_standard_codes[label] = standard.code
            self._pipe_standard_names[standard.code] = standard.display_name
        self._pipe_standard_box.configure(values=labels)
        self._select_pipe_standard(None)

    def _select_pipe_standard(self, code: str | None) -> bool:
        """Select a standard by stable code; legacy state intentionally uses EN 10220."""
        target_code = code or PipeSizeService.DEFAULT_STANDARD_CODE
        label = next(
            (candidate for candidate, candidate_code in self._pipe_standard_codes.items()
             if candidate_code == target_code),
            "",
        )
        self._pipe_standard.set(label)
        return bool(label)

    def _selected_pipe_standard_code(self) -> str | None:
        """Resolve the selected visible name to its stable standard code."""
        selected = getattr(self, "_pipe_standard", None)
        codes = getattr(self, "_pipe_standard_codes", {})
        return codes.get(selected.get()) if selected is not None else None

    def _selected_pipe_standard_name(self) -> str:
        code = self._selected_pipe_standard_code()
        return getattr(self, "_pipe_standard_names", {}).get(code or "", "—")

    def _on_pipe_standard_selected(self, _event: object | None = None) -> None:
        """Keep the explicit event binding; the traced variable owns invalidation."""

    def _load_circuits(self) -> None:
        """Load active D243 circuit defaults from the service layer."""
        self._circuit_codes.clear(); self._circuit_defaults.clear(); self._circuit_names.clear()
        labels: list[str] = []
        for circuit in self._service.get_active_corrosion_allowance_circuits():
            label = circuit.display_name
            if label in self._circuit_codes:
                label = f"{label} ({circuit.code})"
            labels.append(label)
            self._circuit_codes[label] = circuit.code
            self._circuit_defaults[circuit.code] = circuit.default_corrosion_allowance_mm
            self._circuit_names[circuit.code] = circuit.display_name
        self._circuit_box.configure(values=labels)
        self._select_circuit(None)

    def _selected_circuit_code(self) -> str | None:
        circuit = getattr(self, "_circuit", None)
        return getattr(self, "_circuit_codes", {}).get(circuit.get()) if circuit is not None else None

    def _selected_circuit_name(self) -> str:
        code = self._selected_circuit_code()
        return getattr(self, "_circuit_names", {}).get(code or "", "—")

    def _select_circuit(self, code: str | None, *, apply_default: bool = True) -> bool:
        """Select a stable code; only missing legacy state may default to FUEL."""
        target_code = code or "FUEL"
        label = next((name for name, candidate in self._circuit_codes.items() if candidate == target_code), "")
        self._circuit.set(label)
        if label and apply_default:
            default = self._circuit_defaults[target_code]
            self._fields["c"].set(format_user_number(default))
            self._corrosion_allowance_override = False
        self._update_circuit_summary()
        return bool(label)

    def _on_circuit_selected(self, _event: object | None = None) -> None:
        """A circuit switch deliberately loads its new authoritative default c."""
        self._suppress_dirty = True
        try:
            self._select_circuit(self._selected_circuit_code())
        finally:
            self._suppress_dirty = False
        self._on_part2_change()
        self._evaluate_velocity_warning()

    def _load_line_roles(self) -> None:
        """Expose stable line-role codes while retaining Turkish display labels."""
        selected = self._selected_line_role_code()
        self._line_role_codes = {self._t("message.select"): ""}
        self._line_role_codes.update({role.turkish_label: role.code for role in LINE_ROLES})
        self._line_role_box.configure(values=list(self._line_role_codes))
        self._select_line_role(selected)

    def _selected_line_role_code(self) -> str | None:
        code = self._line_role_codes.get(self._line_role.get(), "")
        return code or None

    def _select_line_role(self, code: str | None) -> None:
        label = next((label for label, item_code in self._line_role_codes.items() if item_code == (code or "")), self._t("message.select"))
        self._line_role.set(label)

    def _on_line_role_selected(self, _event: object | None = None) -> None:
        self._evaluate_velocity_warning()
        if not self._suppress_dirty:
            self._mark_dirty()

    def _evaluate_velocity_warning(self) -> None:
        """Re-evaluate advisory velocity context without changing a valid result."""
        findings = ()
        if self._diameter_result:
            system = warning_fluid_for_circuit(self._selected_circuit_code())
            role = self._selected_line_role_code()
            try:
                velocity = getattr(self, "_diameter_warning_velocity_m_s", None)
                if velocity is None:
                    velocity = parse_engineering_float(self._fields["v"].get(), field_name="Design Velocity", field_key="field.design_velocity")
            except ValidationError:
                velocity = None
            if system and role and velocity is not None:
                findings = evaluate_velocity(system, role, velocity)
        self._engineering_findings = findings
        if hasattr(self, "_warning_panel"):
            self._warning_panel.set_findings(findings)

    def _update_circuit_summary(self) -> None:
        """Render default and actual c separately without recalculating anything."""
        code = self._selected_circuit_code()
        default = getattr(self, "_circuit_defaults", {}).get(code or "")
        default_var = getattr(self, "_circuit_default_c", None)
        used_var = getattr(self, "_circuit_used_c", None)
        if default_var is not None:
            default_var.set("—" if default is None else f"{format_user_number(default)} mm")
        if used_var is not None:
            raw = self._fields["c"].get().strip()
            try:
                used = parse_engineering_float(raw, field_name="c", field_key="field.corrosion_allowance")
                used_var.set("—" if used is None else f"{format_user_number(used)} mm")
            except ValidationError:
                used_var.set("—" if not raw else raw)

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
            standard_code = self._selected_pipe_standard_code()
            if standard_code is None:
                raise ValidationError(ValidationIssue("pipe_standard_required"))
            diameter_input = PipeDiameterInput(self._number("q"),self._number("v"))
            result=self._service.calculate(
                diameter=diameter_input,
                standard_code=standard_code,
            )
            if result.errors:
                self._diameter_result = {}
                self._diameter_warning_codes = []
                self._update_diameter_summary()
                self._message.set(self._t("validation.unexpected_error"));return
            assert result.diameter is not None
            self._diameter_result = result.diameter.to_dict()
            self._diameter_warning_velocity_m_s = diameter_input.design_velocity_mps
            self._diameter_warning_codes = self._warning_codes_from_result()
            self._update_diameter_summary()
            self._refresh_diameter_warning_message()
            self._evaluate_velocity_warning()
            self._refresh_formula_panel()
        except ValidationError as error:
            self._diameter_result = {}
            self._diameter_warning_velocity_m_s = None
            self._diameter_warning_codes = []
            self._engineering_findings = ()
            if hasattr(self, "_warning_panel"):
                self._warning_panel.set_findings(())
            self._update_diameter_summary()
            self._message.set(render_validation_issue(error.issue, self._translator_proxy()))
        except ValueError:
            self._diameter_result = {}
            self._diameter_warning_velocity_m_s = None
            self._diameter_warning_codes = []
            self._engineering_findings = ()
            if hasattr(self, "_warning_panel"):
                self._warning_panel.set_findings(())
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
            self._message.set(f"Et kalınlığı: {format_user_number(result.wall_thickness.final_wall_thickness_mm)} mm")
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
        self._refresh_automatic_bend_radius()
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
        diameter_stage = self._translate("formula.stage.pipe_diameter")
        stress_stage = self._translate("formula.stage.allowable_stress")
        base_stage = self._translate("formula.stage.base_wall_thickness")
        bend_stage = self._translate("formula.stage.bend_allowance")
        required_stage = self._translate("formula.stage.required_wall_thickness")
        sections: list[FormulaSection] = [
            FormulaSection("FORMULA", "Qm³/s = Qm³/h / 3600\nD = √((4 × Qm³/s) / (π × V))", diameter_stage, "formula"),
            FormulaSection("VARIABLES", f"D | {self._translate('result.calculated_diameter')} | mm\nQ | {self._translate('field.flow_rate')} | m³/h\nV | {self._translate('field.design_velocity')} | m/s\nπ | {self._translate('formula.mathematical_constant')} | −", diameter_stage, "variables"),
            FormulaSection("CURRENT SUBSTITUTION", self._translate("message.available_after_calculation"), diameter_stage, "substitution"),
            FormulaSection("RESULT", self._translate("message.available_after_calculation"), diameter_stage, "result"),
            FormulaSection("FORMULA", "σallow = Rp0.2 / B", stress_stage, "formula"),
            FormulaSection("VARIABLES", f"σallow | {self._translate('result.allowable_stress')} | MPa\nRp0.2 | {self._translate('field.yield_strength')} | MPa\nB | {self._translate('field.safety_factor')} | −", "2. ALLOWABLE STRESS", "variables"),
            FormulaSection("CURRENT SUBSTITUTION", self._translate("message.available_after_wall_thickness_calculation"), stress_stage, "substitution"),
            FormulaSection("RESULT", self._translate("message.available_after_wall_thickness_calculation"), stress_stage, "result"),
            FormulaSection("FORMULA", "s0 = (da × pc) / ((20 × σallow × w) + pc)", base_stage, "formula"),
            FormulaSection("VARIABLES", f"s0 | {self._translate('result.base_wall_thickness')} | mm\nda | {self._translate('field.pipe_outside_diameter')} | mm\npc | {self._translate('field.design_pressure')} | bar\nw | {self._translate('field.weld_factor')} | −", "3. BASE WALL THICKNESS", "variables"),
            FormulaSection("CURRENT SUBSTITUTION", self._translate("message.available_after_wall_thickness_calculation"), "3. BASE WALL THICKNESS", "substitution"),
            FormulaSection("RESULT", self._translate("message.available_after_wall_thickness_calculation"), "3. BASE WALL THICKNESS", "result"),
            FormulaSection("FORMULA", "b = 0.4 × (da / R) × s0", bend_stage, "formula"),
            FormulaSection("VARIABLES", f"b | {self._translate('result.bend_allowance')} | mm\nR | {self._translate('field.bend_radius')} | mm\ns0 | {self._translate('result.base_wall_thickness')} | mm", "4. BEND ALLOWANCE", "variables"),
            FormulaSection("CURRENT SUBSTITUTION", self._translate("message.available_after_wall_thickness_calculation"), "4. BEND ALLOWANCE", "substitution"),
            FormulaSection("RESULT", self._translate("message.available_after_wall_thickness_calculation"), "4. BEND ALLOWANCE", "result"),
            FormulaSection("FORMULA", "s = s0 + c + b", required_stage, "formula"),
            FormulaSection("VARIABLES", f"s | {self._translate('result.required_wall_thickness')} | mm\nc | {self._translate('field.corrosion_allowance')} | mm\nb | {self._translate('result.bend_allowance')} | mm", "5. REQUIRED WALL THICKNESS", "variables"),
            FormulaSection("CURRENT SUBSTITUTION", self._translate("message.available_after_wall_thickness_calculation"), "5. REQUIRED WALL THICKNESS", "substitution"),
            FormulaSection("RESULT", self._translate("message.available_after_wall_thickness_calculation"), "5. REQUIRED WALL THICKNESS", "result"),
        ]
        if self._diameter_result:
            result = self._diameter_result
            sections[2] = FormulaSection("CURRENT SUBSTITUTION", f"Q = {self._fields['q'].get()} m³/h\nV = {self._fields['v'].get()} m/s\nD = √((4 × (Q / 3600)) / (π × V))", "1. PIPE DIAMETER", "substitution")
            sections[3] = FormulaSection("RESULT", f"{self._translate('result.calculated_diameter')} = {format_user_number(float(result['diameter_mm']))} mm", "1. PIPE DIAMETER", "result")
            if result.get("recommended_dn"):
                sections.append(FormulaSection("PIPE SIZE RECOMMENDATION", f"{self._translate('field.pipe_standard')} = {self._selected_pipe_standard_name()}\n{self._translate('result.recommended_nominal_size')} = {result['recommended_dn']}\n{self._translate('formula.pipe_size_recommendation_note')}\n{self._translate('field.pipe_outside_diameter')} = {result.get('recommended_outside_diameter_mm')} mm", "PIPE SIZE RECOMMENDATION", "note"))
        if self._wall_result:
            result = self._wall_result
            circuit_context = f"{self._translate('field.circuit')} = {self._selected_circuit_name()}\n{self._translate('result.default_corrosion_allowance')} = {self._circuit_default_c.get()}\n{self._translate('result.used_corrosion_allowance')} = {self._circuit_used_c.get()}"
            weld_factor = format_user_number(self._number("wf"))
            safety_factor = format_user_number(self._number("sf"))
            substitution = f"σallow = {format_user_number(result['allowable_stress_mpa'])} MPa\ns0 = {format_user_number(result['base_wall_thickness_mm'])} mm\nb = {format_user_number(result['bend_allowance_mm'])} mm\nc = {format_user_number(result['corrosion_allowance_mm'])} mm\nB = {safety_factor}\nv = {weld_factor}\n{circuit_context}"
            sections[6] = FormulaSection("CURRENT SUBSTITUTION", substitution, "2. ALLOWABLE STRESS", "substitution")
            sections[7] = FormulaSection("RESULT", f"{self._translate('result.allowable_stress')} = {format_user_number(result['allowable_stress_mpa'])} MPa", "2. ALLOWABLE STRESS", "result")
            sections[10] = FormulaSection("CURRENT SUBSTITUTION", substitution, "3. BASE WALL THICKNESS", "substitution")
            sections[11] = FormulaSection("RESULT", f"{self._translate('result.base_wall_thickness')} s0 = {format_user_number(result['base_wall_thickness_mm'])} mm", "3. BASE WALL THICKNESS", "result")
            bend_context = (
                f"{self._translate('field.bend_type')} = {self._selected_bend_mode_label()}\n"
                f"da = {format_user_number(self._number('da'))} mm\n"
                f"R = {format_user_number(self._number('r'))} mm\n"
                f"b = 0,4 × (da / R) × s0\n"
                f"b = {format_user_number(result['bend_allowance_mm'])} mm"
            )
            sections[14] = FormulaSection("CURRENT SUBSTITUTION", bend_context, "4. BEND ALLOWANCE", "substitution")
            sections[15] = FormulaSection("RESULT", f"{self._translate('result.bend_allowance')} b = {format_user_number(result['bend_allowance_mm'])} mm", "4. BEND ALLOWANCE", "result")
            sections[18] = FormulaSection("CURRENT SUBSTITUTION", substitution, "5. REQUIRED WALL THICKNESS", "substitution")
            sections[19] = FormulaSection("RESULT", f"{self._translate('result.required_wall_thickness')} = {format_user_number(result['final_wall_thickness_mm'])} mm", "5. REQUIRED WALL THICKNESS", "result")
            sections.append(FormulaSection("NOT", self._t("formula.weld_factor_reference_note"), required_stage, "note"))
            sections.append(FormulaSection("NOT", self._t("formula.safety_factor_reference_note"), required_stage, "note"))
            sections.append(FormulaSection("NOT", self._t("formula.bend_radius_convention_note"), bend_stage, "note"))
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
            format_user_number(result['final_wall_thickness_mm'])
        )
        self._wall_allowable.set(
            f"{format_user_number(result['allowable_stress_mpa'])} MPa"
        )
        self._wall_base.set(
            f"{format_user_number(result['base_wall_thickness_mm'])} mm"
        )
        self._wall_bend.set(
            f"{format_user_number(result['bend_allowance_mm'])} mm"
        )
        self._wall_supporting.set(
            f"{self._t('result.allowable_stress')}: {format_user_number(result['allowable_stress_mpa'])} MPa\n{self._t('result.base_wall_thickness')}: {format_user_number(result['base_wall_thickness_mm'])} mm\n{self._t('result.bend_allowance')}: {format_user_number(result['bend_allowance_mm'])} mm"
        )
        self._wall_summary.set(
            f"{self._t('result.allowable_stress')}: {format_user_number(result['allowable_stress_mpa'])} MPa\n"
            f"{self._t('result.base_wall_thickness')}: {format_user_number(result['base_wall_thickness_mm'])} mm\n"
            f"{self._t('result.bend_allowance')}: {format_user_number(result['bend_allowance_mm'])} mm\n"
            f"{format_user_number(result['final_wall_thickness_mm'])} mm\n"
            f"{self._t('result.allowable_stress')}: {format_user_number(result['allowable_stress_mpa'])} MPa\n"
            f"{self._t('result.base_wall_thickness')}: {format_user_number(result['base_wall_thickness_mm'])} mm\n"
            f"{self._t('result.bend_allowance')}: {format_user_number(result['bend_allowance_mm'])} mm"
        )

    def _update_diameter_summary(self) -> None:
        """Render the stored library recommendation without duplicating DN state."""
        if not self._diameter_result:
            self._diameter_summary.set("—");getattr(self, "_diameter_value", self._diameter_summary).set("—");getattr(self, "_diameter_standard", self._diameter_summary).set("—");getattr(self, "_diameter_dn", self._diameter_summary).set("—");getattr(self, "_recommended_outside_diameter", self._diameter_summary).set("—")
            button = getattr(self, "_use_recommended_pipe_button", None)
            if button is not None: button.configure(state="disabled")
            return
        diameter = format_user_number(float(self._diameter_result["diameter_mm"]))
        recommended_dn = self._diameter_result.get("recommended_dn")
        getattr(self, "_diameter_value", self._diameter_summary).set(diameter)
        getattr(self, "_diameter_standard", self._diameter_summary).set(
            self._selected_pipe_standard_name()
        )
        getattr(self, "_diameter_dn", self._diameter_summary).set(recommended_dn if isinstance(recommended_dn, str) and recommended_dn else "—")
        recommended_outside = self._recommended_outside_diameter_value()
        getattr(self, "_recommended_outside_diameter", self._diameter_summary).set(
            "—" if recommended_outside is None else f"{format_user_number(recommended_outside)} mm"
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
