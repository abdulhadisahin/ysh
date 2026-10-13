"""Shared D243 presentation components used by calculation-module pilots."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ui.assets import empty_state_path, status_icon_fit_mode, status_icon_path
from ui.widgets.asset_loader import AssetImageLoader, LoadedImage
from ui.widgets.scrollable_treeview import ScrollableTreeview


class TableToolbar(ttk.Frame):
    """A compact, reusable host for a technical-table filter or actions."""

    def __init__(self, parent: tk.Misc, **kwargs: object) -> None:
        super().__init__(parent, style="TableToolbar.TFrame", **kwargs)
        self.columnconfigure(0, weight=1)


class TechnicalTable(ScrollableTreeview):
    """Name the shared engineering-table contract without altering Treeview behavior."""


class EmptyState(ttk.Frame):
    """Contextual illustration and native text for a genuinely empty region."""

    def __init__(
        self,
        parent: tk.Misc,
        image_asset: str,
        title: str,
        body: str,
        helper_text: str = "",
        image_size: int = 180,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, style="EmptyState.TFrame", padding=12, **kwargs)
        self.columnconfigure(0, weight=1)
        self._image: LoadedImage | None = AssetImageLoader.load(
            self, empty_state_path(image_asset), image_size
        )
        self._illustration = ttk.Label(self, style="EmptyState.TLabel")
        if self._image is not None:
            self._illustration.configure(image=self._image.rendered)
        self._illustration.grid(row=0, column=0, pady=(0, 6))
        self._title = ttk.Label(self, text=title, style="EmptyStateTitle.TLabel")
        self._title.grid(row=1, column=0, sticky="n")
        self._body = ttk.Label(self, text=body, style="EmptyState.TLabel", justify="center", wraplength=360)
        self._body.grid(row=2, column=0, sticky="n", pady=(3, 0))
        self._helper = ttk.Label(self, text=helper_text, style="EmptyStateHelper.TLabel", justify="center", wraplength=360)
        if helper_text:
            self._helper.grid(row=3, column=0, sticky="n", pady=(3, 0))


class StatusBadge(ttk.Label):
    """A presentation-only compact semantic status label."""

    def __init__(
        self,
        parent: tk.Misc,
        text: str,
        state: str = "information",
        icon_size: int = 22,
        **kwargs: object,
    ) -> None:
        style = str(kwargs.pop("style", f"Status{state.title()}.TLabel"))
        super().__init__(parent, text=text, style=style, compound="left", **kwargs)
        self._status_image: LoadedImage | None = AssetImageLoader.load(
            self,
            status_icon_path(state),
            icon_size,
            fit_mode=status_icon_fit_mode(state),
        )
        if self._status_image is not None:
            self.configure(image=self._status_image.rendered)
