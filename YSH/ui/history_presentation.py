"""Detached, display-only historical summaries. Never resolves live engineering data."""
from ui.widgets.formula_steps import number
from engineering.fire.units import fraction_to_percent

MODULE_LABELS={'pipe_design':'page.pipe.tab','transfer_pump':'page.transfer.tab',
               'discharge_head_loss':'page.discharge.tab','suction_npsh':'page.suction.tab',
               'fire_foam_system':'fire.history.foam','fire_hazen_williams':'fire.history.hw'}
PRIMARY={'pipe_design':('s','D','Di'),'transfer_pump':('Qgerekli','Qpump','ttransfer'),
         'discharge_head_loss':('Hs',),'suction_npsh':('ENPYm','he'),
         'fire_foam_system':('Vfoam',),'fire_hazen_williams':('ΔpHW',)}


def stage_label(stage: str, translate) -> str:
    return translate('history.stage.'+stage) if stage in (
        'diameter','wall','selection','hydraulics','enpy','design','empirical') else '—'


def scalar(value: object) -> str:
    """Show absent optional metadata safely; retain zero and recorded text."""
    if value is None or value=='' or value=={} or value==[]: return '—'
    return number(value) if isinstance(value,(int,float)) and not isinstance(value,bool) else str(value)


def result_text(value: dict) -> str:
    return f"{value.get('symbol','')} = {scalar(value.get('value'))} {value.get('unit') or ''}".strip()


def context_names(evidence: dict, language: str = 'tr') -> tuple[str,str,str]:
    context=evidence.get('context') or {}
    def label(key):
        ref=context.get(key) or {}
        return (ref.get('name_en') or ref.get('name_tr') or '—') if language=='en' else (ref.get('name_tr') or '—')
    return tuple(label(key) for key in ('system','circuit','fluid'))


def summary_values(evidence: dict) -> tuple[dict,...]:
    return tuple(v for v in evidence.get('summary',()) if isinstance(v,dict) and v.get('value') is not None)


def primary_result(module: str, evidence: dict) -> str:
    values=summary_values(evidence)
    selected=next((v for symbol in PRIMARY.get(module,()) for v in values if v.get('symbol')==symbol),None)
    return result_text(selected or values[0]) if values else '—'


def recorded_checks(evidence: dict) -> tuple[dict,...]:
    return tuple(step['check'] for step in evidence.get('steps',()) if isinstance(step,dict) and step.get('check'))


def recorded_warnings(evidence: dict) -> tuple[dict,...]:
    """Collect existing warnings only, without calling today's warning rules."""
    warnings=list(evidence.get('findings') or ())
    for value in (evidence.get('facts') or {}).values():
        if isinstance(value,dict):
            for warning in value.get('warnings') or ():
                if isinstance(warning,dict) and warning not in warnings:warnings.append(warning)
                elif isinstance(warning,str) and warning:
                    item={'recorded_text':warning}
                    if item not in warnings:warnings.append(item)
    return tuple(warnings)


def recorded_state(evidence: dict, translate) -> str:
    states=tuple(dict.fromkeys(check['status'] for check in recorded_checks(evidence) if check.get('status')))
    return ' · '.join(translate('formula2.check.'+status) for status in states) or (
        translate('history.visual.stored_warning') if recorded_warnings(evidence) else '—')


def recorded_sources(evidence: dict) -> tuple[dict,...]:
    sources=[]
    for step in evidence.get('steps',()):
        candidates=list(step.get('sources') or ())
        candidates += [v.get('source') for name in ('variables','used_values') for v in step.get(name,()) if v.get('source')]
        if (step.get('check') or {}).get('source'): candidates.append(step['check']['source'])
        for source in candidates:
            if source and source not in sources: sources.append(source)
    return tuple(sources)


def frozen_pipe(evidence: dict) -> tuple[tuple[str,object],...]:
    """Read only applied pipe metadata serialized at calculation time."""
    facts=evidence.get('facts') or {}
    fire_pipe=(facts.get('fire') or {}).get('pipe_selection')
    if fire_pipe:
        return tuple((key,value) for key,value in (
            ('mode',fire_pipe.get('mode')),('status',fire_pipe.get('status')),
            ('revision',fire_pipe.get('source_revision'))) if value is not None)
    pipe=next((value.get('pipe_input') for name in ('input','hydraulic_input')
               if isinstance(value:=facts.get(name),dict) and value.get('pipe_input')),None)
    if not pipe: return ()
    snapshot=pipe.get('snapshot') or {}
    return tuple((key,value) for key,value in (
        ('mode',pipe.get('mode')),('status',pipe.get('status')),
        ('revision',snapshot.get('source_revision'))) if value is not None)


def timestamp(value) -> str:
    """Retain the prior local-time conversion and expose its UTC offset explicitly."""
    local=value.astimezone()
    return local.strftime('%d.%m.%Y · %H:%M:%S %z')


def fire_details(evidence: dict, translate) -> tuple[str,...]:
    """Explicit historical Fire details; never infer values from current context."""
    fire=(evidence.get('facts') or {}).get('fire') or {}
    if not fire:return ()
    labels={'protected_area_m2':'fire.foam.area','application_density_lpm_m2':'fire.foam.density',
            'application_duration_min':'fire.foam.duration','foam_fraction':'fire.foam.fraction',
            'flow_lpm':'fire.hw.flow','inside_diameter_mm':'fire.hw.diameter',
            'pipe_length_m':'fire.hw.length','hazen_williams_c':'fire.hw.c'}
    rows=[]
    for key,value in (fire.get('normalized_inputs') or {}).items():
        if key in labels and value is not None:
            if key=='foam_fraction' and (fire.get('input_units') or {}).get(key)=='1':
                rows.append(f"{translate('fire.ui.concentration')}: {scalar(fraction_to_percent(value))} %")
                continue
            rows.append(f"{translate(labels[key])}: {scalar(value)} {(fire.get('input_units') or {}).get(key,'')}")
    for key in ('mixture_basis','service','applicability','source_readiness'):
        if fire.get(key):
            value=translate('fire.value.'+fire[key])
            rows.append(translate('fire.record.'+key)+': '+value)
    for item in fire.get('provenance') or ():
        if item.get('field_name') in labels and item.get('source_status'):
            rows.append(translate(labels[item['field_name']])+': '+translate('fire.ui.source.'+item['source_status']))
    return tuple(rows)


def historical_override_values(module: str, value: dict) -> tuple[str,str]:
    """Format saved recommendation/used independently of current form settings."""
    def display(number):
        if module=='fire_foam_system' and value.get('symbol')=='Cfoam' and value.get('unit')=='1' and number is not None:
            return scalar(fraction_to_percent(number))+' %'
        return scalar(number)
    return display(value.get('recommended_value')),display(value.get('used_value'))
