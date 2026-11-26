"""Independent discharge-volume and nominal-flow scenario; no tank-capacity inference."""
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace
from engineering.input_parsing import parse_engineering_float
from engineering.transfer_pump.discharge_scenario import calculate_discharge_115
from engineering.validation import ValidationError
from i18n.validation import render_validation_issue
from ui.formatting import format_user_number
from ui.widgets.numeric_input import numeric_pair
from ui.widgets.cards import ResultCard,ResultMetric
from ui.widgets.calculation_presentation import calculation_button,set_result_state
from ui.widgets.rounded_button import TRANSFER_PRIMARY_PALETTE,NEUTRAL_BUTTON_PALETTE


class TransferDischargeScenario(ttk.LabelFrame):
    def __init__(self,parent,translate,changed):
        super().__init__(parent,padding=12)
        self.tr=translate;self.changed=changed;self._suppress=False;self.result=None
        self.fields={key:tk.StringVar(self) for key in ('volume','nominal')}
        self.flow=tk.StringVar(self,value='—');self.duration=tk.StringVar(self,value='—')
        self.message=tk.StringVar(self)
        self.columnconfigure(1,weight=1)
        self.notice=ttk.Label(self,style='Info.TLabel',wraplength=620)
        self.notice.grid(row=0,column=0,columnspan=3,sticky='w',pady=(0,6))
        self.form=ttk.Frame(self);self.form.grid(row=1,column=0,sticky='nw',padx=(0,12))
        self.labels={};self.entries={}
        for row,(key,unit) in enumerate((('volume','m³'),('nominal','m³/h'))):
            label=ttk.Label(self.form);label.grid(row=row,column=0,sticky='w',pady=4);self.labels[key]=label
            pair,entry=numeric_pair(self.form,textvariable=self.fields[key],unit=unit)
            pair.grid(row=row,column=1,sticky='w',padx=8,pady=4);self.entries[key]=entry
        actions=ttk.Frame(self);actions.grid(row=2,column=0,columnspan=3,sticky='w',pady=(8,0))
        self.calculate_button=calculation_button(actions,'',self.calculate,primary=True,style='TransferRoundedPrimary.TButton',palette=TRANSFER_PRIMARY_PALETTE,icon_name='calculate')
        self.calculate_button.grid(row=0,column=0,sticky='w')
        self.clear_button=calculation_button(actions,'',self.clear,style='RoundedNeutral.TButton',palette=NEUTRAL_BUTTON_PALETTE,icon_name='clear')
        self.clear_button.grid(row=0,column=1,sticky='w',padx=8)
        self.result_card=ResultCard(self,'');self.result_card.grid(row=1,column=1,sticky='nw')
        self.flow_metric=ResultMetric(self.result_card,'',self.flow,'',normal_style_prefix='TransferResultMetric')
        self.flow_metric.grid(row=0,column=0,sticky='w')
        self.time_metric=ResultMetric(self.result_card,'',self.duration,'',normal_style_prefix='TransferSecondaryMetric')
        self.time_metric.grid(row=1,column=0,sticky='w',pady=(4,0))
        ttk.Label(self,textvariable=self.message,wraplength=620).grid(row=3,column=0,columnspan=3,sticky='w',pady=(6,0))
        for variable in self.fields.values():variable.trace_add('write',self.invalidate)
        self.refresh_texts()

    def refresh_texts(self):
        self.configure(text=self.tr('transfer.scenario115.title'))
        self.notice.configure(text=self.tr('transfer.scenario115.notice'))
        for key,label in self.labels.items():label.configure(text=self.tr('transfer.scenario115.'+key))
        self.result_card.configure(text=self.tr('section.calculation_results'))
        self.flow_metric.set_label(self.tr('transfer.scenario115.flow'))
        self.time_metric.set_label(self.tr('transfer.scenario115.time'))
        self.calculate_button.configure(text=self.tr('calculation.calculate'))
        self.clear_button.configure(text=self.tr('common.clear'))
        self._render()

    def _render(self):
        self.flow.set('—' if self.result is None else format_user_number(self.result.scenario_flow_m3_h))
        self.duration.set('—' if self.result is None else format_user_number(self.result.duration_h))
        set_result_state(self.result_card,self.result is not None)

    def invalidate(self,*_args):
        self.result=None;self.message.set('');self._render()
        if not self._suppress:self.changed()

    def calculate(self):
        self.result=None
        try:
            values={key:parse_engineering_float(var.get(),field_name=key,field_key='transfer.scenario115.'+key) for key,var in self.fields.items()}
            self.result=calculate_discharge_115(values['volume'],values['nominal'])
            self.message.set('')
        except ValidationError as error:
            self.message.set(render_validation_issue(error.issue,SimpleNamespace(translate=self.tr)))
        self._render()

    def export_state(self):
        return {key:value.get() for key,value in self.fields.items()}

    def load_state(self,state):
        self._suppress=True
        try:
            state=state if isinstance(state,dict) else {}
            for key,var in self.fields.items():var.set(str(state.get(key,'')))
            self.result=None;self.message.set('');self._render()
        finally:self._suppress=False

    def clear(self):
        self.load_state({});self.changed()
