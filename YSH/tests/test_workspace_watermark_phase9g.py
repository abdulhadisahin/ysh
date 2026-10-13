"""Display-independent contracts for Phase 9G branding watermarks."""

from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "resources"
MASTER_LOGO_SHA256 = "8e2f26c9967eb51554a404e2b7404d2076b897ca02024e06c3f5ed42d2a4c713"


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_watermark_uses_the_approved_asset_with_a_bounded_translucent_render() -> None:
    """The watermark derives a cached low-opacity view; it never edits the logo file."""
    source = _source("ui/widgets/workspace_watermark.py")

    assert "OPACITY = 0.06" in source
    assert "PREFERRED_WIDTH = 600" in source
    assert "MINIMUM_WIDTH = 520" in source
    assert "MAXIMUM_WIDTH = 680" in source
    assert "Image.open(self._source_path)" in source
    assert "image.putalpha(alpha)" in source
    assert "Image.Resampling.LANCZOS" in source
    assert "self._image_cache" in source
    assert ".save(" not in source


def test_canvas_watermark_stays_centered_below_the_workspace_content() -> None:
    """All calculation pages share one centered Canvas-only background layer."""
    watermark = _source("ui/widgets/workspace_watermark.py")
    host = _source("ui/widgets/scrollable_page_host.py")

    assert "CENTER_X = 0.5" in watermark
    assert "CENTER_Y = 0.5" in watermark
    assert "def _position_in_workspace" in watermark
    assert "round(canvas_width * self.CENTER_X)" in watermark
    assert "round(canvas_height * self.CENTER_Y)" in watermark
    assert "host.set_background_watermark(d243_watermark_logo_path())" in host


def test_technical_logo_derivatives_preserve_the_master_emblem_without_square_background() -> None:
    """The technical files keep the master immutable and only clear its outside corners."""
    master = RESOURCES / "d243_logo.png"
    ui_logo = RESOURCES / "d243_logo_ui.png"
    watermark = RESOURCES / "d243_logo_watermark.png"

    assert hashlib.sha256(master.read_bytes()).hexdigest() == MASTER_LOGO_SHA256
    with Image.open(master) as master_image, Image.open(ui_logo) as ui_image, Image.open(watermark) as watermark_image:
        for derivative in (ui_image, watermark_image):
            assert derivative.size == master_image.size
            assert derivative.getpixel((0, 0))[3] == 0
            assert derivative.getpixel((derivative.width - 1, 0))[3] == 0
            assert derivative.getpixel((derivative.width // 2, derivative.height // 2))[3] == 255


def test_optional_watermark_renderer_is_nonfocusable_and_preserves_wheel_routing() -> None:
    """The retained renderer stays decorative if later used in a safe empty region."""
    watermark = _source("ui/widgets/workspace_watermark.py")

    assert "takefocus=0" in watermark
    assert 'self.bind("<MouseWheel>", self._wheel_callback, add="+")' in watermark
    assert "placement: tuple[float, float]" in watermark
    assert "_parent_background(parent)" in watermark


def test_calculation_pages_use_only_a_canvas_background_watermark() -> None:
    """The optional watermark stays below the content window and cannot obstruct controls."""
    host = _source("ui/widgets/scrollable_page_host.py")
    frame = _source("ui/widgets/scrollable_frame.py")
    watermark = _source("ui/widgets/workspace_watermark.py")

    assert "d243_watermark_logo_path" in host
    assert "host.set_background_watermark(d243_watermark_logo_path())" in host
    assert "CanvasBackgroundWatermark" in frame
    assert "canvas.create_image" in watermark
    assert "canvas.tag_lower(self._item)" in watermark
    canvas_section = watermark.split("class CanvasBackgroundWatermark", 1)[1].split("class WorkspaceWatermark", 1)[0]
    assert "OPACITY = 1.0" in canvas_section
    assert "self.place(" not in canvas_section
