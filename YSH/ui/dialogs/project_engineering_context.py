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
        fluids={self.tr('engineering.none'):None,**{r.name_tr:r for r in self.catalog.fluid_records}}
        surfaces={self.tr('engineering.none'):None,**{r.name:r for r in self.catalog.surface_records}}
        profiles={self.tr('engineering.none'):None,**{r.name:r for r in self.catalog.profile_records}}
        rows=(('fluid',fluids,context.fluid_id),('material',surfaces,context.surface_profile_id),('profile',profiles,context.rule_set_id))
        for row,(name,choices,selected) in enumerate(rows):
            ttk.Label(form,text=self.tr('engineering.'+name)).grid(row=row,column=0,sticky='w',padx=4,pady=3)
            self.choices[name]=choices
            variable=tk.StringVar(value=next((label for label,record in choices.items() if record and record.id==selected),next(iter(choices))))
            self.variables[name]=variable
            ttk.Combobox(form,textvariable=variable,values=tuple(choices),state='readonly',width=40).grid(row=row,column=1,sticky='ew',padx=4)
        for row,(name,current,values) in enumerate((('service',context.service,('', 'DIESEL_FUEL_DELIVERY','BALLAST','BILGE')),
                ('line_type',context.line_type,('', 'SUCTION','DELIVERY')),('applicability',context.applicability_scope,('', 'TL_FFS','TL_LT500')))):
            ttk.Label(form,text=self.tr('engineering.'+name)).grid(row=row,column=2,sticky='w',padx=(14,4))
            choices={self.tr('engineering.none') if not value else self.tr(('engineering.line.' if name=='line_type' else 'engineering.scope.')+value) if name!='service' else value:value for value in values}
            self.choices[name]=choices
            var=tk.StringVar(value=next((label for label,value in choices.items() if value==current),current));self.variables[name]=var
            ttk.Combobox(form,textvariable=var,values=tuple(choices),state='readonly' if name!='service' else 'normal',width=23).grid(row=row,column=3,sticky='ew')
        mechanical={self.tr('engineering.none'):None,**{r.designation:r for r in self.catalog.material_records}}
        self.choices['mechanical']=mechanical
        selected=next((label for label,record in mechanical.items() if record and record.id==context.material_id),next(iter(mechanical)))
        self.variables['mechanical']=tk.StringVar(value=selected)
        ttk.Label(form,text=self.tr('engineering.mechanical_material')).grid(row=3,column=0,sticky='w')
        ttk.Combobox(form,textvariable=self.variables['mechanical'],values=tuple(mechanical),state='readonly',width=40).grid(row=3,column=1,sticky='ew')
        ttk.Button(form,text=self.tr('engineering.apply'),command=self.apply).grid(row=4,column=1,sticky='e',pady=6)
        ttk.Button(form,text=self.tr('engineering.reload'),command=self.reload).grid(row=4,column=3,sticky='e')
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
        context=self.owner._system_context
        fluid=self.choices['fluid'].get(self.variables['fluid'].get());surface=self.choices['material'].get(self.variables['material'].get());profile=self.choices['profile'].get(self.variables['profile'].get())
        mechanical=self.choices['mechanical'].get(self.variables['mechanical'].get())
        updated=context.changed(fluid=ContextReference(id=fluid.id,code=fluid.code,name_tr=fluid.name_tr,name_en=fluid.name_en) if fluid else None,
            surface_profile_id=surface.id if surface else None,material_id=mechanical.id if mechanical else surface.material_id if surface and surface.material_id else None,
            rule_set_id=profile.id if profile else None,line_type=self.choices['line_type'].get(self.variables['line_type'].get(),''),service=self.choices['service'].get(self.variables['service'].get(),self.variables['service'].get()),
            applicability_scope=self.choices['applicability'].get(self.variables['applicability'].get(),''))
        self.controller.apply(updated);self.refresh()
    def reload(self):
        self.catalog.reload();self.controller.observe();self.refresh()
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
