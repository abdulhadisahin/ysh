"""UI/context adapter. Physics remains in pure calculators; applied links are explicit."""
from dataclasses import replace
import json
from engineering.snapshots.serialization import canonical
from engineering.formula.models import FormulaStep,SelectionReason
from services.engineering_value_links import EngineeringValueLink,bind
from engineering.rule_evaluation import evaluate_rule,rule_status,record_payload

FIELD_MAP={'discharge_head_loss':{'kinematic_viscosity':'nu','absolute_roughness':'k'},
           'suction_npsh':{'kinematic_viscosity':'viscosity','absolute_roughness':'roughness','density':'density'}}

class EngineeringContextController:
    def __init__(self,window,catalog):
        self.window=window;self.catalog=catalog;self.links={};self.step_cache={};self.suppress=False
        for module,page in window._pages.items():
            original=page._formula_steps
            page._formula_steps=lambda original=original,module=module:self.explain(module,original())
            if hasattr(page,'_formula_panel'):page._formula_panel._step_provider=page._formula_steps
            page._engineering_rule_provider=lambda velocity,module=module:self.findings(module,velocity)
            for name,key in FIELD_MAP.get(module,{}).items():
                page._fields[key].trace_add('write',lambda *args,module=module,name=name:self.edited(module,name))
            if module in FIELD_MAP and 'kinematic_viscosity' in FIELD_MAP[module]:
                page._viscosity_unit.trace_add('write',lambda *args,module=module:self.edited(module,'kinematic_viscosity'))
            if hasattr(page,'_header'):
                from tkinter import ttk
                label=ttk.Label(page._header,style='Info.TLabel',wraplength=740)
                label.grid(row=2,column=0,sticky='ew');label.grid_remove()
                page._engineering_context_label=label
    def family(self):return self.window._locked_project_family()
    def clear(self):
        self.links={};self.step_cache={}
        for page in self.window._pages.values():page._engineering_context_stale=False
        self.refresh_labels()
    def payload(self):return {'version':1,'stale_modules':[m for m,p in self.window._pages.items() if getattr(p,'_engineering_context_stale',False)],'links':{m:{n:v.payload() for n,v in links.items()} for m,links in self.links.items()}}
    def load(self,payload):
        if payload and payload.get('version')!=1:raise ValueError('Unsupported engineering links')
        self.links={m:{n:EngineeringValueLink.from_payload(v) for n,v in values.items()}
                    for m,values in (payload or {}).get('links',{}).items() if m in FIELD_MAP}
        self.step_cache={}
        for m,p in self.window._pages.items():p._engineering_context_stale=m in (payload or {}).get('stale_modules',())
        self.observe()
    def read(self,module,name):
        page=self.window._pages[module];key=FIELD_MAP[module][name]
        text=page._fields[key].get().strip()
        if not text:return None
        from engineering.input_parsing import parse_engineering_float
        value=parse_engineering_float(text,field_name=name)
        if name=='kinematic_viscosity' and page._viscosity_unit.get()!='cSt':value*=1e6
        return value
    def write(self,module,name,value):
        if value is None:return
        page=self.window._pages[module];self.suppress=True
        try:
            if name=='kinematic_viscosity':page._viscosity_unit.set('cSt')
            if name=='absolute_roughness':
                if module=='discharge_head_loss':page._source_mode='manual';page._source.set(self.window._translate('message.manual_source'));page._set_source_mode()
                else:page._roughness_source_mode='manual';page._roughness_source.set(self.window._translate('message.manual_source'));page._set_roughness_source(reset_value=False)
            page._fields[FIELD_MAP[module][name]].set(str(value))
        finally:self.suppress=False
    def edited(self,module,name):
        if self.suppress or name not in self.links.get(module,{}):return
        try:value=self.read(module,name)
        except ValueError:return
        self.links[module][name]=self.links[module][name].edit(value)
        self.refresh_labels()
    def apply(self,context):
        changed=context!=self.window._system_context
        self.window._apply_system_context(context)
        if changed:
            for page in self.window._pages.values():
                if page._formula_steps():page._engineering_context_stale=True
        references=self.catalog.references(context)
        if self.family()=='fuel':
            for module,mapping in FIELD_MAP.items():
                links=self.links.setdefault(module,{})
                for name in mapping:
                    if name not in references:continue
                    if name in links:
                        links[name]=links[name].observe(references[name]);continue
                    try:current=self.read(module,name)
                    except ValueError:continue
                    links[name]=bind(references[name],current)
                    if current is None:self.write(module,name,links[name].used_value)
        pipe=self.window._pages.get('pipe_design')
        if pipe is not None and context.material_id is not None and not pipe._material.get():
            label=next((label for label,identifier in pipe._material_ids.items() if identifier==context.material_id),None)
            if label and pipe._using_library_source():pipe._material.set(label);pipe._load_selected_material()
        workspace=getattr(self.window,'_fire_workspace',None)
        if self.family()=='fire' and workspace is not None and context.fluid:
            from engineering.fire.hazen_williams_workflow import HWService
            if workspace.model.service is HWService.UNKNOWN and context.fluid.code in ('WATER','FRESH_WATER'):
                workspace.model.service=HWService.WATER
                for view in workspace.views.created.values():view.refresh_texts()
        self.observe();self.window._mark_workspace_dirty()
    def observe(self):
        references=self.catalog.references(self.window._system_context)
        for module,links in self.links.items():
            for name,link in tuple(links.items()):
                links[name]=link.observe(references.get(name))
                if links[name].stale and self.window._pages[module]._formula_steps():self.window._pages[module]._engineering_context_stale=True
        # Compare frozen rule records only; never recalculate historical results.
        for module,page in self.window._pages.items():
            snapshot=getattr(page,'_pdf_snapshot',None)
            if self.rules_changed(snapshot,module):page._engineering_context_stale=True
            if hasattr(page,'_formula_panel'):page._formula_panel.refresh_post_tools()
        workspace=getattr(self.window,'_fire_workspace',None)
        if workspace is not None:
            for kind,snapshot in tuple(workspace.model.snapshots.items()):
                if self.rules_changed(snapshot,kind):
                    workspace.model.invalidate(kind)
                    if kind in workspace.views.created:workspace.views[kind].sync()
        self.refresh_labels()
    def rules_changed(self,snapshot,module):
        if self.family() is None or snapshot is None or not snapshot.formula_steps:return False
        annotation=snapshot.formula_steps[0].engineering_basis_json
        if not annotation:return False
        frozen=json.loads(annotation).get('rules',[])
        captured=[{k:v for k,v in row.items() if k not in ('observed_value','status')} for row in frozen]
        current=[record_payload(r) for r in self.catalog.matching_rules(self.window._system_context,self.family(),module) if r.parameter=='flow_velocity']
        return captured!=current
    def action(self,module,name,action):
        link=self.links[module][name]
        if action=='project':
            if link.stale:raise ValueError('Update the reference before promoting an override')
            if link.used_value is None or link.used_value<0 or (name!='absolute_roughness' and link.used_value==0):raise ValueError('No valid used value')
            context=self.window._system_context
            defaults=json.loads(context.engineering_defaults_json);defaults[link.reference['id']]=link.used_value
            self.apply(context.changed(engineering_defaults_json=canonical(defaults)))
            self.action(module,name,'update')
            return
        result=link.keep() if action=='keep' else link.use_reference() if action=='reference' else link.update()
        self.links[module][name]=result
        if action!='keep':self.write(module,name,result.used_value)
        self.window._mark_workspace_dirty();self.refresh_labels()
    def refresh_labels(self):
        tr=self.window._translate
        for module,page in self.window._pages.items():
            label=getattr(page,'_engineering_context_label',None)
            if label is None:continue
            values=self.links.get(module,{}) if self.family()=='fuel' else {}
            text=' · '.join(tr('engineering.property.'+name)+': '+str(v.used_value)+' '+v.reference.get('unit','')+
                ' ['+tr('engineering.status.'+v.status)+']' for name,v in values.items())
            context=self.window._system_context
            if self.family()=='fuel':
                identity=[]
                if context.fluid:identity.append(context.fluid.name_en if self.window._localization.language=='en' and context.fluid.name_en else context.fluid.name_tr)
                surface=next((r for r in self.catalog.surface_records if r.id==context.surface_profile_id),None)
                profile=next((r for r in self.catalog.profile_records if r.id==context.rule_set_id),None)
                if surface:identity.append(surface.name)
                if profile:identity.append(tr('engineering.profile')+': '+profile.name)
                text=' · '.join(identity)+ ('\n'+text if text else '')
            label.configure(text=text)
            (label.grid if text else label.grid_remove)()
    def findings(self,module,velocity):
        family=self.family()
        if family is None:return None
        rules=self.catalog.matching_rules(self.window._system_context,family,module)
        return tuple(f for rule in rules if rule.parameter=='flow_velocity' for f in evaluate_rule(rule,velocity))
    def explain(self,module,steps):
        cache=self.step_cache.get(module,{})
        return tuple(cache.get(canonical(step),step) for step in steps)
    def freeze(self,snapshot):
        module=snapshot.module_code.value
        if module in self.window._pages:self.window._pages[module]._engineering_context_stale=False
        kind='hw' if module=='fire_hazen_williams' else 'foam'
        context=self.window._system_context
        family=self.family()
        if family is None:return snapshot
        fluid=context.fluid.name_tr if context.fluid else ''
        surface=next((s for s in self.catalog.surface_records if s.id==context.surface_profile_id),None)
        payload={'fluid':fluid,'material':surface.name if surface else '', 'service':context.service,
                 'line_type':{'discharge_head_loss':'DELIVERY','suction_npsh':'SUCTION'}.get(module,context.line_type),'values':[], 'rules':[]}
        for name,link in self.links.get(module,{}).items():
            # Already applied inputs, never substitute defaults while capturing.
            item=link.payload();item['status']=link.status
            payload['values'].append(item)
        evidence=snapshot.evidence;velocity=None
        if module=='pipe_design':
            variable=next((v for step in snapshot.formula_steps for v in step.variables if v.symbol=='V'),None)
            velocity=variable.value if variable else None
        else:
            variable=next((step for step in snapshot.formula_steps if step.result_symbol=='V'),None)
            if variable:velocity=variable.result_value
        if module=='fire_hazen_williams':
            from engineering.pipe_design.selection import actual_velocity
            from engineering.fire.units import lpm_to_m3h
            values=evidence['facts']['fire']['normalized_inputs']
            velocity=actual_velocity(lpm_to_m3h(values['flow_lpm']),values['inside_diameter_mm'])
        roles={'fire_hazen_williams':'hw','fire_foam_system':'foam'}
        rules=self.catalog.matching_rules(context,family,roles.get(module,module))
        findings=[]
        for rule in rules:
            if rule.parameter=='flow_velocity' and velocity is not None:
                record=record_payload(rule);record.update(observed_value=velocity,status=rule_status(rule,velocity));payload['rules'].append(record)
                findings.extend(evaluate_rule(rule,velocity))
        from engineering.warning_rules import EngineeringFinding,WarningSeverity
        for item in payload['values']:
            link_status=item['status']
            if link_status not in ('SOURCE_REQUIRED','STALE'):continue
            name=item['reference']['property_name']
            findings.append(EngineeringFinding(code='engineering.value.'+name,severity=WarningSeverity.ENGINEERING_WARNING,
                message_key='engineering.value_issue',actual_value=item['used_value'],lower_bound=None,upper_bound=None,
                unit=item['reference']['unit'],source_id=None,context={'property':name,'status':link_status},visual_status=link_status))
        # Existing page findings and records remain frozen. Only new distinct rules are appended.
        old=evidence.get('findings',[])
        codes={item['code'] for item in old}
        evidence['findings']=old+[record_payload(f) for f in findings if f.code not in codes]
        steps=snapshot.formula_steps
        symbols={'kinematic_viscosity':'ν','absolute_roughness':'k','density':'ρ'}
        variables={v.symbol:v for step in steps for v in step.variables}
        for item in payload['values']:
            name=item['reference']['property_name'];variable=variables.get(symbols.get(name))
            if variable is not None:
                actual=variable.value*1e6 if name=='kinematic_viscosity' and variable.unit=='m²/s' else variable.value
                item['used_value']=actual
                default=item['reference'].get('default_value')
                if item['status'] not in ('STALE','SOURCE_REQUIRED'):
                    item['status']='OVERRIDE' if default is not None and actual!=default else 'LINKED'
        annotation=canonical(payload)
        from engineering.provenance import EngineeringValue,SourceReference,SourceType,VerificationStatus,OverridePolicy
        enriched=[]
        for index,step in enumerate(steps):
            updates={};used=list(step.used_values)
            for item in payload['values']:
                reference=item['reference'];name=reference['property_name'];variable=next((v for v in step.variables if v.symbol==symbols.get(name)),None)
                if variable is None:continue
                source=SourceReference(source_type=SourceType.MATERIAL_STANDARD if name=='absolute_roughness' else SourceType.FLUID_LIBRARY,
                    source_organization=reference.get('source_authority') or None,document=reference.get('source_document') or None,
                    revision=reference.get('source_edition') or None,
                    verification_status=VerificationStatus.VERIFIED if reference.get('verification')=='VERIFIED' else VerificationStatus.USER_SUPPLIED if reference.get('verification')=='RECOMMENDATION' else VerificationStatus.UNVERIFIED,
                    notes=reference.get('source_note') or None)
                updates[variable.symbol]=replace(variable,source=source,reason=SelectionReason.MATERIAL_LIBRARY if name=='absolute_roughness' else variable.reason)
                default=reference.get('default_value')
                if default is not None and name=='kinematic_viscosity' and variable.unit=='m²/s':default*=1e-6
                evidence_value=EngineeringValue(used_value=variable.value,unit=variable.unit,source=source,
                    override_policy=OverridePolicy.SUGGESTED if default is not None else OverridePolicy.USER_INPUT,
                    recommended_value=default,symbol=variable.symbol,terminology_key=variable.terminology_key,
                    override_reason='Calculation-only manual override' if default is not None and variable.value!=default else None)
                used=[v for v in used if v.symbol!=variable.symbol]+[evidence_value]
            annotated=replace(step,variables=tuple(updates.get(v.symbol,v) for v in step.variables),used_values=tuple(used),
                engineering_basis_json=annotation if index==0 else step.engineering_basis_json)
            enriched.append(annotated);self.step_cache.setdefault(module,{})[canonical(step)]=annotated
        evidence['steps']=enriched
        if module.startswith('fire_'):
            workspace=self.window._fire_workspace
            if not hasattr(workspace,'_engineering_findings'):workspace._engineering_findings={}
            workspace._engineering_findings[kind]=tuple(findings)
            for view_kind,view in workspace.views.created.items():
                view.formula._step_provider=lambda view_kind=view_kind,workspace=workspace:workspace.model.snapshots[view_kind].formula_steps if workspace.model.snapshots[view_kind] else ()
        return replace(snapshot,evidence_json=canonical(evidence))
