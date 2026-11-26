"""Data-only upgrade: fill factory records that were blank, never touch edited or user rows."""
from dataclasses import fields
from engineering.catalog_seeds import fluid_seeds, surface_seeds
from database.library_v6 import insert, scalar

FLUID_COLUMNS = ('source_min', 'source_max', 'default_value', 'default_method', 'reference_temperature_c',
                 'source_authority', 'source_document', 'source_edition', 'source_note', 'verification')
SURFACE_COLUMNS = ('roughness_mm', 'source_authority', 'source_document', 'source_note', 'verification')


def create_v9_schema(connection):
    for row in fluid_seeds():
        if row.source_min is None and row.source_max is None and row.default_value is None:
            continue
        sets = ','.join(name + '=?' for name in FLUID_COLUMNS)
        connection.execute(
            f'UPDATE fluid_specifications SET {sets} WHERE code=? AND is_factory=1 AND default_value IS NULL '
            'AND source_min IS NULL AND source_max IS NULL',
            tuple(scalar(getattr(row, name)) for name in FLUID_COLUMNS) + (row.code,))
    for row in surface_seeds():
        if row.roughness_mm is None:
            continue
        sets = ','.join(name + '=?' for name in SURFACE_COLUMNS)
        connection.execute(
            f'UPDATE material_surfaces SET {sets} WHERE code=? AND is_factory=1 AND roughness_mm IS NULL',
            tuple(scalar(getattr(row, name)) for name in SURFACE_COLUMNS) + (row.code,))
        insert(connection, 'material_surfaces', row)
