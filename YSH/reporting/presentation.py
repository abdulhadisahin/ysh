"""Frozen report hierarchy/provenance mapping; never evaluate engineering rules."""
from dataclasses import replace
from i18n.translator import Translator
from i18n.validation import render_validation_issue
from engineering.validation import ValidationIssue
from reporting.context import snapshot_family
from reporting.models import ReportField, ReportWarning, format_number

LABEL_KEYS = {'Tarih / saat': 'date', 'Snapshot kimliği': 'snapshot', 'Hesap türü': 'stage', 'Proje kimliği': 'project_id', 'Sistem': 'system', 'Devre': 'circuit', 'Akışkan': 'fluid', 'Bağlı boru seçimi': 'linked_pipe', 'Kaynak / doğrulama': 'source_verification', 'Kullanılan değer': 'used', 'Önerilen değer': 'recommended', 'Seçim gerekçesi': 'selection_reason', 'Override gerekçesi': 'override_reason', 'Seçim dayanağı': 'basis', 'Bükme durumu': 'bend', 'Bükme yarıçapı': 'bend_radius', 'Anma çapı': 'nominal', 'Boru standardı': 'standard', 'Boru dış çapı': 'outside', 'Seçilen et kalınlığı': 'selected_wall', 'Boru girdi modu': 'input_mode', 'Mevcut değerler korundu': 'kept', 'Kaynak boru seçimi UUID': 'source_uuid', 'Kaynak boru revizyonu': 'source_revision', 'Gözlenen revizyon': 'observed_revision', 'Boru seçimi UUID': 'selection_uuid', 'Boru seçimi revizyonu': 'selection_revision', 'Kayıt durumu': 'record_status', 'Kaynak boru uygunluk durumu': 'upstream_status', 'Malzeme kimliği': 'material_id', 'Malzeme': 'material', 'Malzeme standardı': 'material_standard', 'Malzeme kaynağı': 'material_source', 'Snapshot şeması': 'schema', 'Hesap modeli': 'model', 'Bağlam revizyonu': 'context_revision', 'Doküman': 'document', 'Notlar': 'notes', 'Hesap / kapasite modu': 'capacity_mode'}


def finalize_report(snapshot, report, language):
    tr = Translator(language).translate
    evidence = snapshot.evidence
    fire = evidence['facts'].get('fire') or {}
    context = evidence.get('report_context') or {}
    family = snapshot_family(snapshot)
    if context.get('system_family', family) != family:
        raise ValueError('Frozen report family and calculation module differ')
    warnings = []
    stale = False
    def notice(severity, message, field=''):
        row = ReportWarning(severity, message, field or report.module)
        if row not in warnings:
            warnings.append(row)
    def walk(node, path=''):
        nonlocal stale
        if isinstance(node, dict):
            status = node.get('status')
            if isinstance(status, str) and status.startswith('LINKED_') and status != 'LINKED_SYNCED':
                stale = True
                notice('STALE', tr('discharge.pipe.status.' + status))
            if status in ('SOURCE_REQUIRED','RULE_NOT_CONFIGURED','BLOCKED_APPLICABILITY'):
                notice({'SOURCE_REQUIRED':'SOURCE_REQUIRED','RULE_NOT_CONFIGURED':'INFO','BLOCKED_APPLICABILITY':'BLOCKED'}[status],
                       tr('report.source_required') if status == 'SOURCE_REQUIRED' else tr('formula2.check.NOT_CONFIGURED'))
            if 'message_key' in node:
                key = node['message_key']
                args = dict(node.get('context') or {})
                if node.get('code') == 'd243.pipe.velocity_max':
                    args['limit'] = format_number(node['upper_bound']).replace(',', '.') if language == 'en' else format_number(node['upper_bound'])
                elif str(node.get('code','')).startswith('velocity.'):
                    args.update(fluid=args.get('system',''), role=args.get('line_role',''),
                                relation=tr('warning.relation.below' if node.get('lower_bound') is not None and node.get('actual_value') is not None and node['actual_value'] < node['lower_bound'] else 'warning.relation.above'))
                try:
                    message = tr(key, **args)
                except (KeyError, ValueError):
                    message = tr('report.recorded_warning')
                severity = node.get('category') or node.get('severity') or 'INFO'
                severity = {'ENGINEERING_WARNING':'WARNING','CRITICAL_WARNING':'WARNING',
                            'SOURCE_CONTEXT_REQUIRED':'SOURCE_REQUIRED'}.get(severity,severity)
                if severity not in ('INFO','WARNING','STALE','SOURCE_REQUIRED','ERROR','BLOCKED'):
                    severity = 'INFO'
                name = node.get('field_name','')
                from reporting.fire import INPUT_LABELS
                label = tr(INPUT_LABELS[name][0]) if name in INPUT_LABELS else report.module
                notice(severity, message, label)
            if {'code','field_key','params'} <= node.keys():
                try:
                    notice('ERROR' if 'errors' in path else 'WARNING',
                           render_validation_issue(ValidationIssue(**node), Translator(language)))
                except (KeyError, TypeError):
                    pass
            for name,value in node.items(): walk(value, path+'.'+name)
        elif isinstance(node, list):
            for value in node: walk(value, path)
    walk(evidence.get('findings', []), 'findings')
    walk(evidence['facts'], 'facts')
    for step in report.formulas:
        check = step.check
        if check:
            severity = {'PASS':'INFO','WARNING':'WARNING','FAIL':'ERROR',
                        'NOT_APPLICABLE':'INFO','NOT_CONFIGURED':'INFO'}[check.status.value]
            message = step.result_symbol + ': ' + tr('formula2.check.'+check.status.value)
            if check.reason_key: message += ' - ' + tr(check.reason_key)
            if check.actual_value is not None and check.reference_value is not None:
                actual = format_number(check.actual_value)
                reference = format_number(check.reference_value)
                if language == 'en': actual, reference = actual.replace(',','.'), reference.replace(',','.')
                message += f' ({actual} {check.operator or ""} {reference})'
            notice(severity, message)
    def origin(variable):
        parts = []
        reason = variable.reason.value if variable.reason else None
        source = variable.source
        if source is None:
            recorded = next((value for step in report.formulas for value in step.used_values
                if value.symbol==variable.symbol and value.used_value==variable.value and value.unit==variable.unit),None)
            if recorded is not None: source = recorded.source
        if variable.source_selection_id or reason == 'LINKED_PIPE_SELECTION':
            parts.append(tr('source.state.linked'))
            if stale: parts.append(tr('source.state.stale'))
        elif reason == 'MATERIAL_LIBRARY' or source and source.source_type.value == 'FLUID_LIBRARY':
            parts.append(tr('source.state.library'))
        elif reason == 'USER_INPUT' or source and source.source_type.value == 'USER_INPUT':
            parts.append(tr('source.state.manual'))
        elif source:
            parts.append(tr('formula2.source_type.'+source.source_type.value))
        if source and source.verification_status is not None and source.verification_status.value == 'UNVERIFIED':
            parts.append(tr('report.source_required'))
        for step in report.formulas:
            for used in step.used_values:
                if used.symbol == variable.symbol and used.used_value == variable.value and used.override_reason:
                    parts.append(tr('source.state.override'))
        return ' - '.join(dict.fromkeys(parts)) or tr('report.not_recorded')
    origins = {}
    for step in report.formulas:
        for variable in step.variables + step.reference_variables:
            label = (variable.context+' · ' if variable.context else '') + tr(variable.terminology_key)
            origins[(label,variable.symbol,variable.value,variable.unit)] = origin(variable)
    fire_provenance = {item['field_name']:item for item in fire.get('provenance',())}
    from reporting.fire import INPUT_LABELS
    by_symbol = {value[1]: name for name,value in INPUT_LABELS.items()}
    def field(row):
        source = row.source or origins.get((row.label,row.symbol,row.value,row.unit),'')
        item = fire_provenance.get(by_symbol.get(row.symbol)) if fire else None
        if item:
            value = item.get('engineering_value') or {}
            status = item.get('source_status')
            source = tr('report.source_required') if status == 'SOURCE_REQUIRED' else (
                tr('source.state.library') if by_symbol.get(row.symbol) in (fire.get('library_inputs') or {}) else
                tr('source.state.linked') if by_symbol.get(row.symbol) == 'inside_diameter_mm' and
                (fire.get('pipe_selection') or {}).get('mode') == 'LINKED' else tr('source.state.manual')
                if status == 'USER_PROJECT_ASSUMPTION' else tr('fire.ui.source.'+status))
            if value.get('override_reason'): source += ' - '+tr('source.state.override')
        label = tr('report.field.'+LABEL_KEYS[row.label]) if row.label in LABEL_KEYS else row.label
        value = snapshot.created_at.strftime('%Y-%m-%d %H:%M %z') if row.label=='Tarih / saat' else row.value
        return replace(row, label=label, source=source, value=value)
    inputs = tuple(field(row) for row in report.inputs)
    computed = {(step.result_symbol,step.result_value,step.result_unit) for step in report.formulas}
    inputs = tuple(row for row in inputs if not ((row.symbol,row.value,row.unit) in computed
        and row.source in ('',tr('report.not_recorded'),tr('formula2.source_type.CALCULATED'))))
    results = tuple(field(row) for row in report.results)
    step_ids = {'pipe_design': ('pipe.wall','pipe.D'),
                'discharge_head_loss': ('discharge.Hs',),
                'suction_npsh': ('suction.ENPYm','suction.he'),
                'transfer_pump': ('transfer.required','transfer.empirical')}
    primary = None
    if fire:
        key = fire.get('primary_result_key')
        row = next((row for row in fire.get('summary',()) if row['key']==key), None)
        if row:
            primary = next((r for r in results if r.symbol==row['symbol'] and r.value==row['value']),None)
    else:
        for step_id in step_ids.get(snapshot.module_code.value, ()):
            step = next((s for s in report.formulas if s.step_id==step_id),None)
            if step:
                primary = next((r for r in results if r.symbol==step.result_symbol and r.value==step.result_value),None)
                if primary: break
    if primary is None and results: primary = results[-1]
    identification = tuple(field(row) for row in report.identification)
    identification = tuple(replace(row,value=tr('report.stage.'+snapshot.stage))
        if row.label==tr('report.field.stage') and snapshot.stage in ('selection','hydraulics','diameter','wall') else row
        for row in identification)
    return replace(report, language=language, module_code=snapshot.module_code.value,
        project_name=context.get('project_name'), system_family=family,
        revision=str(fire['revision']) if fire.get('revision') is not None else None,
        inputs=inputs, results=results, primary_result=primary, warning_items=tuple(warnings),
        identification=identification, selections=tuple(field(r) for r in report.selections),
        metadata=tuple(field(r) for r in report.metadata))
