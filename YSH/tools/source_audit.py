"""Read-only engineering source inventory; outputs never write a user database."""
from __future__ import annotations
import argparse
import ast
from collections import Counter
import hashlib
from html import escape
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
if not __package__ and str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from engineering.source_verification import AUDIT_DATE, SOURCES, record_evidence

TABLES=('sources','rule_sets','fluid_specifications','material_surfaces','engineering_rules',
        'materials','engineering_constants','pump_references','fluid_properties','material_properties',
        'pipe_standards','pipe_sizes','pipe_standard_metadata','pipe_size_metadata',
        'engineering_constant_metadata','corrosion_allowance_sources','corrosion_allowance_circuits')


def audit_database(path):
    """Use SQLite read-only mode, including for old schemas; never initialize/seed."""
    path=Path(path).resolve()
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    connection=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    connection.row_factory=sqlite3.Row
    records=[];counts={}
    try:
        connection.execute('PRAGMA query_only=ON')
        connection.execute('BEGIN')
        tables={r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in TABLES:
            if table not in tables:
                counts[table]=None
                continue
            rows=connection.execute('SELECT * FROM '+table).fetchall()
            counts[table]=len(rows)
            for raw in rows:
                row=dict(raw)
                record=SimpleNamespace(**row)
                proof=record_evidence(record)
                status=row.get('verification',row.get('verification_status'))
                document=row.get('source_document') or row.get('document') or row.get('standard')
                source_id=row.get('source_id')
                issues=[]
                if status in ('SOURCE_REQUIRED','UNVERIFIED'):issues.append(status)
                if status=='VERIFIED' and not (proof or source_id or document):
                    issues.append('VERIFIED_WITHOUT_TRACEABLE_SOURCE')
                if not proof:
                    issues.append('SOURCE_REQUIRED_OR_APPLICABILITY_UNRESOLVED')
                elif proof.scope=='BIBLIOGRAPHY_ONLY':
                    issues.append('NUMERIC_VALUES_NOT_VERIFIED')
                if not proof or proof.publication_date is None:issues.append('PUBLICATION_DATE_UNRESOLVED')
                if table=='engineering_constants' and row.get('key')=='display_decimal_places':
                    issues=['PRESENTATION_SETTING_NOT_ENGINEERING_CONSTANT']
                elif table=='rule_sets':issues=['PROFILE_IDENTITY_NOT_A_VERIFIED_RULE']
                elif table=='pump_references':issues=['REFERENCE_VESSEL_EVIDENCE_REQUIRED_NOT_A_STANDARD_DEFAULT']
                elif row.get('source_type')=='USER_INPUT':issues=['MANUAL_INPUT_NO_EXTERNAL_STANDARD_INFERRED']
                elif row.get('source_type')=='CALCULATED':issues=['D243_CALCULATION_NO_EXTERNAL_STANDARD_INFERRED']
                records.append({'table':table,'record':str(row.get('code') or row.get('key') or row.get('id') or len(records)),
                    'stored_verification':status,'source_link_present':bool(source_id),
                    'document':document,'edition':row.get('source_edition') or row.get('revision'),
                    'verified_evidence':proof.key if proof else None,'issues':issues,
                    'reviewed_values':{k:row[k] for k in ('property_name','unit','source_min','source_max','source_nominal','default_value','default_method','reference_temperature_c','parameter','hard_min','hard_max','applicability') if k in row}
                        if proof and proof.scope in ('NUMERIC_RANGE','LIMITED_VALUE_SCOPE') else None})
    finally:connection.close()
    return {'database_sha256':digest,'table_counts':counts,'records':records}


def audit_code(root=ROOT):
    """Inventory constructors, including callbacks/factories; dynamic facts stay unresolved."""
    records=[]
    for path in sorted(Path(root).rglob('*.py')):
        if 'tests' in path.parts or '__pycache__' in path.parts:continue
        source=path.read_text(encoding='utf-8-sig')
        tree=ast.parse(source)
        aliases={'SourceReference','EngineeringSource'}
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):
                aliases.update(item.asname or item.name for item in node.names if item.name in ('SourceReference','EngineeringSource'))
        for node in ast.walk(tree):
            if not isinstance(node,ast.Call):continue
            name=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else ''
            if name not in aliases:continue
            values={kw.arg:ast.get_source_segment(source,kw.value) for kw in node.keywords if kw.arg}
            origin=values.get('source_type','DYNAMIC')
            issue=('MANUAL_INPUT_NO_EXTERNAL_STANDARD_INFERRED' if origin.endswith('.USER_INPUT') else
                   'D243_CALCULATION_NO_EXTERNAL_STANDARD_INFERRED' if origin.endswith('.CALCULATED') else
                   'CHECK_RECORD_OR_RUNTIME_SOURCE_METADATA')
            records.append({'file':str(path.relative_to(root)).replace('\\','/'),'line':node.lineno,
                'constructor':name,'source_type_expression':origin,'document_expression':values.get('document'),
                'verification_status_expression':values.get('verification_status'),
                'recorded_metadata_expressions':{k:v for k,v in values.items() if k in ('source_organization','part','section','article','table','revision','effective_date','verification_date','notes')},
                'issues':[issue]})
    return records


UNRESOLVED = (
    {'area':'Edition selection','issue':'Priority: Türk Loydu, ISO, Everllence/MAN, other authoritative sources; technical applicability takes precedence. No confirmed superseded same-scope active record was identified. TL current portal requires interactive terms; latest applicability remains review-required. Do not archive historical references or substitute a newer unrelated standard.'},
    {'area':'Historical research references','issue':'TL Chapter 107 (2016), IMO A.1122(30), original Colebrook paper and Wärtsilä profiles remain verification-pending; prior research citations do not establish a current applicable numerical rule.'},
    {'area':'Pipe Design','issue':'Rp0.2/B legacy stress, safety/weld factors and corrosion defaults lack a verified applicable rule. Never attach TL/ISO by resemblance.'},
    {'area':'Transfer Pump','issue':'Reference-vessel records require their original dataset. Q=V/t and regression outputs are D243 calculations, not class limits.'},
    {'area':'Discharge / Suction / ENPY','issue':'Local-loss coefficient tables, empirical unit coefficients and exact NPSH margin edition/application remain unverified. Standard gravity is separately identified.'},
    {'area':'Seawater','issue':'No verified T/salinity/pressure property record, allowable stress 68 MPa or material/service corrosion source established. HW remains blocked.'},
    {'area':'Fire','issue':'Nozzle, seawater HW, universal application density/duration/C and current class compliance remain SOURCE_REQUIRED. Product data and committee drafts cannot unlock them.'},
    {'area':'Warning Center / Formula View / Word','issue':'Display frozen source facts only. No live research lookup may reinterpret historical snapshots.'},
    {'area':'DPO','issue':'7 m/s is an accepted internal D243 criterion. No signed DPO document/publication date was supplied; do not globally relabel D243 or legacy defaults as DPO Standardı.'},
    {'area':'Manufacturer profiles','issue':'Liquid ranges corroborated in a specific Everllence guide. Generic profiles lack exact engine/edition binding; air rows are delivery-side only.'},
    {'area':'TL <500 GT','issue':'2019 clause corroborates the values; generic stored profile does not establish original edition or current project applicability.'},
)


def make_report(database,root=ROOT):
    data=audit_database(database)
    return {'verification_date':AUDIT_DATE,'database':data,'embedded_sources':audit_code(root),
            'source_evidence':[s.payload() for s in SOURCES], 'unresolved':list(UNRESOLVED),
            'policy':'Metadata only; no values, flags, formulas, user databases or historical snapshots changed. No runtime network lookup.'}


def render_html(report):
    def cell(value):return '<td>'+escape(str(value if value is not None else 'Bilinmiyor'))+'</td>'
    def table(headers,rows):
        return '<table><thead><tr>'+''.join('<th>'+escape(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join(
            '<tr>'+''.join(cell(v) for v in row)+'</tr>' for row in rows)+'</tbody></table>'
    sources=table(('Kaynak','Yayın tarihi','Baskı / revizyon','Revizyon tarihi','Kabul / yürürlük tarihi','Değişiklikler','Madde / tablo','Uygulanabilirlik','Kapsam','Doğrulama tarihi','Resmî bağlantı'),(
        (r['document_number'],r['publication_date'],r['edition'],r['revision_date'],str(r['adoption_date'])+' / '+str(r['effective_date']),r['amendments'],r['clause'],r['applicability'],r['scope'],r['verification_date'],r['url']) for r in report['source_evidence']))
    records=table(('Tablo','Kayıt','Kayıtlı durum','Kanıt','İncelenen değerler (değiştirilmedi)','Açık konu'),(
        (r['table'],r['record'],r['stored_verification'],r['verified_evidence'],json.dumps(r['reviewed_values'],ensure_ascii=False) if r['reviewed_values'] else None,'; '.join(r['issues'])) for r in report['database']['records']))
    embedded=table(('Dosya','Satır','Kaynak türü ifadesi','Belge ifadesi','Doğrulama ifadesi','Kayıtlı metaveri ifadeleri','İnceleme'),(
        (r['file'],r['line'],r['source_type_expression'],r['document_expression'],r['verification_status_expression'],json.dumps(r['recorded_metadata_expressions'],ensure_ascii=False),'; '.join(r['issues'])) for r in report['embedded_sources']))
    unresolved=table(('Alan','Açık konu'),((r['area'],r['issue']) for r in report['unresolved']))
    counts=Counter(r['verified_evidence'] or 'UNRESOLVED' for r in report['database']['records'])
    return ('<!doctype html><html lang="tr"><meta charset="utf-8"><title>D243 Mühendislik Kaynak Denetimi</title>'
        '<style>body{font:15px system-ui;margin:32px;color:#102d44}table{border-collapse:collapse;width:100%;margin:18px 0}th,td{border:1px solid #ccd5dd;padding:8px;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#eef3f6}h2{margin-top:36px}</style>'
        '<h1>D243 Mühendislik Kaynak Denetimi</h1><p>Doğrulama tarihi: '+report['verification_date']+
        '. Yayın, revizyon, yürürlük ve doğrulama tarihleri birbirinin yerine kullanılmadı. Belge künyesi doğrulaması sayısal değer onayı değildir.</p>'
        '<p>Veritabanı salt okunur incelendi. Gemi adları ve proje verileri bu rapora alınmadı. Kayıt sayısı: '+str(len(report['database']['records']))+
        '; gömülü kaynak yapıcısı: '+str(len(report['embedded_sources']))+'.</p><pre>'+escape(json.dumps(counts,ensure_ascii=False,indent=2))+'</pre>'
        '<h2>Kaynaklar ve tarihler</h2>'+sources+'<h2>Kayıt bazında denetim</h2>'+records+
        '<h2>Gömülü kaynaklar ve dinamik kullanım</h2>'+embedded+'<h2>Çözülemeyen kaynaklar ve güvenlik sınırları</h2>'+unresolved+'</html>')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,required=True)
    parser.add_argument('--json',type=Path,required=True)
    parser.add_argument('--html',type=Path,required=True)
    args=parser.parse_args()
    report=make_report(args.database)
    args.json.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    args.html.write_text(render_html(report),encoding='utf-8')
    print('records',len(report['database']['records']),'constructors',len(report['embedded_sources']))
