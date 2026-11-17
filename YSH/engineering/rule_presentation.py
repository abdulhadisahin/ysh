"""Read frozen rule findings for UI/report presentation, never evaluate a rule."""
import json

def finding_text(finding,translate):
    tr=translate
    record=json.loads(finding.rule_record_json)
    if finding.code=='d243.pipe.velocity_max':
        headline=tr('pipe.warning.d243_velocity_max',limit=f'{finding.upper_bound:g}')
    else:headline=tr('engineering.rule.finding',name=record['name'],status=tr('engineering.status.'+record['status']))
    low,high=(record.get('hard_min'),record.get('hard_max')) if record['rule_nature']=='HARD_LIMIT' else (record.get('recommended_min'),record.get('recommended_max'))
    lines=[headline,tr('engineering.used')+': '+str(record['observed_value'])+' '+record['unit'],
        tr('engineering.reference')+': '+str(low if low is not None else '')+' … '+str(high if high is not None else '')+' '+record['unit'],
        tr('engineering.nature.'+record['rule_nature']),tr('engineering.source')+': '+' · '.join(record.get(n,'') for n in ('source_authority','source_document','source_edition','source_clause')).strip(' ·')]
    lines.append(tr('engineering.verification.'+record['verification']))
    if record.get('applicability'):lines.append(tr('engineering.applicability')+': '+tr('engineering.scope.'+record['applicability']))
    if record.get('notes'):lines.append(record['notes'])
    return '\n'.join(lines)
