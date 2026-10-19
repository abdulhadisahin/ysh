"""Aspect-safe, cached equation artwork inside the existing formula body."""
from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk

from ui.widgets.asset_loader import AssetImageLoader, Image


def formula_display_size(source: tuple[int, int], width: int) -> tuple[int, int]:
    """Fit the complete formula into at most 560×280 without upscaling."""
    sw, sh = source
    if min(sw, sh, width) <= 1:
        return (0, 0)
    scale = min(max(1, width - 16) / sw, 560 / sw, 280 / sh, 1.0)
    return max(1, round(sw * scale)), max(1, round(sh * scale))


class FormulaImage(ttk.Label):
    """Render complete visible artwork and coalesce parent resize events."""

    def __init__(self, parent: tk.Misc, path: Path | None, **kwargs: object) -> None:
        """Decode only on explicit Formula View access; retain active Tk references."""
        super().__init__(parent, **kwargs)
        self._path = path
        self._source_size = (0, 0)
        self._target = 0
        self._pending = None
        self._width = 576
        self._loaded = None
        if path is not None and Image is not None:
            try:
                with Image.open(path) as image:
                    visible = AssetImageLoader._visible_content(image.convert("RGBA"), 1, 2)
                    self._source_size = visible.size
            except OSError:
                pass
        self._refresh()
        parent.bind("<Configure>", self._on_configure, add="+")
        self.bind("<Destroy>", self._on_destroy, add="+")

    @property
    def available(self) -> bool:
        """Report whether artwork loaded, allowing the standard fallback chain."""
        return self._loaded is not None

    def _on_configure(self, event: tk.Event) -> None:
        if event.width <= 16:
            return
        self._width = max(16, event.width // 16 * 16)
        if self._pending is None:
            self._pending = self.after_idle(self._refresh)

    def _refresh(self) -> None:
        self._pending = None
        size = formula_display_size(self._source_size, self._width)
        target = max(size)
        if target <= 0 or target == self._target:
            return
        loaded = AssetImageLoader.load(self, self._path, target, fit_mode="visible_content",
                                       alpha_threshold=1, padding_percent=2)
        if loaded is not None:
            self._target = target
            self._loaded = loaded
            self.configure(image=loaded.rendered)

    def _on_destroy(self, _event: object = None) -> None:
        if self._pending is not None:
            self.after_cancel(self._pending)
            self._pending = None
