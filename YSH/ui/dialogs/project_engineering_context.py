"""Explicit project defaults and applied calculation values; never a family selector."""
import tkinter as tk
from tkinter import ttk,messagebox
from engineering.system_context import ContextReference
from engineering.catalog_seeds import identity
from dataclasses import replace

class ProjectEngineeringContextDialog:
    def __init__(self,window):
        self.owner=window;self.controller=window._engineering_context_controller;self.catalog=self.controller.catalog;self.tr=window._translate
        self.window=tk.Toplevel(window._root);self.window.title(self.tr('engineering.context_title'))
        self.window.geometry('940x640');self.window.minsize(760,540);self.window.transient(window._root)
        self.window.columnconfigure(0,weight=1);self.window.rowconfigure(2,weight=1)
        context=window._system_context
        self.header=ttk.Label(self.window,text=window._active_project.name+' · '+self.tr('project.family.'+self.controller.family()),style='Info.TLabel')
        self.header.grid(row=0,column=0,sticky='w',padx=12,pady=6)
        form=ttk.Frame(self.window,padding=10);form.grid(row=1,column=0,sticky='ew');form.columnconfigure(1,weight=1);form.columnconfigure(3,weight=1)
        self.choices={};self.variables={}
        from ui.widgets.engineering_selection import EngineeringSelectionForm
        self.selection=EngineeringSelectionForm(form,self.catalog,self.tr,context)
        action_row=max(6,len(self.selection.variables))
        self.selection.grid(row=0,column=0,columnspan=2,rowspan=action_row,sticky='nsew')
        self.variables=self.selection.variables;self.choices=self.selection.choices
        scopes={self.tr('engineering.none'):'',**{self.tr('engineering.scope.'+v):v for v in ('TL_FFS','TL_LT500')}}
        self.choices['applicability']=scopes
        self.variables['applicability']=tk.StringVar(value=next((label for label,value in scopes.items() if value==context.applicability_scope),context.applicability_scope))
        ttk.Label(form,text=self.tr('engineering.applicability')).grid(row=2,column=2,columnspan=2,sticky='w',padx=10)
        ttk.Combobox(form,textvariable=self.variables['applicability'],values=tuple(scopes),width=23).grid(row=3,column=2,columnspan=2,sticky='ew',padx=10)
        mechanical={self.tr('engineering.none'):None,**{r.designation:r for r in self.catalog.material_records}}
        self.choices['mechanical']=mechanical
        selected=next((label for label,record in mechanical.items() if record and record.id==context.material_id),next(iter(mechanical)))
        self.variables['mechanical']=tk.StringVar(value=selected)
        ttk.Label(form,text=self.tr('engineering.mechanical_material')).grid(row=0,column=2,columnspan=2,sticky='w',padx=10)
        ttk.Combobox(form,textvariable=self.variables['mechanical'],values=tuple(mechanical),state='readonly',width=40).grid(row=1,column=2,columnspan=2,sticky='ew',padx=10)
        ttk.Button(form,text=self.tr('engineering.apply'),command=self.apply).grid(row=action_row,column=1,sticky='e',pady=6)
        ttk.Button(form,text=self.tr('engineering.reload'),command=self.reload).grid(row=action_row,column=3,sticky='e')
        body=ttk.Frame(self.window);body.grid(row=2,column=0,sticky='nsew',padx=12);body.rowconfigure(0,weight=1);body.columnconfigure(0,weight=1)
        self.tree=ttk.Treeview(body,columns=('module','property','default','used','status'),show='headings',height=8)
        for column,width in (('module',210),('property',160),('default',110),('used',110),('status',135)):
            self.tree.heading(column,text=self.tr('engineering.'+column));self.tree.column(column,width=width,minwidth=70)
        self.tree.grid(row=0,column=0,sticky='nsew');scroll=ttk.Scrollbar(body,command=self.tree.yview);scroll.grid(row=0,column=1,sticky='ns');self.tree.configure(yscrollcommand=scroll.set)
        self.detail=tk.Text(body,height=6,wrap='word',state='disabled');self.detail.grid(row=1,column=0,columnspan=2,sticky='ew',pady=6)
        self.tree.bind('<<TreeviewSelect>>',self.details)
        actions=ttk.Frame(self.window,padding=8);actions.grid(row=3,column=0,sticky='ew')
        for action in ('update','keep','reference','project'):
            ttk.Button(actions,text=self.tr('engineering.action.'+action),command=lambda action=action:self.action(action)).pack(side='left',padx=3)
        ttk.Button(actions,text=self.tr('common.close'),command=self.window.destroy).pack(side='right')
        ttk.Label(self.window,text=self.tr('engineering.scope_notice'),style='Info.TLabel',wraplength=890).grid(row=4,column=0,sticky='w',padx=12,pady=5)
        self.refresh()
    def apply(self):
        try:updated=self.selection.value()
        except ValueError:
            messagebox.showerror(self.tr('engineering.context_title'),self.tr('engineering.action_unavailable'),parent=self.window)
            return
        mechanical=self.choices['mechanical'].get(self.variables['mechanical'].get())
        surface=next((r for r in self.catalog.surface_records if r.id==updated.surface_profile_id),None)
        updated=updated.changed(material_id=mechanical.id if mechanical else surface.material_id if surface else None,
            applicability_scope=self.choices['applicability'].get(self.variables['applicability'].get(),self.variables['applicability'].get()))
        self.controller.apply(updated);self.refresh()
    def reload(self):
        self.catalog.reload();self.selection.load(self.owner._system_context);self.controller.observe();self.refresh()
    def refresh(self):
        from ui.warning_center_state import MODULE_LABELS
        selected=self.tree.selection();chosen=self.mapping.get(selected[0]) if selected and hasattr(self,'mapping') else None
        self.tree.delete(*self.tree.get_children());self.mapping={}
        for module,links in self.controller.links.items():
            for name,link in links.items():
                key=self.tree.insert('','end',values=(self.tr(MODULE_LABELS[module]),self.tr('engineering.property.'+name),
                    link.reference.get('default_value') if link.reference.get('default_value') is not None else self.tr('engineering.status.SOURCE_REQUIRED'),
                    link.used_value,self.tr('engineering.status.'+link.status)))
                self.mapping[key]=(module,name)
                if chosen==(module,name):self.tree.selection_set(key)
        self.details()
    def details(self,event=None):
        from engineering.basis import basis_text
        chosen=self.tree.selection();pair=self.mapping.get(chosen[0]) if chosen else None
        text=''
        if pair:
            link=self.controller.links[pair[0]][pair[1]]
            item=link.payload();item['status']=link.status
            text=basis_text({'values':[item]},self.tr)
            if link.pending:text+='\n'+self.tr('engineering.pending')+': '+str(link.pending.get('default_value'))+' '+link.pending.get('unit','')
        self.detail.configure(state='normal');self.detail.delete('1.0','end');self.detail.insert('1.0',text);self.detail.configure(state='disabled')
    def action(self,action):
        selected=self.tree.selection();pair=self.mapping.get(selected[0]) if selected else None
        if not pair:return
        try:self.controller.action(*pair,action)
        except ValueError as error:messagebox.showerror(self.tr('engineering.context_title'),self.tr('engineering.action_unavailable'),parent=self.window)
        self.refresh()
