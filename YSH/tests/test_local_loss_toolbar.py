"""Native toolbar geometry and real Add/Edit/Delete/Clear callbacks."""
from uuid import uuid4
import pytest
from core.local_loss_item import LocalLossItem
from engineering.input_parsing import parse_engineering_float
from .test_fire_phase5cd_navigation import application, shell
from ._tk_geometry import settle_geometry


def prepare(w,module):
    assert w._create_project('Toolbar '+str(uuid4()),'','','fuel')
    page=w._pages[module]
    w._page_host.select(w._page_host._page_keys[module])
    return page


def buttons(page,module):
    return page._loss_action_buttons if module=='discharge_head_loss' else tuple(b for b,_ in page._loss_buttons)


def refresh(page,module):
    (page._refresh if module=='discharge_head_loss' else page._refresh_losses)()


@pytest.mark.parametrize('module',['discharge_head_loss','suction_npsh'])
@pytest.mark.parametrize('size',['1100x700','1440x900'])
def test_single_row_with_right_aligned_total_and_preserved_selection(shell,module,size):
    w=shell;page=prepare(w,module);root=w._root
    page._items={'selected':LocalLossItem('Elbow',2,.5)};refresh(page,module)
    page._tree.selection_set('selected')
    actions=buttons(page,module)
    before=tuple((str(b),str(b['command']),b._icon_name,b._palette,getattr(b._tooltip,'_text',None)) for b in actions)
    root.deiconify();root.geometry(size)
    settle_geometry(root,page._loss_actions,page._tree)
    assert {int(b.grid_info()['row']) for b in actions}=={0}
    assert len({b.winfo_rooty()+b.winfo_height()//2 for b in actions})==1
    for left,right in zip(actions,actions[1:]):
        assert left.winfo_rootx()+left.winfo_width()<=right.winfo_rootx()
    total=page._k_total_context;bar=page._loss_actions
    assert int(total.grid_info()['row'])==0
    assert actions[-1].winfo_rootx()+actions[-1].winfo_width()<=total.winfo_rootx()
    assert total.winfo_rootx()+total.winfo_width()==bar.winfo_rootx()+bar.winfo_width()
    assert bar.winfo_rootx()+bar.winfo_width()<=root.winfo_rootx()+root.winfo_width()
    assert bar.winfo_height()==max(total.winfo_height(),*(b.winfo_height() for b in actions))
    assert page._k_total_context_label['text']=='ΣK:'
    assert page._tree.selection()==('selected',)
    assert before==tuple((str(b),str(b['command']),b._icon_name,b._palette,getattr(b._tooltip,'_text',None)) for b in actions)
    # Repeated resize must not return to the old sticky vertical arrangement.
    root.geometry('1440x900' if size=='1100x700' else '1100x700')
    settle_geometry(root,page._loss_actions,page._tree)
    assert {int(b.grid_info()['row']) for b in actions}=={0}
    assert page._tree.selection()==('selected',)


@pytest.mark.parametrize('module',['discharge_head_loss','suction_npsh'])
def test_actions_confirmations_and_sum_k_remain_functional(shell,module,monkeypatch):
    w=shell;page=prepare(w,module);actions=buttons(page,module)
    callback=type(page)._add if module=='discharge_head_loss' else type(page)._add_loss
    globals_=callback.__globals__
    dialog_items=iter((LocalLossItem('Elbow',2,.5),LocalLossItem('Edited elbow',3,.7),
                       LocalLossItem('Valve',1,2),LocalLossItem('Bend',2,.4)))
    monkeypatch.setattr(globals_['LocalLossItemDialog'],'show',lambda self:next(dialog_items))
    answer=False;prompts=[]
    def confirm(*args,**kwargs):prompts.append(args);return answer
    monkeypatch.setattr(globals_['messagebox'],'askyesno',confirm)
    actions[0].invoke();identifier=next(iter(page._items))
    page._tree.selection_set(identifier);actions[1].invoke()
    assert page._items[identifier].name=='Edited elbow'
    assert page._tree.selection()==(identifier,)
    fields=dict(d='100',q='20',nu='2',l='10',k='.015',h='2') if module=='discharge_head_loss' else dict(diameter='100',flow='20',viscosity='2',length='10',roughness='.015')
    for key,value in fields.items():page._fields[key].set(value)
    def calculate():
        (page._calculate if module=='discharge_head_loss' else page._calculate_suction_loss)()
        result=page._last_result if module=='discharge_head_loss' else page._last_loss
        expected=sum(item.subtotal_k for item in page._items.values())
        assert result.local_loss_coefficient_total==pytest.approx(expected)
        assert parse_engineering_float(page._k_total_summary.get(),field_name='ΣK')==pytest.approx(expected)
    calculate()
    actions[2].invoke();assert identifier in page._items and len(prompts)==1
    answer=True;actions[2].invoke();assert not page._items
    actions[0].invoke();actions[0].invoke();assert len(page._items)==2
    calculate()
    answer=False;actions[3].invoke();assert len(page._items)==2
    answer=True;actions[3].invoke();assert not page._items
    assert all(page._fields[key].get()==value for key,value in fields.items())
    calculate()
