"""Add optional salinity metadata, without changing any property or seed value."""


def create_v7_schema(connection):
    columns={row['name'] for row in connection.execute('PRAGMA table_info(fluid_specifications)')}
    if 'reference_salinity_g_kg' not in columns:
        connection.execute('ALTER TABLE fluid_specifications ADD COLUMN reference_salinity_g_kg REAL')
