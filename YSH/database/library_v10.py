"""Data-only upgrade: complete the Cu-Ni / Wärtsilä rules and drop unfillable placeholders (factory rows only)."""
from dataclasses import fields
from uuid import UUID
from engineering.catalog_seeds import cuni_wartsila_rules, identity
from database.library_v6 import insert, scalar

UPDATE_COLUMNS = ('name', 'fluid_group', 'material', 'rule_nature', 'recommended_max', 'source_authority', 'source_document',
                  'source_edition', 'source_clause', 'verification', 'notes')
REMOVED = ('BALLAST', 'BILGE', 'WARTSILA')


def create_v10_schema(connection):
    for code in REMOVED:  # never filled with an invented number; only untouched factory placeholders are removed
        connection.execute("DELETE FROM engineering_rules WHERE code=? AND is_factory=1 AND verification='SOURCE_REQUIRED' "
                           'AND hard_min IS NULL AND hard_max IS NULL AND recommended_min IS NULL AND recommended_max IS NULL', (code,))
    for row in cuni_wartsila_rules():
        sets = ','.join(name + '=?' for name in UPDATE_COLUMNS)
        cursor = connection.execute(
            f"UPDATE engineering_rules SET {sets} WHERE code=? AND is_factory=1 AND verification='SOURCE_REQUIRED' AND recommended_max IS NULL",
            tuple(scalar(getattr(row, name)) for name in UPDATE_COLUMNS) + (row.code,))
        if cursor.rowcount:
            continue
        profile = connection.execute('SELECT id FROM rule_sets WHERE code=? COLLATE NOCASE',
                                     ('ENG_' + ('WARTSILA' if row.code.startswith('WARTSILA') else 'CUNI_REFERENCE'),)).fetchone()
        if profile is not None:
            from dataclasses import replace
            insert(connection, 'engineering_rules', replace(row, profile_id=UUID(profile[0])))
