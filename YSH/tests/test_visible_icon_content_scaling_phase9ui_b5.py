"""Contracts for runtime visible-content icon scaling without source edits."""

from PIL import Image, ImageDraw

from ui.assets import action_icon_fit_mode, status_icon_fit_mode
from ui.widgets.asset_loader import AssetImageLoader


def test_visible_content_crop_ignores_large_transparent_canvas_padding() -> None:
    image = Image.new("RGBA", (100, 80), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((35, 25, 64, 54), fill=(255, 255, 255, 255))
    cropped = AssetImageLoader._visible_content(image, alpha_threshold=8, padding_percent=5)
    assert cropped.size[0] < image.size[0]
    assert cropped.size[1] < image.size[1]
    assert cropped.getchannel("A").getbbox() is not None


def test_visible_content_safety_padding_keeps_opaque_edges_unclipped() -> None:
    image = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((10, 10, 29, 29), fill=(255, 255, 255, 255))
    cropped = AssetImageLoader._visible_content(image, alpha_threshold=8, padding_percent=5)
    assert cropped.size[0] > 20
    assert cropped.size[1] > 20


def test_empty_or_non_alpha_like_content_falls_back_without_failure() -> None:
    transparent = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
    assert AssetImageLoader._visible_content(transparent, 8, 5).size == (24, 24)


def test_shared_consumers_follow_the_central_asset_class_policy() -> None:
    rounded = ("YSH/ui/widgets/rounded_button.py")
    components = "YSH/ui/widgets/engineering_components.py"
    formula = "YSH/ui/widgets/formula_view.py"
    assert "fit_mode=action_icon_fit_mode(self._icon_name)" in open(rounded, encoding="utf-8").read()
    assert "fit_mode=status_icon_fit_mode(state)" in open(components, encoding="utf-8").read()
    assert "fit_mode=status_icon_fit_mode(self._marker_state(section.role))" in open(formula, encoding="utf-8").read()


def test_glyph_content_excludes_the_outer_framed_action_card() -> None:
    image = Image.new("RGBA", (100, 120), (0, 0, 0, 0))
    ImageDraw.Draw(image).rounded_rectangle((10, 10, 90, 95), radius=8, fill=(1, 30, 70, 255))
    ImageDraw.Draw(image).ellipse((40, 38, 60, 58), fill=(255, 210, 30, 255))
    glyph = AssetImageLoader._glyph_content(image, alpha_threshold=8, padding_percent=5)
    assert glyph.size[0] < image.size[0]
    assert glyph.size[1] < image.size[1]


def test_full_asset_safe_retains_the_complete_framed_composition_with_margin() -> None:
    image = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
    drawing = ImageDraw.Draw(image)
    drawing.rectangle((18, 16, 101, 99), outline=(214, 178, 80, 255), width=2)
    drawing.rectangle((20, 18, 99, 97), fill=(16, 43, 70, 255))
    drawing.ellipse((47, 43, 73, 69), fill=(255, 211, 90, 255))
    drawing.rectangle((14, 12, 105, 103), outline=(255, 215, 120, 12), width=1)

    safe = AssetImageLoader._full_asset_safe(image)

    # The decorative frame and low-alpha glow remain, plus safe breathing room.
    assert safe.size[0] > 92
    assert safe.size[1] > 92
    left, top, right, bottom = safe.getchannel("A").getbbox()
    assert left > 0 and top > 0
    assert right < safe.width and bottom < safe.height


def test_silhouette_safe_preserves_edge_to_edge_status_art_with_transparent_padding() -> None:
    image = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    ImageDraw.Draw(image).polygon(((20, 0), (40, 39), (0, 39)), fill=(255, 210, 0, 255))

    safe = AssetImageLoader._silhouette_safe(image)

    left, top, right, bottom = safe.getchannel("A").getbbox()
    assert safe.size[0] > image.size[0]
    assert safe.size[1] > image.size[1]
    assert left > 0 and top > 0
    assert right < safe.width and bottom < safe.height


def test_asset_families_use_safe_modes_without_page_specific_guesses() -> None:
    assert action_icon_fit_mode("calculate") == "full_asset_safe"
    assert action_icon_fit_mode("library_materials") == "full_asset_safe"
    assert action_icon_fit_mode("formula") == "full_asset_safe"
    assert status_icon_fit_mode("warning") == "silhouette_safe"


def test_optional_empty_contexts_fall_back_to_native_text_not_wrong_artwork() -> None:
    from ui.assets import empty_state_path

    assert empty_state_path("result") is not None
    assert empty_state_path("project") is not None
    assert empty_state_path("reference") is not None
    assert empty_state_path("formula") is not None
    assert empty_state_path("local_loss") is None
    assert empty_state_path("library") is None


def test_loader_source_declares_separate_safe_fit_mode_and_cache_key() -> None:
    source = open("YSH/ui/widgets/asset_loader.py", encoding="utf-8").read()
    assert '"glyph_content"' in source
    assert '"full_asset_safe"' in source
    assert '"silhouette_safe"' in source
    assert "alpha_composite(silhouette" in source
    assert "fit_mode, alpha_threshold, padding_percent, cls._dpi_scale(master)" in source
