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


class CanvasBackgroundWatermark:
    """Draw a non-interactive watermark below a Canvas window item.

    Unlike the retired foreground-label approach, this renders as a Canvas
    image below the page content window.  It therefore cannot receive focus,
    intercept clicks, or change the stacking order of engineering controls.
    """

    # Temporary diagnostic setting: render the approved watermark at full
    # opacity so Windows verification can distinguish alpha from layering.
    OPACITY = 1.0
    WIDTH_FRACTION = 0.52
    CENTER_X = 0.5
    CENTER_Y = 0.5

    def __init__(self, canvas: tk.Canvas, source_path: Path | None) -> None:
        self._canvas = canvas
        self._source_path = source_path
        self._image: ImageTk.PhotoImage | None = None
        self._active_width = 0
        self._item: int | None = None
        if source_path is None or not source_path.is_file() or Image is None or ImageTk is None:
            return
        self._item = canvas.create_image(0, 0, anchor="center", state="hidden")
        canvas.tag_lower(self._item)
        canvas.bind("<Configure>", self._on_canvas_configure, add="+")
        canvas.after_idle(self._refresh)

    @property
    def item_id(self) -> int | None:
        """Expose the decorative Canvas item for display-independent tests."""
        return self._item

    def _on_canvas_configure(self, _event: tk.Event[tk.Misc]) -> None:
        self._refresh()

    def _refresh(self) -> None:
        if self._item is None or self._source_path is None or Image is None or ImageTk is None:
            return
        canvas_width = self._canvas.winfo_width()
        canvas_height = self._canvas.winfo_height()
        width = max(1, round(canvas_width * self.WIDTH_FRACTION))
        if width == self._active_width:
            self._position_in_workspace(canvas_width, canvas_height)
            return
        try:
            with Image.open(self._source_path) as source_file:
                image = source_file.convert("RGBA")
            height = max(1, round(image.height * (width / image.width)))
            image = image.resize((width, height), Image.Resampling.LANCZOS)
            alpha = image.getchannel("A").point(lambda value: round(value * self.OPACITY))
            image.putalpha(alpha)
            self._image = ImageTk.PhotoImage(image, master=self._canvas)
        except (OSError, tk.TclError):
            return
        self._active_width = width
        self._canvas.itemconfigure(self._item, image=self._image, state="normal")
        self._position_in_workspace(canvas_width, canvas_height)
        self._canvas.tag_lower(self._item)

    def _position_in_workspace(self, canvas_width: int, canvas_height: int) -> None:
        """Keep the decorative emblem centered in the engineering viewport."""
        if self._item is not None:
            self._canvas.coords(
                self._item,
                round(canvas_width * self.CENTER_X),
                round(canvas_height * self.CENTER_Y),
            )


class WorkspaceWatermark(tk.Label):
    """Render one cached, page-content-relative official-logo watermark.

    The transparent emblem is positioned by the page host.  It remains
    unfocusable and uses the host's existing wheel routing.
    """

    OPACITY = 0.06
    PREFERRED_WIDTH = 600
    MINIMUM_WIDTH = 520
    MAXIMUM_WIDTH = 680
    VIEWPORT_MARGIN = 160

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
        self._image_cache: dict[int, object] = {}
        self._active_width = 0
        self._watermark_image: ImageTk.PhotoImage | None = None
        parent.bind("<Configure>", self._on_parent_configure, add="+")
        self.bind("<MouseWheel>", self._wheel_callback, add="+")
        self.place(relx=placement[0], rely=placement[1], anchor="center")
        self.after_idle(self._refresh_image)

    def _on_parent_configure(self, _event: tk.Event[tk.Misc]) -> None:
        """Regenerate only when a resize selects a new cached target width."""
        self._refresh_image()

    def _refresh_image(self) -> None:
        """Keep a proportionate low-opacity rendering at the current page width."""
        if not self.is_available():
            return
        width = self._target_width()
        if width <= 0 or width == self._active_width:
            return
        image = self._image_cache.get(width)
        if image is None:
            image = self._render_image(width)
            self._image_cache[width] = image
        self._active_width = width
        self._watermark_image = image
        self.configure(image=image)

    def _target_width(self) -> int:
        """Choose a bounded fraction of the page while preserving responsive space."""
        available = self.master.winfo_width() if self.master is not None else 0
        if available <= 1:
            return 0
        available_width = max(self.MINIMUM_WIDTH, available - self.VIEWPORT_MARGIN)
        return min(self.MAXIMUM_WIDTH, self.PREFERRED_WIDTH, available_width)

    @staticmethod
    def _parent_background(parent: tk.Misc) -> str:
        """Composite transparent pixels into the page's actual neutral surface."""
        try:
            style_name = str(parent.cget("style"))
            background = ttk.Style(parent).lookup(style_name, "background")
        except tk.TclError:
            background = ""
        return background or colors.WORKSPACE_SURFACE

    def _render_image(self, width: int) -> object:
        """Create a derived translucent rendering without modifying the source asset."""
        if not self.is_available():
            raise RuntimeError("Pillow is required to render an optional workspace watermark.")
        with Image.open(self._source_path) as source:
            image = source.convert("RGBA")
            ratio = width / image.width
            height = max(1, round(image.height * ratio))
            image = image.resize((width, height), Image.Resampling.LANCZOS)
        alpha = image.getchannel("A").point(lambda value: round(value * self.OPACITY))
        image.putalpha(alpha)
        return ImageTk.PhotoImage(image, master=self)
