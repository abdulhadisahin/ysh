"""New user-approved shell/underlay contract, independent of screenshot capture."""
import pytest
from PIL import Image

from ui.theme import colors
from .test_fire_phase5cd_navigation import application, shell
from .test_ui_consistency_phase7 import descendants, assert_horizontal_bounds, review_language


def test_context_state_preserved_and_project_editor_available(shell,monkeypatch):
    w=shell;before=w._system_context.to_dict() if hasattr(w._system_context,'to_dict') else w._system_context
    from ui.dialogs import project_engineering_context
    opened=[];original=project_engineering_context.ProjectEngineeringContextDialog
    def tracked(owner):
        dialog=original(owner);opened.append(dialog);return dialog
    monkeypatch.setattr(project_engineering_context,'ProjectEngineeringContextDialog',tracked)
    assert w._create_project('Context integration test','','','fuel')
    w._root.deiconify();w._open_system_context();w._root.update()
    try:
        assert len(opened)==1 and opened[0].window.winfo_ismapped()
        assert not w._context_panel.winfo_ismapped()
        assert (w._system_context.to_dict() if hasattr(w._system_context,'to_dict') else w._system_context)==before
    finally:
        if opened:opened[0].window.destroy()
