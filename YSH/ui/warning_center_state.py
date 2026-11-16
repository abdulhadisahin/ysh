"""Project existing live UI statuses into immutable Warning Center records.

Reading never calls calculate, export/load, history, discovery or a Library resolver.
Unvisited blank forms do not acquire synthetic validation failures.
"""
from services.engineering_warning_center import (
    EngineeringWarning, ModuleWarningState, WarningStatus as S, aggregate_warnings, FAMILY_MODULES,
)
from i18n.validation import render_validation_issue

MODULE_LABELS = {'pipe_design': 'page.pipe.tab', 'transfer_pump': 'page.transfer.tab',
                 'discharge_head_loss': 'page.discharge.tab', 'suction_npsh': 'page.suction.tab',
                 'foam': 'fire.ui.foam', 'hw': 'fire.ui.hw'}


def collect_warning_summary(window):
    if getattr(window, '_active_project', None) is None:
        return aggregate_warnings(None, ())
    family = window._locked_project_family()
    tr = window._translate
    states = []
    if family == 'fuel':
        for key, page in window._pages.items():
            if key not in FAMILY_MODULES['fuel']:
                continue
            items = []
            def add(severity, code, message_key='', detail='', source=''):
                items.append(EngineeringWarning(key, severity, code, message_key, detail, source))
            panel = getattr(page, '_warning_panel', None)
            for finding in getattr(panel, 'findings', ()):
                severity = S.ERROR if finding.severity.value == 'ERROR' else S.WARNING
                # The existing presenter retains source/range/context wording.
                add(severity, finding.code, detail=panel._message(finding))
            if key == 'pipe_design':
                results = (getattr(page, '_diameter_result', None), getattr(page, '_wall_result', None))
                error_text = getattr(page, '_center_error_text', '')
                if error_text and page._message.get() == error_text:
                    add(S.ERROR, 'pipe_validation', detail=error_text)
                for code in getattr(page, '_diameter_warning_codes', ()):
                    from ui.pages.pipe_design_page import _DN_WARNING_TRANSLATION_KEYS
                    add(S.WARNING, code, _DN_WARNING_TRANSLATION_KEYS.get(code, 'pipe.warning.recommendation_unavailable'))
                if results[1]:
                    add(S.SOURCE_REQUIRED, 'ab_source', 'pipe.ab_source_required')
            elif key == 'transfer_pump':
                design = getattr(page, '_design_panel', None)
                results = (getattr(page, '_estimate_result', None), getattr(design, '_last_result', None))
                if results[1] is not None:
                    status = results[1].status.value
                    add(S.WARNING if status == 'PUMP_CAPACITY_BELOW_REQUIRED' else S.INFO,
                        'design:' + status, 'transfer.design.status.' + status)
                error = getattr(design, '_error', None)
                if error is not None and error.get():
                    add(S.ERROR, 'design_validation', detail=error.get())
            elif key == 'suction_npsh':
                results = (getattr(page, '_last_loss', None), getattr(page, '_last_enpy', None))
            else:
                results = (getattr(page, '_last_result', None),)
            warning_codes = {issue.code for result in results if result
                             for issue in getattr(result, 'warnings', ())}
            statuses = list(getattr(page, '_status_messages', ()))
            statuses += list(getattr(page, '_loss_status_messages', ()))
            statuses += list(getattr(page, '_enpy_status_messages', ()))
            for issue in statuses:
                # These are startup/model readiness statuses, not design warnings.
                if '.status.' in issue.code or issue.code in ('insufficient_reference_ships', 'material_roughness_missing'):
                    continue
                severity = S.WARNING if issue.code in warning_codes else S.ERROR
                proxy = type('TranslatorProxy', (), {'translate': staticmethod(tr)})()
                add(severity, issue.code, detail=render_validation_issue(issue, proxy))
            workflow = getattr(page, '_workflow', None)
            if workflow is not None:
                pipe = workflow.pipe_input
                if pipe.mode.value == 'LINKED' and pipe.status.value != 'LINKED_SYNCED':
                    add(S.STALE, 'pipe:' + pipe.status.value, 'discharge.pipe.status.' + pipe.status.value)
            if not any(results) and getattr(page, '_pdf_snapshot', None) is not None:
                add(S.STALE, 'superseded_result', 'center.superseded')
            states.append(ModuleWarningState(key, tuple(items), sum(bool(r) for r in results)))
    elif family == 'fire':
        workspace = getattr(window, '_fire_workspace', None)
        if workspace is None:
            return aggregate_warnings(family, ())
        model = workspace.model
        from services.fire_workspace import FOAM_FIELDS, HW_FIELDS
        from ui.widgets.source_status import library_source_name
        for key in ('foam', 'hw'):
            spec = FOAM_FIELDS if key == 'foam' else HW_FIELDS
            def source_context(name):
                label = tr(spec[name][0]) if name in spec else ''
                record = model.library_inputs.links.get(name)
                document = library_source_name(record, tr) if record else model.metadata[key].get(name, {}).get('document', '')
                return ' · '.join(part for part in (label, document) if part)
            items = []
            def add(severity, code, message_key='', detail='', source=''):
                items.append(EngineeringWarning(key, severity, code, message_key, detail, source))
            result = model.results[key]
            view = workspace.views.created.get(key)
            for message in getattr(result, 'warnings', ()):
                category = message.category.value
                severity = {'INFO': S.INFO, 'WARNING': S.WARNING,
                            'SOURCE_REQUIRED': S.SOURCE_REQUIRED,
                            'SOURCE_CONTEXT_REQUIRED': S.SOURCE_REQUIRED}[category]
                add(severity, message.field_name + ':' + message.message_key, message.message_key,
                    source=source_context(message.field_name))
            if not result:
                for name, meta in model.metadata[key].items():
                    if model.fields[key][name].strip() and meta['status'] == 'SOURCE_REQUIRED':
                        add(S.SOURCE_REQUIRED, name + ':source', 'fire.' + key + '.source.SOURCE_REQUIRED', source=source_context(name))
            for name, stale in model.library_inputs.stale.items():
                if stale and name in model.fields[key]:
                    add(S.STALE, name + ':library', 'source.state.stale', source=source_context(name))
            if key == 'hw' and model.pipe.mode.value == 'LINKED' and model.pipe.status.value != 'LINKED_SYNCED':
                add(S.STALE, 'pipe:' + model.pipe.status.value, 'fire.value.' + model.pipe.status.value)
            message = getattr(view, '_center_message', None)
            if message in ('fire.ui.invalid', 'fire.ui.blocked'):
                add(S.BLOCKED if message.endswith('blocked') else S.ERROR, message, message)
            for clarification in getattr(view, 'clarifications', ()):
                add(S.INFO, clarification.message_key, clarification.message_key)
            states.append(ModuleWarningState(key, tuple(items), int(result is not None)))
    return aggregate_warnings(family, states)
