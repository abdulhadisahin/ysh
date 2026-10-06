"""Calculation-first discharge head-loss ttk page."""
from __future__ import annotations
import tkinter as tk
import logging
from collections.abc import Callable
from uuid import uuid4
from tkinter import messagebox,ttk
from core.local_loss_item import LocalLossItem
from core.engineering_context import FLUID_SYSTEMS
from engineering.input_parsing import parse_engineering_float
from engineering.validation import ValidationError, ValidationIssue
from engineering.warning_rules import evaluate_velocity
from i18n.translator import Translator
from i18n.validation import render_validation_issue
from ui.formatting import format_user_number
from ui.dialogs.local_loss_item_dialog import LocalLossItemDialog
from ui.widgets.scrollable_treeview import ScrollableTreeview
from ui.widgets.formula_view import FormulaReferencePanel, FormulaSection
from ui.widgets.engineering_warning_panel import EngineeringWarningPanel
from ui.widgets.rounded_button import ADD_BUTTON_PALETTE, CLEAR_ALL_BUTTON_PALETTE, DELETE_BUTTON_PALETTE, DISCHARGE_PRIMARY_PALETTE, EDIT_BUTTON_PALETTE, FORMULA_BUTTON_PALETTE, NEUTRAL_BUTTON_PALETTE, create_rounded_button
from ui.widgets.cards import CalculationCard, InputCard, ResultCard, ResultMetric, SectionHeader
class DischargeHeadLossPage(ttk.LabelFrame):
    """Collects discharge inputs and delegates all results to its service."""
    def __init__(self,parent:tk.Misc,service:object,constants:object,materials:object,translate:Callable[[str],str]|None=None)->None:
        """Build the enabled page without project dependencies."""
        self._translate=translate or Translator().translate;super().__init__(parent,text=self._translate("page.discharge.tab"),padding=12);self._service=service;self._constants=constants;self._materials=materials;self._items:dict[str,LocalLossItem]={};self._fields={key:tk.StringVar() for key in ("d","q","nu","l","k","h")};self._viscosity_unit=tk.StringVar(value="cSt");self._warning_fluid=tk.StringVar(value=self._translate("message.select"));self._warning_fluid_codes:dict[str,str]={};self._status_messages:list[ValidationIssue]=[];self._message=tk.StringVar(value="");self._result_summary=tk.StringVar(value=self._translate("message.no_current_calculation"));self._system_head_summary=tk.StringVar(value="—");self._local_loss_summary=tk.StringVar(value="—");self._pipe_loss_summary=tk.StringVar(value="—");self._total_loss_summary=tk.StringVar(value="—");self._reynolds_summary=tk.StringVar(value="—");self._relative_roughness_summary=tk.StringVar(value="—");self._friction_factor_summary=tk.StringVar(value="—");self._k_total_summary=tk.StringVar(value="—");self._source_mode="material";self._source=tk.StringVar(value=self._translate("message.material_source"));self._material=tk.StringVar();self._material_ids:dict[str,object]={};self._dirty_callback=None;self._suppress_dirty=True;self._build();self._load_warning_fluids();self._load_materials();self._set_source_mode();self._suppress_dirty=False
        for variable in (*self._fields.values(),self._viscosity_unit,self._source,self._material):variable.trace_add("write",self._mark_dirty);variable.trace_add("write",self._invalidate_result)
        self._warning_fluid.trace_add("write",self._on_warning_context_changed)
    def _build(self)->None:
        self.columnconfigure(0,weight=1)
        self._header=SectionHeader(self,self._translate("page.discharge.title"),self._translate("page.discharge.description"));self._header.grid(row=0,column=0,sticky="ew",pady=(0,10))
        workspace=ttk.Frame(self);workspace.grid(row=1,column=0,sticky="nsew")
        self._workspace=workspace
        workspace.columnconfigure(0,weight=3)
        workspace.columnconfigure(1,weight=3)
        workspace.columnconfigure(2,weight=3)
        self._pipe_card=InputCard(workspace,self._translate("section.hydraulic_inputs"));pipe=self._pipe_card;pipe.grid(row=0,column=0,sticky="nsew",padx=(0,6))
        for row,(key,unit) in enumerate((("d","mm"),("q","m³/h"),("nu",""),("l","m"),("h","m"))):
            localized={"d":"field.pipe_inside_diameter","q":"field.flow_rate","nu":"field.kinematic_viscosity","l":"field.pipe_length","h":"field.geodetic_head"}[key];widget=ttk.Label(pipe,text=f"{self._translate(localized)}"+(f" ({unit})" if unit else ""));widget.grid(row=row,column=0,sticky="w",pady=3);setattr(self,f"_field_label_{key}",widget);ttk.Entry(pipe,textvariable=self._fields[key],width=16).grid(row=row,column=1,sticky="w",padx=(8,0),pady=3)
        ttk.Combobox(pipe,textvariable=self._viscosity_unit,values=("cSt","m²/s"),state="readonly",width=7).grid(row=2,column=2,sticky="w",padx=(8,0))
        self._source_label=ttk.Label(pipe,text=self._translate("field.roughness_source"));self._source_label.grid(row=5,column=0,sticky="w",pady=3);self._source_box=ttk.Combobox(pipe,textvariable=self._source,values=("Material Library","Manual"),state="readonly",width=16);self._source_box.grid(row=5,column=1,sticky="w",padx=(8,0));self._source_box.bind("<<ComboboxSelected>>",lambda _:self._select_source_mode())
        self._material_label=ttk.Label(pipe,text=self._translate("field.material"));self._material_label.grid(row=6,column=0,sticky="w",pady=3);self._material_box=ttk.Combobox(pipe,textvariable=self._material,state="readonly",width=22);self._material_box.grid(row=6,column=1,columnspan=2,sticky="ew",padx=(8,0));self._material_box.bind("<<ComboboxSelected>>",lambda _:self._load_selected_roughness())
        self._active_roughness_label=ttk.Label(pipe,text=f"{self._translate('field.active_roughness')} (mm)");self._active_roughness_label.grid(row=7,column=0,sticky="w",pady=3);self._roughness_entry=ttk.Entry(pipe,textvariable=self._fields["k"],width=16);self._roughness_entry.grid(row=7,column=1,sticky="w",padx=(8,0),pady=3)
        self._warning_fluid_label=ttk.Label(pipe,text=self._translate("field.system_fluid"));self._warning_fluid_label.grid(row=8,column=0,sticky="w",pady=3);self._warning_fluid_box=ttk.Combobox(pipe,textvariable=self._warning_fluid,state="readonly",width=22);self._warning_fluid_box.grid(row=8,column=1,columnspan=2,sticky="w",padx=(8,0),pady=3)
        self._losses_card=InputCard(workspace,self._translate("section.local_losses"));losses=self._losses_card;losses.grid(row=0,column=1,sticky="nsew",padx=6);losses.columnconfigure(0,weight=1)
        self._tree_container=ScrollableTreeview(losses,columns=("name","quantity","k","total"),show="headings",height=8);self._tree=self._tree_container.tree;self._tree.configure(style="Discharge.Treeview")
        for key,label in (("name",self._translate("table.component")),("quantity",self._translate("table.quantity")),("k","K"),("total",self._translate("table.quantity_times_k"))):self._tree.heading(key,text=label)
        self._tree.column("name",width=150,anchor="w");self._tree.column("quantity",width=72,anchor="e");self._tree.column("k",width=72,anchor="e");self._tree.column("total",width=82,anchor="e")
        self._tree_container.grid(row=0,column=0,sticky="nsew");self._tree.bind("<Double-1>",self._edit);self._tree.bind("<Return>",self._edit);self._tree.bind("<Delete>",self._delete)
        self._loss_actions=ttk.Frame(losses);self._loss_actions.grid(row=1,column=0,sticky="w",pady=(8,0))
        self._add_button=create_rounded_button(self._loss_actions,self._translate("common.add"),self._add,style="RoundedAdd.TButton",palette=ADD_BUTTON_PALETTE)
        self._edit_button=create_rounded_button(self._loss_actions,self._translate("common.edit"),self._edit,style="RoundedEdit.TButton",palette=EDIT_BUTTON_PALETTE)
        self._delete_button=create_rounded_button(self._loss_actions,self._translate("common.delete"),self._delete,style="RoundedDelete.TButton",palette=DELETE_BUTTON_PALETTE)
        self._clear_all_button=create_rounded_button(self._loss_actions,self._translate("action.clear_all"),self._clear_all,style="RoundedClearAll.TButton",palette=CLEAR_ALL_BUTTON_PALETTE)
        self._loss_action_buttons=(self._add_button,self._edit_button,self._delete_button,self._clear_all_button)
        for column,button in enumerate(self._loss_action_buttons):button.grid(row=0,column=column,sticky="w",padx=(0 if column==0 else 8,0))
        self._results_card=ResultCard(workspace,self._translate("section.calculation_results"));results=self._results_card;results.grid(row=0,column=2,sticky="nsew",padx=(6,0));results.columnconfigure(0,weight=1)
        self._result_actions=ttk.Frame(results);self._result_actions.grid(row=0,column=0,columnspan=2,sticky="w")
        self._calculate_button=create_rounded_button(self._result_actions,self._translate("calculation.calculate"),self._calculate,style="DischargeRoundedPrimary.TButton",palette=DISCHARGE_PRIMARY_PALETTE,primary=True)
        self._clear_button=create_rounded_button(self._result_actions,self._translate("common.clear"),self._clear,style="RoundedNeutral.TButton",palette=NEUTRAL_BUTTON_PALETTE)
        self._result_action_buttons=(self._calculate_button,self._clear_button)
        for column,button in enumerate(self._result_action_buttons):button.grid(row=0,column=column,sticky="w",padx=(0 if column==0 else 8,0))
        self._system_metric=ResultMetric(results,self._translate("result.pump_discharge_head"),self._system_head_summary,"m",normal_style_prefix="DischargeResultMetric");self._system_metric.grid(row=1,column=0,columnspan=2,sticky="ew",pady=(12,0))
        losses_metrics=ttk.Frame(results);losses_metrics.grid(row=2,column=0,columnspan=2,sticky="ew",pady=(8,0));losses_metrics.columnconfigure(0,weight=1);losses_metrics.columnconfigure(1,weight=1)
        self._total_loss_metric=ResultMetric(losses_metrics,self._translate("result.total_hydraulic_loss"),self._total_loss_summary,"m",normal_style_prefix="DischargeLossMetric");self._total_loss_metric.grid(row=0,column=0,columnspan=2,sticky="ew")
        self._local_loss_metric=ResultMetric(losses_metrics,self._translate("result.local_loss"),self._local_loss_summary,"m",normal_style_prefix="DischargeLossMetric");self._local_loss_metric.grid(row=1,column=0,sticky="ew",pady=(8,0),padx=(0,4))
        self._pipe_loss_metric=ResultMetric(losses_metrics,self._translate("result.pipe_friction_loss"),self._pipe_loss_summary,"m",normal_style_prefix="DischargeLossMetric");self._pipe_loss_metric.grid(row=1,column=1,sticky="ew",pady=(8,0),padx=(4,0))
        self._supporting_metrics=ttk.Frame(results);self._supporting_metrics.grid(row=3,column=0,columnspan=2,sticky="ew",pady=(10,0))
        self._supporting_metric_widgets=[]
        for label,value in (("result.reynolds_number",self._reynolds_summary),("result.relative_roughness",self._relative_roughness_summary),("result.friction_factor",self._friction_factor_summary),("result.local_loss_coefficient",self._k_total_summary)):
            metric=ttk.Frame(self._supporting_metrics)
            label_widget=ttk.Label(metric,text=self._translate(label),style="ResultMetricLabel.TLabel")
            label_widget.grid(row=0,column=0,sticky="w")
            value_widget=ttk.Label(metric,textvariable=value,style="ResultMetricLabel.TLabel")
            value_widget.grid(row=0,column=1,sticky="e",padx=(8,0))
            metric.columnconfigure(1,weight=1)
            self._supporting_metric_widgets.append((metric,label_widget,label))
        self._reflow_supporting_metrics()
        self._warning_panel=EngineeringWarningPanel(results,self._translate);self._warning_panel.grid(row=4,column=0,columnspan=2,sticky="ew",pady=(10,0));self._warning_panel.set_findings(())
        ttk.Label(self,textvariable=self._message,wraplength=1000).grid(row=2,column=0,sticky="w",pady=(8,0))
        self._formula_panel=FormulaReferencePanel(self,self._formula_sections,self._translate,self._create_formula_toggle);self._formula_panel.grid(row=3,column=0,sticky="ew",pady=(10,0))
        self._responsive_layout_mode=""
        self._workspace.bind("<Configure>",self._on_workspace_configure,add="+")
        self._loss_actions.bind("<Configure>",self._on_action_configure,add="+")
        self._result_actions.bind("<Configure>",self._on_action_configure,add="+")
        self._results_card.bind("<Configure>",self._on_results_configure,add="+")
        self.after_idle(self._reflow_layout)
    @staticmethod
    def _create_formula_toggle(parent:tk.Misc,text:str,command:Callable[[],None])->ttk.Button:
        """Create the Discharge-only rounded tertiary Formula toggle."""
        return create_rounded_button(parent,text,command,style="RoundedFormula.TButton",palette=FORMULA_BUTTON_PALETTE)
    def refresh_texts(self)->None:
        """Refresh discharge labels without changing hydraulic inputs or results."""
        manual=self._source_mode=="manual";self._suppress_dirty=True;self._source.set(self._translate("message.manual_source") if manual else self._translate("message.material_source"));self._suppress_dirty=False;self.configure(text=self._translate("page.discharge.tab"));self._header.set_content(self._translate("page.discharge.title"),self._translate("page.discharge.description"));self._pipe_card.configure(text=self._translate("section.hydraulic_inputs"));self._losses_card.configure(text=self._translate("section.local_losses"));self._results_card.configure(text=self._translate("section.calculation_results"));self._calculate_button.configure(text=self._translate("calculation.calculate"));self._clear_button.configure(text=self._translate("common.clear"));self._system_metric.set_label(self._translate("result.pump_discharge_head"));self._total_loss_metric.set_label(self._translate("result.total_hydraulic_loss"));self._local_loss_metric.set_label(self._translate("result.local_loss"));self._pipe_loss_metric.set_label(self._translate("result.pipe_friction_loss"));self._field_label_d.configure(text=f"{self._translate('field.pipe_inside_diameter')} (mm)");self._field_label_q.configure(text=f"{self._translate('field.flow_rate')} (m³/h)");self._field_label_nu.configure(text=self._translate("field.kinematic_viscosity"));self._field_label_l.configure(text=f"{self._translate('field.pipe_length')} (m)");self._field_label_h.configure(text=f"{self._translate('field.geodetic_head')} (m)");self._source_label.configure(text=self._translate("field.roughness_source"));self._material_label.configure(text=self._translate("field.material"));self._active_roughness_label.configure(text=f"{self._translate('field.active_roughness')} (mm)");self._source_box.configure(values=(self._translate("message.material_source"),self._translate("message.manual_source")));self._tree.heading("name",text=self._translate("table.component"));self._tree.heading("quantity",text=self._translate("table.quantity"));self._tree.heading("total",text=self._translate("table.quantity_times_k"));self._add_button.configure(text=self._translate("common.add"));self._edit_button.configure(text=self._translate("common.edit"));self._delete_button.configure(text=self._translate("common.delete"));self._clear_all_button.configure(text=self._translate("action.clear_all"));
        self._warning_fluid_label.configure(text=self._translate("field.system_fluid"));self._load_warning_fluids();self._warning_panel.refresh_texts()
        for _metric,label,key in self._supporting_metric_widgets:
            label.configure(text=self._translate(key))
        self._render_status();self._render_result();self._formula_panel.refresh_texts();self.after_idle(self._reflow_layout)

    def _on_workspace_configure(self,event:tk.Event[tk.Misc])->None:
        """Reflow the upper engineering workspace for the usable page width."""
        self._reflow_layout(event.width)

    def _reflow_layout(self,available_width:int|None=None)->None:
        """Select a content-driven workspace arrangement without horizontal scrolling."""
        width=available_width or self._workspace.winfo_width()
        if width<=1:
            return
        pipe_width=self._pipe_card.winfo_reqwidth()
        losses_width=self._losses_card.winfo_reqwidth()
        results_width=self._results_card.winfo_reqwidth()
        wide_width=pipe_width+losses_width+results_width+24
        two_column_width=max(pipe_width+results_width+12,losses_width)
        content_width=max(1,width-12)
        mode=("wide" if content_width>=wide_width else "two_column"
              if content_width>=two_column_width else "stacked")
        if mode==self._responsive_layout_mode:
            return
        self._responsive_layout_mode=mode
        self._apply_responsive_layout(mode)

    def _apply_responsive_layout(self,mode:str)->None:
        """Place the existing cards in wide, two-column, or stacked order."""
        for column in range(3):
            self._workspace.columnconfigure(column,weight=0)
        for row in range(3):
            self._workspace.rowconfigure(row,weight=0)
        if mode=="wide":
            self._workspace.columnconfigure(0,weight=1)
            self._workspace.columnconfigure(1,weight=1)
            self._workspace.columnconfigure(2,weight=1)
            self._pipe_card.grid_configure(row=0,column=0,columnspan=1,padx=(0,6),pady=0)
            self._losses_card.grid_configure(row=0,column=1,columnspan=1,padx=6,pady=0)
            self._results_card.grid_configure(row=0,column=2,columnspan=1,padx=(6,0),pady=0)
        elif mode=="two_column":
            self._workspace.columnconfigure(0,weight=1)
            self._workspace.columnconfigure(1,weight=1)
            self._pipe_card.grid_configure(row=0,column=0,columnspan=1,padx=(0,6),pady=0)
            self._results_card.grid_configure(row=0,column=1,columnspan=1,padx=(6,0),pady=0)
            self._losses_card.grid_configure(row=1,column=0,columnspan=2,padx=0,pady=(10,0))
        else:
            self._workspace.columnconfigure(0,weight=1)
            self._pipe_card.grid_configure(row=0,column=0,columnspan=1,padx=0,pady=0)
            self._losses_card.grid_configure(row=1,column=0,columnspan=1,padx=0,pady=(10,0))
            self._results_card.grid_configure(row=2,column=0,columnspan=1,padx=0,pady=(10,0))
        self.after_idle(self._reflow_action_buttons)
        self.after_idle(self._reflow_supporting_metrics)

    def _on_action_configure(self,_event:tk.Event[tk.Misc])->None:
        """Keep local-loss and result actions fully visible at narrow widths."""
        self._reflow_action_buttons()

    def _reflow_action_buttons(self)->None:
        """Use compact rows until translated button text needs a vertical stack."""
        self._reflow_button_group(self._loss_actions,self._loss_action_buttons)
        self._reflow_button_group(self._result_actions,self._result_action_buttons)

    @staticmethod
    def _reflow_button_group(container:ttk.Frame,buttons:tuple[ttk.Button,...])->None:
        """Re-grid a button group horizontally or vertically without callback changes."""
        width=container.winfo_width()
        if width<=1:
            return
        required=sum(button.winfo_reqwidth() for button in buttons)+8*(len(buttons)-1)
        stacked=width<required
        for index,button in enumerate(buttons):
            if stacked:
                button.grid_configure(row=index,column=0,padx=0,pady=(0 if index==0 else 6,0),sticky="w")
            else:
                button.grid_configure(row=0,column=index,padx=(0 if index==0 else 8,0),pady=0,sticky="w")

    def _on_results_configure(self,event:tk.Event[tk.Misc])->None:
        """Adapt secondary metrics to the width available inside the result card."""
        self._reflow_supporting_metrics(event.width)

    def _reflow_supporting_metrics(self,available_width:int|None=None)->None:
        """Keep Re, ε, f, and ΣK readable in a two-column or stacked grid."""
        width=available_width or self._results_card.winfo_width()
        if width<=1 or not hasattr(self,"_supporting_metric_widgets"):
            return
        two_columns=width>=2*max(metric.winfo_reqwidth() for metric,_,_ in self._supporting_metric_widgets)+20
        for column in range(2):
            self._supporting_metrics.columnconfigure(column,weight=1 if two_columns else 0)
        for index,(metric,_,_) in enumerate(self._supporting_metric_widgets):
            row,column=(divmod(index,2) if two_columns else (index,0))
            metric.grid_configure(row=row,column=column,sticky="ew",padx=(0 if column==0 else 8,0),pady=(0 if row==0 else 4,0))
    def set_dirty_callback(self, callback: object) -> None:
        """Register the optional active-project dirty callback.""";self._dirty_callback=callback
    def _mark_dirty(self,*_args:object)->None:
        """Notify the owner only for genuine user edits."""
        if not self._suppress_dirty and callable(self._dirty_callback):self._dirty_callback()
    def _invalidate_result(self,*_args:object)->None:
        """Discard stale hydraulic result details after a user input changes."""
        if not self._suppress_dirty:
            self.__dict__.pop("_last_result",None)
            self._result_summary.set(self._translate("message.no_current_calculation"))
            self._clear_result_metrics()
            self._set_semantic_messages([])
            if hasattr(self,"_warning_panel"):self._warning_panel.set_findings(())
            self._refresh_formula_panel()

    def _clear_result_metrics(self)->None:
        """Reset visual result values without changing hydraulic inputs or items."""
        for value in (
            self._system_head_summary,
            self._local_loss_summary,
            self._pipe_loss_summary,
            self._total_loss_summary,
            self._reynolds_summary,
            self._relative_roughness_summary,
            self._friction_factor_summary,
            self._k_total_summary,
        ):value.set("—")
    def _load_warning_fluids(self)->None:
        selected=self._selected_warning_fluid()
        self._warning_fluid_codes={self._translate("message.select"):""}
        self._warning_fluid_codes.update({item.turkish_label:item.code for item in FLUID_SYSTEMS})
        self._warning_fluid_box.configure(values=list(self._warning_fluid_codes))
        self._set_warning_fluid(selected)

    def _selected_warning_fluid(self)->str|None:
        return self._warning_fluid_codes.get(self._warning_fluid.get(),"") or None

    def _set_warning_fluid(self,code:str|None)->None:
        self._warning_fluid.set(next((label for label,item_code in self._warning_fluid_codes.items() if item_code==(code or "")),self._translate("message.select")))

    def _on_warning_context_changed(self,*_args:object)->None:
        if not self._suppress_dirty:self._mark_dirty()
        self._evaluate_velocity_warning()

    def _evaluate_velocity_warning(self)->None:
        result=getattr(self,"_last_result",None);fluid=self._selected_warning_fluid()
        findings=() if result is None or fluid is None else evaluate_velocity(fluid,"DELIVERY",result.flow_velocity_m_s)
        if hasattr(self,"_warning_panel"):self._warning_panel.set_findings(findings)

    def export_state(self)->dict[str,object]:
        """Serialize editable fields, selectors, local losses, and message."""
        return {"fields":{k:v.get() for k,v in self._fields.items()},"source":self._source_mode,"material":self._material.get(),"viscosity_unit":self._viscosity_unit.get(),"warning_fluid":self._selected_warning_fluid(),"items":[{"name":x.name,"quantity":x.quantity,"k":x.k_coefficient} for x in self._items.values()]}
    def load_state(self,state:dict[str,object])->None:
        """Restore state without touching material library records."""
        self._suppress_dirty=True
        try:
            for key,value in dict(state.get("fields",{})).items():
                if key in self._fields:self._fields[key].set(str(value))
            saved_source=str(state.get("source","material"));self._source_mode="manual" if saved_source in {"manual","Manual"} else "material";self._source.set(self._translate("message.manual_source") if self._source_mode=="manual" else self._translate("message.material_source"));self._material.set(str(state.get("material","")));self._viscosity_unit.set(str(state.get("viscosity_unit","cSt")));self._set_warning_fluid(state.get("warning_fluid") if isinstance(state.get("warning_fluid"),str) else None);self._items={str(uuid4()):LocalLossItem(str(x["name"]),int(x["quantity"]),float(x["k"])) for x in state.get("items",[]) if isinstance(x,dict)};self._refresh();self._set_source_mode();self._set_semantic_messages([])
        finally:self._suppress_dirty=False
    def clear_state(self)->None:
        """Clear project state without marking the project dirty.""";self._suppress_dirty=True
        try:self._clear()
        finally:self._suppress_dirty=False
    def _load_materials(self)->None:
        materials=self._materials.get_all_materials();values=[]
        for material in materials:
            label=f"{material.name} ({material.designation})";values.append(label);self._material_ids[label]=material.id
        self._material_box["values"]=values
    def _set_source_mode(self)->None:
        manual=self._source_mode=="manual";self._material_box.configure(state="disabled" if manual else "readonly");self._roughness_entry.configure(state="normal" if manual else "readonly");self._fields["k"].set("") if manual else self._load_selected_roughness();self._set_semantic_messages([])

    def _select_source_mode(self)->None:
        """Map the selected display entry to a stable non-localized source value."""
        self._source_mode="manual" if self._source_box.current()==1 else "material";self._set_source_mode()
    def _load_selected_roughness(self)->None:
        identifier=self._material_ids.get(self._material.get())
        if identifier is None:return
        material=self._materials.get_material(identifier)
        if material.roughness_mm is None:self._set_semantic_messages([ValidationIssue("material_roughness_missing")]);return
        self._fields["k"].set(str(material.roughness_mm));self._set_semantic_messages([])
    def _refresh(self)->None:
        for row in self._tree.get_children():self._tree.delete(row)
        for identifier,item in self._items.items():self._tree.insert("","end",iid=identifier,values=(item.name,item.quantity,item.k_coefficient,item.subtotal_k))
    def _add(self)->None:
        item=LocalLossItemDialog(self,translate=self._translate).show()
        if item:self._items[str(uuid4())]=item;self._refresh();self._invalidate_result();self._mark_dirty()
    def _edit(self,event:object|None=None)->str:
        """Edit the selected local-loss item through one shared workflow."""
        selected=self._tree.selection()
        if not selected:return "break"
        identifier=selected[0];item=LocalLossItemDialog(self,self._items[identifier],translate=self._translate).show()
        if item:self._items[identifier]=item;self._refresh();self._tree.selection_set(identifier);self._invalidate_result();self._mark_dirty()
        return "break"
    def _delete(self,event:object|None=None)->str:
        """Confirm and delete the selected local-loss item."""
        selected=self._tree.selection()
        if selected and messagebox.askyesno(self._translate("dialog.delete_local_loss"),self._translate("confirm.delete_local_loss"),parent=self):del self._items[selected[0]];self._refresh();self._invalidate_result();self._mark_dirty()
        return "break"
    def _clear_all(self)->None:
        """Confirm and clear all local-loss rows without clearing inputs."""
        if self._items and messagebox.askyesno(self._translate("dialog.clear_local_losses"),self._translate("confirm.clear_local_losses"),parent=self):self._items.clear();self._refresh();self._invalidate_result();self._mark_dirty()
    def _clear(self)->None:
        """Clear only current calculation state and restore source defaults."""
        for field in self._fields.values():field.set("")
        self._set_warning_fluid(None)
        self._items.clear();self._refresh();self._viscosity_unit.set("cSt");self._source_mode="material";self._source.set(self._translate("message.material_source"));self._material.set("");self._set_source_mode();self._set_semantic_messages([]);self.__dict__.pop("_last_result",None);self._result_summary.set(self._translate("message.no_current_calculation"));self._clear_result_metrics();self._mark_dirty();self._refresh_formula_panel()
    def _formula_sections(self)->list[FormulaSection]:
        """Show canonical YSH coefficient formulas from the current result."""
        result=getattr(self,"_last_result",None)
        sections=[
            FormulaSection("FORMULA", f"v = 4Q / (πD²)\nRe = vD / ν\nε = k / D\nf = {self._translate('formula.approved_ysh_moody_result')}", self._translate("formula.stage.flow_and_friction"), "formula"),
            FormulaSection("VARIABLES", f"v | {self._translate('result.flow_velocity')} | m/s\nRe | {self._translate('result.reynolds_number')} | −\nD | {self._translate('field.pipe_inside_diameter')} | mm\nQ | {self._translate('field.flow_rate')} | m³/h\nν | {self._translate('field.kinematic_viscosity')} | m²/s\nk | {self._translate('field.roughness')} | mm\nε | {self._translate('result.relative_roughness')} | −\nf | {self._translate('result.friction_factor')} | −", self._translate("formula.stage.flow_and_friction"), "variables"),
            FormulaSection("CURRENT SUBSTITUTION", self._translate("message.available_after_calculation"), self._translate("formula.stage.flow_and_friction"), "substitution"),
            FormulaSection("RESULT", self._translate("message.available_after_calculation"), self._translate("formula.stage.flow_and_friction"), "result"),
            FormulaSection("FORMULA", "Ktotal = Σ(quantity × K)\nh_local = 6400 × Ktotal × Q² / D⁴\nh_pipe = 6.4 × 10⁶ × f × L × Q² / D⁵", self._translate("formula.stage.hydraulic_losses"), "formula"),
            FormulaSection("VARIABLES", f"Ktotal | {self._translate('formula.total_local_loss_coefficient')} | −\nK | {self._translate('field.local_loss_k')} | −\nL | {self._translate('field.pipe_length')} | m\nh_local | {self._translate('result.local_loss')} | m\nh_pipe | {self._translate('result.pipe_friction_loss')} | m", self._translate("formula.stage.hydraulic_losses"), "variables"),
            FormulaSection("CURRENT SUBSTITUTION", self._translate("message.available_after_calculation"), self._translate("formula.stage.hydraulic_losses"), "substitution"),
            FormulaSection("RESULT", self._translate("message.available_after_calculation"), self._translate("formula.stage.hydraulic_losses"), "result"),
            FormulaSection("FORMULA", "h_total = h_pipe + h_local\nH_system = Hgeo + h_total", self._translate("formula.stage.system_manometric_head"), "formula"),
            FormulaSection("VARIABLES", f"h_total | {self._translate('result.total_hydraulic_loss')} | m\nHgeo | {self._translate('field.geodetic_head')} | m\nH_system | {self._translate('result.system_manometric_head')} | m", self._translate("formula.stage.system_manometric_head"), "variables"),
            FormulaSection("CURRENT SUBSTITUTION", self._translate("message.available_after_calculation"), self._translate("formula.stage.system_manometric_head"), "substitution"),
            FormulaSection("RESULT", self._translate("message.available_after_calculation"), self._translate("formula.stage.system_manometric_head"), "result"),
        ]
        if result is None:
            return sections
        flow_stage = self._translate("formula.stage.flow_and_friction")
        loss_stage = self._translate("formula.stage.hydraulic_losses")
        system_stage = self._translate("formula.stage.system_manometric_head")
        sections[2] = FormulaSection("CURRENT SUBSTITUTION", f"f = {format_user_number(result.friction_factor)}\nRe = {format_user_number(result.reynolds_number)}\nε = {format_user_number(result.relative_roughness)}", flow_stage, "substitution")
        sections[3] = FormulaSection("RESULT", f"{self._translate('result.friction_factor')} f = {format_user_number(result.friction_factor)}", flow_stage, "result")
        sections[6] = FormulaSection("CURRENT SUBSTITUTION", f"Ktotal = {format_user_number(result.local_loss_coefficient_total)}\nh_local = {format_user_number(result.local_loss_m)} m\nh_pipe = {format_user_number(result.pipe_friction_loss_m)} m", loss_stage, "substitution")
        sections[7] = FormulaSection("RESULT", f"{self._translate('result.total_hydraulic_loss')} h_total = {format_user_number(result.total_hydraulic_loss_m)} m", loss_stage, "result")
        sections[10] = FormulaSection("CURRENT SUBSTITUTION",f"h_total = h_pipe + h_local\nHgeo = {self._fields['h'].get()} m\nH_system = Hgeo + h_total", system_stage, "substitution")
        sections[11] = FormulaSection("RESULT",f"{self._translate('result.total_hydraulic_loss')} h_total = {format_user_number(result.total_hydraulic_loss_m)} m\n{self._translate('result.system_manometric_head')} H_system = {format_user_number(result.system_head_m)} m", system_stage, "result")
        return sections
    def _calculate(self)->None:
        try:
            labels={"d":"Pipe Inside Diameter (mm)","q":"Flow Rate","nu":"Kinematic Viscosity","l":"Pipe Length","k":"Roughness (mm)","h":"Geodetic Head"};field_keys={"d":"field.pipe_inside_diameter","q":"field.flow_rate","nu":"field.kinematic_viscosity","l":"field.pipe_length","k":"field.roughness","h":"field.geodetic_head"};n=lambda key:parse_engineering_float(self._fields[key].get(),field_name=labels[key],field_key=field_keys[key]);viscosity=n("nu")*1e-6 if self._viscosity_unit.get()=="cSt" else n("nu");material_id=self._material_ids.get(self._material.get()) if self._using_library_source() else None
            if self._using_library_source() and material_id is None:raise ValidationError(ValidationIssue("selection_required","field.material"))
            result=self._service.calculate(n("d"),n("q"),viscosity,n("l"),None if material_id else n("k"),n("h"),list(self._items.values()),material_id);self._last_result=result;self._render_result()
            self._mark_dirty()
            self._refresh_formula_panel()
        except ValidationError as error:self._set_semantic_messages([error.issue])
        except Exception:
            logging.getLogger(__name__).exception("Discharge head-loss calculation failed")
            self._set_semantic_messages([ValidationIssue("unexpected_error")])

    def _refresh_formula_panel(self)->None:
        """Update an expanded formula reference after state changes."""
        if hasattr(self,"_formula_panel") and self._formula_panel.expanded:
            self._formula_panel.refresh()

    def _render_result(self)->None:
        """Render the stored hydraulic result in the current UI language."""
        result=getattr(self,"_last_result",None)
        if result is None:return
        self._set_semantic_messages([ValidationIssue("discharge.status.result_ready",params={"pipe_loss":format_user_number(result.pipe_friction_loss_m),"local_loss":format_user_number(result.local_loss_m),"total_loss":format_user_number(result.total_hydraulic_loss_m),"system_head":format_user_number(result.system_head_m)}),*result.warnings])
        self._evaluate_velocity_warning()
        self._result_summary.set(self._translate("message.ready"))
        self._system_head_summary.set(format_user_number(result.system_head_m))
        self._local_loss_summary.set(format_user_number(result.local_loss_m))
        self._pipe_loss_summary.set(format_user_number(result.pipe_friction_loss_m))
        self._total_loss_summary.set(format_user_number(result.total_hydraulic_loss_m))
        self._reynolds_summary.set(format_user_number(result.reynolds_number))
        self._relative_roughness_summary.set(format_user_number(result.relative_roughness))
        self._friction_factor_summary.set(format_user_number(result.friction_factor))
        self._k_total_summary.set(format_user_number(result.local_loss_coefficient_total))

    def _set_semantic_messages(self,messages:list[ValidationIssue])->None:
        """Store semantic page status and render it using the active translator."""
        self._status_messages=list(messages);self._render_status()

    def _render_status(self)->None:
        """Render current semantic status without recalculating hydraulic results."""
        if not self._status_messages:self._message.set(self._translate("message.ready"));return
        self._message.set("; ".join(self._render_semantic_message(message) for message in self._status_messages))

    def _render_semantic_message(self,message:ValidationIssue)->str:
        """Render discharge status codes and validation issues at the UI boundary."""
        if message.code.startswith("discharge.status."):return self._translate(message.code,**dict(message.params or {}))
        return render_validation_issue(message,self._translator_proxy())

    def _translator_proxy(self)->object:
        """Expose the active page translator to the shared issue renderer."""
        return type("TranslatorProxy",(),{"translate":self._translate})()

    def _using_library_source(self)->bool:
        """Return whether the visible source selector represents library data."""
        return self._source_mode=="material"
