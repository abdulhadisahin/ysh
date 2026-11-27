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

NAVY = colors.HexColor('#102B46')
GOLD = colors.HexColor('#F2B705')
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
    """Render the frozen report hierarchy. No calculator, project or Library access."""
    from reportlab.pdfgen import canvas as canvas_module
    from i18n.translator import Translator
    tr = Translator(report.language).translate
    font_root = ApplicationPaths().resource_root / 'resources' / 'fonts'
    for name, filename in (('D243', 'DejaVuSans.ttf'), ('D243Bold', 'DejaVuSans-Bold.ttf')):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(font_root / filename)))
    cyan = colors.HexColor('#1766C4')
    normal = ParagraphStyle('Body', fontName='D243', fontSize=8.5, leading=12, textColor=NAVY, spaceAfter=4)
    small = ParagraphStyle('Small', parent=normal, fontSize=7.5, leading=10)
    heading = ParagraphStyle('Section', parent=normal, fontName='D243Bold', fontSize=11,
                             leading=15, spaceBefore=12, spaceAfter=7, keepWithNext=True)
    title = ParagraphStyle('Title', parent=heading, fontSize=17, leading=22, spaceBefore=0)
    metric = ParagraphStyle('Metric', parent=normal, fontName='D243Bold', fontSize=25, leading=33, spaceAfter=7)
    caption = ParagraphStyle('Caption', parent=normal, fontName='D243Bold', fontSize=10, leading=14)
    step_title = ParagraphStyle('Step', parent=heading, fontSize=9.5, leading=13, spaceBefore=8)
    table_header = ParagraphStyle('TableHeader', parent=small, fontName='D243Bold', textColor=colors.white)
    def fmt(value):
        if isinstance(value, bool): return tr('report.yes' if value else 'report.no')
        text = format_number(value)
        return text.replace(',', '.') if report.language == 'en' and isinstance(value,(int,float)) else text
    def p(text, style=normal):
        text = re.sub(r'(?:[A-Za-z]:[\\/]|\\\\)[^\n;<>]*', tr('report.redacted'), str(text))
        return Paragraph(escape(text).replace('\n', '<br/>'), style)
    story = []
    def table(rows, widths, highlight=False):
        content = [[p(value, table_header if index==0 else small) for value in row]
                   for index,row in enumerate(rows)]
        tab = Table(content, colWidths=widths, repeatRows=1, splitInRow=1, hAlign='LEFT')
        tab.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'TOP'), ('BACKGROUND',(0,0),(-1,0),NAVY),
            ('LINEBELOW',(0,0),(-1,0),1,cyan),
            ('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#DDE3E8')),
            ('LEFTPADDING',(0,0),(-1,-1),6), ('RIGHTPADDING',(0,0),(-1,-1),6),
            ('TOPPADDING',(0,0),(-1,-1),5), ('BOTTOMPADDING',(0,0),(-1,-1),5),
        ] + ([('BOX',(0,0),(-1,-1),.7,cyan)] if highlight else [])))
        story.append(tab)
    def field_table(values, include_source=False):
        if not values:
            story.append(p(tr('report.empty'), small)); return
        if include_source:
            table([[tr('report.parameter'),tr('report.value'),tr('report.unit'),tr('report.source')]]+
                  [[r.label + (' ('+r.symbol+')' if r.symbol else ''),fmt(r.value),r.unit,
                    r.source or tr('report.not_recorded')] for r in values],
                  [WIDTH*.38,WIDTH*.19,WIDTH*.11,WIDTH*.32])
        else:
            table([[tr('report.parameter'),tr('report.value'),tr('report.unit')]]+
                  [[r.label + (' ('+r.symbol+')' if r.symbol else ''),fmt(r.value),r.unit] for r in values],
                  [WIDTH*.45,WIDTH*.42,WIDTH*.13])
    def section(number,key):
        story.append(p(str(number)+'. '+tr('report.'+key), heading))
    lockup = [p('D243', title), p(tr('report.title'), caption)]
    logo = d243_small_logo_path()
    if logo:
        image = Image(BytesIO(_print_image(str(logo), 17*mm, 17*mm)))
        image._restrictSize(17*mm,17*mm)
        header = Table([[image,lockup]], colWidths=[23*mm,WIDTH-23*mm])
        header.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                                   ('LINEBELOW',(0,0),(-1,-1),1,cyan),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        story.append(header)
    else: story.extend(lockup)
    story.extend([Spacer(1,4*mm),p(report.module.upper(), caption)])
    if report.module_code=='transfer_pump':
        story.append(p(tr('report.empirical' if report.stage=='empirical' else 'report.design'),small))
    context_rows = []
    if report.project_name: context_rows.append(ReportField(tr('report.project'),'',report.project_name))
    if report.system_family:
        context_rows.append(ReportField(tr('report.family'),'',tr('project.family.'+report.system_family)))
    context_rows.append(ReportField(tr('report.module'),'',report.module))
    if report.revision: context_rows.append(ReportField(tr('report.revision'),'',report.revision))
    technical_labels = {tr('report.field.snapshot'),tr('report.field.project_id')}
    context_rows += [row for row in report.identification if row.label not in technical_labels]
    section(1,'context');field_table(tuple(context_rows))
    section(2,'inputs');field_table(report.inputs,True)
    primary = report.primary_result
    primary_block = [p('3. '+tr('report.primary'),heading)]
    if primary:
        primary_block += [p(primary.label,caption),p(fmt(primary.value)+' '+primary.unit,metric)]
        if primary.source: primary_block.append(p(primary.source,small))
    else: primary_block.append(p(tr('report.empty'),small))
    story.append(KeepTogether(primary_block))
    section(4,'supporting')
    field_table(tuple(r for r in report.results if r != primary))
    for step_index,step in enumerate(report.formulas):
        block_start = len(story)
        if step_index == 0: section(5,'steps')
        formula = tr(step.formula_text) if step.formula_text.startswith('formula2.') else step.formula_text
        story.append(p(tr(step.title_key), step_title))
        story.append(p(tr('formula2.classification.'+step.classification.value), small))
        equation = None
        for key in step_asset_names(step):
            path = formula_asset_path(key)
            if path:
                equation = Image(BytesIO(_print_image(str(path),WIDTH*.72,35*mm)))
                equation._restrictSize(WIDTH*.72,35*mm);break
        if equation is None and formula in MATHTEXT_LINES:
            try:
                equation = Image(BytesIO(_math_image(formula)))
                equation.drawWidth = equation.imageWidth*72/300
                equation.drawHeight = equation.imageHeight*72/300
                equation._restrictSize(WIDTH*.90,20*mm)
            except (ValueError,RuntimeError): pass
        if equation is not None:
            equation.hAlign='CENTER';story.append(equation)
        story.append(p(formula,small))
        bindings = '; '.join(f'{v.symbol} = {fmt(v.value)} {v.unit}' for v in step.variables)
        if bindings: story.append(p(tr('report.substitution')+': '+bindings,small))
        if step.substitution: story.append(p(step.substitution,small))
        story.append(p(tr('report.result')+f': {step.result_symbol} = {fmt(step.result_value)} {step.result_unit}',caption))
        block = story[block_start:]
        del story[block_start:]
        story.append(KeepTogether(block))
    section(6,'warnings')
    if report.warning_items:
        table([[tr('report.status'),tr('report.module'),tr('report.message')]]+
              [[w.severity+' - '+tr('center.status.'+w.severity),w.context or report.module,w.message]
               for w in report.warning_items], [WIDTH*.20,WIDTH*.25,WIDTH*.55])
    if not any(item.severity != 'INFO' for item in report.warning_items):
        story.append(p(tr('report.no_warnings'),small))
    if report.engineering_basis_json:
        import json
        from engineering.basis import basis_rows
        story.append(p(tr('engineering.basis'),heading))
        table([[tr('report.parameter'),tr('report.value')]]+list(basis_rows(json.loads(report.engineering_basis_json),tr)),[WIDTH*.38,WIDTH*.62])
    section(7,'provenance')
    field_table(report.inputs, True)
    if report.selections:
        story.append(p(tr('report.selections'),step_title));field_table(report.selections)
    for index,source in enumerate(report.sources,1):
        story.append(p(tr('report.source')+' '+str(index),step_title))
        table([[tr('report.parameter'),tr('report.source')]]+[list(row) for row in source.rows],
              [WIDTH*.27,WIDTH*.73])
    approval = Table([
        ['',p(tr('report.prepared'),caption),p(tr('report.checked'),caption),p(tr('report.approved'),caption)],
        [p(tr('report.name'),small),'','',''],
        [p(tr('report.date'),small),'','',''],
        [p(tr('report.signature'),small),'','','']],
        colWidths=[WIDTH*.16,WIDTH*.28,WIDTH*.28,WIDTH*.28],rowHeights=[25,27,27,35])
    approval.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('BACKGROUND',(0,0),(-1,0),PALE),
        ('GRID',(0,0),(-1,-1),.4,colors.HexColor('#DDE3E8')),('LEFTPADDING',(0,0),(-1,-1),6)]))
    audit = list(report.metadata) + [row for row in report.identification if row.label in technical_labels]
    audit_text = ' | '.join(row.label+': '+fmt(row.value) for row in audit)
    story.append(KeepTogether([p('8. '+tr('report.approval'),heading), approval,
                               Spacer(1,3*mm),p(audit_text,small),p(tr('report.frozen'),small)]))
    output = BytesIO()
    document = SimpleDocTemplate(output,pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,
        topMargin=17*mm,bottomMargin=18*mm,title='D243 - '+report.module+' - '+tr('report.title'),
        author='D243',subject=tr('report.frozen'),creator='D243',invariant=1)
    identity = (report.project_name+' - ' if report.project_name else '')+report.module
    def footer(canvas, document):
        canvas.saveState();canvas.setStrokeColor(cyan)
        canvas.line(18*mm,14*mm,A4[0]-18*mm,14*mm)
        canvas.setFillColor(NAVY);canvas.setFont('D243',7)
        canvas.drawString(18*mm,10*mm,'D243 - '+identity[:62])
        canvas.restoreState()
    class NumberedCanvas(canvas_module.Canvas):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs);self._pages=[]
        def showPage(self):
            self._pages.append(dict(self.__dict__));self._startPage()
        def save(self):
            total=len(self._pages)
            for state in self._pages:
                self.__dict__.update(state)
                self.setFillColor(NAVY);self.setFont('D243',7)
                self.drawRightString(A4[0]-18*mm,10*mm,tr('report.page',page=self._pageNumber,total=total))
                super().showPage()
            super().save()
    document.build(story,onFirstPage=footer,onLaterPages=footer,canvasmaker=NumberedCanvas)
    return output.getvalue()
