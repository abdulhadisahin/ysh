"""Compact project-linked engineering identity; overrides require an explicit action."""
import tkinter as tk
from tkinter import ttk, messagebox
from i18n.catalog_text import catalog_text

def rule_summary(rule,tr):
    """Present recorded limits and sources without inferring missing metadata."""
    lo,hi=(rule.hard_min,rule.hard_max) if rule.rule_nature=='HARD_LIMIT' else (rule.recommended_min,rule.recommended_max)
    bounds=('≥ '+str(lo) if lo is not None else '')+(' · ' if lo is not None and hi is not None else '')+('≤ '+str(hi) if hi is not None else '')
    source=' · '.join(value for value in (rule.source_authority,rule.source_document,rule.source_edition,rule.source_clause) if value)
    scope=tr('engineering.scope.'+rule.applicability) if rule.applicability else tr('engineering.scope_unrecorded')
    if rule.applicability and scope=='engineering.scope.'+rule.applicability:scope=rule.applicability
    from engineering.source_verification import record_evidence,evidence_rows
    proof=record_evidence(rule)
    metadata='\n'+' · '.join(label+': '+value for label,value in evidence_rows(proof.payload(),tr)) if proof else ''
    return (rule.name+': '+bounds+' '+rule.unit+' · '+tr('engineering.nature.'+rule.rule_nature)+'\n'+
            tr('engineering.source')+': '+(source or tr('engineering.status.SOURCE_REQUIRED'))+' · '+scope+' · '+
            tr('engineering.verification.'+rule.verification)+metadata)

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
        self.rules=ttk.Label(self,style='Info.TLabel',wraplength=650)
        self.rules.grid(row=4,column=0,columnspan=3,sticky='ew')
        if module in ('discharge_head_loss','suction_npsh'):
            self._build_fluid_controls()
        self.bind('<Configure>',self._fit)

    def _build_fluid_controls(self):
        from ui.widgets.numeric_input import numeric_entry
        self.fluid_box.configure(state='readonly')
        self.operating=ttk.Frame(self);self.operating.grid(row=5,column=0,columnspan=3,sticky='ew')
        self.conditions={name:tk.StringVar(self) for name in ('temperature','salinity','pressure')}
        self._loading_conditions=False;self._shown_context=None
        for variable in self.conditions.values():variable.trace_add('write',self._draft_changed)
        self.fluid_box.bind('<<ComboboxSelected>>',self._draft_changed)
        self.controller.window._pages[self.module]._fluid_preflight=self._apply_fluid
        self.condition_labels={};self.condition_entries={}
        for row,name in enumerate(self.conditions):
            label=ttk.Label(self.operating);label.grid(row=row,column=0,sticky='w')
            entry=numeric_entry(self.operating,textvariable=self.conditions[name]);entry.grid(row=row,column=1,sticky='w',padx=6,pady=2)
            self.condition_labels[name]=label;self.condition_entries[name]=entry
        self.atmosphere=ttk.Button(self.operating,command=lambda:self.conditions['pressure'].set('0.101325'))
        self.atmosphere.grid(row=2,column=2,sticky='w')
        self.apply_fluid=ttk.Button(self.operating,command=self._apply_fluid);self.apply_fluid.grid(row=0,column=2,sticky='w')
        self.project_fluid=ttk.Button(self.operating,command=self._project_fluid);self.project_fluid.grid(row=1,column=2,sticky='w')
        if self.module=='discharge_head_loss':
            self.density_label=ttk.Label(self.operating);self.density_label.grid(row=3,column=0,sticky='w')
            numeric_entry(self.operating,textvariable=self.controller.window._pages[self.module]._fields['fluid_density']).grid(row=3,column=1,sticky='w',padx=6)
        self.guidance=ttk.Label(self.operating,style='Info.TLabel',wraplength=620);self.guidance.grid(row=4,column=0,columnspan=3,sticky='w')
        self.fluid_actions=ttk.Frame(self.operating);self.fluid_actions.grid(row=5,column=0,columnspan=3,sticky='w')
        self.update_fluid=ttk.Button(self.fluid_actions,command=lambda:self._link_action('update'));self.update_fluid.pack(side='left')
        self.keep_fluid=ttk.Button(self.fluid_actions,command=lambda:self._link_action('keep'));self.keep_fluid.pack(side='left',padx=6)

    def _link_action(self,action):
        for name in ('density','kinematic_viscosity'):
            link=self.controller.links.get(self.module,{}).get(name)
            if link and link.stale:self.controller.action(self.module,name,action)

    def _project_fluid(self):
        self.controller.use_project_fluid(self.module)

    def _apply_fluid(self):
        from engineering.input_parsing import parse_engineering_float
        try:
            if not self.controller.family():return True
            values={k:parse_engineering_float(v.get(),field_name=k) if v.get().strip() else None for k,v in self.conditions.items()}
            if self.controller.context_for(self.module).fluid is None and self.fluid_box.get() not in self.fluid_choices and not any(v is not None for v in values.values()):
                # Legacy manual calculations need no invented fluid identity.
                if self.module not in self.controller.hydraulic_modules:
                    self.controller.hydraulic_modules.add(self.module)
                    self.controller._apply_module_context(self.module,fluid_only=True)
                return True
            self.controller.select_fluid(self.module,self.fluid_choices.get(self.fluid_box.get()),values['temperature'],values['salinity'],values['pressure'])
            return True
        except ValueError:
            tr=self.controller.window._translate
            messagebox.showerror(tr('engineering.context_title'),tr('engineering.action_unavailable'),parent=self)
            return False

    def _draft_changed(self,*_args):
        if self._loading_conditions:return
        page=self.controller.window._pages[self.module]
        pressure=getattr(page,'_pressure_panel',None)
        if pressure is not None:pressure.clear()
        page._engineering_context_stale=True
        if hasattr(page,'_formula_panel'):page._formula_panel.refresh_post_tools()
        self.controller.window._mark_workspace_dirty()
    def _fit(self,event):
        for widget in (self.surface,self.summary,self.rules):widget.configure(wraplength=max(240,event.width-10))
    def refresh(self,text):
        c=self.controller;tr=c.window._translate;context=c.context_for(self.module)
        surface=next((r for r in c.catalog.surface_records if r.id==context.surface_profile_id),None)
        self.fluid_label.configure(text=tr('engineering.select.fluid'))
        self.material_label.configure(text=tr('engineering.select.material'))
        fluids=c.catalog.project_fluids(c.family()) if hasattr(self,'operating') else c.catalog.fluid_records
        self.fluid_choices={catalog_text(tr,r.name_tr)+' · '+r.code:r.id for r in fluids}
        self.fluid_box.configure(values=tuple(self.fluid_choices),state='readonly' if hasattr(self,'operating') and c.family() else 'disabled')
        self.material_box.configure(values=tuple(dict.fromkeys(r.material_name for r in c.catalog.surface_records)))
        changed=not hasattr(self,'operating') or self._shown_context!=context
        if changed:self.fluid_box.set(next((label for label,identifier in self.fluid_choices.items() if identifier==context.fluid_id),context.fluid.name_tr if context.fluid else tr('engineering.none')))
        if hasattr(self,'operating'):
            self._loading_conditions=True
            for name,key in (('temperature','fluid_temperature_c'),('salinity','fluid_salinity_g_kg'),('pressure','fluid_reference_pressure_mpa')):
                value=getattr(context,key)
                if changed:self.conditions[name].set('' if value is None else str(value))
                self.condition_labels[name].configure(text=tr('hydro.fluid.'+name))
            for widget in (self.condition_labels['salinity'],self.condition_entries['salinity']):
                (widget.grid if c.family()=='seawater' else widget.grid_remove)()
            self.apply_fluid.configure(text=tr('hydro.fluid.apply'),state='normal' if c.family() else 'disabled')
            self.project_fluid.configure(text=tr('engineering.use_project'))
            self.atmosphere.configure(text=tr('hydro.fluid.atmosphere'))
            self.guidance.configure(text=tr('hydro.fluid.notice'))
            self.update_fluid.configure(text=tr('engineering.action.update'));self.keep_fluid.configure(text=tr('engineering.action.keep'))
            stale=any(link.stale for name,link in c.links.get(self.module,{}).items() if name in ('density','kinematic_viscosity'))
            (self.fluid_actions.grid if stale else self.fluid_actions.grid_remove)()
            if self.module=='discharge_head_loss':self.density_label.configure(text=tr('hydro.fluid.density_reference'))
            self._loading_conditions=False;self._shown_context=context
        self.material_box.set(surface.material_name if surface else tr('engineering.none'))
        state=tr('engineering.status.OVERRIDE') if self.module in c.module_contexts else tr('engineering.status.LINKED') if context.fluid or surface else tr('engineering.status.MANUAL')
        surface_text=''
        if surface:
            epsilon=str(surface.roughness_mm)+' mm' if surface.roughness_mm is not None else tr('engineering.status.SOURCE_REQUIRED')
            surface_text=tr('engineering.select.surface')+': '+surface.surface_condition.replace('_',' ').title()+' · ε: '+epsilon+' · '
        self.surface.configure(text=surface_text+state)
        if self.module=='discharge_head_loss':
            density=c.catalog.hydraulic_references(context).get('density')
            pressure=getattr(c.window._pages[self.module],'_pressure_panel',None)
            if pressure is not None:
                pressure.observe_fluid((context.fluid_id,context.fluid_temperature_c,context.fluid_salinity_g_kg,context.fluid_reference_pressure_mpa))
            if density:
                value=density.get('default_value')
                shown=str(value)+' '+density['unit'] if value is not None else tr('engineering.status.SOURCE_REQUIRED')
                temperature=density.get('reference_temperature_c')
                if temperature is not None:shown+=' @ '+str(temperature)+' °C'
                text=tr('engineering.density_reference')+': '+shown+'\n'+text
        self.summary.configure(text=text)
        line={'discharge_head_loss':'DELIVERY','suction_npsh':'SUCTION'}.get(self.module)
        if line or c.family()=='seawater':
            details=[tr('engineering.module_line',line=tr('engineering.line.'+line))] if line else []
            if c.family():
                for rule in c.catalog.matching_rules(context,c.family(),self.module):
                    if rule.verification!='SOURCE_REQUIRED' and any(v is not None for v in (
                        rule.hard_min,rule.hard_max,rule.recommended_min,rule.recommended_max)):
                        details.append(rule_summary(rule,tr))
            self.rules.configure(text='\n'.join(details));self.rules.grid()
        else:self.rules.grid_remove()
        self.project_button.configure(text=tr('engineering.edit_project'),state='normal' if c.family() else 'disabled')
        self.override_button.configure(text=tr('engineering.edit_module'))
