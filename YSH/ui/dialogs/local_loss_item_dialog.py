"""Modal editor for local hydraulic-loss rows."""
from __future__ import annotations
import math
import tkinter as tk
from tkinter import messagebox,ttk
from core.local_loss_item import LocalLossItem
from engineering.input_parsing import parse_engineering_float,parse_engineering_integer
from engineering.validation import ValidationError, ValidationIssue
from i18n.translator import Translator
from i18n.validation import render_validation_issue
from ui.theme.spacing import MD, SM
class LocalLossItemDialog:
    """Collects one validated local-loss component."""
    def __init__(self,parent:tk.Misc,item:LocalLossItem|None=None,translate:object|None=None)->None:
        """Create an add or edit dialog."""
        self._translate=translate or Translator().translate;self.result:LocalLossItem|None=None;self._dialog=tk.Toplevel(parent);self._dialog.transient(parent);self._dialog.title(self._translate("dialog.local_loss_item"));self._name=tk.StringVar(value="" if item is None else item.name);self._quantity=tk.StringVar(value="" if item is None else str(item.quantity));self._coefficient=tk.StringVar(value="" if item is None else str(item.k_coefficient));frame=ttk.Frame(self._dialog,style="Dialog.TFrame",padding=MD);frame.grid();
        for row,(label,value) in enumerate(((self._translate("field.component"),self._name),(self._translate("field.quantity"),self._quantity),(self._translate("field.local_loss_k"),self._coefficient))):ttk.Label(frame,text=label).grid(row=row,column=0,sticky="w",pady=SM // 2);ttk.Entry(frame,textvariable=value,width=24).grid(row=row,column=1,padx=(SM,0),pady=SM // 2)
        ttk.Button(frame,text=self._translate("common.save"),command=self._save,style="Success.TButton").grid(row=3,column=1,sticky="e",pady=MD);self._dialog.grab_set();self._dialog.bind("<Return>",self._save);self._dialog.bind("<Escape>",self._cancel);self._dialog.protocol("WM_DELETE_WINDOW",self._cancel)
    def show(self)->LocalLossItem|None:
        """Wait for Save or Cancel."""
        self._dialog.wait_window();return self.result
    def _save(self,event:object|None=None)->str:
        try:
            name=self._name.get().strip()
            if not name: raise ValidationError(ValidationIssue("required","field.component"))
            quantity=parse_engineering_integer(self._quantity.get(),field_name="Local Loss Quantity",field_key="field.quantity")
            if quantity < 0: raise ValidationError(ValidationIssue("zero_or_greater","field.quantity"))
            coefficient=parse_engineering_float(self._coefficient.get(),field_name="Local Loss Coefficient",field_key="field.local_loss_k")
            if not math.isfinite(coefficient) or coefficient < 0: raise ValidationError(ValidationIssue("zero_or_greater","field.local_loss_k"))
        except ValidationError as error:messagebox.showerror(self._translate("dialog.error"),render_validation_issue(error.issue,type("T",(),{"translate":self._translate})()),parent=self._dialog);return "break"
        self.result=LocalLossItem(name,quantity,coefficient);self._dialog.destroy();return "break"
    def _cancel(self,event:object|None=None)->str:self._dialog.destroy();return "break"
