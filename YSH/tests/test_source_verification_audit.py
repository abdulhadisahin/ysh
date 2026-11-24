"""Metadata verification cannot promote changed values or reinterpret history."""
from dataclasses import asdict, replace
import hashlib
import json
import sqlite3

import pytest

from engineering.catalog_seeds import fluid_seeds, rule_seeds
from engineering.source_verification import BY_KEY, REVIEWED, SOURCES, evidence_rows, record_evidence, source_label_key
from engineering.rule_evaluation import record_payload, rule_status
from engineering.provenance import SourceReference, SourceType, VerificationStatus
from engineering.basis import basis_rows
from i18n.translator import Translator
from reporting.word_presentation import basis_explanations
from services.library_views import catalog_sources
from YSH.tools.source_audit import audit_database, audit_code


@pytest.mark.parametrize('code', REVIEWED)
def test_exact_reviewed_records_only(code):
    record = next(r for r in (*fluid_seeds(), *rule_seeds()) if r.code == code)
    before = asdict(record)
    proof = record_evidence(record)
    assert proof is not None
    assert record_payload(record)['source_evidence'] == proof.payload()
    assert asdict(record) == before
    assert record_evidence(replace(record, source_edition='another edition')) is None
    if hasattr(record, 'default_value'):
        assert record_evidence(replace(record, reference_temperature_c=99)) is None
        assert record_evidence(replace(record, unit='another unit')) is None
    else:
        assert record_evidence(replace(record, applicability='another scope')) is None
        assert record_evidence(replace(record, hard_max=99)) is None


def test_bibliography_is_not_value_approval():
    row = next(r for r in fluid_seeds() if r.code == 'DMA_DENSITY')
    assert record_evidence(row).scope == 'BIBLIOGRAPHY_ONLY'
    assert row.default_value is None and row.verification == 'SOURCE_REQUIRED'
    assert record_evidence(replace(row, source_document='Unknown')) is None
    for row in rule_seeds():
        if row.rule_nature == 'SOURCE_REQUIRED':
            assert rule_status(row, 1) == 'SOURCE_REQUIRED'
            assert record_evidence(row) is None


def test_dates_keep_precision_and_distinct_events():
    tl = BY_KEY['TL_FFS_2019']
    assert tl.publication_date == '2019-07' and tl.effective_date == '2019-07-01'
    assert '2022' in tl.amendments
    imo = BY_KEY['IMO_MSC98']
    assert imo.adoption_date == '2000-12-05' and imo.publication_date is None
    assert imo.revision_date is None
    assert BY_KEY['SKUM_ZF_04'].publication_date is None
    assert BY_KEY['SKUM_ZF_04'].copyright_year == '2024'
    assert BY_KEY['FOMTEC_XMAX'].publication_date is None
    assert BY_KEY['FOMTEC_XMAX'].revision_date == '2025-04-22'
    assert all(s.verification_date == '2026-11-24' for s in SOURCES)


@pytest.mark.parametrize('language', ['tr', 'en'])
def test_frozen_metadata_display_and_localization(language, monkeypatch):
    row = next(r for r in fluid_seeds() if r.code == 'F76_DENSITY')
    ref = record_payload(row)
    payload = {'values': [{'reference': ref, 'used_value': 838, 'status': 'MANUAL'}]}
    old = {'values': [{'reference': asdict(row), 'used_value': 838, 'status': 'MANUAL'}]}
    frozen = json.dumps(payload, default=str, sort_keys=True)
    monkeypatch.setattr('engineering.source_verification.record_evidence', lambda _: pytest.fail('live lookup'))
    tr = Translator(language).translate
    rows = basis_rows(payload, tr)
    assert (tr('sourceaudit.publication_date'), '2025-01-03') in rows
    assert any('2025-01-03' in p for p in basis_explanations(payload, language))
    assert tr('sourceaudit.publication_date') not in dict(basis_rows(old, tr))
    assert json.dumps(payload, default=str, sort_keys=True) == frozen
    for proof in SOURCES:
        for label, value in evidence_rows(proof.payload(), tr):
            assert not label.startswith('sourceaudit.')
            assert not value.startswith('sourceaudit.')


def test_explicit_confirmed_dpo_only():
    criterion = SourceReference(source_type=SourceType.D243_CRITERION,
        source_organization='DPO', verification_status=VerificationStatus.USER_SUPPLIED)
    assert source_label_key(criterion) == 'sourceaudit.dpo'
    assert source_label_key(replace(criterion, source_organization='D243')) != 'sourceaudit.dpo'
    assert source_label_key(replace(criterion, verification_status=None)) != 'sourceaudit.dpo'
    assert source_label_key(replace(criterion, source_type=SourceType.USER_INPUT)) != 'sourceaudit.dpo'
    tr = Translator('tr').translate
    assert tr('formula2.source_type.USER_INPUT') == 'Kullanıcı'
    assert tr('formula2.source_type.CALCULATED') == 'D243 Hesabı'


def test_library_projection_keeps_canonical_record_untouched():
    rows = fluid_seeds()
    before = tuple(asdict(r) for r in rows)
    first = catalog_sources(rows, ())
    assert first == catalog_sources(rows, ())
    assert tuple(asdict(r) for r in rows) == before
    assert any(r.publication_date == '2025-01-03' for r in first)
    assert len({r.id for r in first}) == len(first)


def test_auditor_read_only_old_schema_and_untraceable_verified(tmp_path):
    path = tmp_path / 'old.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE fluid_properties (id TEXT, verification_status TEXT, source_id TEXT)')
        db.execute("INSERT INTO fluid_properties VALUES ('legacy', 'VERIFIED', NULL)")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    first = audit_database(path)
    assert first == audit_database(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert 'VERIFIED_WITHOUT_TRACEABLE_SOURCE' in first['records'][0]['issues']
    assert first['table_counts']['engineering_rules'] is None


def test_constructor_audit_keeps_dynamic_sources_uncertain(tmp_path):
    (tmp_path / 'module.py').write_text('from x import SourceReference as Ref\ns = Ref(**saved)\n')
    records = audit_code(tmp_path)
    assert len(records) == 1
    assert records[0]['source_type_expression'] == 'DYNAMIC'
    assert records[0]['issues'] == ['CHECK_RECORD_OR_RUNTIME_SOURCE_METADATA']
