"""Data-only upgrade: add the P235TR2 (EN 10216-1) pipe material when absent."""
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5
from core.material import Material

DESCRIPTION = ('EN 10216-1:2013, material number 1.0255, seamless non-alloy steel tube, delivery condition TR2. '
               'Yield 235 MPa is ReH minimum for wall thickness up to 16 mm (Table 5); it is 225 MPa for 16-40 mm and '
               '215 MPa for 40-60 mm, so use a lower value for thicker walls. Roughness 0.045 mm is the commercial steel value. '
               'TS EN 10216-1 national adoption not verified.')


def p235tr2_material():
    return Material(name='P235TR2', designation='TS EN 10216-1', standard='EN 10216-1:2013 (TS EN 10216-1)', yield_strength_mpa=235.0,
                    roughness_mm=0.045, description=DESCRIPTION, source='EN 10216-1:2013 Table 5', is_system=True,
                    id=uuid5(NAMESPACE_URL, 'd243:material:P235TR2'))


def create_v11_schema(connection):
    if not connection.execute('SELECT 1 FROM materials LIMIT 1').fetchone():
        return  # empty library: MaterialService seeds it (including P235TR2) on first use
    row = p235tr2_material()
    if connection.execute('SELECT 1 FROM materials WHERE designation=? COLLATE NOCASE OR name=? COLLATE NOCASE',
                          (row.designation, row.name)).fetchone():
        return
    now = datetime.now(timezone.utc).isoformat()
    connection.execute('INSERT INTO materials(id,name,designation,standard,yield_strength_mpa,roughness_mm,description,source,is_system,created_at,modified_at) '
                       'VALUES(?,?,?,?,?,?,?,?,1,?,?)',
                       (str(row.id), row.name, row.designation, row.standard, row.yield_strength_mpa, row.roughness_mm,
                        row.description, row.source, now, now))
