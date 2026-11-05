"""Native geometry and warning boundaries for compact calculation inputs."""
from dataclasses import replace

import pytest

from engineering.warning_rules import evaluate_velocity
from ui.theme.spacing import NUMERIC_INPUT_WIDTH
from .test_fire_phase5cd_navigation import application, shell
from .test_ui_consistency_phase7 import descendants, assert_horizontal_bounds, review_language


@pytest.mark.parametrize('size', [(1100,700),(1280,800),(1440,900),(1700,1000)])
@pytest.mark.parametrize('language', ['tr','en'])
def test_compact_numeric_geometry_and_units(shell, size, language):
    w=shell; root=w._root; old=w._localization.language
    try:
        review_language(w,language)
        root.deiconify(); root.geometry(f'{size[0]}x{size[1]}'); root.update()
        tested=set()
        for family in ('fuel','fire'):
            w._show_family(family,dirty=False); root.update()
            host=w._page_host if family=='fuel' else w._fire_workspace.host
            for key,viewport in host._page_keys.items():
                host.select(viewport); root.update()
                page=w._pages[key] if family=='fuel' else w._fire_workspace.views[key]
                widgets=list(descendants(page))
                entries=[item for item in widgets if getattr(item,'numeric_width_class',None)=='compact']
                assert entries, key
                tested.add(key)
                for entry in entries:
                    assert int(entry.cget('width'))==NUMERIC_INPUT_WIDTH
                    if not entry.winfo_ismapped():
                        continue  # Inactive Transfer mode deliberately hides its controls.
                    assert entry.winfo_width()==entry.winfo_reqwidth()
                    # Numeric pairs pack their units; ordinary grids use the
                    # following column. Pipe Q/V include units in their labels.
                    if entry.winfo_manager()=='pack':
                        units=[item for item in entry.master.winfo_children() if item is not entry]
                    else:
                        info=entry.grid_info(); row=int(info['row']); col=int(info['column'])
                        units=[item for item in entry.master.grid_slaves(row=row,column=col+1)
                               if item.winfo_class() in ('TLabel','TCombobox')]
                        if key=='pipe_design': units=[]
                    for unit in units:
                        assert unit.winfo_ismapped()
                        gap=unit.winfo_rootx()-(entry.winfo_rootx()+entry.winfo_width())
                        assert 0<=gap<=16, (key,str(entry),gap)
                assert_horizontal_bounds(widgets,viewport.canvas)
                if family=='fire':
                    assert len(entries)==4
                    # Source metadata entries remain independent of numeric sizing.
                    assert all(not hasattr(editor,'numeric_width_class')
                               for editor in page.meta_editors.values() if hasattr(editor,'cget'))
        assert len(tested)==6
    finally:
        w._localization.set_language(old)


def test_pipe_suppresses_only_man_source_and_preserves_other_findings(monkeypatch):
    import ui.pages.pipe_design_page as module
    page=module.PipeDesignPage.__new__(module.PipeDesignPage)
    page._diameter_result={'diameter_mm':59.0}
    page._diameter_warning_velocity_m_s=.32
    page._selected_circuit_code=lambda:'FUEL'
    page._selected_line_role_code=lambda:'SUCTION'
    man=evaluate_velocity('DIESEL_FUEL','SUCTION',.32)[0]
    other=replace(man,code='other.advice',source_id='OTHER_SOURCE')
    monkeypatch.setattr(module,'evaluate_velocity',lambda *_:(man,other))
    page._evaluate_velocity_warning()
    assert page._engineering_findings==(other,)
    assert page._diameter_result=={'diameter_mm':59.0}
    # Shared MAN guidance is still available to other hydraulic modules.
    assert evaluate_velocity('DIESEL_FUEL','SUCTION',.32)==(man,)
