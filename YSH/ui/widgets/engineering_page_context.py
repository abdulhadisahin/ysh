"""Compact project-linked engineering identity; overrides require an explicit action."""
from tkinter import ttk

class EngineeringPageContext(ttk.Frame):
    def __init__(self,parent,controller,module):
        super().__init__(parent)
        self.controller=controller;self.module=module;self.columnconfigure(1,weight=1)
        self.fluid_label=ttk.Label(self);self.fluid_label.grid(row=0,column=0,sticky='w',padx=(0,10))
        self.fluid_box=ttk.Combobox(self,state='disabled',width=32);self.fluid_box.grid(row=0,column=1,sticky='ew')
        self.project_button=ttk.Button(self,command=controller.window._open_system_context)
        self.project_button.grid(row=0,column=2,sticky='e',padx=(8,0))
        self.material_label=ttk.Label(self);self.material_label.grid(row=1,column=0,sticky='w',padx=(0,10))
        self.material_box=ttk.Combobox(self,state='disabled',width=32);self.material_box.grid(row=1,column=1,sticky='ew')
        self.override_button=ttk.Button(self,command=lambda:controller.open_module_context(module))
        self.override_button.grid(row=1,column=2,sticky='e',padx=(8,0))
        self.surface=ttk.Label(self,style='Info.TLabel',wraplength=650);self.surface.grid(row=2,column=0,columnspan=3,sticky='w')
        self.summary=ttk.Label(self,style='Info.TLabel',wraplength=650);self.summary.grid(row=3,column=0,columnspan=3,sticky='ew')
        self.bind('<Configure>',self._fit)
    def _fit(self,event):
        for widget in (self.surface,self.summary):widget.configure(wraplength=max(240,event.width-10))
    def refresh(self,text):
        c=self.controller;tr=c.window._translate;context=c.context_for(self.module)
        surface=next((r for r in c.catalog.surface_records if r.id==context.surface_profile_id),None)
        self.fluid_label.configure(text=tr('engineering.select.fluid'))
        self.material_label.configure(text=tr('engineering.select.material'))
        self.fluid_box.configure(values=tuple(r.name_tr for r in c.catalog.fluid_records))
        self.material_box.configure(values=tuple(dict.fromkeys(r.material_name for r in c.catalog.surface_records)))
        self.fluid_box.set(context.fluid.name_tr if context.fluid else tr('engineering.none'))
        self.material_box.set(surface.material_name if surface else tr('engineering.none'))
        state=tr('engineering.status.OVERRIDE') if self.module in c.module_contexts else tr('engineering.status.LINKED') if context.fluid or surface else tr('engineering.status.MANUAL')
        surface_text=''
        if surface:
            epsilon=str(surface.roughness_mm)+' mm' if surface.roughness_mm is not None else tr('engineering.status.SOURCE_REQUIRED')
            surface_text=tr('engineering.select.surface')+': '+surface.surface_condition.replace('_',' ').title()+' · ε: '+epsilon+' · '
        self.surface.configure(text=surface_text+state)
        if self.module=='discharge_head_loss':
            density=c.catalog.references(context).get('density')
            if density:
                value=density.get('default_value')
                shown=str(value)+' '+density['unit'] if value is not None else tr('engineering.status.SOURCE_REQUIRED')
                temperature=density.get('reference_temperature_c')
                if temperature is not None:shown+=' @ '+str(temperature)+' °C'
                text=tr('engineering.density_reference')+': '+shown+'\n'+text
        self.summary.configure(text=text)
        self.project_button.configure(text=tr('engineering.edit_project'),state='normal' if c.family() else 'disabled')
        self.override_button.configure(text=tr('engineering.edit_module'))
