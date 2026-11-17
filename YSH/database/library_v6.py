"""Additive engineering catalogs. Old V5 properties and user rows are untouched."""
from dataclasses import fields,replace
from typing import get_type_hints
from uuid import UUID
from datetime import datetime
from engineering.catalog import FluidSpecification,MaterialSurface,EngineeringRule
from engineering.catalog_seeds import identity,PROFILES,fluid_seeds,surface_seeds,rule_seeds

MODELS={'fluid_specifications':FluidSpecification,'material_surfaces':MaterialSurface,'engineering_rules':EngineeringRule}

def scalar(value):
    if isinstance(value,(UUID,datetime)):return value.isoformat() if isinstance(value,datetime) else str(value)
    return int(value) if isinstance(value,bool) else value

def insert(connection,table,row):
    names=[f.name for f in fields(row)]
    connection.execute(f'INSERT OR IGNORE INTO {table} ({",".join(names)}) VALUES ({",".join("?" for _ in names)})',tuple(scalar(getattr(row,n)) for n in names))

def create_v6_schema(connection):
    for table,model in MODELS.items():
        types=get_type_hints(model);columns=[]
        for f in fields(model):
            expected=types[f.name]
            kind='REAL' if 'float' in str(expected) else 'INTEGER' if expected is bool else 'TEXT'
            constraint=' PRIMARY KEY NOT NULL' if f.name=='id' else ' NOT NULL UNIQUE' if f.name=='code' else ''
            columns.append(f.name+' '+kind+constraint)
        extra={'fluid_specifications':', FOREIGN KEY(fluid_id) REFERENCES fluids(id)',
               'material_surfaces':', FOREIGN KEY(material_id) REFERENCES materials(id)',
               'engineering_rules':', FOREIGN KEY(profile_id) REFERENCES rule_sets(id)'}[table]
        connection.execute(f'CREATE TABLE {table} ({",".join(columns)}{extra})')
    profile_ids={}
    for profile in PROFILES:
        connection.execute('INSERT OR IGNORE INTO rule_sets(id,code,name,is_active,created_at,modified_at) VALUES(?,?,?,1,?,?)',
            (str(identity('profile:'+profile)),'ENG_'+profile,profile,'2026-11-17T00:00:00+00:00','2026-11-17T00:00:00+00:00'))
        profile_ids[identity('profile:'+profile)]=UUID(connection.execute('SELECT id FROM rule_sets WHERE code=? COLLATE NOCASE',('ENG_'+profile,)).fetchone()[0])
    for row in fluid_seeds():
        fluid_code=row.code.rsplit('_'+row.property_name.upper(),1)[0]
        found=connection.execute('SELECT id FROM fluids WHERE code=? COLLATE NOCASE',(fluid_code,)).fetchone()
        fluid_id=UUID(found[0]) if found else row.fluid_id
        if not found:
            connection.execute('INSERT INTO fluids(id,code,name_tr,name_en,is_factory,is_active) VALUES(?,?,?,?,1,1)',(str(fluid_id),fluid_code,row.name,row.name))
        insert(connection,'fluid_specifications',replace(row,fluid_id=fluid_id))
    for row in surface_seeds():insert(connection,'material_surfaces',row)
    for row in rule_seeds():insert(connection,'engineering_rules',replace(row,profile_id=profile_ids[row.profile_id]))
    connection.execute('CREATE INDEX idx_fluid_specs_fluid ON fluid_specifications(fluid_id)')
    connection.execute('CREATE INDEX idx_engineering_rules_profile ON engineering_rules(profile_id)')
