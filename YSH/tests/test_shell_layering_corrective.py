"""Corrective acceptance for native text drawing and real Foam application flow."""
import pytest
from tkinter import ttk

from .test_fire_phase5cd_navigation import application, shell
from .test_fire_phase5_live_ui import fill_view
from .test_fire_phase6_library import library, record


def elements(layout):
    for name,options in layout:
        yield name
        yield from elements(options.get('children',()))


def test_foam_calculates_and_uses_native_text_painter(shell):
    w=shell;root=w._root;root.geometry('1100x700');root.deiconify();w._show_family('fire',dirty=False);root.update()
    view=w._fire_workspace.views['foam']
    w._fire_workspace.host.select(w._fire_workspace.host._page_keys['hw']);root.update()
    w._fire_workspace.host.select(w._fire_workspace.host._page_keys['foam']);root.update()
    assert w._fire_workspace.views['foam'] is view
    assert all(entry.winfo_viewable() for entry in view.entries.values())
    fill_view(view,('210','5','30','3'));view.calculate();root.update()
    backdrop=w._fire_workspace.host._active_host()._workspace_backdrop
    backdrop.paint();root.update()
    assert w._fire_workspace.model.results['foam'].domain_result.foam_concentrate_volume_l==945
    assert view.pdf_button.instate(['!disabled'])
    canvas=w._fire_workspace.host._active_host().canvas
    primary=view.result_labels[0]
    assert primary.winfo_rooty()>=canvas.winfo_rooty()
    assert primary.winfo_rooty()+primary.winfo_height()<=canvas.winfo_rooty()+canvas.winfo_height()
    for label in (*view.labels.values(),*view.result_labels,w._fire_workspace.title):
        assert label.winfo_viewable() and label.cget('text')
        layout=ttk.Style(root).layout(label.cget('style') or 'TLabel')
        assert list(elements(layout))==list(elements(ttk.Style(root).layout('TLabel')))
        assert not any(name.startswith('GlassSurface') for name in elements(layout))


def test_source_aware_foam_formula_pdf_snapshot_history_and_stale(shell,library,monkeypatch):
    from io import BytesIO
    from pypdf import PdfReader
    from reporting.models import adapt_snapshot
    from reporting.renderer import render_pdf
    w=shell;root=w._root;root.deiconify();w._show_family('fire',dirty=False);root.update()
    page=w._fire_workspace;view=page.views['foam'];panel=view.library_panel
    service,_=library;item=record(library)
    previous=(page._library_provider,page._library_service)
    page._library_provider=lambda:service;page._library_service=service
    try:
        fill_view(view,('210','','30','3'));panel.context.set('TEST_ONLY');panel.refresh()
        box=panel.boxes['application_density_lpm_m2'];box.current(0)
        panel.action('application_density_lpm_m2','use')
        assert page.model.library_inputs.links['application_density_lpm_m2'].id==item.id
        view.variables['application_density_lpm_m2'].set('6')
        view.meta_vars['application_density_lpm_m2']['reason'].set('TEST_ONLY approved override')
        view.calculate();root.update()
        assert page.model.results['foam'].domain_result.foam_concentrate_volume_l==1134
        snapshot=page.model.snapshots['foam'];before=snapshot.to_json()
        assert view.result_labels[0].winfo_viewable() and 'Vfoam' in view.result_labels[0].cget('text')
        assert all(widget.grid_info() for widget in panel.reasons['application_density_lpm_m2'])
        view.formula.toggle();root.update()
        assert view.formula._dialog.winfo_exists() and view.formula._steps==snapshot.formula_steps
        view.formula._close_dialog()
        exported=[]
        monkeypatch.setattr('ui.dialogs.pdf_report.save_snapshot_pdf',lambda parent,value:exported.append(value))
        view.pdf_button.invoke();assert exported==[snapshot]
        pdf=render_pdf(adapt_snapshot(snapshot));assert len(PdfReader(BytesIO(pdf)).pages)>0
        w._open_calculation_history();history=w._history_window
        assert any(row.to_json()==before for row in w._snapshot_history.list(None))
        assert str(snapshot.snapshot_id) in history._rows
        history._selected_id=str(snapshot.snapshot_id)
        history._render_selected();root.update()
        assert history._formula_panel._step_provider()==snapshot.formula_steps
        assert history._pdf_button.instate(['!disabled'])
        history._close()
        view.variables['foam_fraction'].set('6');root.update()
        assert view.pdf_button.instate(['disabled']) and page.model.results['foam'] is None
        assert snapshot.to_json()==before
    finally:
        page._library_provider,page._library_service=previous


def test_hw_native_inputs_results_and_stale_pdf(shell):
    from engineering.fire.hazen_williams_workflow import HWService
    w=shell;root=w._root;root.deiconify();w._show_family('fire',dirty=False)
    page=w._fire_workspace;page.host.select(page.host._page_keys['hw']);root.update()
    view=page.views['hw'];page.model.service=HWService.WATER
    fill_view(view,('2000','105','150','120'));view.calculate();root.update()
    page.host._active_host()._workspace_backdrop.paint();root.update()
    assert page.model.results['hw'].domain_result.total_pressure_loss_bar==pytest.approx(2.3717829024660286)
    assert view.result_labels[0].winfo_viewable() and 'ΔpHW' in view.result_labels[0].cget('text')
    canvas=page.host._active_host().canvas;primary=view.result_labels[0]
    assert primary.winfo_rooty()>=canvas.winfo_rooty()
    assert primary.winfo_rooty()+primary.winfo_height()<=canvas.winfo_rooty()+canvas.winfo_height()
    for label in (*view.labels.values(),*view.result_labels):
        assert not any(name.startswith('GlassSurface') for name in elements(ttk.Style(root).layout(label.cget('style'))))
    assert view.pdf_button.instate(['!disabled'])
    snapshot=page.model.snapshots['hw'];before=snapshot.to_json()
    view.variables['hazen_williams_c'].set('140');root.update()
    assert view.pdf_button.instate(['disabled']) and snapshot.to_json()==before
