"""Read-only pressure equivalent using the page's single density input."""
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace
from engineering.head_loss.pressure import pressure_equivalent_bar
from engineering.input_parsing import parse_engineering_float
from engineering.validation import ValidationError
from i18n.validation import render_validation_issue
from ui.formatting import format_user_number


class DischargePressurePanel(ttk.Frame):
    def __init__(self,parent,translate,density_text):
        super().__init__(parent)
        self.tr=translate;self.density_text=density_text
        self.head=None;self.fluid_identity=None
        self.value=tk.StringVar(self,value='—');self.reason=tk.StringVar(self)
        self.used_density=None;self.pressure_bar=None
        self.title=ttk.Label(self,style='ResultMetricLabel.TLabel',wraplength=240)
        self.title.grid(row=0,column=0,sticky='w')
        ttk.Label(self,textvariable=self.value,style='ResultMetricValue.TLabel').grid(row=1,column=0,sticky='w')
        ttk.Label(self,textvariable=self.reason,style='Info.TLabel',wraplength=240).grid(row=2,column=0,sticky='w')
        self.refresh_texts()

    def refresh_texts(self):
        self.title.configure(text=self.tr('discharge.pressure.title'));self.render()

    def observe_fluid(self,identity):
        if identity!=self.fluid_identity:self.clear()
        self.fluid_identity=identity

    def set_head(self,head):
        self.head=head;self.render()

    def clear(self):
        self.head=None;self.pressure_bar=None;self.used_density=None
        self.value.set('—');self.reason.set(self.tr('discharge.pressure.recalculate'))

    def render(self):
        self.pressure_bar=None;self.used_density=None;self.value.set('—')
        if self.head is None:
            self.reason.set(self.tr('discharge.pressure.recalculate'));return
        try:
            density=parse_engineering_float(self.density_text(),field_name='Density',field_key='hydro.fluid.density_reference')
            value=pressure_equivalent_bar(density,self.head)
        except ValidationError as error:
            self.reason.set(render_validation_issue(error.issue,SimpleNamespace(translate=self.tr)));return
        self.used_density=density;self.pressure_bar=value
        self.value.set(format_user_number(value)+' bar')
        self.reason.set(self.tr('discharge.pressure.used',density=format_user_number(density)))
