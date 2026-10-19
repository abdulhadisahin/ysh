"""Low-opacity, non-interactive D243 identity watermark for calculation pages."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tkinter as tk
from tkinter import ttk

try:  # Pillow is bundled with the charting runtime, but branding remains optional.
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover - protects source launches missing Pillow.
    Image = None  # type: ignore[assignment]
    ImageTk = None  # type: ignore[assignment]

from ui.theme import colors


def watermark_size(source_size: tuple[int, int], viewport: tuple[int, int]) -> tuple[int, int]:
    """Fit the complete emblem inside its available surface, preserving its ratio."""
    sw, sh = source_size
    width, height = viewport
    if min(sw, sh) <= 1 or min(width, height) <= 24:
        return (0, 0)
    ratio = min(max(1, width - 24) / sw, max(1, height - 24) / sh, 480 / max(sw, sh))
    return (max(1, round(sw * ratio)), max(1, round(sh * ratio)))


class CanvasBackgroundWatermark:
    """Retain the optional Canvas image renderer for plain Canvas surfaces.

    Engineering pages use WorkspaceWatermark on existing control surfaces so
    they reserve no sibling column and avoid an opaque full-page window.
    """

    OPACITY = 0.14
    CENTER_X = 0.5
    CENTER_Y = 0.5
    CACHE_LIMIT = 6

    def __init__(self, canvas: tk.Canvas, source_path: Path | None) -> None:
        """Defer image loading until a visible viewport has usable dimensions."""
        self._canvas = canvas
        self._source_path = source_path
        self._source = None
        self._image = None
        self._cache: dict[tuple[int, int], object] = {}
        self._pending = None
        self._item = None
        if source_path is None or not source_path.is_file() or Image is None or ImageTk is None:
            return
        self._item = canvas.create_image(0, 0, anchor="center", state="hidden")
        canvas.tag_lower(self._item)
        canvas.bind("<Configure>", self._on_canvas_configure, add="+")
        self._pending = canvas.after_idle(self._refresh)

    @property
    def item_id(self) -> int | None:
        """Expose the decorative Canvas item for display-independent tests."""
        return self._item

    def _on_canvas_configure(self, _event: tk.Event[tk.Misc]) -> None:
        if self._pending is None:
            self._pending = self._canvas.after_idle(self._refresh)

    def _refresh(self) -> None:
        self._pending = None
        if self._item is None or Image is None or ImageTk is None:
            return
        width, height = self._canvas.winfo_width(), self._canvas.winfo_height()
        if min(width, height) <= 1:
            return
        try:
            if self._source is None:
                with Image.open(self._source_path) as source_file:
                    self._source = source_file.convert("RGBA")
            # Quantized bounds prevent a resize image for every single pixel.
            size = watermark_size(self._source.size, (width // 8 * 8, height // 8 * 8))
            if min(size) <= 0:
                return
            image = self._cache.get(size)
            if image is None:
                rgba = self._source.resize(size, Image.Resampling.LANCZOS)
                alpha = rgba.getchannel("A").point(lambda value: round(value * self.OPACITY))
                rgba.putalpha(alpha)
                image = ImageTk.PhotoImage(rgba, master=self._canvas)
                self._cache[size] = image
                if len(self._cache) > self.CACHE_LIMIT:
                    del self._cache[next(iter(self._cache))]
            self._image = image
        except (OSError, tk.TclError):
            return
        self._canvas.itemconfigure(self._item, image=self._image, state="normal")
        self._position_in_workspace(width, height)

    def _position_in_workspace(self, canvas_width: int, canvas_height: int) -> None:
        """Keep the complete decorative emblem inside its own viewport."""
        self._canvas.coords(self._item, round(canvas_width * self.CENTER_X),
                            round(canvas_height * self.CENTER_Y))


class WorkspaceWatermark(tk.Label):
    """Render one cached, page-content-relative official-logo watermark.

    The transparent emblem is positioned by the page host.  It remains
    unfocusable and uses the host's existing wheel routing.
    """

    OPACITY = 0.12
    CACHE_LIMIT = 6

    @classmethod
    def is_available(cls) -> bool:
        """Report whether the optional image renderer can safely be used."""
        return Image is not None and ImageTk is not None

    def __init__(
        self,
        parent: tk.Misc,
        source_path: Path,
        wheel_callback: Callable[[tk.Event[tk.Misc]], str | None],
        placement: tuple[float, float],
    ) -> None:
        """Create a decorative layer using only the approved D243 PNG."""
        super().__init__(
            parent,
            background=self._parent_background(parent),
            borderwidth=0,
            highlightthickness=0,
            takefocus=0,
        )
        self._source_path = source_path
        self._wheel_callback = wheel_callback
        self._image_cache: dict[tuple[int, int], object] = {}
        self._source = None
        self._pending = None
        self._active_size = (0, 0)
        self._watermark_image: ImageTk.PhotoImage | None = None
        parent.bind("<Configure>", self._on_parent_configure, add="+")
        self.bind("<MouseWheel>", self._wheel_callback, add="+")
        self.place(relx=placement[0], rely=placement[1], x=-12, y=-12, anchor="se")
        self.lower()  # One stable background layer; controls retain their stacking order.
        self._pending = self.after_idle(self._refresh_image)

    def _on_parent_configure(self, _event: tk.Event[tk.Misc]) -> None:
        """Coalesce resize events without polling or changing control stacking."""
        if self._pending is None:
            self._pending = self.after_idle(self._refresh_image)

    def _refresh_image(self) -> None:
        """Reuse a bounded aspect-preserving rendering inside the existing surface."""
        self._pending = None
        if not self.is_available():
            return
        try:
            viewport = (self.master.winfo_width() // 8 * 8,
                        self.master.winfo_height() // 8 * 8)
            if min(viewport) <= 24:
                self.configure(image="")
                self._active_size = (0, 0)
                return
            if self._source is None:
                with Image.open(self._source_path) as source:
                    self._source = source.convert("RGBA")
            size = watermark_size(self._source.size, viewport)
            if min(size) <= 0 or size == self._active_size:
                return
            image = self._image_cache.get(size)
            if image is None:
                image = self._render_image(size)
                self._image_cache[size] = image
                if len(self._image_cache) > self.CACHE_LIMIT:
                    del self._image_cache[next(iter(self._image_cache))]
            self._active_size = size
            self._watermark_image = image
            self.configure(image=image)
        except (OSError, tk.TclError):
            return

    @staticmethod
    def _parent_background(parent: tk.Misc) -> str:
        """Composite transparent pixels into the page's actual neutral surface."""
        try:
            style_name = str(parent.cget("style"))
            background = ttk.Style(parent).lookup(style_name, "background")
        except tk.TclError:
            background = ""
        return background or colors.WORKSPACE_SURFACE

    def _render_image(self, size: tuple[int, int]) -> object:
        """Derive translucent artwork without modifying the canonical asset."""
        image = self._source.resize(size, Image.Resampling.LANCZOS)
        alpha = image.getchannel("A").point(lambda value: round(value * self.OPACITY))
        image.putalpha(alpha)
        return ImageTk.PhotoImage(image, master=self)
