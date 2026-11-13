"""Percent convention is deterministic; clarification never changes engineering evidence."""
from io import BytesIO
from dataclasses import replace

import pytest
from pypdf import PdfReader

from engineering.validation import ValidationError
from engineering.snapshots.models import CalculationSnapshot
from i18n.translator import Translator
from reporting.models import adapt_snapshot
from reporting.renderer import render_pdf
from services.fire_workspace import FireWorkspace
from ui.fire_input_presentation import foam_percent_clarifications
from ui.history_presentation import fire_details, historical_override_values
from .test_fire_phase5_live_ui import live, fill_view, foam


@pytest.mark.parametrize('text,fraction,warning',[
    ('3',.03,False),('3,00',.03,False),('6',.06,False),('6,00',.06,False),
    ('0,03',.0003,True),('0.5',.005,True),('1',.01,False),
])
def test_input_convention_is_percent_without_guessing(text,fraction,warning):
    draft=FireWorkspace();foam(draft,percent=text)
    result=draft.calculate('foam')
    assert result.domain_result.input.foam_fraction==pytest.approx(fraction)
    assert bool(foam_percent_clarifications(text)) is warning
    if warning:
        message=foam_percent_clarifications(text)[0]
        assert message.category=='UI_INPUT_CLARIFICATION'
        assert message.field_name=='foam_fraction'
        assert 'SOURCE_REQUIRED' not in message.category


@pytest.mark.parametrize('text',['0','100','120','-1'])
def test_existing_fraction_validation_unchanged(text):
    draft=FireWorkspace();foam(draft,percent=text)
    with pytest.raises(ValidationError):draft.calculate('foam')
    assert foam_percent_clarifications(text)==()


def test_help_adjacent_unit_and_empty_initial_value(live):
    from tkinter import ttk
    root,page,saved,tr=live;view=page.views['foam']
    assert view.variables['foam_fraction'].get()==''
    assert view.concentration_help['text']=='Köpük yüzdesini giriniz; %3 için 3 yazınız.'
    assert view.concentration_warning.grid_info()=={}
    assert any(widget['text']=='Önerilen (%)' for widget,key in view.meta_labels if key=='fire.ui.recommended_percent')
    percent_label=next(w for w in view.input_card.winfo_children() if isinstance(w,ttk.Label) and w['text']=='%')
    assert percent_label.grid_info()['row']==view.entries['foam_fraction'].grid_info()['row']
    assert percent_label.grid_info()['column']==view.entries['foam_fraction'].grid_info()['column']+1


def test_observed_low_percent_case_warns_and_stays_small(live):
    root,page,saved,tr=live;view=page.views['foam']
    fill_view(view,('210','5','30','0,03'))
    assert view.clarifications[0].category=='UI_INPUT_CLARIFICATION'
    assert view.concentration_warning.grid_info()
    assert '%3 için 3' in view.concentration_warning['text']
    view.calculate()
    result=page.model.results['foam']
    assert result.domain_result.input.foam_fraction==pytest.approx(.0003)
    assert result.domain_result.foam_concentrate_volume_l==pytest.approx(9.45)
    assert 'invalid' not in view.entries['foam_fraction'].state()
    assert str(view.pdf_button['state'])=='normal'
    snapshot=saved[-1];payload=snapshot.evidence['facts']['fire']
    assert payload['raw_inputs']['foam_fraction']['value']==pytest.approx(.03)
    assert payload['raw_inputs']['foam_fraction']['unit']=='%'
    assert payload['normalized_inputs']['foam_fraction']==pytest.approx(.0003)
    assert all(w['category']!='UI_INPUT_CLARIFICATION' for w in payload['warnings'])
    assert all(v.source_status.value=='USER_PROJECT_ASSUMPTION' for v in result.input_provenance)
    view.variables['foam_fraction'].set('1')
    assert not view.clarifications and view.concentration_warning.grid_info()=={}


def test_ui_three_percent_reference_and_formula_steps_unchanged(live):
    root,page,saved,tr=live;view=page.views['foam']
    fill_view(view,('210','5','30','3'));view.calculate()
    result=page.model.results['foam'];d=result.domain_result
    assert (d.solution_flow_lpm,d.foam_concentrate_flow_lpm,d.water_flow_lpm,d.foam_concentrate_volume_l)==(1050,31.5,1018.5,945)
    assert not view.clarifications
    ratio=next(v for s in view.steps() for v in s.variables if v.symbol=='Cfoam')
    assert ratio.value==.03 and ratio.unit=='1'
    assert view.steps()==saved[-1].formula_steps


@pytest.mark.parametrize('language',['tr','en'])
def test_clarification_localization(language,live):
    root,page,saved,tr=live;view=page.views['foam']
    view.tr=Translator(language).translate
    view.variables['foam_fraction'].set('0.5');view.refresh_texts()
    assert view.concentration_help['text']==view.tr('fire.ui.percent_help')
    assert view.concentration_warning['text']==view.tr('fire.ui.percent_low')
    if language=='en':assert view.concentration_help['text']=='Enter a percentage; for 3%, enter 3.'


def test_frozen_history_and_pdf_show_percent_with_canonical_formula_and_overrides(live):
    root,page,saved,tr=live;view=page.views['foam']
    fill_view(view,('210','5','30','6'))
    view.meta_vars['foam_fraction']['recommended'].set('3')
    view.meta_vars['foam_fraction']['reason'].set('Project-selected approved concentrate')
    view.calculate()
    snapshot=CalculationSnapshot.from_payload(saved[-1].to_payload());before=snapshot.to_json()
    evidence=snapshot.evidence;fire=evidence['facts']['fire']
    assert fire['normalized_inputs']['foam_fraction']==.06
    assert fire['raw_inputs']['foam_fraction']['value']==6
    assert 'Köpük Konsantrasyonu: 6,00 %' in fire_details(evidence,tr.translate)
    used=next(v for s in evidence['steps'] for v in s['used_values'] if v.get('symbol')=='Cfoam')
    assert historical_override_values('fire_foam_system',used)==('3,00 %','6,00 %')
    assert historical_override_values('pipe_design',used)==('0,03','0,06')
    report=adapt_snapshot(snapshot)
    concentration=next(r for r in report.inputs if r.symbol=='Cfoam')
    assert (concentration.value,concentration.unit)==(6,'%')
    values=[r for r in report.selections if r.symbol=='Cfoam' and r.unit=='%']
    assert {r.value for r in values}>={3,6}
    assert report.results[-1].value==1890
    assert 'Project-selected approved concentrate' in report.to_json()
    text='\n'.join(p.extract_text() for p in PdfReader(BytesIO(render_pdf(report))).pages)
    assert 'Köpük Konsantrasyonu' in text and '6,00' in text and '%' in text
    assert snapshot.to_json()==before


def test_three_percent_pdf_display_is_not_point_zero_three_percent():
    draft=FireWorkspace();foam(draft);draft.calculate('foam')
    snapshot=draft.snapshots['foam'];before=snapshot.to_json()
    report=adapt_snapshot(snapshot)
    row=next(r for r in report.inputs if r.symbol=='Cfoam')
    assert (row.value,row.unit)==(3,'%')
    assert next(v for s in report.formulas for v in s.variables if v.symbol=='Cfoam').value==.03
    text='\n'.join(p.extract_text() for p in PdfReader(BytesIO(render_pdf(report))).pages)
    assert '3,00' in text and '%' in text and '945,00' in text
    assert snapshot.to_json()==before


def test_help_and_warning_fit_narrow_viewport_without_overlap(live):
    root,page,saved,tr=live;view=page.views['foam']
    root.deiconify();root.geometry('1100x700')
    page.pack_forget();page.place(x=320,y=110,width=780,height=560)
    fill_view(view,('210','5','30','0,03'));root.update()
    canvas=page.host._page_keys['foam'].canvas
    right=canvas.winfo_rootx()+canvas.winfo_width()
    assert view.concentration_help.winfo_rootx()+view.concentration_help.winfo_width()<=right+2
    assert view.concentration_warning.winfo_rootx()+view.concentration_warning.winfo_width()<=right+2
    assert not view.concentration_help.grid_info()
    assert view.concentration_warning.winfo_rooty()+view.concentration_warning.winfo_height()<=view.scope.winfo_rooty()
