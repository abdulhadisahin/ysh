"""Data-only upgrade: give the factory ST37 / ST52 materials their minimum yield strength (untouched rows only)."""
STEEL_DESCRIPTIONS = {
    'ST37': ('DIN 1629 St 37.0 seamless tube (replaced by EN 10216-1 P235TR2); minimum yield 235 MPa. For thicker walls use a lower value: '
             'S235JR (St 37-2) is 225 MPa for 16-40 mm and 215 MPa above 40 mm. Roughness 0.045 mm is the commercial steel value.',
             'DIN 1629 / EN 10025-2 (secondary sources)'),
    'ST52': ('DIN 1629 St 52.0 seamless tube (replaced by EN 10216-3 P355N); minimum yield 355 MPa. For thicker walls use a lower value: '
             'St 52-3 / S355J2 is 345 MPa for 16-40 mm and 335 MPa for 40-63 mm. Roughness 0.045 mm is the commercial steel value.',
             'DIN 1629 / DIN 17100 (secondary sources)'),
}
YIELD = {'ST37': 235.0, 'ST52': 355.0}


def create_v12_schema(connection):
    for name, strength in YIELD.items():
        description, source = STEEL_DESCRIPTIONS[name]
        connection.execute("UPDATE materials SET yield_strength_mpa=?, description=CASE WHEN description='' THEN ? ELSE description END, source=? "
                           "WHERE designation=? COLLATE NOCASE AND is_system=1 AND yield_strength_mpa IS NULL",
                           (strength, description, source, name))
