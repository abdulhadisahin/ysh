"""Display-independent layout contracts for the Pipe Design formula panel."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_formula_panel_has_a_dedicated_row_below_pipe_page_content() -> None:
    """The full-width panel does not share a grid row with controls or status."""
    source = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")
    assert 'message_label.grid(row=2, column=0, sticky="w", pady=(8, 0))' in source
    assert 'self._formula_panel.grid(row=3, column=0, sticky="ew", pady=(10, 0))' in source
    assert "self._formula_panel.grid(row=10" not in source


def test_formula_panel_uses_only_grid_in_its_pipe_page_parent() -> None:
    """The Pipe page has no mixed-manager overlap risk for formula content."""
    source = (ROOT / "ui/pages/pipe_design_page.py").read_text(encoding="utf-8")
    assert "self._formula_panel.grid(" in source
    assert "self._formula_panel.pack(" not in source
    assert "self._formula_panel.place(" not in source


def test_inline_panel_expansion_and_host_scrollregion_remain_layout_driven() -> None:
    """Expansion changes normal grid geometry and the page host updates bounds."""
    panel = (ROOT / "ui/widgets/formula_view.py").read_text(encoding="utf-8")
    frame = (ROOT / "ui/widgets/scrollable_frame.py").read_text(encoding="utf-8")
    assert "self._content.grid(row=1" in panel
    assert "self._content.grid_remove()" in panel
    assert 'self.content.bind("<Configure>", self._update_scrollregion)' in frame
    assert "self.canvas.configure(scrollregion=self.canvas.bbox(\"all\"))" in frame
