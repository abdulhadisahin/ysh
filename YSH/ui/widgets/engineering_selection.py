"""Shared catalog selectors. Material identity and surface condition are separate."""
import tkinter as tk
from tkinter import ttk
from i18n.catalog_text import catalog_text
from engineering.system_context import SystemContext,ContextReference
from services.library_scope import material_relevant,profile_relevant

SERVICES=('', 'DIESEL_FUEL_DELIVERY','DIESEL_FUEL_SUCTION','SEA_WATER_COOLING','FRESH_WATER_COOLING','LUBE_OIL','BALLAST','BILGE')

class EngineeringSelectionForm(ttk.Frame):
    def __init__(self,parent,catalog,translate,context=None,*,module=None,family=None):
        super().__init__(parent)
        self.catalog=catalog;self.tr=translate;self.variables={};self.boxes={};self.labels={};self.choices={};self.family=family
        self.columnconfigure(1,weight=1)
        fixed_line=module in ('discharge_head_loss','suction_npsh')
        fields=('fluid','material','surface','profile') if fixed_line else ('fluid','material','surface','service','profile')
        seawater=context is not None and context.system is not None and context.system.code=='SEA_WATER'
        if seawater:
            if module is not None:fields+=('strength_material',)
            fields+=('fluid_temperature_c','fluid_salinity_g_kg')
        for row,name in enumerate(fields):
            self.labels[name]=ttk.Label(self);self.labels[name].grid(row=row,column=0,sticky='w',padx=(0,10),pady=2)
            self.variables[name]=tk.StringVar()
            box=(ttk.Entry(self,textvariable=self.variables[name],width=12) if name in ('fluid_temperature_c','fluid_salinity_g_kg')
                 else ttk.Combobox(self,textvariable=self.variables[name],state='readonly',width=36))
            box.grid(row=row,column=1,sticky='ew',pady=2);self.boxes[name]=box
        self.boxes['material'].bind('<<ComboboxSelected>>',self._material_changed)
        self.load(context or SystemContext())
    def _set(self,name,choices,selected):
        self.choices[name]=choices;self.boxes[name].configure(values=tuple(choices))
        self.variables[name].set(next((label for label,value in choices.items() if value==selected),next(iter(choices))))
    def load(self,context):
        self.context=context;none=self.tr('engineering.none')
        fluid_choices={none:None}
        seawater=context.system is not None and context.system.code=='SEA_WATER'
        for fluid in (self.catalog.project_fluids(self.family) if self.family else self.catalog.project_fluids('seawater') if seawater else self.catalog.fluid_records):
            label=catalog_text(self.tr,fluid.name_tr)
            if label in fluid_choices:label+=' · '+fluid.code
            fluid_choices[label]=fluid.id
        self._set('fluid',fluid_choices,context.fluid_id)
        if seawater:self.boxes['fluid'].configure(state='disabled')
        if 'strength_material' in self.boxes:
            self._set('strength_material',{none:None,**{r.designation:r.id for r in self.catalog.material_records}},context.material_id)
        if 'fluid_temperature_c' in self.boxes:
            for name in ('fluid_temperature_c','fluid_salinity_g_kg'):
                value=getattr(context,name)
                self.variables[name].set('' if value is None else str(value))
        surface=next((r for r in self.catalog.surface_records if r.id==context.surface_profile_id),None)
        material=surface.material_name if surface else None
        family=self.family
        self._set('material',{none:None,**{r.material_name:r.material_name for r in self.catalog.surface_records if r.material_name==material or material_relevant(family,r.material_name,r.name)}},material)
        self._surfaces(context.surface_profile_id)
        if 'service' in self.boxes:
            services={none:None,**{self.tr('engineering.service.'+code):code for code in SERVICES if code}}
            if context.service and context.service not in SERVICES:services[context.service]=context.service
            self._set('service',services,context.service or None)
        self._set('profile',{none:None,**{r.name:r.id for r in self.catalog.profile_records if r.id==context.rule_set_id or profile_relevant(family,r.name)}},context.rule_set_id)
        for name,label in self.labels.items():label.configure(text=self.tr('engineering.select.'+name))
    def _surfaces(self,selected=None):
        material=self.choices['material'].get(self.variables['material'].get())
        choices={self.tr('engineering.none'):None}
        for record in self.catalog.surface_records:
            if record.material_name==material:choices[record.surface_condition.replace('_',' ').title()]=record.id
        self._set('surface',choices,selected)
    def _material_changed(self,event=None):
        self._surfaces()
        # A sole profile is unambiguous, never synthesize a roughness value.
        if len(self.choices['surface'])==2:self.variables['surface'].set(tuple(self.choices['surface'])[1])
    def value(self):
        chosen=lambda name:self.choices[name].get(self.variables[name].get())
        fluid=next((r for r in self.catalog.fluid_records if r.id==chosen('fluid')),None)
        surface=next((r for r in self.catalog.surface_records if r.id==chosen('surface')),None)
        optional={name:chosen(name) or '' for name in ('service','line_type') if name in self.variables}
        if 'strength_material' in self.variables:
            optional['material_id']=chosen('strength_material')
        if 'fluid_temperature_c' in self.variables:
            from engineering.input_parsing import parse_engineering_float
            for name in ('fluid_temperature_c','fluid_salinity_g_kg'):
                text=self.variables[name].get().strip()
                optional[name]=parse_engineering_float(text,field_name=name) if text else None
        return self.context.changed(fluid=ContextReference(id=fluid.id,code=fluid.code,name_tr=fluid.name_tr,name_en=fluid.name_en) if fluid else None,
            surface_profile_id=surface.id if surface else None,rule_set_id=chosen('profile'),**optional)
