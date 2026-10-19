"""A4 ReportLab renderer. Only immutable report data and bundled assets are read."""
from __future__ import annotations

from io import BytesIO
from functools import lru_cache
from pathlib import Path
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether

from paths import ApplicationPaths
from reporting.equations import MATHTEXT_LINES
from reporting.models import EngineeringReport, ReportField, format_number, _TR
from ui.assets import formula_asset_path, d243_small_logo_path
from ui.formula_asset_policy import step_asset_names

NAVY = colors.HexColor('#163047')
GOLD = colors.HexColor('#CBB78F')
PALE = colors.HexColor('#F2F5F7')
WIDTH = A4[0] - 36 * mm


@lru_cache(maxsize=24)
def _print_image(path: str, max_width: float, max_height: float) -> bytes:
    """Embed at 300 DPI without cropping, stretching, or enlarging source pixels."""
    from PIL import Image as PillowImage
    with PillowImage.open(path) as source:
        source.thumbnail((round(max_width / 72 * 300), round(max_height / 72 * 300)),
                         PillowImage.Resampling.LANCZOS)
        output = BytesIO()
        source.save(output, format='PNG', optimize=True)
        return output.getvalue()


@lru_cache(maxsize=64)
def _math_image(formula: str) -> bytes:
    """Cache in-memory print equations; no temporary files are created."""
    from matplotlib.mathtext import math_to_image
    buffer = BytesIO()
    math_to_image('$' + MATHTEXT_LINES[formula] + '$', buffer, dpi=300, format='png')
    return buffer.getvalue()


def render_pdf(report: EngineeringReport) -> bytes:
    """Render searchable text to memory without Tk, calculations or current repositories."""
    font_root = ApplicationPaths().resource_root / 'resources' / 'fonts'
    for name, filename in (('D243', 'DejaVuSans.ttf'), ('D243Bold', 'DejaVuSans-Bold.ttf')):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(font_root / filename)))
    normal = ParagraphStyle('Body', fontName='D243', fontSize=8.5, leading=12, textColor=NAVY, spaceAfter=4)
    small = ParagraphStyle('Small', parent=normal, fontSize=7.5, leading=10)
    heading = ParagraphStyle('Section', parent=normal, fontName='D243Bold', fontSize=11,
                             leading=15, spaceBefore=13, spaceAfter=7, keepWithNext=True)
    title = ParagraphStyle('Title', parent=heading, fontSize=16, leading=21)
    step_title = ParagraphStyle('Step', parent=heading, fontSize=9.5, leading=13, spaceBefore=8)
    def p(text: object, style: ParagraphStyle = normal) -> Paragraph:
        text = re.sub(r'(?:[A-Za-z]:[\\/]|\\\\)[^\n;<>]*', '[yerel dosya yolu gizlendi]', str(text))
        return Paragraph(escape(text).replace('\n', '<br/>'), style)
    story = []
    logo = d243_small_logo_path()
    lockup = [p('D243', title), p('Boru ve Tulumba Boyutlandırma Programı')]
    if logo:
        image = Image(BytesIO(_print_image(str(logo), 22*mm, 22*mm))); image._restrictSize(22*mm, 22*mm)
        header = Table([[image, lockup]], colWidths=[27*mm, WIDTH-27*mm])
        header.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LINEBELOW',(0,0),(-1,-1),1,GOLD)]))
        story.append(header)
    else:
        story.extend(lockup)
    story.extend([Spacer(1, 6*mm), p(report.module.upper() + ' HESAP RAPORU', title)])
    if report.stage == 'empirical':
        story.append(p('AMPİRİK / REFERANS GEMİ TAHMİNİ - regresyon modeli'))
    elif report.module == 'Yakıt Transfer Tulumbası':
        story.append(p('DESIGN - hacim ve süre temelli tasarım hesabı'))
    def table(rows: list[list[object]], widths: list[float], highlight: bool = False) -> None:
        content = [[p(value, small) for value in row] for row in rows]
        tab = Table(content, colWidths=widths, repeatRows=1, splitInRow=1, hAlign='LEFT')
        tab.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'TOP'), ('BACKGROUND',(0,0),(-1,0),PALE),
            ('LINEBELOW',(0,0),(-1,0),.7,GOLD), ('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#DDE3E8')),
            ('LEFTPADDING',(0,0),(-1,-1),6), ('RIGHTPADDING',(0,0),(-1,-1),6),
            ('TOPPADDING',(0,0),(-1,-1),5), ('BOTTOMPADDING',(0,0),(-1,-1),5),
        ] + ([('BOX',(0,0),(-1,-1),.8,GOLD)] if highlight else [])))
        story.append(tab)
    def field_table(values: tuple[ReportField, ...], highlight: bool = False) -> None:
        if not values:
            story.append(p('Bu hesap kaydında ek veri bulunmamaktadır.'))
            return
        table([['Parametre', 'Sembol', 'Değer', 'Birim']] +
              [[r.label, r.symbol, format_number(r.value), r.unit] for r in values],
              [WIDTH*.37, WIDTH*.13, WIDTH*.37, WIDTH*.13], highlight)
    def section(number: int, name: str) -> None:
        story.append(p(f'{number}. {name}', heading))
    section(1, 'Rapor Bilgileri'); field_table(report.identification)
    section(2, 'Girdi Verileri'); field_table(report.inputs)
    section(3, 'Kullanılan Katsayılar / Seçimler'); field_table(report.selections)
    for step_index, step in enumerate(report.formulas):
        formula = _TR(step.formula_text) if step.formula_text.startswith('formula2.') else step.formula_text
        block = ([p('4. Hesap Adımları', heading)] if step_index == 0 else []) + [p(_TR(step.title_key), step_title),
                 p(_TR('formula2.classification.' + step.classification.value), small)]
        equation = None
        for key in step_asset_names(step):
            path = formula_asset_path(key)
            if path:
                equation = Image(BytesIO(_print_image(str(path), WIDTH*.72, 43*mm))); equation._restrictSize(WIDTH*.72, 43*mm)
                break
        if equation is None and formula in MATHTEXT_LINES:
            try:
                equation = Image(BytesIO(_math_image(formula)))
                equation.drawWidth = equation.imageWidth * 72 / 300
                equation.drawHeight = equation.imageHeight * 72 / 300
                equation._restrictSize(WIDTH*.90, 22*mm)
            except (ValueError, RuntimeError):
                equation = None
        if equation is not None:
            equation.hAlign = 'CENTER'; block.append(equation)
        # Always retain the exact frozen expression as searchable text.
        block.append(p(formula, small))
        bindings = '; '.join(f'{v.symbol} = {format_number(v.value)} {v.unit}' for v in step.variables)
        if bindings:
            block.append(p('Yerine koyma: ' + bindings, small))
        if step.substitution:
            block.append(p(step.substitution, small))
        block.append(p(f'Sonuç: {step.result_symbol} = {format_number(step.result_value)} {step.result_unit}'))
        story.append(KeepTogether(block))
    section(5, 'Sonuçlar'); field_table(report.results, True)
    section(6, 'Uyarılar / Uygunluk')
    for warning in report.warnings or ('Bu hesap kaydında ek uyarı bulunmamaktadır.',):
        story.append(p(warning))
    section(7, 'Kaynaklar ve Doğrulama')
    for index, source in enumerate(report.sources, 1):
        story.append(p(f'Kaynak {index}', step_title))
        table([['Alan', 'Kayıtlı kaynak bilgisi']] + [list(row) for row in source.rows], [WIDTH*.27, WIDTH*.73])
    if not report.sources:
        story.append(p('Bu hesap kaydında ek kaynak bilgisi bulunmamaktadır.'))
    section(8, 'Rapor Meta Bilgisi'); field_table(report.metadata)
    story.append(p('Rapor içeriği saklanan D243 hesap snapshot kaydını yansıtır.', small))
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
        topMargin=17*mm, bottomMargin=18*mm, title=f'D243 - {report.module} Hesap Raporu',
        author='D243', subject='Snapshot tabanlı mühendislik hesap raporu',
        creator='D243 Boru ve Tulumba Boyutlandırma Programı', invariant=1)
    def footer(canvas: object, _document: object) -> None:
        canvas.saveState(); canvas.setStrokeColor(GOLD)
        canvas.line(18*mm, 14*mm, A4[0]-18*mm, 14*mm)
        canvas.setFillColor(NAVY); canvas.setFont('D243', 7)
        canvas.drawString(18*mm, 10*mm, 'D243 · ' + report.snapshot_id[:8])
        canvas.drawRightString(A4[0]-18*mm, 10*mm, f'Sayfa {canvas.getPageNumber()}')
        canvas.restoreState()
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
