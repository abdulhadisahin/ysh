from reporting.reference_catalog import references_for, REFERENCES

def test_stainless_fuel_pipe_has_no_cuni_reference():
    docs = ' '.join(r.document + r.table for r in references_for('pipe_design', 'fuel'))
    assert 'Table 8.8' not in docs and 'Wieland' not in docs and 'ISO 4200' in docs

def test_seawater_pipe_has_cuni_references():
    assert any('Table 8.8' in r.table for r in references_for('pipe_design', 'seawater'))

def test_every_reference_has_both_languages():
    assert all(r.use_tr and r.use_en and r.basis in ('primary', 'secondary') for r in REFERENCES)
