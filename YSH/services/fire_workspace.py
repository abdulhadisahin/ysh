"""Live form state and orchestration, independent of widgets and persistence queries."""
from dataclasses import replace

from engineering.fire.enums import FireSourceStatus, FoamMixtureBasis, HWApplicability
from engineering.fire.foam_workflow import FoamWorkflowInput, FoamRawInput
from engineering.fire.hazen_williams_workflow import HazenWilliamsWorkflowInput, HWService
from engineering.fire.provenance import ParameterProvenance
from engineering.fire.units import percent_to_fraction, m3h_to_lpm
from engineering.input_parsing import parse_engineering_float
from engineering.pipe_design.transfer import PipeInputState, PipeInputMode
from engineering.pipe_design.transfer_serialization import pipe_input_to_dict, pipe_input_from_dict
from engineering.provenance import EngineeringValue, SourceReference, SourceType, VerificationStatus, OverridePolicy
from engineering.snapshots.fire import build_fire_snapshot
from engineering.system_context import SystemContext
from engineering.validation import ValidationError, ValidationIssue
from services.fire_foam_service import FoamCalculationService
from services.fire_hazen_williams_service import HazenWilliamsCalculationService, HWApplicabilityBlocked

FOAM_FIELDS = {'protected_area_m2':('fire.foam.area','m²'),
    'application_density_lpm_m2':('fire.foam.density','L/(min·m²)'),
    'application_duration_min':('fire.foam.duration','min'), 'foam_fraction':('fire.ui.concentration','%')}
HW_FIELDS = {'flow_lpm':('fire.hw.flow','L/min'), 'inside_diameter_mm':('fire.hw.diameter','mm'),
    'pipe_length_m':('fire.hw.length','m'), 'hazen_williams_c':('fire.hw.c','1')}


class FireWorkspace:
    """Edits invalidate only live results; saved snapshots are never edited."""
    def __init__(self):
        self.fields = {kind:dict.fromkeys(spec,'') for kind,spec in (('foam',FOAM_FIELDS),('hw',HW_FIELDS))}
        self.metadata = {kind:{name:{'status':('SOURCE_REQUIRED' if name=='hazen_williams_c' else
            'USER_PROJECT_ASSUMPTION'),'document':'','recommended':'','reason':''} for name in spec}
            for kind,spec in (('foam',FOAM_FIELDS),('hw',HW_FIELDS))}
        self.active = 'foam'
        self.service = HWService.UNKNOWN
        self.pipe = PipeInputState()
        self.mode = PipeInputMode.MANUAL
        self.context = SystemContext()
        self.results = {'foam':None,'hw':None}
        self.snapshots = {'foam':None,'hw':None}

    def invalidate(self, kind):
        self.results[kind] = None
        self.snapshots[kind] = None

    def set_field(self, kind, name, value):
        if name not in self.fields[kind] or not isinstance(value,str):raise ValueError('Invalid Fire field')
        self.fields[kind][name] = value
        self.invalidate(kind)

    def set_context(self, context):
        if self.context != context:
            self.context=context
            for kind in self.results:self.invalidate(kind)

    def use_pipe(self, selection, action='link'):
        self.pipe = (self.pipe.update(selection) if action=='update' else
                     self.pipe.keep_current(selection) if action=='keep' else self.pipe.link_to(selection))
        self.mode=PipeInputMode.LINKED
        self._pipe_fields()
        self.invalidate('hw')

    def observe(self, selection):
        observed=self.pipe.observe(selection)
        if observed!=self.pipe:
            self.pipe=observed
            self.invalidate('hw')

    def _pipe_fields(self):
        if self.pipe.snapshot:
            diameter,flow=self.pipe.used_values.hydraulic_values()
            self.fields['hw']['inside_diameter_mm']=repr(diameter)
            self.fields['hw']['flow_lpm']=repr(m3h_to_lpm(flow))

    def _parameter(self, kind, name):
        spec=FOAM_FIELDS if kind=='foam' else HW_FIELDS
        key,unit=spec[name]
        def parse(text):
            value=parse_engineering_float(text,field_name=key,field_key=key)
            return percent_to_fraction(value) if name=='foam_fraction' else value
        value=parse(self.fields[kind][name])
        meta=self.metadata[kind][name]
        recommended=parse(meta['recommended']) if meta['recommended'].strip() else None
        if recommended is not None and value!=recommended and not meta['reason'].strip():
            raise ValidationError(ValidationIssue('fire_override_reason',key))
        evidence=EngineeringValue(used_value=value,unit='1' if name=='foam_fraction' else unit,
            source=SourceReference(source_type=SourceType.PROJECT_CRITERION,
                document=meta['document'] or None,verification_status=VerificationStatus.USER_SUPPLIED),
            override_policy=OverridePolicy.SUGGESTED if recommended is not None else OverridePolicy.USER_INPUT,
            recommended_value=recommended,override_reason=meta['reason'] if recommended is not None and value!=recommended else None)
        return ParameterProvenance(field_name=name,engineering_value=evidence,source_status=FireSourceStatus(meta['status']))

    def calculate(self, kind, *, project_id=None):
        self.invalidate(kind)
        if kind=='foam':
            params={name:self._parameter(kind,name) for name in FOAM_FIELDS}
            raw=parse_engineering_float(self.fields[kind]['foam_fraction'],field_name='fire.ui.concentration',field_key='fire.ui.concentration')
            result=FoamCalculationService().calculate(FoamWorkflowInput(**params,context=self.context,
                mixture_basis=FoamMixtureBasis.CONCENTRATE_VOLUME_PER_SOLUTION_VOLUME,
                raw_inputs=(FoamRawInput(field_name='foam_fraction',value=raw,unit='%'),)))
        else:
            # Explicit service plus captured context; no fuel/seawater alias to water.
            fluid=self.context.fluid.code.upper() if self.context.fluid else ''
            service=(HWService.SEAWATER if fluid in ('SEAWATER','SEA_WATER') else
                     HWService.FUEL if fluid in ('FUEL','OIL','DIESEL') else
                     HWService.UNKNOWN if fluid and fluid not in ('WATER','FRESH_WATER') else self.service)
            applicability={HWService.WATER:HWApplicability.WATER_ONLY,
                HWService.SEAWATER:HWApplicability.SEAWATER_SOURCE_REQUIRED,
                HWService.FUEL:HWApplicability.OTHER_FLUID_SOURCE_REQUIRED}.get(service,HWApplicability.NOT_CONFIGURED)
            draft=HazenWilliamsWorkflowInput(service=service,applicability=applicability)
            if service is not HWService.WATER:raise HWApplicabilityBlocked(draft)
            if self.mode is PipeInputMode.LINKED and self.pipe.snapshot is None:
                raise ValidationError(ValidationIssue('fire_pipe_required','fire.ui.pipe'))
            params={name:self._parameter(kind,name) for name in HW_FIELDS
                    if not (self.mode is PipeInputMode.LINKED and name=='inside_diameter_mm')}
            result=HazenWilliamsCalculationService().calculate(replace(draft,**params,context=self.context,
                pipe_input=self.pipe if self.mode is PipeInputMode.LINKED else None))
        self.results[kind]=result
        self.snapshots[kind]=build_fire_snapshot(result,project_id=project_id)
        return result

    def export_state(self):
        import copy
        return copy.deepcopy({'version':1,'active':self.active,'fields':self.fields,'metadata':self.metadata,
                             'service':self.service.value,'mode':self.mode.value,'pipe':pipe_input_to_dict(self.pipe)})

    @classmethod
    def from_state(cls, state):
        draft=cls()
        if not state:return draft
        if state.get('version')!=1:raise ValueError('Unsupported Fire workspace version')
        if state.get('active') not in ('foam','hw'):raise ValueError('Invalid Fire view')
        for kind,spec in (('foam',FOAM_FIELDS),('hw',HW_FIELDS)):
            for name in spec:
                text=state['fields'][kind][name]
                if not isinstance(text,str):raise ValueError('Invalid Fire text')
                draft.fields[kind][name]=text
                meta=state['metadata'][kind][name]
                if set(meta)!=set(draft.metadata[kind][name]) or not all(isinstance(v,str) for v in meta.values()):
                    raise ValueError('Invalid Fire metadata')
                FireSourceStatus(meta['status'])
                draft.metadata[kind][name]=dict(meta)
        draft.active=state['active'];draft.service=HWService(state['service']);draft.mode=PipeInputMode(state['mode'])
        draft.pipe=pipe_input_from_dict(state['pipe'])
        return draft
