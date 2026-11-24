"""Optional report identity captured once, before a new snapshot is persisted."""
from dataclasses import replace
from engineering.snapshots.serialization import canonical


def snapshot_family(snapshot):
    """Honor frozen additive family identity; legacy records keep their original fallback."""
    from services.engineering_warning_center import FAMILY_MODULES
    module = snapshot.module_code.value
    family = snapshot.evidence.get('report_context', {}).get('system_family')
    if family is not None:
        if module not in FAMILY_MODULES.get(family, ()) and not (
            family == 'fire' and module in ('fire_foam_system', 'fire_hazen_williams')):
            raise ValueError('Frozen report family and calculation module differ')
        return family
    return 'fire' if module.startswith('fire_') else 'fuel'


def freeze_report_context(snapshot, *, project_name=None, system_family=None):
    """Return a new immutable snapshot; never enrich existing historical records."""
    evidence = snapshot.evidence
    if 'report_context' in evidence:
        return snapshot
    family = snapshot_family(snapshot)
    if system_family is not None:
        from services.engineering_warning_center import FAMILY_MODULES
        if system_family != family and snapshot.module_code.value not in FAMILY_MODULES.get(system_family, ()):
            raise ValueError('Report system family does not match the calculation module')
        family = system_family
    context = {'system_family': family}
    if snapshot.project_id is not None and project_name:
        context['project_name'] = project_name
    evidence['report_context'] = context
    return replace(snapshot, evidence_json=canonical(evidence))
