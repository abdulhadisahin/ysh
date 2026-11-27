from io import BytesIO
from docx import Document
from reporting.word_presentation import ReportLanguage, clean_label, symbol_segments
from reporting.word_renderer import _math_png, _ref_text


def test_symbols_become_localized_subscripts():
    assert symbol_segments('Vfuel', 'tr') == [('V', False), ('yakıt', True)]
    assert symbol_segments('Qpump', 'en') == [('Q', False), ('pump', True)]
    assert symbol_segments('tdef', 'tr') == [('t', False), ('hedef', True)]
    assert symbol_segments('Qgerekli = Vtransfer / tdef', 'tr')[1] == ('gerekli', True)


def test_labels_have_no_symbol_or_unit_garble():
    ui = ReportLanguage('tr')
    assert ui.label('Transfer hacmi Vtransfer (m³)', 'Vtransfer', 'm³') == 'Transfer hacmi'
    assert clean_label('Seçili tulumba kapasitesi Qtulumba (m³/h, isteğe bağlı)') == 'Seçili tulumba kapasitesi (isteğe bağlı)'


def test_reference_cells_turkish():
    assert _ref_text('Table 1 (distillates)', False) == 'Tablo 1 (distilatlar)'
    assert _ref_text('Table 1 (distillates)', True) == 'Table 1 (distillates)'


def test_math_png_for_turkish_formula():
    assert _math_png('Qgerekli = Vtransfer / tdef', 'tr')[:4] == b'\x89PNG'
    assert _math_png('unknown formula', 'tr') is None


def test_word_report_carries_identity_accents():
    from io import BytesIO
    from zipfile import ZipFile
    from reporting.word_renderer import GOLD, NAVY, _rule
    from docx import Document
    assert (NAVY, GOLD) == ('102B46', 'F2B705')
    paragraph = Document().add_paragraph('x'); _rule(paragraph)
    assert 'F2B705' in paragraph._p.xml
