"""Compact source summaries plus explicit Library selection; no engineering math."""
import tkinter as tk
from tkinter import ttk

from engineering.fire.library import FIELD_PARAMETERS, FireParameter
from engineering.fire.units import fraction_to_percent
from services.engineering_library_service import LibraryError
from ui.widgets.detail_disclosure import DetailDisclosure
from ui.widgets.formula_steps import number


class FireLibraryInputPanel(ttk.Frame):
    def __init__(self,parent,view):
        super().__init__(parent,style='Fire.TFrame')
        self.view=view;self.loading=True;self.choices={};self.summaries={};self.controls=[];self.reasons={}
        self.names=tuple(name for name in view.spec if name in FIELD_PARAMETERS)
        self.columnconfigure(0,weight=1)
        for row,name in enumerate(self.names):
            label=ttk.Label(self,style='Fire.TLabel',wraplength=500,justify='left')
            label.grid(row=row,column=0,sticky='ew',pady=3);self.summaries[name]=label
        self.details=DetailDisclosure(self,'',style='Fire.TFrame',body_style='Fire.TFrame')
        self.details.grid(row=len(self.names),column=0,sticky='ew')
        body=self.details.body;body.columnconfigure(0,weight=1)
        self.context_label=ttk.Label(body,style='Fire.TLabel',wraplength=500)
        self.context_label.grid(row=0,column=0,sticky='w')
        self.context=tk.StringVar(self)
        self.context_entry=ttk.Entry(body,textvariable=self.context)
        self.context_entry.grid(row=1,column=0,sticky='ew')
        self.context.trace_add('write',self._context)
        self.refresh_button=ttk.Button(body,command=self.refresh)
        self.refresh_button.grid(row=2,column=0,sticky='w',pady=4)
        self.boxes={}
        for index,name in enumerate(self.names):
            row=3+index*5
            label=ttk.Label(body,style='Fire.TLabel');label.grid(row=row,column=0,sticky='w');self.controls.append((label,view.spec[name][0]))
            combo=ttk.Combobox(body,state='readonly',width=18)
            combo.grid(row=row+1,column=0,sticky='ew');self.boxes[name]=combo
            actions=ttk.Frame(body,style='Fire.TFrame');actions.grid(row=row+2,column=0,sticky='w',pady=3)
            for column,action in enumerate(('use','update','keep','manual')):
                button=ttk.Button(actions,command=lambda n=name,a=action:self.action(n,a))
                button.grid(row=0,column=column,padx=(0,4));self.controls.append((button,'fire.library.'+action))
            reason_label=ttk.Label(body,style='Fire.TLabel');reason_label.grid(row=row+3,column=0,sticky='w')
            self.controls.append((reason_label,'fire.ui.reason'))
            entry=ttk.Entry(body,textvariable=view.meta_vars[name]['reason']);entry.grid(row=row+4,column=0,sticky='ew')
            self.reasons[name]=(reason_label,entry)
        self.message=ttk.Label(body,style='Fire.TLabel',wraplength=500,justify='left')
        self.message.grid(row=3+len(self.names)*5,column=0,sticky='ew',pady=4)
        self.bind('<Configure>',self._fit,add='+')
        self.loading=False;self.refresh_texts()

    @property
    def model(self):return self.view.model

    def _fit(self,event):
        width=max(120,event.width-12)
        for label in (*self.summaries.values(),self.context_label,self.message):label.configure(wraplength=width)

    def _context(self,*_):
        if self.loading:return
        self.model.set_library_context(self.view.kind,self.context.get())
        self.choices={}
        for box in self.boxes.values():box.set('');box.configure(values=())
        self.view._dirty()

    def refresh(self):
        """One explicit lookup; never auto-pick a candidate or replace used inputs."""
        try:
            library=self.view.workspace.library_service()
            records=library.fire_records_for_context(self.context.get(),self.model.library_service(self.view.kind)) if library else ()
            if library:self.model.observe_library(library.get_fire_record)
            for name,box in self.boxes.items():
                self.choices[name]={}
                for record in records:
                    if record.parameter_type!=FIELD_PARAMETERS[name]:continue
                    value=fraction_to_percent(record.value) if name=='foam_fraction' else record.value
                    unit='%' if name=='foam_fraction' else record.unit
                    label=f'{number(value)} {unit} · {record.source.document if record.source else ""} · r{record.revision} · {str(record.id)[:8]}'
                    self.choices[name][label]=record
                selected=box.get();box.configure(values=tuple(self.choices[name]))
                if selected not in self.choices[name]:box.set('')
            self.message.configure(text='');self.sync()
        except LibraryError:self.message.configure(text=self.view.tr('library2.error.storage'))

    def action(self,name,action):
        try:
            if action=='manual':self.model.manual_library(self.view.kind,name)
            elif action=='keep':self.model.keep_library(name)
            else:
                library=self.view.workspace.library_service()
                linked=self.model.library_inputs.links.get(name)
                record=(library.get_fire_record(linked.id) if library and linked and action=='update'
                        else self.choices.get(name,{}).get(self.boxes[name].get()) if action=='use' else None)
                if record is None:raise ValueError('Explicit selection required')
                self.model.link_library(self.view.kind,name,record,update=action=='update')
            self.view.load_fields();self.view.workspace.on_dirty();self.view.sync()
            self.message.configure(text='')
        except (ValueError,LibraryError):self.message.configure(text=self.view.tr('fire.library.choose'))

    def sync(self):
        tr=self.view.tr;self.loading=True
        self.context.set(self.model.library_inputs.contexts[self.view.kind]);self.loading=False
        for name,label in self.summaries.items():
            record=self.model.library_inputs.links.get(name)
            value=fraction_to_percent(record.value) if record and name=='foam_fraction' else record.value if record else None
            unit='%' if name=='foam_fraction' else self.view.spec[name][1]
            status=record.source_status.value if record else 'SOURCE_REQUIRED'
            source=record.source.document if record and record.source else ''
            recommended=number(value)+' '+unit if value is not None else '—'
            used=self.model.fields[self.view.kind][name] or '—'
            text=f'{tr(self.view.spec[name][0])} · {tr("fire.library.recommended")}: {recommended} · {tr("fire.library.used")}: {used} {unit}\n{tr("fire.ui.source."+status)}'
            if source:text+=' · '+source+f' · r{record.revision}'
            if record and not record.applicable(self.context.get(),self.model.library_service(self.view.kind)):
                text+=' · '+tr('fire.library.mismatch')
            if self.model.library_inputs.stale.get(name):text+=' · '+tr('fire.library.stale')
            if self.model.library_inputs.kept.get(name):text+=' · '+tr('fire.library.kept')
            label.configure(text=text)
            for widget in self.reasons[name]:(widget.grid if record else widget.grid_remove)()
            for field in ('status','document','recommended'):
                editor=self.view.meta_editors[name][field]
                editor.configure(state='disabled' if record else 'readonly' if field=='status' else 'normal')

    def refresh_texts(self):
        tr=self.view.tr
        self.details._title=tr('fire.library.title')
        self.details._toggle.configure(text=('▾ ' if self.details.expanded else '▸ ')+self.details._title)
        self.context_label.configure(text=tr('fire.library.context'))
        self.refresh_button.configure(text=tr('fire.library.refresh'))
        for control,key in self.controls:control.configure(text=tr(key))
        self.sync()
