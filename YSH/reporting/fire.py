"""Explicit Fire report rows from stored primitives; no workflow imports or execution."""
from dataclasses import replace

from reporting.models import ReportField, _TR
from engineering.fire.units import fraction_to_percent

INPUT_LABELS = {
    'protected_area_m2':('fire.foam.area','A'),
    'application_density_lpm_m2':('fire.foam.density','q'),
    'application_duration_min':('fire.foam.duration','t'),
    'foam_fraction':('fire.foam.fraction','Cfoam'),
    'flow_lpm':('fire.hw.flow','Q'), 'inside_diameter_mm':('fire.hw.diameter','Di'),
    'pipe_length_m':('fire.hw.length','L'), 'hazen_williams_c':('fire.hw.c','CHW'),
}


def enrich_fire_report(snapshot, report):
    """Use stable whitelists; missing optional fields simply produce no extra row."""
    payload = snapshot.evidence['facts'].get('fire') or {}
    inputs = tuple(ReportField(_TR(INPUT_LABELS[name][0]), INPUT_LABELS[name][1], value,
                              (payload.get('input_units') or {}).get(name,''))
                   for name,value in (payload.get('normalized_inputs') or {}).items()
                   if name in INPUT_LABELS and isinstance(value,(int,float)))
    def percent_row(row):
        if row.symbol=='Cfoam' and row.unit=='1' and isinstance(row.value,(int,float)):
            return replace(row, value=fraction_to_percent(row.value), unit='%',
                label=_TR('fire.ui.concentration') if row.label==_TR('fire.foam.fraction') else row.label)
        return row
    inputs=tuple(percent_row(row) for row in inputs)
    rows = list(report.selections)
    rows = [percent_row(row) for row in rows]
    for key in ('mixture_basis','service','applicability','source_readiness','status'):
        if payload.get(key) is not None:
            value = payload[key]
            rows.append(ReportField(_TR('fire.record.'+key), '', _TR('fire.value.'+value)))
    pipe = payload.get('pipe_selection') or {}
    for key in ('mode','status','source_selection_id','source_revision','observed_revision','kept_current'):
        value = pipe.get(key)
        if value is not None:
            display = _TR('fire.value.'+value) if key in ('mode','status') else value
            rows.append(ReportField(_TR('fire.pipe.'+key), '', display))
    values = pipe.get('values') or {}
    if values.get('pipe_id'):
        rows.append(ReportField(_TR('fire.pipe.pipe_id'), '', values['pipe_id']))
    for item in payload.get('provenance') or ():
        name = item.get('field_name')
        if name in INPUT_LABELS and item.get('source_status'):
            rows.append(ReportField(_TR('fire.record.source_status'), INPUT_LABELS[name][1],
                                   item['source_status']))
    warnings = list(report.warnings)
    for warning in payload.get('warnings') or ():
        if warning.get('message_key'):
            warnings.append(_TR(warning['message_key'])+' · '+warning.get('source_status',''))
    identification = tuple(replace(row, value=_TR('fire.calculation.'+snapshot.module_code.value))
                           if row.value == snapshot.stage.upper() else row
                           for row in report.identification) + (
        ReportField(_TR('fire.record.system'), '', _TR('fire.system')),
        ReportField(_TR('fire.record.calculation'), '', _TR('fire.calculation.'+snapshot.module_code.value)),)
    results = tuple(ReportField(_TR('fire.foam.required_volume') if row.get('key')=='foam_concentrate_volume_l'
                                else _TR(row.get('label_key','formula2.result')),
                                row.get('symbol',''), row['value'], row.get('unit',''))
                    for row in payload.get('summary') or ()
                    if row.get('value') is not None and row.get('key') in (payload.get('results') or {}))
    metadata = list(report.metadata)
    for key in ('workflow_version','case_id','revision'):
        if payload.get(key) is not None:
            metadata.append(ReportField(_TR('fire.record.'+key), '', payload[key]))
    if payload.get('rule_ids'):
        metadata.append(ReportField(_TR('fire.record.rule_ids'), '', ', '.join(payload['rule_ids'])))
    return replace(report, inputs=inputs or report.inputs, results=results or report.results,
        identification=identification, selections=tuple(dict.fromkeys(rows)),
        warnings=tuple(dict.fromkeys(warnings)), metadata=tuple(metadata))
