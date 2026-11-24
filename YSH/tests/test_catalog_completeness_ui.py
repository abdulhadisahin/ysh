"""Published points and mechanical grades remain reachable and read-only."""
from types import SimpleNamespace
import tkinter as tk
import pytest
from engineering.catalog_completion import MechanicalGrade, OperatingFluidProperty
from services.engineering_library_service import EngineeringLibraryService
from i18n.translator import Translator
from ui.dialogs.engineering_library_workspace import EngineeringLibraryWorkspace
from ._tk_geometry import settle_geometry


@pytest.mark.parametrize('size',['1100x700','1440x900'])
@pytest.mark.parametrize('language',['tr','en'])
def test_scoped_library_records_native(library_database,size,language):
    service=EngineeringLibraryService(library_database)
    root=tk.Tk();window=None
    owner=SimpleNamespace(register_localizable=lambda _:None,unregister_localizable=lambda _:None)
    try:
        window=EngineeringLibraryWorkspace(root,service,Translator(language).translate,owner)
        window.geometry(size)
        settle_geometry(root,window,window._tree)
        for category,kind in (('materials',MechanicalGrade),('fluid_properties',OperatingFluidProperty)):
            window.show_category(category)
            record=next(r for r in window._controller.records if isinstance(r,kind))
            window._tree.selection_set(str(record.id));window._select_record()
            settle_geometry(root,window,window._tree)
            assert window._controller.selected==record and window._body.winfo_children()
            assert str(window._buttons['edit']['state'])=='disabled'
            assert window._tree.winfo_rootx()+window._tree.winfo_width()<=window.winfo_rootx()+window.winfo_width()
        window.show_category('material_properties')
        assert any(value==service.completion.grades.get_all()[0].id for value in window._parents.values())
        for row in window._controller.records:
            if hasattr(row,'grade_id'):
                window._tree.selection_set(str(row.id));window._select_record()
                assert str(window._buttons['edit']['state'])=='disabled'
    finally:
        if window is not None:window.destroy()
        root.destroy()
