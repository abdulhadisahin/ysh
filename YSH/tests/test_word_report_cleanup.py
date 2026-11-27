"""Word report: translated formula keys, subscripts, one-time basis rows, warnings separated from notes."""
from datetime import datetime, timezone
from io import BytesIO
from docx import Document
from engineering.formula.models import FormulaStep
from reporting.models import EngineeringReport, ReportField, ReportWarning
from reporting.word_renderer import render_word


def build(language):
    steps = (FormulaStep(step_id='a', title_key='pipe.D', formula_text='D = √((4 × Qm³/s) / (π × V))', result_value=85.15, result_unit='mm', result_symbol='D', display_order=0,
                         variables=(), reference_variables=(), used_values=()),
             FormulaStep(step_id='b', title_key='pipe.Di', formula_text='formula2.standard_selection', result_value=107.1, result_unit='mm', result_symbol='Di', display_order=1,
                         variables=(), reference_variables=(), used_values=()))
    return EngineeringReport(snapshot_id='x', module='Boru Tasarımı', stage='selection', created_at=datetime.now(timezone.utc), identification=(), inputs=(),
        selections=(ReportField('Seçim dayanağı', '', 'x'),), formulas=steps, results=(), warnings=(), sources=(), metadata=(), language=language,
        warning_items=(ReportWarning('INFO', 'Kural yapılandırılmadı', 'Boru Tasarımı'), ReportWarning('WARNING', 'Hız yüksek', 'Boru Tasarımı')))


def test_formula_keys_are_translated_and_info_rows_are_separate():
    doc = Document(BytesIO(render_word(build('tr'))))
    text = '\n'.join(p.text for p in doc.paragraphs)
    assert 'formula2.standard_selection' not in text and 'Seçilen standarttaki uygun boru kaydı' in text
    headings = [p.text for p in doc.paragraphs if p.style.name.startswith('Heading')]
    assert 'Mühendislik Uyarıları' in headings and 'Kontroller ve Notlar' in headings
    cells = ' '.join(c.text for t in doc.tables for r in t.rows for c in r.cells)
    assert 'Kayıtlı durumun açıklaması mevcut değil' not in cells and 'Bilgi' in cells


def test_subscripts_restored_in_formula():
    doc = Document(BytesIO(render_word(build('en'))))
    paragraph = next(p for p in doc.paragraphs if p.text.startswith('D = √'))
    assert any(run.font.subscript and run.text == 'm³/s' for run in paragraph.runs)
