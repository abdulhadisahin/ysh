"""Non-pixel contracts for compact explanations and library navigation."""
from types import SimpleNamespace

import pytest

from engineering.formula.common import step
from engineering.provenance import SourceReference, SourceType
from i18n.translator import Translator
from services.library_catalog import CATEGORIES
from ui.dialogs.engineering_library_workspace import EngineeringLibraryWorkspace
from ui.library_presentation import detail_group
from ui.widgets.detail_disclosure import DetailDisclosure
from ui.widgets.formula_image import formula_display_size
from ui.widgets.formula_steps import source_rows, step_sections


@pytest.mark.parametrize('source,width', [((1448,1086),900),((1448,500),300),
    ((800,1800),200),((30,20),1000),((1448,1086),80)])
def test_formula_image_fits_width_height_aspect_without_upscaling(source, width):
    w,h=formula_display_size(source,width)
    assert w <= min(560,width) and h <= 280
    assert w <= source[0] and h <= source[1]
    assert abs(w/h-source[0]/source[1]) < .03
    assert (w,h)==formula_display_size(source,width)


@pytest.mark.parametrize('size,width', [((0,100),600),((100,0),600),((100,100),0),((100,100),-10)])
def test_formula_image_missing_geometry_is_safe(size,width):
    assert formula_display_size(size,width)==(0,0)


def test_disclosure_toggle_retains_body_and_requires_no_source_queries():
    events=[]
    body=SimpleNamespace(grid=lambda:events.append('show'),grid_remove=lambda:events.append('hide'))
    toggle=SimpleNamespace(configure=lambda **kw:events.append(kw['text']))
    widget=SimpleNamespace(expanded=False,body=body,_toggle=toggle,_title='Source')
    DetailDisclosure.toggle(widget)
    assert widget.expanded and widget.body is body
    DetailDisclosure.toggle(widget)
    assert not widget.expanded and widget.body is body
    assert events==['show','▾ Source','hide','▸ Source']


def test_long_frozen_source_collapses_and_result_status_remain():
    from engineering.formula.models import FormulaCheck, CheckStatus
    source=SourceReference(source_type=SourceType.ENGINEERING_REFERENCE,
        source_organization='Synthetic organization',document='Synthetic document',
        table='Synthetic table',revision='A',notes='Long frozen provenance')
    current=step('x','Q',1.123456789,'m³/h','Q',(),0,sources=(source,),
                 check=FormulaCheck(status=CheckStatus.NOT_CONFIGURED))
    sections=step_sections(current,Translator('tr').translate)
    details=next(s for s in sections if s.key=='source')
    assert details.details and 'Synthetic organization' in details.text
    assert any(row[1]=='Synthetic table' for row in details.rows)
    assert {'formula','source','result','check'} <= {s.key for s in sections}
    assert current.result_value==1.123456789
    assert all(value not in ('None','') for _,value in source_rows(SourceReference(source_type=SourceType.USER_INPUT),Translator('tr').translate))


def test_navigation_builds_all_categories_and_groups_without_service_reads():
    records=[]
    navigation=SimpleNamespace(get_children=lambda:(),insert=lambda parent,index,**kw:records.append((parent,kw)),
        selection_set=lambda value:None,see=lambda value:None)
    window=SimpleNamespace(_navigation=navigation,_controller=SimpleNamespace(category='systems'),
                           _translate=Translator('tr').translate)
    EngineeringLibraryWorkspace._refresh_navigation(window)
    assert len(CATEGORIES)==21
    assert len({c.group for c in CATEGORIES})==9
    assert {kw['iid'] for parent,kw in records if parent and not kw['iid'].startswith('group:')}=={c.code for c in CATEGORIES}
    branches={kw['iid']:parent for parent,kw in records if parent and kw['iid'].startswith('group:')}
    assert branches=={'group:fire:foam':'group:fire','group:fire:hw':'group:fire'}
    category_parents={kw['iid']:parent for parent,kw in records if not kw['iid'].startswith('group:')}
    for category in CATEGORIES:
        expected='group:fire:'+('hw' if category.code=='fire_hw' else 'foam') if category.group=='fire' else 'group:'+category.group
        assert category_parents[category.code]==expected
    assert len([1 for parent,kw in records if not parent])==9


def test_navigation_ignores_group_headers_and_current_category():
    calls=[]
    for selection in ((),('group:systems',),('systems',)):
        window=SimpleNamespace(_navigation=SimpleNamespace(selection=lambda:selection),
            _controller=SimpleNamespace(category='systems'),show_category=calls.append)
        EngineeringLibraryWorkspace._choose_navigation(window)
    assert not calls


@pytest.mark.parametrize('name,group', [('name','basic'),('value','engineering'),
    ('reference_temperature_c','engineering'),('verification_status','verification'),
    ('source_id','relationships'),('is_system','ownership'),('notes','source'),('id','technical')])
def test_detail_groups_preserve_every_original_field(name,group):
    assert detail_group(name)==group


def test_unverified_legacy_tl_labels_are_not_presented_as_authoritative():
    for language in ('tr','en'):
        tr=Translator(language).translate
        assert '8.9' not in tr('formula.safety_factor_reference_note')
        assert '8.9' not in tr('pipe.source_notes')
        assert 'no verified' in tr('pipe.source_notes_warning').lower() or 'doğrul' in tr('pipe.source_notes_warning').lower()


@pytest.mark.parametrize('language', ['tr','en'])
def test_record_counter_caption_translates_without_missing_format_arguments(language):
    label=Translator(language).translate('library2.record_count')
    assert label in ('kayıt','records')
    assert '{count}' not in label
