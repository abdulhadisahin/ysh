"""Optional report identity captured once, before a new snapshot is persisted."""
from dataclasses import replace
from engineering.snapshots.serialization import canonical


def snapshot_family(snapshot):
    return 'fire' if snapshot.module_code.value.startswith('fire_') else 'fuel'


def freeze_report_context(snapshot, *, project_name=None, system_family=None):
    """Return a new immutable snapshot; never enrich existing historical records."""
    evidence = snapshot.evidence
    if 'report_context' in evidence:
        return snapshot
    family = snapshot_family(snapshot)
    if system_family is not None and system_family != family:
        raise ValueError('Report system family does not match the calculation module')
    context = {'system_family': family}
    if snapshot.project_id is not None and project_name:
        context['project_name'] = project_name
    evidence['report_context'] = context
    return replace(snapshot, evidence_json=canonical(evidence))
