"""Editable Word report renderer consuming only an immutable EngineeringReport."""
from __future__ import annotations

from io import BytesIO
import re

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from reporting.word_presentation import ReportLanguage, basis_explanations, USER_SOURCE_KEYS

SOURCE_LABEL = "Kaynak / doğrulama"
NAVY = "102B46"
CYAN = "1766C4"
GOLD = "F2B705"
GOLD_SOFT = "FFF8DC"


def _cell_shading(cell, fill: str) -> None:
    props = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd"); shading.set(qn("w:fill"), fill); props.append(shading)


def _repeat_header(row) -> None:
    props = row._tr.get_or_add_trPr(); marker = OxmlElement("w:tblHeader"); marker.set(qn("w:val"), "true"); props.append(marker)


def _no_split(row) -> None:
    row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))


def _page_field(paragraph, instruction: str) -> None:
    run = paragraph.add_run(); begin = OxmlElement("w:fldChar"); begin.set(qn("w:fldCharType"), "begin")
    text = OxmlElement("w:instrText"); text.set(qn("xml:space"), "preserve"); text.text = instruction
    separate = OxmlElement("w:fldChar"); separate.set(qn("w:fldCharType"), "separate")
    value = OxmlElement("w:t"); value.text = "1"
    end = OxmlElement("w:fldChar"); end.set(qn("w:fldCharType"), "end")
    for item in (begin, text, separate, value, end): run._r.append(item)


class Sym(str):
    """A symbol cell: written with real subscript runs (language set by render_word)."""
    language = "tr"


def _symbol(value: str) -> str:
    return Sym(value) if value else value


def _write_runs(paragraph, text, language, size=None, bold=False):
    from reporting.word_presentation import symbol_segments
    for part, sub in symbol_segments(text, language):
        run = paragraph.add_run(part)
        if sub: run.font.subscript = True
        if size: run.font.size = Pt(size)
        if bold: run.bold = True


WIDTHS = {2: (6.5, 10.5), 3: (3.2, 8.3, 5.5), 4: (6.6, 2.4, 4.2, 3.8), 5: (4.8, 2.0, 2.8, 2.0, 5.4)}


def _fix_widths(table, widths):
    layout = OxmlElement("w:tblLayout"); layout.set(qn("w:type"), "fixed"); table._tbl.tblPr.append(layout)
    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            cell.width = Cm(width)


def _table(document, headers, rows, widths=None, language="tr", highlight_first=False):
    table = document.add_table(rows=1, cols=len(headers)); table.style = "Table Grid"
    table.autofit = True; _repeat_header(table.rows[0])
    borders=OxmlElement("w:tblBorders")
    for edge in ("top","left","bottom","right","insideH","insideV"):
        item=OxmlElement("w:"+edge);item.set(qn("w:val"),"single");item.set(qn("w:sz"),"4");item.set(qn("w:color"),"D9D9D9");borders.append(item)
    table._tbl.tblPr.append(borders)
    def pad(cell):
        margins=OxmlElement("w:tcMar")
        for side,value in (("top","90"),("left","110"),("bottom","90"),("right","110")):
            node=OxmlElement("w:"+side);node.set(qn("w:w"),value);node.set(qn("w:type"),"dxa");margins.append(node)
        cell._tc.get_or_add_tcPr().append(margins)
    for index, title in enumerate(headers):
        cell = table.rows[0].cells[index]; cell.text = str(title); _cell_shading(cell, NAVY)
        pad(cell)
        for run in cell.paragraphs[0].runs: run.bold = True; run.font.color.rgb = RGBColor(255,255,255)
    for row_index,values in enumerate(rows):
        cells = table.add_row().cells; _no_split(table.rows[-1])
        for index, value in enumerate(values):
            if isinstance(value, Sym):
                cells[index].text = ""; _write_runs(cells[index].paragraphs[0], str(value), language)
            else: cells[index].text = str(value if value is not None else "—")
            cells[index].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            pad(cells[index])
            if highlight_first and row_index==0:
                _cell_shading(cells[index],GOLD_SOFT)
                for run in cells[index].paragraphs[0].runs: run.bold = True
            elif row_index%2:_cell_shading(cells[index],"F3F7FA")
            for paragraph in cells[index].paragraphs:paragraph.paragraph_format.space_after=Pt(2)
    widths = widths or WIDTHS.get(len(headers))
    if widths and len(widths) == len(headers): _fix_widths(table, widths)
    return table


FORMULA_PT = 15
INTERNAL_FORMULA = re.compile(r"formula2\.[\w.]+")
# Turkish/English subscript words inside the shared mathtext sources.
MATH_WORDS = {"fuel": {"tr": "yakıt", "en": "fuel"}, "pump": {"tr": "tulumba", "en": "pump"},
              "def": {"tr": "hedef", "en": "target"}, "gerekli": {"tr": "gerekli", "en": "required"},
              "tulumba": {"tr": "tulumba", "en": "pump"}}
WORD_MATHTEXT = {
    "Qgerekli = Vtransfer / tdef": r"Q_{\mathrm{gerekli}} = \frac{V_{\mathrm{transfer}}}{t_{\mathrm{def}}}",
    "ttransfer = Vtransfer / Qtulumba": r"t_{\mathrm{transfer}} = \frac{V_{\mathrm{transfer}}}{Q_{\mathrm{tulumba}}}",
}


def _math_png(formula: str, language: str):
    """Typeset an accepted equation with the application's own mathtext sources (no new engineering)."""
    from reporting.equations import MATHTEXT_LINES
    source = WORD_MATHTEXT.get(formula) or MATHTEXT_LINES.get(formula)
    if not source: return None
    for word, names in MATH_WORDS.items():
        source = source.replace(r"\mathrm{%s}" % word, r"\mathrm{%s}" % names[language if language in names else "en"])
    try:
        from matplotlib.mathtext import math_to_image
        buffer = BytesIO(); math_to_image("$" + source + "$", buffer, dpi=300, format="png")
        return buffer.getvalue()
    except Exception: return None


def _asset_png(step):
    """Audited formula artwork for this stored step (never quarantined ones), trimmed and on white."""
    try:
        from ui.formula_asset_policy import step_asset_names
        from ui.assets import formula_asset_path
        from PIL import Image
        for name in step_asset_names(step):
            path = formula_asset_path(name)
            if not path or not path.exists(): continue
            image = Image.open(path).convert("RGBA"); box = image.getbbox()
            if box: image = image.crop(box)
            sheet = Image.new("RGBA", (image.width + 40, image.height + 40), (255, 255, 255, 255))
            sheet.alpha_composite(image, (20, 20)); output = BytesIO(); sheet.convert("RGB").save(output, "PNG")
            return output.getvalue()
    except Exception: return None
    return None


def _formula_block(document, step, text, language):
    """One formula: audited artwork, else typeset image, else large centered text with real subscripts."""
    png = _asset_png(step); wide = Cm(11.0)
    if png is None:
        png = _math_png(step.formula_text, language); wide = None
    if png is not None:
        paragraph = document.add_paragraph(); paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_before = Pt(6); paragraph.paragraph_format.space_after = Pt(8)
        run = paragraph.add_run()
        if wide is not None: run.add_picture(BytesIO(png), width=wide)
        else:
            from PIL import Image
            with Image.open(BytesIO(png)) as image: width_cm = image.width / 300 * 2.54 * 1.6
            run.add_picture(BytesIO(png), width=Cm(min(max(width_cm, 3.5), 14.5)))
        return paragraph
    return _formula_paragraph(document, text, language)


def _formula_paragraph(document, text, language="tr"):
    """Large, centered, shaded formula line(s); symbols carry real subscripts."""
    paragraph = document.add_paragraph(); paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(6); paragraph.paragraph_format.space_after = Pt(8)
    shading = OxmlElement("w:shd"); shading.set(qn("w:val"), "clear"); shading.set(qn("w:fill"), "EEF5F8")
    paragraph._p.get_or_add_pPr().append(shading)
    for index, line in enumerate(str(text).split("\n")):
        if index: paragraph.add_run().add_break()
        _write_runs(paragraph, line, language, size=FORMULA_PT, bold=True)
    return paragraph


REF_TR = (("Tables ", "Tablolar "), ("Table ", "Tablo "), (" and ", " ve "), ("distillates", "distilatlar"),
          ("Standard wall series", "Standart et kalınlığı serisi"), ("Dimension tables", "Boyut tabloları"),
          ("Typical maximum velocity table", "Tipik azami hız tablosu"), ("Density Eqs.", "Yoğunluk denk."),
          ("viscosity Eqs.", "viskozite denk."), ("NPSH margin", "ENPY (NPSH) payı"), ("Section", "Bölüm"),
          ("series", "seri"), ("Part 107 Ch.8 (Jan 2022)", "Kısım 107 Bölüm 8 (Ocak 2022)"),
          ("Chapter 11 - Fire Fighting Ships (2019)", "Bölüm 11 – Yangın Söndürme Gemileri (2019)"),
          ("Pipe Frictional Losses", "Boru Sürtünme Kayıpları"), ("Data Tool", "Veri Aracı"),
          ("Product Guide", "Ürün Kılavuzu"), ("brochure", "broşür"), ("Thermophysical Properties Library", "Termofiziksel Özellikler Kütüphanesi"),
          ("Seawater system design (cites", "Deniz suyu sistem tasarımı (atıf:"), ("seawater system design (cites", "deniz suyu sistem tasarımı (atıf:"))


def _ref_text(value, english):
    if english: return value
    for source, target in REF_TR: value = value.replace(source, target)
    return value


def _logo(document):
    """D243 patch at the top right of the first page; silently skipped if the resource is absent."""
    try:
        from ui.assets import branding_asset_path, D243_LOGO_SMALL
        path = branding_asset_path(D243_LOGO_SMALL)
        if not path: return
        paragraph = document.add_paragraph(); paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.add_run().add_picture(str(path), width=Cm(2.6))
    except Exception: return


def _rule(paragraph, color=GOLD, size="18"):
    """Gold rule under a heading (identity accent)."""
    border = OxmlElement("w:pBdr"); line = OxmlElement("w:bottom")
    for key, value in (("val", "single"), ("sz", size), ("space", "4"), ("color", color)): line.set(qn("w:" + key), value)
    border.append(line); paragraph._p.get_or_add_pPr().append(border)


def _banner(paragraph):
    """Navy title band with a gold underline: the report's visible identity block."""
    pPr = paragraph._p.get_or_add_pPr()
    shade = OxmlElement("w:shd")
    for key, value in (("val", "clear"), ("color", "auto"), ("fill", NAVY)): shade.set(qn("w:" + key), value)
    pPr.append(shade)
    paragraph.paragraph_format.left_indent = Cm(0.2); paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(10)
    for run in paragraph.runs: run.font.color.rgb = RGBColor.from_string("FFFFFF")
    _rule(paragraph, GOLD, "36")


def _heading_bar(style):
    """Gold bar to the left of every first-level heading."""
    pPr = style.element.get_or_add_pPr(); border = OxmlElement("w:pBdr"); line = OxmlElement("w:left")
    for key, value in (("val", "single"), ("sz", "36"), ("space", "6"), ("color", GOLD)): line.set(qn("w:" + key), value)
    border.append(line); pPr.append(border)


def render_word(report) -> bytes:
    """Create an editable A4 DOCX from frozen report data; performs no engineering work."""
    ui = ReportLanguage(report.language); tr = ui.tr; doc = Document()
    section = doc.sections[0]; section.page_width=Cm(21); section.page_height=Cm(29.7)
    section.top_margin=Cm(1.8); section.bottom_margin=Cm(1.7); section.left_margin=Cm(2); section.right_margin=Cm(2)
    normal = doc.styles["Normal"]; normal.font.name="Aptos"; normal.font.size=Pt(10); normal.font.color.rgb=RGBColor.from_string(NAVY)
    for style_name,size in (("Title",22),("Heading 1",14),("Heading 2",11)):
        style=doc.styles[style_name]; style.font.name="Aptos Display"; style.font.size=Pt(size); style.font.bold=True; style.font.color.rgb=RGBColor.from_string(NAVY)
    _heading_bar(doc.styles["Heading 1"]); doc.styles["Heading 1"].font.color.rgb=RGBColor.from_string(CYAN)
    header=section.header.paragraphs[0]; header.text="D243  |  "+tr("report.title"); header.runs[0].bold=True; header.runs[0].font.color.rgb=RGBColor.from_string(CYAN)
    footer=section.footer.paragraphs[0]; footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT; footer.add_run("D243  ·  "+tr("word.page")+" "); _page_field(footer,"PAGE")
    _logo(doc)
    title=doc.add_paragraph(style="Title"); title.add_run("D243 — "+tr("report.title")); _banner(title)
    doc.add_paragraph(tr("word.intro",module=ui.text(report.module)))
    doc.add_heading(tr("report.project"),1)
    identity=[]
    if report.project_name: identity.append((tr("report.project"),ui.plain(report.project_name)))
    if report.system_family: identity.append((tr("report.family"),tr("word.family."+report.system_family)))
    identity.append((tr("report.module"),ui.text(report.module)))
    identity.append((tr("report.field.date"),report.created_at.strftime("%Y-%m-%d %H:%M")))
    context_keys={tr("report.field.system"),tr("report.field.circuit"),tr("report.field.fluid")}
    identity.extend((ui.text(field.label),ui.plain(field.value)) for field in report.identification
                    if field.label in context_keys and field.value not in (None,""))
    if report.revision is not None:identity.append((tr("report.revision"),ui.text(report.revision)))
    _table(doc,(tr("report.parameter"),tr("report.value")),identity)

    input_rows=list(report.inputs)+list(report.transfer_details)
    if input_rows:
        doc.add_heading(tr("report.inputs"),1)
        _table(doc,(tr("report.parameter"),tr("word.symbol"),tr("report.value"),tr("report.unit"),tr("report.source")),
            [(ui.label(f.label,f.symbol,f.unit),_symbol(f.symbol),ui.number(f.value),ui.text(f.unit),ui.source(f.source)) for f in input_rows],language=report.language)
    if report.selections:
        safe_selections=[f for f in report.selections if not any(token in f.label.casefold() for token in ("uuid","kimliği","identity","revision","schema","model"))]
        selection_rows=[(ui.label(f.label,f.symbol,f.unit),ui.source(f.value) if f.label==SOURCE_LABEL else ui.text(ui.number(f.value))) for f in safe_selections]
        selection_rows=[row for row in selection_rows if not (row[0]==SOURCE_LABEL and row[1]=='-')]
        if selection_rows:
            doc.add_heading(tr("report.selections"),1)
            _table(doc,(tr("report.parameter"),tr("report.value")),selection_rows)
    if report.engineering_basis_json:
        import json
        try: explanations=basis_explanations(json.loads(report.engineering_basis_json),report.language)
        except (ValueError,TypeError,KeyError): explanations=()
        for explanation in explanations: doc.add_paragraph(ui.text(explanation))

    if report.primary_result or report.results:
        doc.add_heading(tr("report.primary"),1)
        result_rows=[]
        if report.primary_result:
            field=report.primary_result; result_rows.append((ui.label(field.label,field.symbol,field.unit),_symbol(field.symbol),ui.number(field.value),ui.text(field.unit)))
        for field in report.results:
            if field is not report.primary_result and (not report.primary_result or (field.symbol,field.value,field.unit)!=(report.primary_result.symbol,report.primary_result.value,report.primary_result.unit)):
                result_rows.append((ui.label(field.label,field.symbol,field.unit),_symbol(field.symbol),ui.number(field.value),ui.text(field.unit)))
        _table(doc,(tr("report.parameter"),tr("word.symbol"),tr("report.value"),tr("report.unit")),result_rows,language=report.language,highlight_first=True)

    if report.formulas:
        doc.add_heading(tr("report.steps"),1)
        for index,step in enumerate(report.formulas,1):
            doc.add_heading(f"{index}. {ui.text(tr(step.title_key))}",2)
            if step.formula_text:
                if INTERNAL_FORMULA.fullmatch(step.formula_text): _formula_paragraph(doc,tr(step.formula_text),report.language)
                else: _formula_block(doc,step,step.formula_text,report.language)
            vars_rows=[(ui.label(tr(item.terminology_key),item.symbol,item.unit),_symbol(item.symbol),ui.number(item.value),ui.text(item.unit)) for item in step.variables+step.reference_variables]
            if vars_rows: _table(doc,(tr("report.parameter"),tr("word.symbol"),tr("report.value"),tr("report.unit")),vars_rows,language=report.language)
            if step.substitution: doc.add_paragraph(ui.text(step.substitution))
            if step.result_value is not None: doc.add_paragraph(f"{tr('report.result')}: {ui.number(step.result_value)} {ui.text(step.result_unit)}")

    graph=report.transfer_graph
    if graph:
        doc.add_heading(tr("word.graph.title"),1)
        from reporting.transfer_graph import render_transfer_graph
        image=render_transfer_graph(graph,tr); doc.add_picture(BytesIO(image),width=Cm(15.5))
        doc.add_paragraph(tr("word.graph.note"))
        doc.add_heading(tr("word.graph.references"),2)
        _table(doc,(tr("word.reference_vessel"),tr("word.graph.x"),tr("word.graph.y"),tr("report.source"),tr("report.status")),
            [(ui.text(p.name),ui.number(p.fuel_capacity_m3),ui.number(p.pump_capacity_m3_h),ui.text(p.source) or "-",ui.status(p.verification)) for p in graph.references])
        stats=[(tr("word.transfer.equation"),f"Q = {ui.number(graph.slope)} V + {ui.number(graph.intercept)}"),
            (tr("word.transfer.r2"),ui.number(graph.r_squared) if graph.r_squared is not None else "—"),
            (tr("word.transfer.predicted"),ui.number(graph.predicted_capacity_m3_h) if graph.predicted_capacity_m3_h is not None else "—"),
            (tr("word.transfer.average"),ui.number(graph.required_average_m3_h) if graph.required_average_m3_h is not None else "—"),
            (tr("word.transfer.time"),ui.number(graph.transfer_time_h) if graph.transfer_time_h is not None else "—")]
        _table(doc,(tr("report.parameter"),tr("report.value")),stats)
    elif report.module_code=="transfer_pump" and report.stage=="empirical": doc.add_paragraph(tr("word.transfer.no_graph"))
    elif report.module_code=="transfer_pump": doc.add_paragraph(tr("word.transfer.design_note"))

    warning_rows=[]
    for item in report.warning_items:
        warning_rows.append((ui.severity(item.severity),ui.text(item.message),ui.text(item.context)))
    notes=[row for item,row in zip(report.warning_items,warning_rows) if item.severity=='INFO']
    warning_rows=[row for item,row in zip(report.warning_items,warning_rows) if item.severity!='INFO']
    if warning_rows:
        doc.add_heading(tr("report.warnings"),1); _table(doc,(tr("report.status"),tr("report.message"),tr("report.context")),warning_rows)
    if notes:
        doc.add_heading(tr("word.checks_notes"),1); _table(doc,(tr("report.status"),tr("report.message"),tr("report.context")),notes)
    if report.sources:
        # One compact line per distinct origin; "entered by the user" is self-evident and is not repeated.
        type_label=tr('formula2.source.source_type'); own={tr(key).casefold() for key in USER_SOURCE_KEYS}; rows=[]
        for source in report.sources:
            values=[(label,ui.text(value)) for label,value in source.rows]
            kind=next((value for label,value in values if label==type_label),'')
            detail=' · '.join(value for label,value in values if label!=type_label and value and value.casefold() not in own)
            if kind.casefold() in own and not detail: continue
            row=(kind or '—',detail or '—')
            if row not in rows: rows.append(row)
        if rows:
            doc.add_heading(tr("report.provenance"),1)
            _table(doc,(tr("report.source"),tr("word.source_detail")),rows,widths=(5.0,12.0))
    from reporting.reference_catalog import references_for
    refs=references_for(report.module_code,report.system_family)
    if refs:
        en=report.language=='en'
        doc.add_heading("References" if en else "Referanslar",1)
        _table(doc,("Document" if en else "Doküman","Table / clause" if en else "Tablo / madde","Used for" if en else "Kullanım","Basis" if en else "Dayanak"),
            [(_ref_text(r.document,en)+("\n"+r.url if r.url else ""),_ref_text(r.table,en),r.use_en if en else r.use_tr,
              ("Primary" if r.basis=="primary" else "Secondary (quoted)") if en else ("Birincil" if r.basis=="primary" else "İkincil (alıntı)")) for r in refs],
            widths=(6.0,3.2,5.8,2.0))
    doc.add_heading(tr("report.approval"),1)
    _table(doc,(tr("report.checked"),tr("report.signature"),tr("report.date")),[("\n\n", "\n\n", "\n\n")])
    doc.add_paragraph(tr("word.frozen"),style="Caption")
    output=BytesIO(); doc.save(output); return output.getvalue()
