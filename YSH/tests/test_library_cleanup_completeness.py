"""Library-only projections preserve canonical data, links and uncertainty."""
from dataclasses import replace
from datetime import date
from types import SimpleNamespace
from uuid import uuid4
import tkinter as tk

import pytest

from core.material import Material
from engineering.provenance import SourceReference, SourceType, VerificationStatus
from i18n.translator import Translator
from repositories.v2_models import SourceRecord
from services.engineering_constant_service import EngineeringConstantService
from services.engineering_library_service import EngineeringLibraryService
from services.library_catalog import HIDDEN_LIBRARY_CATEGORIES, VISIBLE_CATEGORIES, CATEGORY_BY_CODE
from services.library_views import PropertyView, SourceView
from ui.dialogs.engineering_library_workspace import EngineeringLibraryWorkspace, record_label, localized_library_value
from ._tk_geometry import settle_geometry


@pytest.fixture
def service(library_database):
    result = EngineeringLibraryService(library_database)
    EngineeringConstantService(result._repos['constants'])
    result._repos['materials'].create(Material(name='Legacy grade', designation='Legacy grade',
        yield_strength_mpa=190, roughness_mm=.015, source='Existing legacy record'))
    return result


def test_projections_are_read_only_repeatable_and_not_foreign_key_choices(service, library_database):
    with library_database.connection() as connection:
        before = tuple(connection.iterdump())
    first = {code: service.list_display_records(code) for code in (
        'sources', 'fluid_properties', 'material_properties', 'constants', 'presentation_settings')}
    assert all(first.values())
    assert first == {code: service.list_display_records(code) for code in first}
    for code in ('sources', 'material_properties'):
        assert not service.list_records(code)
        assert all(not service.can_edit(code, row) for row in first[code])
    assert len({r.id for r in first['sources']}) == len(first['sources'])
    assert len({r.reference for r in first['sources']}) == len(first['sources'])
    with library_database.connection() as connection:
        assert tuple(connection.iterdump()) == before


def test_f76_range_temperature_and_derived_default_are_preserved(service):
    canonical = next(r for r in service.list_records('fluid_specifications') if r.code == 'F76_DENSITY')
    rows = service.list_display_records('fluid_properties', canonical.fluid_id)
    assert canonical in rows
    assert canonical.reference_temperature_c == 15
    assert (canonical.source_min, canonical.source_max, canonical.default_value) == (800, 876, 838)
    assert canonical.default_method == 'DERIVED_MIDPOINT'
    assert canonical.source_document == 'MIL-DTL-16884R' and canonical.source_edition == 'R'
    assert not service.can_edit('fluid_properties', canonical)
    assert all(row.fluid_id == canonical.fluid_id for row in rows)
    # Different temperatures remain distinct, with the same canonical fluid identity.
    variant = service._repos['fluid_specifications'].create(replace(canonical,
        id=uuid4(), code='TEST_TEMPERATURE', reference_temperature_c=20,
        is_factory=False))
    assert variant in service.list_display_records('fluid_properties', canonical.fluid_id)
    assert not service.can_edit('fluid_properties', variant)


def test_source_projection_preserves_scope_edition_and_missing_dates(service):
    sources = service.list_display_records('sources')
    tl = next(row for row in sources if row.reference.section == 'Section 1, C.5.3.3')
    assert isinstance(tl, SourceView)
    assert tl.reference.source_organization == 'Türk Loydu'
    assert tl.reference.revision == 'July 2019' and 'TL_FFS' in tl.reference.notes
    assert tl.reference.verification_status is VerificationStatus.PARTIALLY_VERIFIED
    assert tl.reference.effective_date is None and tl.reference.verification_date is None
    d243 = next(row for row in sources if row.reference.source_type is SourceType.D243_CRITERION)
    assert d243.reference.source_organization == 'D243'
    assert d243.reference.document == 'D243'
    recorded = service._repos['sources'].create(SourceRecord(reference=SourceReference(
        source_type=SourceType.USER_INPUT, source_organization='User source',
        effective_date=date(2020, 1, 1), verification_date=date(2021, 1, 1), revision='A')))
    assert recorded in service.list_display_records('sources')
    assert service.get_record('sources', recorded.id) == recorded
    assert service.details('sources', recorded).sources == (recorded.reference,)


def test_legacy_material_is_not_promoted_to_verified_standard(service):
    row = next(r for r in service.list_display_records('material_properties')
               if r.property_name == 'yield_strength_mpa')
    assert isinstance(row, PropertyView) and row.value == 190 and row.unit == 'MPa'
    assert row.source == 'Existing legacy record'
    assert row.verification_status is VerificationStatus.UNVERIFIED
    assert not service.details('material_properties', row).editable


def test_decimal_places_is_display_setting_without_changing_storage(service):
    stored = service.list_records('constants')
    setting = next(r for r in stored if r.key == 'display_decimal_places')
    assert setting not in service.list_display_records('constants')
    assert service.list_display_records('presentation_settings') == (setting,)
    assert service.get_record('constants', setting.id) == setting
    assert all(c in CATEGORY_BY_CODE for c in HIDDEN_LIBRARY_CATEGORIES)
    assert not HIDDEN_LIBRARY_CATEGORIES & {c.code for c in VISIBLE_CATEGORIES}


@pytest.mark.parametrize('language', ['tr', 'en'])
def test_labels_are_localized_without_mutating_internal_names(service, language):
    tr = Translator(language).translate
    for row in service.list_display_records('constants'):
        label = record_label(row, tr)
        assert 'constant.' not in label
        if language == 'tr':
            assert row.display_name not in label
    assert localized_library_value('source', 'User', tr) == ('Kullanıcı' if language == 'tr' else 'User')
    for category in VISIBLE_CATEGORIES:
        assert tr('library2.category.'+category.code) != 'library2.category.'+category.code
        assert tr('library2.group.'+category.group) != 'library2.group.'+category.group
    assert service.get_record('constants', service.list_display_records('presentation_settings')[0].id).key == 'display_decimal_places'


@pytest.mark.parametrize('size', ['1100x700', '1440x900'])
def test_native_library_navigation_details_and_settings(service, size):
    root = tk.Tk()
    owner = SimpleNamespace(register_localizable=lambda _: None, unregister_localizable=lambda _: None)
    window = None
    try:
        window = EngineeringLibraryWorkspace(root, service, Translator('tr').translate, owner)
        window.geometry(size)
        settle_geometry(root, window, window._navigation)
        assert all(not window._navigation.exists(code) for code in HIDDEN_LIBRARY_CATEGORIES)
        for code in ('systems', 'sources', 'fluid_properties', 'material_properties', 'constants', 'presentation_settings'):
            window.show_category(code)
            settle_geometry(root, window, window._navigation, window._tree)
            assert window._tree.get_children()
            record = window._controller.records[0]
            window._tree.selection_set(str(record.id))
            window._select_record()
            settle_geometry(root, window, window._tree)
            assert window._controller.selected == record
            assert window._body.winfo_children()
            if code in ('sources', 'material_properties', 'presentation_settings'):
                assert str(window._buttons['edit']['state']) == 'disabled'
            row = window._tree.get_children()[0]
            window._tree.selection_set(row)
            window._select_record()
            root.update()
            assert window._controller.selected is not None
            assert window._tree.winfo_rootx() + window._tree.winfo_width() <= window.winfo_rootx() + window.winfo_width()
        window.show_category('constant_metadata')
        assert window._controller.category == 'constants'
    finally:
        if window is not None:
            window.destroy()
        root.destroy()
