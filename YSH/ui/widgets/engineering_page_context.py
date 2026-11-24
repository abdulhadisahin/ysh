"""Compact project-linked engineering identity; overrides require an explicit action."""
from tkinter import ttk

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
        self.bind('<Configure>',self._fit)
    def _fit(self,event):
        for widget in (self.surface,self.summary,self.rules):widget.configure(wraplength=max(240,event.width-10))
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
