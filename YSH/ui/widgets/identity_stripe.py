"""Three-colour identity stripe (cyan / gold / sunset) used as the app signature."""

from __future__ import annotations

import tkinter as tk

from ui.theme import colors

STRIPE_HEIGHT = 4
# Proportions of the stripe; sunset orange is decorative only, never a state colour.
STRIPE_SEGMENTS = ((colors.SHELL_CYAN, 0.55), (colors.GOLD, 0.30), (colors.SUNSET, 0.15))


class IdentityStripe(tk.Canvas):
    """Draw the brand stripe and keep its proportions when resized."""

    def __init__(self, parent: tk.Misc, *, background: str = colors.NAVY) -> None:
        super().__init__(parent, height=STRIPE_HEIGHT, background=background,
                         highlightthickness=0, borderwidth=0, takefocus=0)
        self.bind("<Configure>", self._redraw)

    def _redraw(self, _event: object = None) -> None:
        width = max(1, self.winfo_width())
        self.delete("all")
        left = 0
        for index, (colour, share) in enumerate(STRIPE_SEGMENTS):
            right = width if index == len(STRIPE_SEGMENTS) - 1 else left + int(width * share)
            self.create_rectangle(left, 0, right, STRIPE_HEIGHT, fill=colour, outline=colour)
            left = right

    @classmethod
    def attach(cls, parent: tk.Misc, *, edge: str = "bottom", background: str = colors.NAVY) -> "IdentityStripe | None":
        """Overlay a stripe on the top or bottom edge of a real Tk container; skipped for non-Tk test doubles."""
        if not isinstance(parent, tk.Misc):
            return None
        stripe = cls(parent, background=background)
        if edge == "top":
            stripe.place(x=0, y=0, relwidth=1.0, height=STRIPE_HEIGHT)
        else:
            stripe.place(x=0, rely=1.0, anchor="sw", relwidth=1.0, height=STRIPE_HEIGHT)
        return stripe
