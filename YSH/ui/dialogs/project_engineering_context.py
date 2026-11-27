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
        form=ttk.Frame(self.window,padding=(10,4));form.grid(row=1,column=0,sticky='ew');form.columnconfigure(0,weight=3);form.columnconfigure(1,weight=2)
        self.choices={};self.variables={}
        from ui.widgets.engineering_selection import EngineeringSelectionForm
        family=self.controller.family()
        left=ttk.LabelFrame(form,text=self.tr('engineering.section.fluid_material'),padding=8);left.grid(row=0,column=0,sticky='nsew',padx=(0,6));left.columnconfigure(0,weight=1)
        self.selection=EngineeringSelectionForm(left,self.catalog,self.tr,context,family=family)
        self.selection.grid(row=0,column=0,sticky='ew')
        self.variables=self.selection.variables;self.choices=self.selection.choices
        right=ttk.LabelFrame(form,text=self.tr('engineering.section.rules_scope'),padding=8);right.grid(row=0,column=1,sticky='nsew',padx=(6,0));right.columnconfigure(0,weight=1)
        from services.library_scope import scope_relevant,material_relevant
        scopes={self.tr('engineering.none'):'',**{self.tr('engineering.scope.'+v):v for v in ('TL_FFS','TL_LT500') if v==context.applicability_scope or scope_relevant(family,v)}}
        self.choices['applicability']=scopes
        self.variables['applicability']=tk.StringVar(value=next((label for label,value in scopes.items() if value==context.applicability_scope),context.applicability_scope))
        mechanical={self.tr('engineering.none'):None,**{r.designation:r for r in self.catalog.material_records if r.id==context.material_id or material_relevant(family,r.designation)}}
        self.choices['mechanical']=mechanical
        selected=next((label for label,record in mechanical.items() if record and record.id==context.material_id),next(iter(mechanical)))
        self.variables['mechanical']=tk.StringVar(value=selected)
        ttk.Label(right,text=self.tr('engineering.mechanical_material')).grid(row=0,column=0,sticky='w')
        ttk.Combobox(right,textvariable=self.variables['mechanical'],values=tuple(mechanical),state='readonly',width=34).grid(row=1,column=0,sticky='ew',pady=(0,8))
        ttk.Label(right,text=self.tr('engineering.applicability')).grid(row=2,column=0,sticky='w')
        ttk.Combobox(right,textvariable=self.variables['applicability'],values=tuple(scopes),width=34).grid(row=3,column=0,sticky='ew')
        buttons=ttk.Frame(form);buttons.grid(row=1,column=0,columnspan=2,sticky='e',pady=(6,0))
        ttk.Button(buttons,text=self.tr('engineering.reload'),command=self.reload).pack(side='left',padx=4)
        ttk.Button(buttons,text=self.tr('engineering.apply'),command=self.apply).pack(side='left',padx=4)
        body=ttk.LabelFrame(self.window,text=self.tr('engineering.section.values'),padding=6);body.grid(row=2,column=0,sticky='nsew',padx=12,pady=(4,0));body.rowconfigure(0,weight=1);body.columnconfigure(0,weight=1)
        self.tree=ttk.Treeview(body,columns=('module','property','default','used','status'),show='headings',height=5)
        for column,width in (('module',210),('property',160),('default',110),('used',110),('status',135)):
            self.tree.heading(column,text=self.tr('engineering.'+column));self.tree.column(column,width=width,minwidth=70)
        for status,colour in (('LINKED','#1b6e3c'),('OVERRIDE','#1f4f9a'),('STALE','#b00020'),('SOURCE_REQUIRED','#9a5b00')):
            self.tree.tag_configure(status,foreground=colour)
        self.tree.grid(row=0,column=0,sticky='nsew');scroll=ttk.Scrollbar(body,command=self.tree.yview);scroll.grid(row=0,column=1,sticky='ns');self.tree.configure(yscrollcommand=scroll.set)
        self.detail=tk.Text(body,height=6,wrap='word',state='disabled',relief='flat',background='#f6f8fa');self.detail.grid(row=1,column=0,columnspan=2,sticky='ew',pady=(6,0))
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
                    link.used_value if link.used_value is not None else self.tr('engineering.empty'),self.tr('engineering.status.'+link.status)),
                    tags=(link.status,))
                self.mapping[key]=(module,name)
                if chosen==(module,name):self.tree.selection_set(key)
        if not self.tree.selection() and self.mapping:self.tree.selection_set(next(iter(self.mapping)))
        self.details()
    def details(self,event=None):
        from engineering.basis import basis_text
        chosen=self.tree.selection();pair=self.mapping.get(chosen[0]) if chosen else None
        text=self.tr('engineering.detail_hint')
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
