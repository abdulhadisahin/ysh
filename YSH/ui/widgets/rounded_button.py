"""Image-backed rounded ttk buttons for controlled presentation prototypes."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from collections.abc import Callable
from tkinter import font as tkfont
from tkinter import ttk


@dataclass(frozen=True, slots=True)
class RoundedButtonPalette:
    """Describe the four visual surface states of one rounded button."""

    normal: tuple[str, str]
    hover: tuple[str, str]
    pressed: tuple[str, str]
    disabled: tuple[str, str]
    focus_border: str


TRANSFER_PRIMARY_PALETTE = RoundedButtonPalette(
    normal=("#F47A16", "#B7520A"),
    hover=("#F98D32", "#B7520A"),
    pressed=("#C85B08", "#9A4406"),
    disabled=("#E9C9B1", "#D5AD8D"),
    focus_border="#C85B08",
)
DISCHARGE_PRIMARY_PALETTE = RoundedButtonPalette(
    normal=("#1265D8", "#0D55B8"),
    hover=("#2878E4", "#0D55B8"),
    pressed=("#0D55B8", "#093D84"),
    disabled=("#B9CDE9", "#A3B9D7"),
    focus_border="#0D55B8",
)
SUCTION_PRIMARY_PALETTE = RoundedButtonPalette(
    normal=("#2600FF", "#1E00CC"),
    hover=("#3E1AFF", "#1E00CC"),
    pressed=("#1E00CC", "#170099"),
    disabled=("#C9C2EA", "#B6ADDC"),
    focus_border="#1E00CC",
)
ADD_BUTTON_PALETTE = RoundedButtonPalette(
    normal=("#F0FAF7", "#159A55"),
    hover=("#E2F6EE", "#218F59"),
    pressed=("#D2EEDF", "#117A45"),
    disabled=("#EDF4F0", "#C6D8CD"),
    focus_border="#117A45",
)
EDIT_BUTTON_PALETTE = RoundedButtonPalette(
    normal=("#F2F7FF", "#1265D8"),
    hover=("#E5EFFF", "#2878E4"),
    pressed=("#D6E5FF", "#0D55B8"),
    disabled=("#EEF2F8", "#C4D1E3"),
    focus_border="#0D55B8",
)
DELETE_BUTTON_PALETTE = RoundedButtonPalette(
    normal=("#FFF3F4", "#E52B32"),
    hover=("#FFE7E9", "#EC454A"),
    pressed=("#FFD7DA", "#B4232A"),
    disabled=("#F7EFF0", "#E1C7C9"),
    focus_border="#B4232A",
)
NEUTRAL_BUTTON_PALETTE = RoundedButtonPalette(
    normal=("#F9FBFD", "#C8D5E3"),
    hover=("#EEF4F8", "#AABFD3"),
    pressed=("#E0EAF2", "#8EA8C2"),
    disabled=("#EEF2F6", "#DCE4ED"),
    focus_border="#596B82",
)
CLEAR_ALL_BUTTON_PALETTE = RoundedButtonPalette(
    normal=("#FFF9EF", "#C79540"),
    hover=("#FFF1D7", "#D5A44D"),
    pressed=("#FFE5B5", "#A77A2D"),
    disabled=("#F7F2E9", "#DDD2BE"),
    focus_border="#A77A2D",
)
FORMULA_BUTTON_PALETTE = RoundedButtonPalette(
    normal=("#F4F2FF", "#2600FF"),
    hover=("#E8E4FF", "#2600FF"),
    pressed=("#DCD6FF", "#1E00CC"),
    disabled=("#F1EFF5", "#D8D0E4"),
    focus_border="#1E00CC",
)


def create_rounded_button(
    parent: tk.Misc,
    text: str,
    command: Callable[[], object],
    *,
    style: str,
    palette: RoundedButtonPalette,
    primary: bool = False,
    outside_background: str | None = None,
) -> "RoundedImageButton":
    """Create one compact module action without duplicating visual geometry."""
    return RoundedImageButton(
        parent,
        text=text,
        command=command,
        style=style,
        palette=palette,
        outside_background=outside_background,
        horizontal_padding=15 if primary else 14,
        vertical_padding=6,
    )


class RoundedImageButton(ttk.Button):
    """Keep native button interaction while painting a rounded image surface.

    The image provides only the reusable surface.  The inherited ttk label
    remains live text, so localization and keyboard button semantics remain
    native to Tk.
    """

    def __init__(
        self,
        parent: tk.Misc,
        *,
        palette: RoundedButtonPalette,
        outside_background: str | None = None,
        radius: int = 9,
        horizontal_padding: int = 20,
        vertical_padding: int = 9,
        **kwargs: object,
    ) -> None:
        """Create a native ttk button with an aspect-safe rounded surface."""
        self._palette = palette
        self._outside_background = outside_background
        self._radius = radius
        self._horizontal_padding = horizontal_padding
        self._vertical_padding = vertical_padding
        self._hovered = False
        self._pressed = False
        self._focused = False
        self._stable_texts: tuple[str, ...] = ()
        self._surface_images: dict[str, tk.PhotoImage] = {}
        requested_style = str(kwargs.get("style", "TButton"))
        if outside_background is not None:
            kwargs["style"] = self._surface_aware_style(
                parent,
                requested_style,
                outside_background,
            )
        super().__init__(parent, compound="center", **kwargs)
        self.bind("<Configure>", self._on_configure, add="+")
        self.bind("<Enter>", self._on_enter, add="+")
        self.bind("<Leave>", self._on_leave, add="+")
        self.bind("<ButtonPress-1>", self._on_press, add="+")
        self.bind("<ButtonRelease-1>", self._on_release, add="+")
        self.bind("<FocusIn>", self._on_focus_in, add="+")
        self.bind("<FocusOut>", self._on_focus_out, add="+")
        self.after_idle(self._refresh_surface)

    @staticmethod
    def _surface_aware_style(
        parent: tk.Misc,
        base_style: str,
        outside_background: str,
    ) -> str:
        """Mirror a button style while matching its rectangular host to its parent."""
        style = ttk.Style(parent)
        color_key = outside_background.removeprefix("#").upper()
        derived_style = f"Surface{color_key}.{base_style}"
        base_settings = style.configure(base_style)
        if base_settings:
            style.configure(derived_style, **base_settings)
        base_map = style.map(base_style)
        if base_map:
            style.map(derived_style, **base_map)
        style.configure(
            derived_style,
            background=outside_background,
            borderwidth=0,
            focusthickness=0,
            padding=0,
            relief="flat",
        )
        return derived_style

    def configure(self, cnf: object | None = None, **kwargs: object) -> object:
        """Refresh the generated surface after text or state changes."""
        if "text" in kwargs:
            super().configure(image="")
            self._surface_images.clear()
        result = super().configure(cnf, **kwargs)
        if "state" in kwargs or "text" in kwargs:
            self.after_idle(self._refresh_surface)
        return result

    config = configure

    def set_stable_texts(self, texts: tuple[str, ...]) -> None:
        """Reserve the largest natural surface needed by interchangeable labels."""
        self._stable_texts = tuple(texts)
        self._surface_images.clear()
        self.after_idle(self._refresh_surface)

    def _on_configure(self, _event: tk.Event[tk.Misc]) -> None:
        """Regenerate an undistorted surface after a native size change."""
        self._refresh_surface()

    def _on_enter(self, _event: tk.Event[tk.Misc]) -> None:
        """Display the hover surface while the pointer is over an enabled button."""
        self._hovered = True
        self._refresh_surface()

    def _on_leave(self, _event: tk.Event[tk.Misc]) -> None:
        """Restore the normal surface after the pointer leaves the button."""
        self._hovered = False
        self._pressed = False
        self._refresh_surface()

    def _on_press(self, _event: tk.Event[tk.Misc]) -> None:
        """Display the pressed surface without altering the existing command."""
        self._pressed = True
        self._refresh_surface()

    def _on_release(self, _event: tk.Event[tk.Misc]) -> None:
        """Restore the hover surface after native button command processing."""
        self._pressed = False
        self._refresh_surface()

    def _on_focus_in(self, _event: tk.Event[tk.Misc]) -> None:
        """Make keyboard focus visible in the rendered border."""
        self._focused = True
        self._refresh_surface()

    def _on_focus_out(self, _event: tk.Event[tk.Misc]) -> None:
        """Remove the focus border when keyboard focus moves away."""
        self._focused = False
        self._refresh_surface()

    def _refresh_surface(self) -> None:
        """Select or create an idempotent surface from natural content dimensions."""
        width, height = self._content_surface_dimensions()
        state_name = self._surface_state_name()
        cache_key = (
            f"{state_name}:{int(self._focused)}:{width}:{height}:"
            f"{self._outside_background or 'transparent'}"
        )
        surface = self._surface_images.get(cache_key)
        if surface is None:
            fill, border = getattr(self._palette, state_name)
            if self._focused and state_name != "disabled":
                border = self._palette.focus_border
            surface = self._create_surface(width, height, fill, border)
            self._surface_images[cache_key] = surface
        super().configure(image=surface)

    def _content_surface_dimensions(self) -> tuple[int, int]:
        """Measure text and padding without reusing a prior rendered surface size."""
        style_name = str(self.cget("style"))
        font_spec = ttk.Style(self).lookup(style_name, "font") or "TkDefaultFont"
        font = tkfont.Font(root=self, font=font_spec)
        texts = self._stable_texts or (str(self.cget("text")),)
        text_width = max(
            font.measure(line)
            for text in texts
            for line in (text.splitlines() or [""])
        )
        line_count = max(max(1, len(text.splitlines())) for text in texts)
        return self._surface_dimensions_from_content(
            text_width,
            font.metrics("linespace") * line_count,
            self._horizontal_padding,
            self._vertical_padding,
        )

    @staticmethod
    def _surface_dimensions_from_content(
        content_width: int,
        content_height: int,
        horizontal_padding: int,
        vertical_padding: int,
    ) -> tuple[int, int]:
        """Return the stable rendered dimensions for one measured text surface."""
        return (
            max(1, content_width) + (horizontal_padding * 2),
            max(20, content_height + (vertical_padding * 2)),
        )

    def _surface_state_name(self) -> str:
        """Resolve the visual state without changing ttk's native state model."""
        if self.instate(("disabled",)):
            return "disabled"
        if self._pressed:
            return "pressed"
        if self._hovered:
            return "hover"
        return "normal"

    def _create_surface(
        self,
        width: int,
        height: int,
        fill: str,
        border: str,
    ) -> tk.PhotoImage:
        """Render a transparent-corner rounded surface without stretching art."""
        image = tk.PhotoImage(master=self, width=width, height=height)
        radius = min(self._radius, max(2, (min(width, height) // 2) - 1))
        for y in range(height):
            runs: list[tuple[int, int, str]] = []
            run_start = 0
            run_color: str | None = None
            for x in range(width):
                color = self._surface_pixel(x, y, width, height, radius, fill, border)
                if color != run_color:
                    if run_color is not None:
                        runs.append((run_start, x, run_color))
                    run_start = x
                    run_color = color
            if run_color is not None:
                runs.append((run_start, width, run_color))
            for start, end, color in runs:
                image.put(color, to=(start, y, end, y + 1))
        if self._outside_background is None:
            self._set_transparent_corners(image, width, height, radius)
        return image

    def _surface_pixel(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        radius: int,
        fill: str,
        border: str,
    ) -> str:
        """Return the correct fill or border color for one rounded-surface pixel."""
        if not self._inside_rounded_rectangle(x, y, width, height, radius):
            return self._outside_background or fill
        if self._inside_rounded_rectangle(
            x - 1,
            y - 1,
            width - 2,
            height - 2,
            max(radius - 1, 1),
        ):
            return fill
        return border

    @staticmethod
    def _inside_rounded_rectangle(
        x: int,
        y: int,
        width: int,
        height: int,
        radius: int,
    ) -> bool:
        """Determine whether a pixel lies inside a rounded rectangle."""
        if x < 0 or y < 0 or x >= width or y >= height:
            return False
        nearest_x = min(max(x, radius), width - radius - 1)
        nearest_y = min(max(y, radius), height - radius - 1)
        return (x - nearest_x) ** 2 + (y - nearest_y) ** 2 <= radius**2

    @staticmethod
    def _set_transparent_corners(
        image: tk.PhotoImage,
        width: int,
        height: int,
        radius: int,
    ) -> None:
        """Preserve true rounded corners when Tk supports PhotoImage transparency."""
        setter = getattr(image, "transparency_set", None)
        if not callable(setter):
            return
        for y in range(height):
            for x in range(width):
                if not RoundedImageButton._inside_rounded_rectangle(
                    x, y, width, height, radius
                ):
                    setter(x, y, True)
