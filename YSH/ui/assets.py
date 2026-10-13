"""Local-only asset locations reserved for future approved YSH artwork."""

from __future__ import annotations

from pathlib import Path

from YSH.paths import ApplicationPaths


ASSET_DIRECTORY = Path(__file__).resolve().parent / "assets"
LOGO_SYMBOL_PATH = ASSET_DIRECTORY / "logo_symbol.png"
SIDEBAR_SHIP_PATH = ASSET_DIRECTORY / "sidebar_ship.png"
TAB_ICON_PATHS = {
    "pipe_design": ASSET_DIRECTORY / "tab_pipe.png",
    "transfer_pump": ASSET_DIRECTORY / "tab_transfer.png",
    "discharge_head_loss": ASSET_DIRECTORY / "tab_discharge.png",
    "suction_npsh": ASSET_DIRECTORY / "tab_suction.png",
}
BRANDING_RESOURCE_DIRECTORY = "resources"
YSH_LOGO_FILENAME = "ysh_logo.png"
D243_LOGO_FILENAME = "d243_logo.png"
D243_UI_LOGO_FILENAME = "d243_logo_ui.png"
D243_WATERMARK_LOGO_FILENAME = "d243_logo_watermark.png"
D243_ICON_FILENAME = "d243_logo.ico"
D243_LOGO_MAIN = "branding/d243_logo_main.png"
D243_LOGO_MEDIUM = "branding/d243_logo_medium.png"
D243_LOGO_SMALL = "branding/d243_logo_small.png"
D243_LOGO_WATERMARK = "branding/d243_logo_watermark.png"
D243_LOGO_ICO = "branding/d243_logo.ico"
BTN_YENI = "btn_yeni.png"
BTN_AC = "btn_ac.png"
BTN_KAYDET = "btn_kaydet.png"
BTN_FARKLI_KAYDET = "btn_farkli_kaydet.png"
BTN_SIL = "btn_sil.png"
BTN_YENILE = "btn_yenile.png"
BTN_HESAPLA = "btn_hesapla.png"
BTN_TEMIZLE = "btn_temizle.png"
BTN_EKLE = "btn_ekle.png"
BTN_DUZENLE = "btn_duzenle.png"
BTN_HAKKINDA = "btn_hakkinda.png"
BTN_FORMULU_GOSTER = "btn_formulu_goster.png"
BTN_PROJE = "btn_proje.png"
BTN_KUTUPHANE = "btn_kutuphane.png"
BTN_GRAFIK = "btn_grafik.png"
BTN_UYARI = "btn_uyari.png"
STATUS_HAZIR = "status_hazir.png"
STATUS_BILGI = "status_bilgi.png"
STATUS_UYARI = "status_uyari.png"
STATUS_KRITIK = "status_kritik.png"
STATUS_HATA = "status_hata.png"
STATUS_BASARILI = "status_basarili.png"
STATUS_KAYDEDILDI = "status_kaydedildi.png"
STATUS_ISLEMDE = "status_islemde.png"

EMPTY_STATE_FILENAMES = {
    "project": "proje_yok_denizcilik_blueprinti.png.png",
    "result": "denizcilik_temali_sonuc_bulunamadi.png.png",
    "reference": "denizcilik_referans_verisi_yok.png.png",
    # No dedicated approved image exists for local-loss or library emptiness.
    # ``EmptyState`` keeps its Turkish native-text presentation in those
    # contexts instead of showing an unrelated workspace illustration.
    "local_loss": None,
    "formula": "denizcilik_formulleri_bos_durumu.png.png",
    "library": None,
    "chart": "grafik_henuz_olusmadi.png.png",
    "workspace": "denizcilik_muhendisligi_hesaplama_alani.png.png",
}
YSH_ICON_FILENAME = "ysh.ico"
YSH_SHIP_TOP_RIGHT_FILENAME = "ysh_ship_top_right.png"
YSH_SHIP_BOTTOM_LEFT_FILENAME = "ysh_ship_bottom_left.png"

ACTION_ICON_FILENAMES = {
    "new": BTN_YENI,
    "open": BTN_AC,
    "save": BTN_KAYDET,
    "save_as": BTN_FARKLI_KAYDET,
    "delete": BTN_SIL,
    "refresh": BTN_YENILE,
    "calculate": BTN_HESAPLA,
    "clear": BTN_TEMIZLE,
    "add": BTN_EKLE,
    "edit": BTN_DUZENLE,
    "about": BTN_HAKKINDA,
    "formula": BTN_FORMULU_GOSTER,
    "project": BTN_PROJE,
    "library": BTN_KUTUPHANE,
    "chart": BTN_GRAFIK,
    "warning": BTN_UYARI,
}

# Distinct approved action masters used by the four library categories.
LIBRARY_CATEGORY_ICON_FILENAMES = {
    "library_materials": "malzemeler.png",
    "library_pipe_sizes": "boru_olculeri.png",
    "library_engineering_constants": "muhendislik_sabitleri.png",
    "library_corrosion_circuits": "devre_korozyon_artimi.png",
    "library_corrosion_circuit": "devre_korozyon_artimi.png",
}

STATUS_ICON_FILENAMES = {
    "ready": STATUS_HAZIR,
    "information": STATUS_BILGI,
    "warning": STATUS_UYARI,
    "critical": STATUS_KRITIK,
    "error": STATUS_HATA,
    "success": STATUS_BASARILI,
    "saved": STATUS_KAYDEDILDI,
    "working": STATUS_ISLEMDE,
}

# Formula artwork is a presentation-only representation of stable equations.
# Calculation pages still own their formula strings, substitutions, and live
# results; this manifest only maps supplied packaged art to those equations.
FORMULA_ASSET_FILENAMES = {
    "pipe_diameter": "formula_boru_capi.png.png",
    "allowable_stress": "formula_musaade_edilebilir_gerilme.png.png",
    "base_wall_thickness": "formula_temel_et_kalinligi.png.png",
    "bend_allowance": "formula_bukum_ilavesi.png.png",
    "required_wall_thickness": "formula_toplam_et_kalinligi.png.png",
    "local_loss": "formula_lokal_kayip.png.png",
    "pipe_friction_loss": "formula_boru_surtunme_kaybi.png.png",
    "available_enpy": "formula_enpy.png.png",
}

# Rendering policy belongs to the asset family, never to an individual page.
# Action masters contain an intentional navy/gold tile, frame, and soft edge;
# their complete composition is therefore meaningful.  Status marks are
# standalone transparent symbols, so they use a dedicated fit that preserves
# the full silhouette and adds an in-memory transparent safety border.
ACTION_ICON_FIT_MODE = "full_asset_safe"
LIBRARY_CATEGORY_ICON_FIT_MODE = "full_asset_safe"
STATUS_ICON_FIT_MODE = "silhouette_safe"


def local_asset_path(path: Path) -> Path | None:
    """Return an existing packaged-local asset, never downloading a resource."""
    return path if path.is_file() else None


def branding_asset_path(
    filename: str,
    resource_root: Path | None = None,
) -> Path | None:
    """Return an approved branding asset from source or frozen resources."""
    root = resource_root or ApplicationPaths().resource_root
    return local_asset_path(root / BRANDING_RESOURCE_DIRECTORY / filename)


def production_branding_path(filename: str, resource_root: Path | None = None) -> Path | None:
    """Resolve one approved production branding asset from its manifest path."""
    return branding_asset_path(filename, resource_root)


def d243_main_logo_path(resource_root: Path | None = None) -> Path | None:
    """Return the approved prominent shell emblem."""
    return production_branding_path(D243_LOGO_MAIN, resource_root)


def d243_medium_logo_path(resource_root: Path | None = None) -> Path | None:
    """Return the approved medium information-card emblem."""
    return production_branding_path(D243_LOGO_MEDIUM, resource_root)


def d243_small_logo_path(resource_root: Path | None = None) -> Path | None:
    """Return the approved compact-dialog emblem."""
    return production_branding_path(D243_LOGO_SMALL, resource_root)


def d243_production_icon_path(resource_root: Path | None = None) -> Path | None:
    """Return the approved multi-resolution production Windows icon."""
    return production_branding_path(D243_LOGO_ICO, resource_root)


def ysh_logo_path(resource_root: Path | None = None) -> Path | None:
    """Return the approved YSH header-logo path when available."""
    return branding_asset_path(YSH_LOGO_FILENAME, resource_root)


def d243_logo_path(resource_root: Path | None = None) -> Path | None:
    """Return the locked D243 emblem when the product owner supplies it."""
    return branding_asset_path(D243_LOGO_FILENAME, resource_root)


def d243_ui_logo_path(resource_root: Path | None = None) -> Path | None:
    """Return the transparent technical derivative used by the shell lockup."""
    return branding_asset_path(D243_UI_LOGO_FILENAME, resource_root)


def d243_watermark_logo_path(resource_root: Path | None = None) -> Path | None:
    """Return the transparent technical derivative used by workspace watermarks."""
    return production_branding_path(D243_LOGO_WATERMARK, resource_root)


def action_icon_path(name: str, resource_root: Path | None = None) -> Path | None:
    """Resolve one optional action icon without coupling a command to artwork."""
    action_filename = ACTION_ICON_FILENAMES.get(name)
    if action_filename:
        return branding_asset_path(f"icons/actions/{action_filename}", resource_root)
    category_filename = LIBRARY_CATEGORY_ICON_FILENAMES.get(name)
    if category_filename:
        return branding_asset_path(f"icons/library/{category_filename}", resource_root)
    return None


def action_icon_fit_mode(name: str) -> str:
    """Return the safe renderer policy for a production action asset."""
    if name in LIBRARY_CATEGORY_ICON_FILENAMES:
        return LIBRARY_CATEGORY_ICON_FIT_MODE
    return ACTION_ICON_FIT_MODE


def status_icon_path(name: str, resource_root: Path | None = None) -> Path | None:
    """Resolve one optional presentation-only status icon."""
    filename = STATUS_ICON_FILENAMES.get(name)
    return branding_asset_path(f"icons/status/{filename}", resource_root) if filename else None


def status_icon_fit_mode(_name: str) -> str:
    """Return the safe renderer policy for standalone status glyphs."""
    return STATUS_ICON_FIT_MODE


def formula_asset_path(name: str, resource_root: Path | None = None) -> Path | None:
    """Resolve an approved static equation image for Formula-card presentation."""
    filename = FORMULA_ASSET_FILENAMES.get(name)
    return branding_asset_path(f"formulas/{filename}", resource_root) if filename else None


def empty_state_path(name: str, resource_root: Path | None = None) -> Path | None:
    """Resolve a contextual empty-state illustration without coupling UI to filenames."""
    filename = EMPTY_STATE_FILENAMES.get(name)
    return branding_asset_path(f"empty_states/{filename}", resource_root) if filename else None


def d243_icon_path(resource_root: Path | None = None) -> Path | None:
    """Return the approved multi-resolution D243 Windows icon when packaged."""
    return d243_production_icon_path(resource_root)


def ysh_icon_path(resource_root: Path | None = None) -> Path | None:
    """Return the approved YSH Windows icon path when available."""
    return branding_asset_path(YSH_ICON_FILENAME, resource_root)


def ysh_ship_top_right_path(resource_root: Path | None = None) -> Path | None:
    """Return the optional approved upper-shell marine artwork path."""
    return branding_asset_path(YSH_SHIP_TOP_RIGHT_FILENAME, resource_root)


def ysh_ship_bottom_left_path(resource_root: Path | None = None) -> Path | None:
    """Return the optional approved sidebar marine artwork path."""
    return branding_asset_path(YSH_SHIP_BOTTOM_LEFT_FILENAME, resource_root)
