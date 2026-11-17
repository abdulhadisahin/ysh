"""Parameter-aware severity for explicit source records. Never blocks arithmetic."""
from dataclasses import asdict
import json,math


def record_payload(record):
    return json.loads(json.dumps(asdict(record),default=str,ensure_ascii=False,allow_nan=False))

def rule_status(rule,value):
    if rule.rule_nature=='SOURCE_REQUIRED' or rule.verification=='SOURCE_REQUIRED':return 'SOURCE_REQUIRED'
    if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value):raise ValueError('Invalid rule observation')
    lo,hi=(rule.hard_min,rule.hard_max) if rule.rule_nature=='HARD_LIMIT' else (rule.recommended_min,rule.recommended_max)
    below=lo is not None and value<lo;above=hi is not None and value>hi
    if not below and not above:return 'OK'
    bound=lo if below else hi
    extreme=(rule.parameter=='flow_velocity' and bound>0 and (value<bound/rule.critical_multiplier if below else value>=bound*rule.critical_multiplier))
    if extreme:return 'CRITICAL'
    if rule.rule_nature=='HARD_LIMIT':return 'OUT_OF_RANGE'
    fraction=abs(value-bound)/abs(bound) if bound else float('inf')
    return 'WARNING' if fraction<=rule.yellow_fraction+1e-12 else 'OUT_OF_RANGE'

def evaluate_rule(rule,value):
    from engineering.warning_rules import EngineeringFinding,WarningSeverity
    status=rule_status(rule,value)
    if status=='OK':return ()
    payload=record_payload(rule);payload.update(observed_value=value,status=status)
    d243=rule.code=='D243_FUEL_MAX'
    return (EngineeringFinding(code='d243.pipe.velocity_max' if d243 else 'engineering.rule.'+rule.code,
        severity=WarningSeverity.ENGINEERING_WARNING,message_key='pipe.warning.d243_velocity_max' if d243 else 'engineering.rule.finding',
        actual_value=value,lower_bound=rule.hard_min if rule.rule_nature=='HARD_LIMIT' else rule.recommended_min,
        upper_bound=rule.hard_max if rule.rule_nature=='HARD_LIMIT' else rule.recommended_max,unit=rule.unit,
        source_id=None,context={'criterion':'D243'} if d243 else {},visual_status=status,
        rule_record_json=json.dumps(payload,ensure_ascii=False,sort_keys=True)),)

def applicable_rules(records,*,family,profile_id,fluid_group,line_type,material='',scope='',service=''):
    return tuple(r for r in records if r.is_active and (r.profile_id==profile_id or (family=='fuel' and r.code=='D243_FUEL_MAX'))
        and (not r.system_family or r.system_family==family) and (not r.fluid_group or r.fluid_group==fluid_group)
        and (not r.line_type or r.line_type==line_type) and (not r.material or r.material==material)
        and (not r.applicability or r.applicability==scope) and (not r.service or r.service==service))
