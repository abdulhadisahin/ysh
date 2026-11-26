"""Native editable cells, invalidation, project isolation and compact geometry."""
from uuid import uuid4
import pytest
from .test_fire_phase5cd_navigation import application,shell
from ._tk_geometry import settle_geometry


def prepared(w):
    assert w._create_project('Batch '+str(uuid4()),'','','fuel')
    page=w._pages['pipe_design']
    w._root.deiconify();w._root.geometry('1440x900')
    w._page_host.select(w._page_host._page_keys['pipe_design'])
    w._page_host._page_keys['pipe_design'].canvas.yview_moveto(1)
    settle_geometry(w._root,page._batch_diameter)
    return page,page._batch_diameter


def test_edit_invalidates_only_its_row_and_single_calculation_is_preserved(shell):
    page,batch=prepared(shell)
    page._fields['q'].set('240');page._fields['v'].set('7');page._calculate_diameter()
    original=dict(page._diameter_result)
    batch.load_inputs([['A','350','7'],['B','240','7'],['Invalid','-1','7'],['Large','999999999','7'],['','','']])
    batch.calculate()
    first,second,bad,large,blank=batch.tree.get_children()
    assert batch.tree.set(first,'dn')=='DN150' and batch.tree.set(second,'dn')=='DN125'
    assert batch.tree.set(bad,'dn') and batch.tree.item(bad,'tags')==('invalid',)
    assert batch.tree.set(large,'diameter') and batch.tree.set(large,'dn')=='Uygun DN bulunamadı'
    assert batch.tree.set(blank,'dn')==''
    batch.set_cell(first,1,'300')
    assert batch.tree.set(first,'diameter')==batch.tree.set(first,'dn')==''
    assert batch.tree.set(second,'dn')=='DN125'
    assert page._diameter_result==original
    batch.calculate()
    page._pipe_standard.set('missing catalog')
    assert all(batch.tree.set(i,'diameter')==batch.tree.set(i,'dn')=='' for i in batch.inputs)


def test_cell_editor_keyboard_and_row_actions(shell):
    _,batch=prepared(shell)
    batch.load_inputs([['A','350','7']]);batch.calculate()
    identity=batch.tree.get_children()[0]
    batch.start_edit(identity,0)
    shell._root.focus_force();batch.editor.focus_set();shell._root.update()
    batch.edit_value.set('Free name / 12')
    assert batch.tree.set(identity,'dn')==''
    batch.editor.event_generate('<Tab>');shell._root.update()
    assert batch.active==(identity,1) and batch.editor is not None
    batch.edit_value.set('240')
    batch.editor.event_generate('<Shift-Tab>');shell._root.update()
    assert batch.active==(identity,0)
    batch.editor.event_generate('<Return>');shell._root.update()
    assert len(batch.inputs)==2 and batch.active[1]==0
    batch.finish_edit();batch.start_edit(identity,3)
    assert batch.editor is None
    batch.tree.selection_set(identity);batch.delete_rows()
    assert identity not in batch.inputs


@pytest.mark.parametrize('size',['1100x700','1440x900'])
def test_table_geometry_and_saved_inputs_without_automatic_recalculation(shell,size):
    page,batch=prepared(shell)
    shell._root.geometry(size)
    settle_geometry(shell._root,batch,batch.tree)
    right=shell._root.winfo_rootx()+shell._root.winfo_width()
    assert batch.tree.winfo_rootx()+batch.tree.winfo_width()<=right
    assert batch.calculate_button.winfo_rootx()+batch.calculate_button.winfo_width()<=right
    assert batch.tree['columns']==('name','flow','velocity','diameter','dn')
    batch.load_inputs([['Saved line','350','7']]);batch.calculate()
    assert shell._save_project()
    project=shell._active_project
    assert shell._create_project('Other '+str(uuid4()),'','','seawater')
    assert page._batch_diameter.export_inputs()==[['','','']]
    assert shell._activate_project(project)
    assert batch.export_inputs()==[['Saved line','350','7']]
    assert all(not batch.tree.set(i,'dn') for i in batch.inputs)
