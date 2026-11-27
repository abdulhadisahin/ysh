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

from reporting.word_presentation import ReportLanguage, basis_explanations

SOURCE_LABEL = "Kaynak / doğrulama"
NAVY = "163047"
CYAN = "119EAD"


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


def _symbol(value: str) -> str:
    """Render conventional camel-case internals as a secondary subscript symbol."""
    match = re.fullmatch(r"([A-Za-z]+)([a-z][A-Za-z]+)", value or "")
    return f"{match.group(1)}_{match.group(2)}" if match else value


WIDTHS = {2: (6.5, 10.5), 3: (3.2, 8.3, 5.5), 4: (6.6, 2.4, 4.2, 3.8), 5: (4.8, 2.0, 2.8, 2.0, 5.4)}


def _fix_widths(table, widths):
    layout = OxmlElement("w:tblLayout"); layout.set(qn("w:type"), "fixed"); table._tbl.tblPr.append(layout)
    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            cell.width = Cm(width)


def _table(document, headers, rows, widths=None):
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
            cells[index].text = str(value if value is not None else "—"); cells[index].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            pad(cells[index])
            if row_index%2:_cell_shading(cells[index],"F3F7FA")
            for paragraph in cells[index].paragraphs:paragraph.paragraph_format.space_after=Pt(2)
    widths = widths or WIDTHS.get(len(headers))
    if widths and len(widths) == len(headers): _fix_widths(table, widths)
    return table


FORMULA_SUBSCRIPT = re.compile(r"(?<![A-Za-z])([QDV])(m³/s|m³/h|i)(?![A-Za-z])")


def _formula_paragraph(document, text):
    """Plain-text formula with subscripts restored (Qm³/s -> Q with subscript m³/s, Di -> D with subscript i)."""
    paragraph = document.add_paragraph(); position = 0
    for match in FORMULA_SUBSCRIPT.finditer(text):
        paragraph.add_run(text[position:match.start()] + match.group(1))
        paragraph.add_run(match.group(2)).font.subscript = True
        position = match.end()
    paragraph.add_run(text[position:])
    return paragraph


def render_word(report) -> bytes:
    """Create an editable A4 DOCX from frozen report data; performs no engineering work."""
    ui = ReportLanguage(report.language); tr = ui.tr; doc = Document()
    section = doc.sections[0]; section.page_width=Cm(21); section.page_height=Cm(29.7)
    section.top_margin=Cm(1.8); section.bottom_margin=Cm(1.7); section.left_margin=Cm(2); section.right_margin=Cm(2)
    normal = doc.styles["Normal"]; normal.font.name="Aptos"; normal.font.size=Pt(10); normal.font.color.rgb=RGBColor.from_string(NAVY)
    for style_name,size in (("Title",22),("Heading 1",14),("Heading 2",11)):
        style=doc.styles[style_name]; style.font.name="Aptos Display"; style.font.size=Pt(size); style.font.bold=True; style.font.color.rgb=RGBColor.from_string(NAVY)
    header=section.header.paragraphs[0]; header.text="D243  |  "+tr("report.title"); header.runs[0].bold=True; header.runs[0].font.color.rgb=RGBColor.from_string(CYAN)
    footer=section.footer.paragraphs[0]; footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT; footer.add_run("D243  ·  "+tr("word.page")+" "); _page_field(footer,"PAGE")
    title=doc.add_paragraph(style="Title"); title.add_run("D243 — "+tr("report.title"))
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
            [(ui.label(f.label,f.symbol,f.unit),_symbol(f.symbol),ui.number(f.value),ui.text(f.unit),ui.source(f.source)) for f in input_rows])
    if report.selections:
        doc.add_heading(tr("report.selections"),1)
        safe_selections=[f for f in report.selections if not any(token in f.label.casefold() for token in ("uuid","kimliği","identity","revision","schema","model"))]
        if safe_selections:
            _table(doc,(tr("report.parameter"),tr("report.value")),[(ui.label(f.label,f.symbol,f.unit),ui.source(f.value) if f.label==SOURCE_LABEL else ui.text(ui.number(f.value))) for f in safe_selections])
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
        _table(doc,(tr("report.parameter"),tr("word.symbol"),tr("report.value"),tr("report.unit")),result_rows)

    if report.formulas:
        doc.add_heading(tr("report.steps"),1)
        for index,step in enumerate(report.formulas,1):
            doc.add_heading(f"{index}. {ui.text(tr(step.title_key))}",2)
            if step.formula_text:
                if re.fullmatch(r'formula2\.[\w.]+',step.formula_text): doc.add_paragraph(ui.text(tr(step.formula_text)))
                else: _formula_paragraph(doc,ui.text(step.formula_text))
            vars_rows=[(ui.text(tr(item.terminology_key)),_symbol(item.symbol),ui.number(item.value),ui.text(item.unit)) for item in step.variables+step.reference_variables]
            if vars_rows: _table(doc,(tr("report.parameter"),tr("word.symbol"),tr("report.value"),tr("report.unit")),vars_rows)
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
            [(ui.text(p.name),ui.number(p.fuel_capacity_m3),ui.number(p.pump_capacity_m3_h),ui.text(p.source) or tr("report.source_required"),ui.status(p.verification)) for p in graph.references])
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
        doc.add_heading(tr("report.provenance"),1)
        rows=[]
        for source in report.sources:
            rows.extend((ui.text(label),ui.text(value)) for label,value in source.rows)
        if rows: _table(doc,(tr("report.parameter"),tr("report.value")),rows)
    from reporting.reference_catalog import references_for
    refs=references_for(report.module_code,report.system_family)
    if refs:
        en=report.language=='en'
        doc.add_heading("References" if en else "Referanslar",1)
        _table(doc,("Document" if en else "Doküman","Table / clause" if en else "Tablo / madde","Used for" if en else "Kullanım","Basis" if en else "Dayanak"),
            [(r.document+("\n"+r.url if r.url else ""),r.table,r.use_en if en else r.use_tr,
              ("Primary" if r.basis=="primary" else "Secondary (quoted)") if en else ("Birincil" if r.basis=="primary" else "İkincil (alıntı)")) for r in refs],
            widths=(6.0,3.2,5.8,2.0))
    doc.add_heading(tr("report.approval"),1)
    _table(doc,(tr("report.checked"),tr("report.signature"),tr("report.date")),[("\n\n", "\n\n", "\n\n")])
    doc.add_paragraph(tr("word.frozen"),style="Caption")
    output=BytesIO(); doc.save(output); return output.getvalue()
