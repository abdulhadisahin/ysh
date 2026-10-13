"""Centralized, cache-backed loading for optional packaged visual assets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tkinter as tk

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover - optional artwork must never block startup.
    Image = None  # type: ignore[assignment]
    ImageTk = None  # type: ignore[assignment]


@dataclass(frozen=True)
class LoadedImage:
    """Keep source and rendered image references alive for one UI consumer."""

    source: tk.PhotoImage
    rendered: tk.PhotoImage


class AssetImageLoader:
    """Load existing resource images safely across source and frozen execution.

    Paths are resolved by :mod:`ui.assets`; missing optional artwork returns
    ``None`` so commands and layouts remain fully usable without it.
    """

    _cache: dict[tuple[str, str, int, str, int, int, float], LoadedImage] = {}

    @staticmethod
    def _visible_content(rgba: object, alpha_threshold: int, padding_percent: int) -> object:
        """Crop transparent margins in memory while retaining a small safe border."""
        if Image is None or not hasattr(rgba, "getchannel"):
            return rgba
        alpha = rgba.getchannel("A")
        mask = alpha.point(lambda value: 255 if value >= alpha_threshold else 0)
        bbox = mask.getbbox()
        if bbox is None:
            return rgba
        left, top, right, bottom = bbox
        content_width, content_height = right - left, bottom - top
        padding = max(1, round(max(content_width, content_height) * padding_percent / 100))
        bounds = (
            max(0, left - padding), max(0, top - padding),
            min(rgba.width, right + padding), min(rgba.height, bottom + padding),
        )
        return rgba.crop(bounds)

    @classmethod
    def _glyph_content(cls, rgba: object, alpha_threshold: int, padding_percent: int) -> object:
        """Extract the central symbol viewport from the approved framed action art.

        The action masters contain a large opaque navy/gold card and a lower
        text plaque.  Alpha bounds therefore describe the card, not the inner
        glyph.  This deliberately conservative viewport is used only by action
        buttons; all branding and composition-sensitive art keeps canvas fit.
        """
        visible = cls._visible_content(rgba, alpha_threshold, padding_percent)
        if Image is None or not hasattr(visible, "crop") or visible.width < 8 or visible.height < 8:
            return visible
        width, height = visible.width, visible.height
        left, right = round(width * 0.24), round(width * 0.76)
        top, bottom = round(height * 0.12), round(height * 0.64)
        if right - left < 4 or bottom - top < 4:
            return visible
        glyph = visible.crop((left, top, right, bottom))
        return cls._visible_content(glyph, alpha_threshold, padding_percent)

    @classmethod
    def _full_asset_safe(cls, rgba: object) -> object:
        """Retain one composed action tile with its frame, glow, and shadow.

        Composite D243 button assets are not mere glyphs: their navy tile,
        gold keyline, and soft outer treatment are part of the approved visual
        composition.  A threshold of one keeps anti-aliased and translucent
        edge pixels, while eight percent in-memory breathing room prevents a
        rendered tile from being cropped at its own output edge.
        """
        return cls._visible_content(rgba, alpha_threshold=1, padding_percent=8)

    @staticmethod
    def _silhouette_safe(rgba: object) -> object:
        """Fit one standalone transparent symbol without trimming its outline.

        Some approved status masters deliberately place anti-aliased pixels at
        the canvas edge.  A conventional crop cannot leave breathing room in
        that case, and the framed-action ``glyph_content`` policy would cut the
        symbol to a central viewport.  This status-only mode instead creates a
        transparent in-memory border around the complete alpha silhouette.
        """
        if Image is None or not hasattr(rgba, "getchannel"):
            return rgba
        alpha = rgba.getchannel("A")
        bbox = alpha.point(lambda value: 255 if value >= 1 else 0).getbbox()
        if bbox is None:
            return rgba
        silhouette = rgba.crop(bbox)
        padding = max(1, round(max(silhouette.width, silhouette.height) * 7 / 100))
        safe_canvas = Image.new(
            "RGBA",
            (silhouette.width + padding * 2, silhouette.height + padding * 2),
            (0, 0, 0, 0),
        )
        safe_canvas.alpha_composite(silhouette, (padding, padding))
        return safe_canvas

    @staticmethod
    def _dpi_scale(master: tk.Misc) -> float:
        """Expose Tk scaling to the cache without coupling assets to a monitor."""
        try:
            return round(float(master.tk.call("tk", "scaling")), 3)
        except (AttributeError, tk.TclError, TypeError, ValueError):
            return 1.0

    @classmethod
    def load(
        cls,
        master: tk.Misc,
        path: Path | None,
        target_size: int,
        *,
        fit_mode: str = "canvas",
        alpha_threshold: int = 8,
        padding_percent: int = 5,
    ) -> LoadedImage | None:
        """Return a cached, aspect-safe image rendered with high-quality scaling."""
        if path is None or not path.is_file() or target_size <= 0:
            return None
        interpreter = getattr(master, "tk", None)
        if interpreter is None:
            return None
        if fit_mode not in {
            "canvas", "visible_content", "glyph_content", "full_asset_safe", "silhouette_safe",
        }:
            fit_mode = "canvas"
        # ``full_asset_safe`` owns its conservative threshold and margin so
        # callers cannot accidentally crop a composite tile through defaults.
        if fit_mode == "full_asset_safe":
            alpha_threshold, padding_percent = 1, 8
        key = (str(interpreter), str(path.resolve()), target_size, fit_mode, alpha_threshold, padding_percent, cls._dpi_scale(master))
        cached = cls._cache.get(key)
        if cached is not None:
            return cached
        if Image is None or ImageTk is None:
            return None
        try:
            with Image.open(path) as source_file:
                rgba = source_file.convert("RGBA")
            render_source = {
                "canvas": rgba,
                "visible_content": cls._visible_content(rgba, alpha_threshold, padding_percent),
                "glyph_content": cls._glyph_content(rgba, alpha_threshold, padding_percent),
                "full_asset_safe": cls._full_asset_safe(rgba),
                "silhouette_safe": cls._silhouette_safe(rgba),
            }[fit_mode]
            ratio = min(target_size / render_source.width, target_size / render_source.height, 1.0)
            rendered_size = (
                max(1, round(render_source.width * ratio)),
                max(1, round(render_source.height * ratio)),
            )
            rendered_rgba = render_source.resize(rendered_size, Image.Resampling.LANCZOS)
            source = ImageTk.PhotoImage(rgba, master=master)
            rendered = ImageTk.PhotoImage(rendered_rgba, master=master)
        except (OSError, tk.TclError):
            return None
        loaded = LoadedImage(source=source, rendered=rendered)
        cls._cache[key] = loaded
        return loaded
