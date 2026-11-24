"""Audit a read-only V7 database and rehearse migration on a disposable copy."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from dataclasses import asdict
import sys

ROOT=Path(__file__).resolve().parents[1]
if not __package__ and str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from database.library_database import LibraryDatabase
from engineering.catalog_completion_seeds import FLUID_IDENTITIES
from engineering.source_verification import BY_KEY, AUDIT_DATE
from services.catalog_completion_service import CatalogCompletionService


def audit(path):
    path=Path(path).resolve();before_hash=hashlib.sha256(path.read_bytes()).hexdigest()
    source=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    source.row_factory=sqlite3.Row
    try:
        fluids=[dict(r) for r in source.execute('SELECT * FROM fluids')]
        version=source.execute('SELECT version FROM schema_version').fetchone()[0]
        legacy_grade=source.execute("SELECT COUNT(*) FROM materials WHERE designation IN ('P235TR2','1.0255','P235TR2 / 1.0255') COLLATE NOCASE").fetchone()[0]
        old_tables=[r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table' AND name!='schema_version'")]
        before={t:tuple(tuple(r) for r in source.execute('SELECT * FROM '+t)) for t in old_tables}
        with TemporaryDirectory() as temp:
            target=Path(temp)/'copy.db'
            with closing(sqlite3.connect(target)) as copy:source.backup(copy)
            database=LibraryDatabase(target);database.initialize()
            service=CatalogCompletionService(database)
            states=[]
            for code,tr,en,group,aliases in FLUID_IDENTITIES:
                canonical=service.resolve_fluid(code)
                existed=any(r['id']==str(canonical.id) for r in fluids)
                states.append({'fluid':en,'canonical_code':code,'before':'EXISTS' if existed and code in ('F76','F44') else 'PARTIAL' if existed else 'MISSING',
                    'identity_action':'REUSED' if existed else 'INSERTED_IN_MIGRATION_COPY',
                    'aliases':service.aliases(canonical.id),'classification':group,
                    'remaining':'Published specification limits only; actual operating data required.' if code in ('F76','F44') else
                        'Discrete published points only; no interpolation or automatic calculator default.' if code in ('WATER','SEAWATER') else
                        'Product/composition/operating conditions required; no numerical physical properties invented.'})
            with database.connection() as db:
                preserved=all(set(rows)<=set(tuple(r) for r in db.execute('SELECT * FROM '+table)) for table,rows in before.items())
                dump=tuple(db.iterdump())
                violations=[tuple(r) for r in db.execute('PRAGMA foreign_key_check')]
            database.initialize()
            with database.connection() as db:idempotent=tuple(db.iterdump())==dump
            result={'audit_date':AUDIT_DATE,'source_schema':version,'target_schema':8,'source_database_sha256':before_hash,
                'production_database_modified':False,'old_rows_preserved_in_copy':preserved,'idempotent':idempotent,'foreign_key_violations':violations,
                'fluid_inventory':states,'operating_properties':[asdict(r) for r in service.operating.get_all()],
                'material_inventory':{'required':'P235TR2 / 1.0255 - TS EN 10216-1','before':'PARTIAL' if legacy_grade else 'MISSING',
                    'after':'PARTIAL','verified_basis':'EN 10216-1:2013 Table 5','unresolved':'TS national adoption edition/date; no allowable stress or roughness inferred.'},
                'mechanical_grades':[asdict(r) for r in service.grades.get_all()],
                'mechanical_properties':[asdict(r) for r in service.mechanics.get_all()],
                'sources':[BY_KEY[k].payload() for k in ('MIT_WATER_TABLES_2023','EN10216_1_2013')],
                'unresolved':['TS EN 10216-1 national adoption edition/publication date requires primary TSE confirmation.',
                    'Existing separate Sea water user identity is retained; no merge or history relinking.',
                    'Water points are correlation-table references at 0.101325 MPa, not class limits or measured batch properties.',
                    'No new hydraulic method approval, allowable stress, roughness or mixture viscosity. SOURCE_REQUIRED blockers remain.',
                    'No automatic application of new operating points to existing calculator inputs or snapshots.']}
    finally:source.close()
    if hashlib.sha256(path.read_bytes()).hexdigest()!=before_hash:raise RuntimeError('Source database changed during audit')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if args.database.resolve()==args.output.resolve():parser.error('Output must not overwrite the source database')
    result=audit(args.database)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    print('reused',sum(r['identity_action']=='REUSED' for r in result['fluid_inventory']),
          'inserted',sum(r['identity_action']!='REUSED' for r in result['fluid_inventory']),
          'points',len(result['operating_properties']),'preserved',result['old_rows_preserved_in_copy'],'idempotent',result['idempotent'])
