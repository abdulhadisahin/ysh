"""Static regression tests for scoped mouse-wheel ownership."""

from __future__ import annotations

from pathlib import Path

from ui.widgets.scrollable_frame import ScrollableFrame


ROOT = Path(__file__).resolve().parents[1]


def test_treeview_routes_wheel_to_the_outer_page_only_at_its_boundary() -> None:
    """Tables retain local scrolling while allowing natural page continuation."""
    source = (ROOT / "ui/widgets/scrollable_treeview.py").read_text(encoding="utf-8")
    assert 'bind("<MouseWheel>"' in source
    assert "ScrollableFrame.route_nested_mousewheel(event, self.tree)" in source


def test_entries_and_closed_combos_route_to_page_scroll() -> None:
    """Keep wheel input non-destructive for data-entry controls."""
    source = (ROOT / "ui/widgets/scrollable_frame.py").read_text(encoding="utf-8")
    assert '"TEntry"' in source and '"TCombobox"' in source
    assert 'child.bind("<MouseWheel>", self.scroll_mousewheel' in source
    assert "bind_all" not in source


class _NestedView:
    """Minimal yview-compatible fixture for boundary-routing contracts."""

    def __init__(self, view: tuple[float, float]) -> None:
        self._view = view

    def yview(self) -> tuple[float, float]:
        """Return the current visible fraction."""
        return self._view


def test_nested_wheel_boundary_detection_prefers_the_inner_scrollable() -> None:
    """Direction-aware checks prevent outer scrolling while inner rows remain."""
    middle = _NestedView((0.2, 0.8))
    top = _NestedView((0.0, 0.8))
    bottom = _NestedView((0.2, 1.0))

    assert ScrollableFrame._can_scroll(middle, -1)
    assert ScrollableFrame._can_scroll(middle, 1)
    assert not ScrollableFrame._can_scroll(top, -1)
    assert not ScrollableFrame._can_scroll(bottom, 1)


def test_canvas_descendants_use_the_same_boundary_router_as_tables() -> None:
    """Embedded TkAgg canvases cannot permanently trap normal page navigation."""
    source = (ROOT / "ui/widgets/scrollable_frame.py").read_text(encoding="utf-8")

    assert 'widget_class == "Canvas"' in source
    assert "route_nested_mousewheel" in source
    assert "nearest_page_host" in source
