"""Phase 6A presentation acceptance with real Tk controls and synthetic sources."""
from types import SimpleNamespace

import pytest

from engineering.fire.library import FireParameter
from i18n.translator import Translator
from ui.dialogs.engineering_library_workspace import EngineeringLibraryWorkspace
from ui.theme.library_visuals import fire_source_role
from ui.widgets.formula_steps import number
from .test_fire_phase6_library import library, record
from .test_fire_phase5_live_ui import live, fill_view


PARAMETERS = [
    ('foam', 'application_density_lpm_m2', FireParameter.APPLICATION_RATE, 5, '6'),
    ('foam', 'application_duration_min', FireParameter.DURATION, 30, '31'),
    ('foam', 'foam_fraction', FireParameter.CONCENTRATION, .03, '6'),
    ('hw', 'hazen_williams_c', FireParameter.HW_COEFFICIENT, 120, '140'),
]


def linked_view(page, library, kind, name, parameter, value):
    service, _ = library
    page._library_provider = lambda: service
    item = record(library, parameter, value)
    view = page.views[kind]
    if kind == 'hw':
        from engineering.fire.hazen_williams_workflow import HWService
        page.model.service = HWService.WATER
    panel = view.library_panel
    panel.context.set('TEST_ONLY')
    panel.refresh()
    panel.boxes[name].current(0)
    panel.action(name, 'use')
    return view, panel, item


def visible(widget):
    """Grid visibility independent of a collapsed disclosure or withdrawn test root."""
    return bool(widget.grid_info())


@pytest.mark.parametrize('kind,name,parameter,value,changed', PARAMETERS)
def test_linked_reason_changes_dynamically_only_for_actual_override(live, library, kind, name, parameter, value, changed):
    _, page, _, _ = live
    view, panel, item = linked_view(page, library, kind, name, parameter, value)
    original = view.variables[name].get()
    assert all(not visible(widget) for widget in panel.reasons[name])
    assert not visible(view.meta_groups[name])  # no duplicate source / reason editor
    assert view.tr('fire.library.mode.linked') in panel.summaries[name]['text']
    view.variables[name].set(changed)
    assert all(visible(widget) for widget in panel.reasons[name])
    assert all(widget.master is panel for widget in panel.reasons[name])
    assert not panel.details.expanded  # required reason is outside collapsed Library administration
    text = panel.summaries[name]['text']
    assert view.tr('fire.library.mode.override') in text
    assert view.tr('fire.library.recommended') in text and changed in text
    view.meta_vars[name]['reason'].set('TEST_ONLY retained draft reason')
    view.variables[name].set(original)
    assert all(not visible(widget) for widget in panel.reasons[name])
    assert view.meta_vars[name]['reason'].get() == 'TEST_ONLY retained draft reason'
    assert page.model.library_inputs.links[name] == item


@pytest.mark.parametrize('kind,name,parameter,value,changed', PARAMETERS)
def test_manual_without_recommendation_has_no_override_or_stale_controls(live, library, kind, name, parameter, value, changed):
    _, page, _, _ = live
    view = page.views[kind]
    panel = view.library_panel
    view.variables[name].set(changed)
    assert all(not visible(widget) for widget in panel.reasons[name])
    assert all(not visible(widget) for widget in view.meta_reason_controls[name])
    assert view.tr('fire.library.mode.manual') in panel.summaries[name]['text']
    assert view.tr('fire.library.mode.override') not in panel.summaries[name]['text']
    assert '—' in panel.summaries[name]['text']
    assert panel.summaries[name]['style'] == 'Fire.Source.Muted.TLabel'
    assert not visible(panel.buttons[name]['update'])
    assert not visible(panel.buttons[name]['keep'])


@pytest.mark.parametrize('kind,name,parameter,value,changed', PARAMETERS)
def test_stale_controls_update_and_keep_preserve_used_value(live, library, kind, name, parameter, value, changed):
    _, page, _, _ = live
    service, _ = library
    view, panel, item = linked_view(page, library, kind, name, parameter, value)
    assert not visible(panel.buttons[name]['update'])
    assert not visible(panel.buttons[name]['keep'])
    view.variables[name].set(changed)
    view.meta_vars[name]['reason'].set('TEST_ONLY override')
    category = {FireParameter.APPLICATION_RATE: 'fire_foam_rate', FireParameter.DURATION: 'fire_foam_duration',
                FireParameter.CONCENTRATION: 'fire_foam_concentration', FireParameter.HW_COEFFICIENT: 'fire_hw'}[parameter]
    values = service.form_values(category, item)
    values['value'] = value * 1.1
    service.save(category, values, item.id)
    panel.refresh()
    assert page.model.library_inputs.links[name].revision == 1
    assert view.variables[name].get() == changed  # observing cannot update silently
    assert visible(panel.buttons[name]['update']) and visible(panel.buttons[name]['keep'])
    panel.action(name, 'keep')
    assert view.variables[name].get() == changed
    assert page.model.library_inputs.links[name].revision == 1
    assert page.model.library_inputs.stale[name]  # accepted semantics: retained stale revision
    assert view.tr('fire.library.kept') in panel.summaries[name]['text']
    panel.action(name, 'update')
    assert view.variables[name].get() == changed
    assert page.model.library_inputs.links[name].revision == 2
    assert not visible(panel.buttons[name]['update']) and not visible(panel.buttons[name]['keep'])
    panel.action(name, 'manual')
    assert view.variables[name].get() == changed
    assert all(not visible(widget) for widget in panel.reasons[name])


@pytest.mark.parametrize('name', ['protected_area_m2', 'application_density_lpm_m2', 'application_duration_min', 'foam_fraction'])
def test_manual_recommendation_reason_and_summary_follow_accepted_metadata(live, name):
    _, page, _, _ = live
    view = page.views['foam']
    view.variables[name].set('3,0')
    view.meta_vars[name]['recommended'].set('3')
    assert all(not visible(widget) for widget in view.meta_reason_controls[name])
    view.variables[name].set('6')
    assert all(visible(widget) for widget in view.meta_reason_controls[name])
    if name in view.library_panel.summaries:
        text = view.library_panel.summaries[name]['text']
        assert view.tr('fire.library.mode.override') in text
        assert view.tr('fire.library.recommended') + ': 3' in text
    view.meta_vars[name]['recommended'].set('')
    assert all(not visible(widget) for widget in view.meta_reason_controls[name])


@pytest.mark.parametrize('status', ['SOURCE_VERIFIED', 'SOURCE_VERIFIED_CONTEXT_DEPENDENT', 'DERIVED_FROM_VERIFIED_RULE'])
def test_legacy_manual_claim_does_not_display_verified_source(live, status):
    _, page, _, _ = live
    from services.fire_workspace import FireWorkspace
    state = page.model.export_state()
    state.pop('library_inputs')  # legacy project without a frozen Library record
    name = 'application_density_lpm_m2'
    state['fields']['foam'][name] = '5'
    state['metadata']['foam'][name].update(status=status, document='TEST_ONLY unverified legacy claim')
    page.model = FireWorkspace.from_state(state)
    view = page.views['foam']; view.load_fields(); view.sync()
    summary = view.library_panel.summaries[name]
    assert summary['style'] == 'Fire.Source.Muted.TLabel'
    assert view.tr('fire.ui.source.SOURCE_REQUIRED') in summary['text']
    assert view.tr('fire.ui.source.'+status) not in summary['text']
    assert page.model.metadata['foam'][name]['status'] == status  # presentation only
    assert not page.model.library_inputs.links


def test_duplicate_choices_are_explicit_and_never_show_ids(live, library):
    _, page, _, _ = live
    service, _ = library
    page._library_provider = lambda: service
    first = record(library)
    second = record(library)
    view = page.views['foam']; panel = view.library_panel; name = 'application_density_lpm_m2'
    panel.context.set('TEST_ONLY'); panel.refresh()
    labels = tuple(panel.choices[name])
    assert len(labels) == 2 and labels[0] != labels[1]
    assert panel.boxes[name].get() == '' and panel.buttons[name]['use'].instate(['disabled'])
    for label in labels:
        assert number(5)+' L/(min·m²)' in label and first.source.document in label
        assert all(str(item.id)[:8] not in label for item in (first, second))
    panel.boxes[name].current(1)
    panel.boxes[name].event_generate('<<ComboboxSelected>>')
    assert panel.buttons[name]['use'].instate(['!disabled'])
    assert not page.model.library_inputs.links
    panel.action(name, 'use')
    assert page.model.library_inputs.links[name] == panel.choices[name][labels[1]]


def test_refresh_does_not_transfer_selection_to_an_identical_caption(live, library):
    _, page, _, _ = live
    service, _ = library
    page._library_provider = lambda: service
    record(library); record(library)
    panel = page.views['foam'].library_panel; name = 'application_density_lpm_m2'
    panel.context.set('TEST_ONLY'); panel.refresh()
    panel.boxes[name].current(0)
    selected = panel.choices[name][panel.boxes[name].get()]
    values = service.form_values('fire_foam_rate', selected); values['is_active'] = False
    service.save('fire_foam_rate', values, selected.id)
    panel.refresh()
    assert len(panel.choices[name]) == 1
    assert panel.boxes[name].get() == ''
    assert panel.buttons[name]['use'].instate(['disabled'])
    assert not page.model.library_inputs.links


@pytest.mark.parametrize('language', ['tr', 'en'])
@pytest.mark.parametrize('size', [(1100,700), (1280,800), (1440,900), (1700,1000)])
def test_library_hierarchy_and_human_readable_details(live, library, language, size):
    root, _, _, _ = live
    root.deiconify(); root.geometry(f'{size[0]}x{size[1]}')
    service, _ = library
    item = record(library)
    owner = SimpleNamespace(register_localizable=lambda *_: None, unregister_localizable=lambda *_: None)
    tr = Translator(language).translate
    window = EngineeringLibraryWorkspace(root, service, tr, owner, 'fire_foam_rate')
    try:
        from tkinter import ttk, font
        window.geometry(f'{size[0]}x{size[1]}'); window.update()
        nav = window._navigation
        face = font.Font(root=window, font=ttk.Style(window).lookup('LibraryNav.Treeview','font') or 'TkDefaultFont')
        assert nav.item('group:fire:foam', 'text') == ('Köpük Sistemi' if language == 'tr' else 'Foam System')
        assert nav.item('group:fire:hw', 'text') == 'Hazen-Williams'
        assert nav.get_children('group:fire:foam') == ('fire_foam_rate', 'fire_foam_duration', 'fire_foam_concentration')
        assert nav.get_children('group:fire:hw') == ('fire_hw',)
        for code in ('fire_foam_rate', 'fire_foam_duration', 'fire_foam_concentration', 'fire_hw'):
            assert face.measure(nav.item(code,'text'))+60 <= int(nav.column('#0','width'))
        window._controller.select(item.id); window._render_details()
        def labels(parent):
            for child in parent.winfo_children():
                if child.winfo_class() == 'TLabel':
                    yield str(child.cget('text'))
                yield from labels(child)
        text = '\n'.join(labels(window._body))
        assert 'FIRE.FOAM.APPLICATION_RATE' not in text
        assert tr('library2.category.fire_foam_rate') in text
        assert str(item.source_id) not in text
        window._new()
        assert not {'system_family', 'system_type', 'family'} & window._edit_vars.keys()
        assert tr('library2.field.context') in '\n'.join(labels(window._body))
        assert 'Cfoam' not in '\n'.join(labels(window._body))
        window.update()
        for widget in window._body.winfo_children():
            if widget.winfo_class() in ('TEntry', 'TCombobox'):
                assert widget.winfo_x()+widget.winfo_width() <= window._body.winfo_width()+2
    finally:
        window.destroy()


@pytest.mark.parametrize('status,role', [('SOURCE_VERIFIED','Verified'), ('SOURCE_VERIFIED_CONTEXT_DEPENDENT','Info'),
                                       ('WORKBOOK_REFERENCE_ONLY','Info'), ('SOURCE_REQUIRED','Muted'),
                                       ('NOT_CONFIGURED','Muted'), ('SOURCE_CONFLICT','Warning')])
def test_source_styles_do_not_present_missing_sources_as_critical_errors(status, role):
    assert fire_source_role(status) == role


@pytest.mark.parametrize('language', ['tr', 'en'])
@pytest.mark.parametrize('size', [(1100,700), (1280,800), (1440,900), (1700,1000)])
def test_linked_override_stale_controls_and_results_fit(live, library, language, size):
    root, page, _, _ = live
    service, _ = library
    view, panel, item = linked_view(page, library, *PARAMETERS[0][:4])
    view.tr = Translator(language).translate
    fill_view(view, ('210','6','30','3'))
    view.meta_vars['application_density_lpm_m2']['reason'].set('TEST_ONLY override')
    view.calculate()
    result = page.model.results['foam']; snapshot = page.model.snapshots['foam']
    values = service.form_values('fire_foam_rate', item); values['value'] = 7
    service.save('fire_foam_rate', values, item.id); panel.refresh(); view.refresh_texts()
    root.deiconify(); root.geometry(f'{size[0]}x{size[1]}')
    page.pack_forget(); page.place(x=300,y=150,width=size[0]-320,height=size[1]-180)
    panel.details.toggle(); root.update()
    canvas = page.host._page_keys['foam'].canvas
    edge = canvas.winfo_rootx()+canvas.winfo_width()
    widgets = [*panel.summaries.values(), *panel.buttons['application_density_lpm_m2'].values(),
               *panel.reasons['application_density_lpm_m2'], *view.result_labels,
               view.calculate_button, view.clear_button, view.pdf_button]
    for widget in widgets:
        assert widget.winfo_rootx()+widget.winfo_width() <= edge+2
    assert int(view.actions.grid_info()['row']) < int(view.result_card.grid_info()['row']) < int(view.status.grid_info()['row'])
    assert result.domain_result.solution_flow_lpm == 1260
    assert page.model.results['foam'] is result and page.model.snapshots['foam'] is snapshot
