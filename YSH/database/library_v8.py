"""Add separate operating points and mechanical grades; never rewrite V7 records."""
from dataclasses import fields, replace
from uuid import UUID
from engineering.catalog_completion import FluidCatalogProfile, OperatingFluidProperty, MechanicalGrade, MechanicalGradeProperty
from engineering.catalog_completion_seeds import FLUID_IDENTITIES, REQUIREMENTS, operating_seeds, mechanical_seeds
from engineering.catalog_seeds import identity
from database.library_v6 import insert

MODELS={'fluid_catalog_profiles':FluidCatalogProfile,'operating_fluid_properties':OperatingFluidProperty,
        'mechanical_grades':MechanicalGrade,'mechanical_grade_properties':MechanicalGradeProperty}


def create_v8_schema(connection):
    foreign_keys={
        'fluid_catalog_profiles':', FOREIGN KEY(fluid_id) REFERENCES fluids(id)',
        'operating_fluid_properties':', FOREIGN KEY(fluid_id) REFERENCES fluids(id)',
        'mechanical_grades':'',
        'mechanical_grade_properties':', FOREIGN KEY(grade_id) REFERENCES mechanical_grades(id)',
    }
    for table,model in MODELS.items():
        columns=[]
        for field in fields(model):
            kind='REAL' if 'float' in str(field.type) else 'INTEGER' if field.type is bool else 'TEXT'
            constraint=' PRIMARY KEY NOT NULL' if field.name=='id' or (table=='fluid_catalog_profiles' and field.name=='fluid_id') else ' UNIQUE NOT NULL' if field.name in ('code','canonical_code') else ''
            columns.append(field.name+' '+kind+constraint)
        connection.execute(f'CREATE TABLE IF NOT EXISTS {table} ({",".join(columns)}{foreign_keys[table]})')
    connection.execute('CREATE TABLE IF NOT EXISTS fluid_aliases (alias TEXT PRIMARY KEY COLLATE NOCASE, fluid_id TEXT NOT NULL REFERENCES fluids(id))')
    ids={}
    for code,tr,en,classification,aliases in FLUID_IDENTITIES:
        found=connection.execute('SELECT id FROM fluids WHERE code=? COLLATE NOCASE',(code,)).fetchone()
        if not found:
            names={name.casefold() for name in (*aliases,tr,en)}
            matches=[row for row in connection.execute('SELECT id,code,name_tr,name_en FROM fluids')
                     if any(str(row[key] or '').casefold() in names for key in ('code','name_tr','name_en'))]
            if len(matches)>1:raise ValueError('Ambiguous existing fluid identity: '+code)
            found=matches[0] if matches else None
        fluid_id=UUID(found['id']) if found else identity('fluid:'+code)
        if not found:
            connection.execute('INSERT INTO fluids(id,code,name_tr,name_en,is_factory,is_active) VALUES(?,?,?,?,1,1)',(str(fluid_id),code,tr,en))
        ids[code]=fluid_id
        insert(connection,'fluid_catalog_profiles',FluidCatalogProfile(fluid_id=fluid_id,canonical_code=code,
            classification=classification,operating_requirements=REQUIREMENTS[classification],
            concentration_basis='volume_percent' if code=='FOAM_SOLUTION' else ''))
        for alias in (*aliases,code):
            # A legacy code must retain its identity; aliases cannot shadow it.
            conflict=connection.execute('SELECT id FROM fluids WHERE code=? COLLATE NOCASE',(alias,)).fetchone()
            if conflict and conflict['id']!=str(fluid_id):continue
            connection.execute('INSERT OR IGNORE INTO fluid_aliases(alias,fluid_id) VALUES(?,?)',(alias,str(fluid_id)))
    for row in operating_seeds(ids):insert(connection,'operating_fluid_properties',row)
    grade,properties=mechanical_seeds()
    existing=connection.execute('SELECT id FROM mechanical_grades WHERE code=? COLLATE NOCASE',(grade.code,)).fetchone()
    insert(connection,'mechanical_grades',grade)
    grade_id=UUID(existing['id']) if existing else grade.id
    for row in properties:insert(connection,'mechanical_grade_properties',replace(row,grade_id=grade_id))
