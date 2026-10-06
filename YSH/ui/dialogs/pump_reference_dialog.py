"""Modal ttk dialog for adding or editing pump reference ships."""
from __future__ import annotations
import tkinter as tk
from tkinter import messagebox,ttk
from core.pump_reference import PumpReference
from engineering.input_parsing import parse_engineering_float
from engineering.validation import ValidationError, ValidationIssue
from i18n.translator import Translator
from i18n.validation import render_validation_issue
from ui.theme.spacing import MD, SM
class PumpReferenceDialog:
    """Edits one PumpReference through its service layer."""
    def __init__(self,parent:tk.Misc,service:object,reference:PumpReference|None=None,translate:object|None=None)->None:
        """Create an add or edit modal dialog."""
        self._translate=translate or Translator("tr").translate;self._service=service;self._reference=reference;self.result:PumpReference|None=None;self._dialog=tk.Toplevel(parent);self._dialog.title(self._translate("dialog.pump_reference"));self._dialog.transient(parent);self._values={key:tk.StringVar(value="" if reference is None else str(getattr(reference,key))) for key in ("ship_name","fuel_capacity_m3","pump_capacity_m3h","description","source")};self._build();self._dialog.grab_set();self._entries["ship_name"].focus_set();self._dialog.bind("<Return>",self._save);self._dialog.bind("<Escape>",self._cancel);self._dialog.protocol("WM_DELETE_WINDOW",self._cancel)
    def _build(self)->None:
        frame=ttk.Frame(self._dialog,style="Dialog.TFrame",padding=MD);frame.grid();self._entries={};labels=(("ship_name",self._translate("field.ship_name")),("fuel_capacity_m3",f"{self._translate('field.fuel_capacity')} (m³)"),("pump_capacity_m3h",f"{self._translate('field.pump_capacity')} (m³/h)"),("description",self._translate("project.description")),("source",self._translate("field.source")))
        for row,(key,label) in enumerate(labels):ttk.Label(frame,text=label).grid(row=row,column=0,sticky="w",pady=SM // 2);entry=ttk.Entry(frame,textvariable=self._values[key],width=38);entry.grid(row=row,column=1,padx=(SM,0),pady=SM // 2);self._entries[key]=entry
        ttk.Button(frame,text=self._translate("common.cancel"),command=self._cancel,style="Neutral.TButton").grid(row=5,column=0,pady=MD);ttk.Button(frame,text=self._translate("common.save"),command=self._save,style="Success.TButton").grid(row=5,column=1,sticky="e",pady=MD)
    def show(self)->PumpReference|None:
        """Wait for successful save or cancellation."""
        self._dialog.wait_window();return self.result
    def _save(self,event:tk.Event[tk.Misc]|None=None)->str:
        try:
            name=self._values["ship_name"].get().strip()
            if not name: raise ValidationError(ValidationIssue("required","field.ship_name"))
            fuel=parse_engineering_float(self._values["fuel_capacity_m3"].get(),field_name="Yakıt Kapasitesi",field_key="field.fuel_capacity")
            if fuel <= 0: raise ValidationError(ValidationIssue("greater_than_zero","field.fuel_capacity"))
            pump=parse_engineering_float(self._values["pump_capacity_m3h"].get(),field_name="Tulumba Kapasitesi",field_key="field.pump_capacity")
            if pump <= 0: raise ValidationError(ValidationIssue("greater_than_zero","field.pump_capacity"))
            description=self._values["description"].get().strip();source=self._values["source"].get().strip()
            if self._reference is None:self.result=self._service.create_reference(name,fuel,pump,description,source)
            else:self._reference.ship_name=name;self._reference.fuel_capacity_m3=fuel;self._reference.pump_capacity_m3h=pump;self._reference.description=description;self._reference.source=source;self.result=self._service.update_reference(self._reference)
        except ValidationError as error:messagebox.showerror(self._translate("dialog.error"),render_validation_issue(error.issue,type("T",(),{"translate":self._translate})()),parent=self._dialog);return "break"
        except LookupError:messagebox.showerror(self._translate("dialog.error"),self._translate("validation.unexpected_error"),parent=self._dialog);return "break"
        self._dialog.destroy();return "break"
    def _cancel(self,event:tk.Event[tk.Misc]|None=None)->str:self._dialog.destroy();return "break"
