"""Human-readable frozen engineering basis, shared by Formula View and PDF."""
import json

def basis_rows(payload,translate):
    tr=translate;rows=[]
    for name in ('fluid','material','service','line_type'):
        if payload.get(name):
            value=str(payload[name])
            if name=='line_type' and value in ('SUCTION','DELIVERY'):value=tr('engineering.line.'+value)
            rows.append((tr('engineering.'+name),value))
    for item in payload.get('values',()):
        reference=item['reference'];unit=reference.get('unit','');name=reference.get('property_name','')
        label=tr('engineering.property.'+name)
        if reference.get('name'):rows.append((label+' / '+tr('engineering.record'),reference['name']))
        lo=reference.get('source_min');hi=reference.get('source_max')
        span=('≥ '+str(lo) if lo is not None else '')+(' … ' if lo is not None and hi is not None else '')+('≤ '+str(hi) if hi is not None else '')
        temperature=reference.get('reference_temperature_c')
        rows.append((label+' / '+tr('engineering.reference'),(span+' '+unit+(' @ '+str(temperature)+' °C' if temperature is not None else '')).strip() if span else tr('engineering.range_unrecorded')))
        if reference.get('source_nominal') is not None:rows.append((label+' / '+tr('engineering.nominal'),str(reference['source_nominal'])+' '+unit))
        rows.append((label+' / '+tr('engineering.default'),str(reference['default_value'])+' '+unit if reference.get('default_value') is not None else tr('engineering.status.SOURCE_REQUIRED')))
        if 'library_default' in reference:rows.append((label+' / '+tr('engineering.library_default'),str(reference['library_default'])+' '+unit))
        rows.append((label+' / '+tr('engineering.method.label'),tr('engineering.method.'+reference.get('default_method','SOURCE_REQUIRED'))))
        rows.append((label+' / '+tr('engineering.used'),str(item['used_value'])+' '+unit if item.get('used_value') is not None else tr('engineering.none')))
        rows.append((label+' / '+tr('engineering.status'),tr('engineering.status.'+item.get('status','MANUAL'))))
        source=' · '.join(str(reference.get(n) or '') for n in ('source_authority','source_document','source_edition'))
        rows.append((label+' / '+tr('engineering.source'),source.strip(' ·')))
        rows.append((label+' / '+tr('engineering.verification.label'),tr('engineering.verification.'+reference.get('verification','SOURCE_REQUIRED'))))
        if reference.get('source_note'):rows.append((label+' / '+tr('engineering.note'),reference['source_note']))
    for rule in payload.get('rules',()):
        rows.append((rule['name'],tr('engineering.nature.'+rule['rule_nature'])))
        lo,hi=(rule.get('hard_min'),rule.get('hard_max')) if rule['rule_nature']=='HARD_LIMIT' else (rule.get('recommended_min'),rule.get('recommended_max'))
        rows.append((tr('engineering.reference'),f'{lo if lo is not None else ""} … {hi if hi is not None else ""} {rule["unit"]}'))
        if rule.get('observed_value') is not None:rows.append((tr('engineering.used'),str(rule['observed_value'])+' '+rule['unit']))
        rows.append((tr('engineering.status'),tr('engineering.status.'+rule.get('status','SOURCE_REQUIRED'))))
        rows.append((tr('engineering.source'),' · '.join(rule.get(n,'') for n in ('source_authority','source_document','source_edition','source_clause')).strip(' ·')))
        rows.append((tr('engineering.verification.label'),tr('engineering.verification.'+rule['verification'])))
        if rule.get('applicability'):rows.append((tr('engineering.applicability'),tr('engineering.scope.'+rule['applicability'])))
        if rule.get('notes'):rows.append((tr('engineering.note'),rule['notes']))
    return tuple(rows)

def basis_text(payload,translate):return '\n'.join(label+': '+value for label,value in basis_rows(payload,translate))
