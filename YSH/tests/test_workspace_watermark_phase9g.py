"""Canonical branding assets remain intact after workspace watermark removal."""

from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "resources"
MASTER_LOGO_SHA256 = "8e2f26c9967eb51554a404e2b7404d2076b897ca02024e06c3f5ed42d2a4c713"


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


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
