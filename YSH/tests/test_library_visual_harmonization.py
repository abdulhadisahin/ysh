"""Library presentation contracts with the existing protected data service."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from engineering.provenance import VerificationStatus, SourceReference, SourceType
from i18n.translator import Translator
from i18n.messages_tr import MESSAGES as TR
from i18n.messages_en import MESSAGES as EN
from services.library_catalog import CATEGORIES
from ui.dialogs.engineering_library_workspace import (
    EngineeringLibraryWorkspace, record_verification, visible_detail,
)
from ui.library_controller import LibraryController
from ui.library_presentation import ordered_editor_fields, detail_group
from ui.theme import colors
from ui.theme.library_visuals import configure_library_visuals, verification_role, LIBRARY_SOFT, PANE_WEIGHTS, pane_positions
from .test_pipe_visual_pilot import Style
from .test_engineering_library_phase13 import library, editor_stub

ROOT = Path(__file__).parents[1]


def test_editor_sections_are_contiguous_without_changing_allowed_fields():
    for category in CATEGORIES:
        fields=ordered_editor_fields(category.fields)
        assert len(fields)==len(category.fields) and set(fields)==set(category.fields)
        headings=[]
        for field in fields:
            group=detail_group(field.name)
            if not headings or headings[-1]!=group: headings.append(group)
        assert len(headings)==len(set(headings))


def test_library_styles_are_scoped_and_reuse_master_geometry():
    style=Style();configure_library_visuals(style)
    assert all(key.startswith('Library') for key in style.configurations | style.maps)
    assert style.configurations['Library.Data.Treeview']['rowheight']==32
    assert style.configurations['Library.Data.Treeview.Heading']['background']==colors.SURFACE_ALT
    assert style.maps['Library.Data.Treeview']['background'][0]==('selected',LIBRARY_SOFT)
    assert style.configurations['Library.TEntry']['fieldbackground']==colors.WHITE
    assert PANE_WEIGHTS==(2,4,3)
    assert len(CATEGORIES)==17 and len({c.group for c in CATEGORIES})==8


@pytest.mark.parametrize('width',[1068,1334,1568,1668])
def test_pane_weights_leave_readable_navigation_table_and_details(width):
    left,second=pane_positions(width)
    assert left>=196 and second-left>=320 and width-second>=300
    assert .20<=left/width<=.23
    assert .42<=(second-left)/width<=.48
    assert .30<=(width-second)/width<=.35


def test_detail_wrap_accepts_native_empty_option_without_data_queries(monkeypatch):
    import ui.dialogs.engineering_library_workspace as view
    class Label:
        def cget(self,key): return ''
        def configure(self,**kwargs): self.options=kwargs
        def winfo_children(self): return ()
    monkeypatch.setattr(view.ttk,'Label',Label)
    child=Label()
    owner=SimpleNamespace(_detail_scroll=SimpleNamespace(canvas=SimpleNamespace(winfo_width=lambda:340)),
        _body=SimpleNamespace(winfo_children=lambda:(child,)))
    EngineeringLibraryWorkspace._fit_detail_text(owner)
    assert child.options=={'wraplength':292}


@pytest.mark.parametrize('value,visible', [(None,False),('',False),({},False),([],False),((),False),(0,True),(False,True),('0',True)])
def test_empty_metadata_is_hidden_without_losing_zero_or_false(value,visible):
    assert visible_detail(value) is visible


@pytest.mark.parametrize('status,role', [(VerificationStatus.VERIFIED,'Verified'),
    (VerificationStatus.PARTIALLY_VERIFIED,'Warning'),(VerificationStatus.USER_SUPPLIED,'Info'),
    (VerificationStatus.UNVERIFIED,'Warning'),(VerificationStatus.DEPRECATED,'Error'),(None,'Muted')])
def test_verification_is_not_inferred_from_source_presence(status,role):
    assert verification_role(status)==role
    record=SimpleNamespace(reference=SourceReference(source_type=SourceType.USER_INPUT,verification_status=status))
    assert record_verification(record) is status
    assert record_verification(object()) is None


def table_stub(service,category):
    class Variable:
        def __init__(self,value=''): self.value=value
        def get(self): return self.value
        def set(self,value): self.value=value
    class Tree:
        def __init__(self): self.rows={}
        def selection(self): return ()
        def get_children(self): return tuple(self.rows)
        def delete(self,key): self.rows.pop(key)
        def insert(self,*args,**kwargs): self.rows[kwargs['iid']]=kwargs
    class Empty:
        def configure(self,**kwargs): self.text=kwargs['text']
        def place(self,**kwargs): self.visible=True
        def place_forget(self): self.visible=False
    controller=LibraryController(service);controller.browse(category)
    return SimpleNamespace(_controller=controller,_translate=Translator('tr').translate,
        _filters=[{'all':None,'active':True},{'all':None,'user':'user'},{'all':None,'verified':'VERIFIED'}],
        _active=Variable('all'),_ownership=Variable('all'),_verification=Variable('all'),
        _search=Variable(),_tree=Tree(),_record_count=Variable(),_table_empty=Empty())


def test_real_table_search_filters_empty_state_and_count(library):
    service,rows=library
    window=table_stub(service,'systems')
    window._search.set('Test system')
    EngineeringLibraryWorkspace._render_rows(window)
    assert list(window._row_map)==[str(rows['systems'].id)]
    assert window._record_count.get()=='1 kayıt' and not window._table_empty.visible
    window._ownership.set('user');EngineeringLibraryWorkspace._render_rows(window)
    assert len(window._row_map)==1
    window._verification.set('verified');EngineeringLibraryWorkspace._render_rows(window)
    assert not window._row_map and window._table_empty.visible
    assert window._table_empty.text==TR['library.visual.no_matches']
    assert window._record_count.get()=='0 kayıt'


def test_table_shows_existing_source_verification_without_per_row_queries(library,monkeypatch):
    service,rows=library
    window=table_stub(service,'sources')
    monkeypatch.setattr(service,'details',lambda *args:(_ for _ in ()).throw(AssertionError('No per-row detail query')))
    EngineeringLibraryWorkspace._render_rows(window)
    item=window._tree.rows[str(rows['sources'].id)]
    assert item['values'][3]==TR['formula2.verification_status.USER_SUPPLIED']


def test_editor_styles_keep_existing_save_cancel_and_protection(library,monkeypatch):
    window,created=editor_stub(library,'sources',monkeypatch)
    assert window._buttons['save'].options['state']=='normal'
    assert window._tree.options['selectmode']=='none'
    assert any(widget.options.get('style')=='Library.TEntry' for widget in created)
    assert any(widget.options.get('text')==TR['library.visual.edit_mode'] for widget in created)
    assert library[0].can_edit('sources',library[1]['sources'])
    assert not library[0].can_edit('pipe_sizes',library[1]['pipe_sizes'])
    assert not library[0].can_edit('corrosion',library[1]['corrosion'])


def test_library_chrome_denylist_and_lazy_scope():
    keys=('library.visual.title','library.visual.subtitle','library.visual.no_matches',
          'library.visual.edit_mode','library.visual.create_mode','library2.read_only',
          'library2.ownership.factory','library2.ownership.user','library2.ownership.reference')
    denylist=('Material Library','Read Only','Factory','Library','Search','Cancel','Save')
    for key in keys:
        assert TR[key] and EN[key]
        assert not any(word in TR[key] for word in denylist)
    source=(ROOT/'ui/dialogs/engineering_library_workspace.py').read_text(encoding='utf-8')
    assert 'configure_library_visuals(ttk.Style(self))' in source
    assert 'self._controller.browse(category)' in source
    assert 'self._advanced_filters.grid_remove' in source
    assert "key in ('new','save')" in source
    assert 'watermark' not in source.lower()
