"""Turkish display text for factory library records stored in English.

Seed records keep their stored (English) text so that existing databases, project
snapshots and source fingerprints stay untouched. Presentation code asks for a
display value instead: ``catalog_text(translate, stored_text)`` returns the
translation for the active language and falls back to the stored text when no
translation is registered (or the user edited the record).
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable

# Factory fluid identities whose stored ``name_tr`` is English (code -> (stored, Turkish)).
FLUID_DISPLAY_NAMES: dict[str, tuple[str, str]] = {
    "F76": ("NATO F-76 Naval Distillate", "NATO F-76 Deniz Distilatı"),
    "WATER": ("Fresh Water", "Tatlı Su"),
    "SEAWATER": ("Seawater", "Deniz Suyu"),
    "LUBE_OIL": ("Lubricating Oil", "Yağlama Yağı"),
    "CONTROL_AIR": ("Control Air", "Kontrol Havası"),
    "STARTING_AIR": ("Starting Air", "Marş Havası"),
}

# (stored English text, Turkish). Matching is exact; user-edited text is never touched.
PAIRS: tuple[tuple[str, str], ...] = (
    # Fluid names
    ("NATO F-76 Naval Distillate", "NATO F-76 Deniz Distilatı"),
    ("Fresh Water", "Tatlı Su"), ("Seawater", "Deniz Suyu"),
    ("Lubricating Oil", "Yağlama Yağı"), ("Control Air", "Kontrol Havası"), ("Starting Air", "Marş Havası"),
    # Surface profiles, materials and conditions
    ("Carbon Steel / New Commercial", "Karbon Çelik / Yeni Ticari"),
    ("Stainless Steel / New Clean", "Paslanmaz Çelik / Yeni Temiz"),
    ("Galvanized Steel / New", "Galvanizli Çelik / Yeni"),
    ("Cu-Ni 90/10 / New Drawn", "Cu-Ni 90/10 / Yeni Çekme"),
    ("Copper / Drawn", "Bakır / Çekme"), ("PVC / Smooth", "PVC / Pürüzsüz"),
    ("Cast Iron / New", "Dökme Demir / Yeni"), ("Carbon Steel / Corroded", "Karbon Çelik / Korozyona Uğramış"),
    ("Carbon Steel", "Karbon Çelik"), ("Stainless Steel", "Paslanmaz Çelik"),
    ("Galvanized Steel", "Galvanizli Çelik"), ("Copper", "Bakır"), ("Cast Iron", "Dökme Demir"),
    ("NEW_COMMERCIAL", "Yeni, ticari"), ("NEW_CLEAN", "Yeni, temiz"), ("NEW", "Yeni"),
    ("NEW_DRAWN", "Yeni, çekme"), ("DRAWN", "Çekme"), ("SMOOTH", "Pürüzsüz"), ("CORRODED", "Korozyona uğramış"),
    # Rule names
    ("D243 Fuel Velocity Criterion", "D243 Yakıt Hız Kriteri"),
    ("DIESEL FUEL / Suction", "Dizel Yakıt / Emme"), ("DIESEL FUEL / Delivery", "Dizel Yakıt / Basma"),
    ("HEAVY FUEL / Suction", "Ağır Yakıt / Emme"), ("HEAVY FUEL / Delivery", "Ağır Yakıt / Basma"),
    ("LUBE OIL / Suction", "Yağlama Yağı / Emme"), ("LUBE OIL / Delivery", "Yağlama Yağı / Basma"),
    ("FRESH WATER / Suction", "Tatlı Su / Emme"), ("FRESH WATER / Delivery", "Tatlı Su / Basma"),
    ("SEA WATER / Suction", "Deniz Suyu / Emme"), ("SEA WATER / Delivery", "Deniz Suyu / Basma"),
    ("CONTROL AIR", "Kontrol Havası"), ("STARTING AIR", "Marş Havası"),
    ("TL Fire Fighting Ships / Suction", "TL Yangın Söndürme Gemileri / Emme"),
    ("TL Fire Fighting Ships / Delivery", "TL Yangın Söndürme Gemileri / Basma"),
    ("TL Fire Fighting Ships / NPSH Margin", "TL Yangın Söndürme Gemileri / ENPY marjı"),
    ("TL <500 GT / Galvanized Steel", "TL <500 GT / Galvanizli Çelik"), ("TL <500 GT / Copper", "TL <500 GT / Bakır"),
    ("Ballast", "Balast"), ("Bilge", "Sintine"),
    ("90/10 Cu-Ni source-specific maximum", "90/10 Cu-Ni kaynağa özgü azami değer"),
    ("70/30 Cu-Ni source-specific maximum", "70/30 Cu-Ni kaynağa özgü azami değer"),
    ("Wärtsilä applicable profile", "Wärtsilä geçerli profil"),
    # Calculation-record notes shown in reports
    ("Existing Rp0.2 / B compatibility calculation; not a verified current TL rule.",
     "Mevcut Rp0,2 / B uyumluluk hesabı; doğrulanmış güncel bir TL kuralı değildir."),
    ("D243 V2 project fuel design maximum; not a TL rule.",
     "D243 V2 proje yakıt tasarım azami değeri; bir TL kuralı değildir."),
    ("Phase 0 S03 practical units; limited water straight-pipe scope; not a C-value source or compliance approval.",
     "Faz 0 S03 pratik birimler; sınırlı su düz boru kapsamı; C değeri kaynağı veya uygunluk onayı değildir."),
    ("Derived relation under explicit mixture basis; not a source for input defaults or compliance.",
     "Açık karışım esasına göre türetilmiş bağıntı; girdi varsayılanları veya uygunluk için kaynak değildir."),
    # Sources, documents and clauses
    ("US Department of Defense", "ABD Savunma Bakanlığı"),
    ("D243 user-approved engineering reference", "D243 kullanıcı onaylı mühendislik referansı"),
    ("Project Guide reference profile", "Proje kılavuzu referans profili"),
    ("Chapter 11 - Fire Fighting Ships", "Kısım 11 – Yangın Söndürme Gemileri"),
    ("User-approved ships less than 500 GT profile", "Kullanıcı onaylı 500 GT altı gemiler profili"),
    ("July 2019", "Temmuz 2019"), ("Section 1, C.5.3.3", "Bölüm 1, C.5.3.3"), ("Section 1, C.5.1", "Bölüm 1, C.5.1"),
    # Record notes
    ("User-approved specification range. Midpoint is a D243 derived default, not a source nominal.",
     "Kullanıcı onaylı şartname aralığı. Orta değer, D243’ten türetilmiş varsayılan değerdir; kaynak nominal değeri değildir."),
    ("Exact applicable property and reference temperature require source verification.",
     "Geçerli özellik ve referans sıcaklığı için kaynak doğrulaması gerekir."),
    ("Absolute roughness epsilon, not Darcy f. Exact surface condition applies; source edition not supplied.",
     "Mutlak pürüzlülük ε’dur, Darcy f değildir. Yüzey durumu tam olarak eşleşmelidir; kaynak baskısı sağlanmadı."),
    ("Internal criterion; not a classification HARD_LIMIT. Does not prevent calculation.",
     "Dahili kriter; klas kuruluşunun sert sınırı (HARD_LIMIT) değildir. Hesabı engellemez."),
    ("User-approved starting profile. Engine/project guide edition must be selected before claiming applicability. Other editions may differ.",
     "Kullanıcı onaylı başlangıç profili. Uygulanabilirlik iddia edilmeden önce motor/proje kılavuzu baskısı seçilmelidir. Diğer baskılar farklı olabilir."),
    ("Line length and pressure drop can require different design values. Exact edition/profile not supplied.",
     "Hat uzunluğu ve basınç düşümü farklı tasarım değerleri gerektirebilir. Kesin baskı/profil sağlanmadı."),
    ("Explicit Fire Fighting Ships applicability required; not universal to every vessel.",
     "Yangın Söndürme Gemileri kapsamı açıkça belirtilmelidir; her gemi için geçerli değildir."),
    ("Only explicit <500 GT scope. Exact document edition/clause requires confirmation; never universal TL.",
     "Yalnızca açıkça belirtilen <500 GT kapsamı. Kesin doküman baskısı/maddesi doğrulanmalıdır; genel bir TL kuralı değildir."),
    ("Exact applicable source/profile required; no invented numeric rule.",
     "Kesin geçerli kaynak/profil gerekir; sayısal kural uydurulmamıştır."),
    # Source registry applicability notes
    ("Published correlation tables, not measured batch properties. Stored subset: T=10/20/40°C, S=0 or 30/35/40 g/kg, P=0.101325 MPa. No interpolation. S=0 is pure-water approximation.",
     "Yayımlanmış korelasyon tabloları; ölçülmüş parti özellikleri değildir. Saklanan alt küme: T=10/20/40°C, S=0 veya 30/35/40 g/kg, P=0,101325 MPa. İnterpolasyon yapılmaz. S=0, saf su yaklaşımıdır."),
    ("P235TR2 / 1.0255 seamless non-alloy TR2 tubes; room-temperature properties, specified delivery condition. T>60 mm by agreement. Not allowable stress or roughness. TS national adoption/date not verified.",
     "P235TR2 / 1.0255 dikişsiz alaşımsız TR2 borular; oda sıcaklığı özellikleri, belirtilen teslim durumu. T>60 mm için anlaşmaya göre. İzin verilen gerilme veya pürüzlülük değildir. TS ulusal kabulü/tarihi doğrulanmadı."),
    ("F-76: density at 15°C; viscosity at 40°C. Midpoints are D243-derived, not source nominals.",
     "F-76: yoğunluk 15°C’de; viskozite 40°C’de. Orta değerler D243’ten türetilmiştir, kaynak nominal değerleri değildir."),
    ("JP-5/F-44: density at 15°C; viscosity maximum at -20°C. No viscosity default verified.",
     "JP-5/F-44: yoğunluk 15°C’de; viskozite azami değeri −20°C’de. Doğrulanmış varsayılan viskozite değeri yoktur."),
    ("Document identity/date only; normative grade/property tables not obtained.",
     "Yalnızca doküman kimliği/tarihi; normatif kalite/özellik tabloları elde edilemedi."),
    ("TL_FFS only. Retrieved PDF includes RCS 03/2021 and 02/2022; not a universal vessel rule.",
     "Yalnızca TL_FFS. Alınan PDF, RCS 03/2021 ve 02/2022 değişikliklerini içerir; her gemi için geçerli genel bir kural değildir."),
    ("Galvanised steel/copper seawater piping in this explicit scope. Original edition of generic D243 profile is unspecified.",
     "Bu açık kapsamdaki galvanizli çelik/bakır deniz suyu boruları. Genel D243 profilinin özgün baskısı belirtilmemiştir."),
    ("Engine-specific non-binding recommendations. Do not assign this variant/edition to generic profiles. Air ranges are delivery-side only.",
     "Motora özgü, bağlayıcı olmayan tavsiyeler. Bu varyant/baskı genel profillere atanmamalıdır. Hava aralıkları yalnızca basma tarafı içindir."),
    ("Bibliography verified via CEN-member preview; all 148 local dimensions not reverified against licensed tables. Not an allowable-stress standard.",
     "Kaynakça, CEN üyesi önizlemesi üzerinden doğrulandı; 148 yerel ölçünün tamamı lisanslı tablolara karşı yeniden doğrulanmadı. İzin verilen gerilme standardı değildir."),
    ("National adoption date; must not replace the EN publication date.",
     "Ulusal kabul tarihi; EN yayım tarihinin yerine kullanılmamalıdır."),
    ("Edition identified; full margin tables/applicability not obtained. ANSI approval 2024-07-29 is not established as publication date.",
     "Baskı belirlendi; tam marj tabloları/uygulanabilirlik elde edilemedi. ANSI onayı (2024-07-29) yayım tarihi olarak doğrulanmamıştır."),
    ("Hazen-Williams equation/unit package only. Does not authorize seawater applicability or a universal C value.",
     "Yalnızca Hazen-Williams denklemi/birim paketi. Deniz suyu için uygulanabilirliği veya genel geçer bir C değerini onaylamaz."),
    ("Water-distribution method context; not marine approval or verification of D243 loss coefficients.",
     "Su dağıtım yöntemi bağlamı; denizcilik onayı veya D243 kayıp katsayılarının doğrulaması değildir."),
    ("Conventional standard gravity; not a measured local acceleration.",
     "Geleneksel standart yerçekimi ivmesi; ölçülmüş yerel ivme değildir."),
    ("Adopted 2000-12-05; effective 2002-07-01. Historical instrument, not current consolidated compliance.",
     "Kabul: 2000-12-05; yürürlük: 2002-07-01. Tarihsel belgedir; güncel konsolide uygunluk değildir."),
    ("Edition listed; full consolidated normative text not reviewed.",
     "Baskı listelendi; tam konsolide normatif metin incelenmedi."),
    ("Product-specific volumetric concentration example; no D243 default or product recommendation.",
     "Ürüne özgü hacimsel konsantrasyon örneği; D243 varsayılanı veya ürün tavsiyesi değildir."),
    ("Product-specific application/concentration; revision date is not established as publication date.",
     "Ürüne özgü uygulama/konsantrasyon; revizyon tarihi yayım tarihi olarak doğrulanmamıştır."),
    ("Product-specific examples; no dated revision supplied.",
     "Ürüne özgü örnekler; tarihli revizyon sağlanmadı."),
    ("Date code retained verbatim; no unsupported date interpretation or Nozzle activation.",
     "Tarih kodu olduğu gibi korunmuştur; desteklenmeyen tarih yorumu veya Nozul etkinleştirmesi yoktur."),
    ("Full standard unavailable to this audit; no C-table verification from edition number.",
     "Standardın tamamı bu denetimde mevcut değildi; baskı numarasından C tablosu doğrulaması yapılmadı."),
    ("Committee draft is not an issued normative standard.",
     "Komite taslağı, yayımlanmış normatif bir standart değildir."),
    ("Thermodynamic framework identified. Does not verify stored seawater values, viscosity defaults or Hazen-Williams applicability.",
     "Termodinamik çerçeve belirlendi. Saklanan deniz suyu değerlerini, varsayılan viskoziteleri veya Hazen-Williams uygulanabilirliğini doğrulamaz."),
)

# Classification / code labels the library showed as raw keys or codes.
EXTRA_TR = {
    "catalog.classification.HEAVY_FUEL": "Ağır Yakıt",
    "catalog.classification.CONTROL_AIR": "Kontrol Havası",
    "catalog.classification.STARTING_AIR": "Marş Havası",
    "engineering.property.flow_velocity": "Akış hızı",
    "engineering.property.npsh_margin": "ENPY marjı",
}
EXTRA_EN = {
    "catalog.classification.HEAVY_FUEL": "Heavy Fuel",
    "catalog.classification.CONTROL_AIR": "Control Air",
    "catalog.classification.STARTING_AIR": "Starting Air",
    "engineering.property.flow_velocity": "Flow velocity",
    "engineering.property.npsh_margin": "NPSH margin",
}


_KNOWN = frozenset(en for en, _ in PAIRS)


def text_key(text: str) -> str:
    """Stable message key for one stored text."""
    return "catalogtext." + hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def turkish_messages() -> dict[str, str]:
    return {**{text_key(en): tr for en, tr in PAIRS}, **EXTRA_TR}


def english_messages() -> dict[str, str]:
    return {**{text_key(en): en for en, _ in PAIRS}, **EXTRA_EN}


def catalog_text(translate: Callable[[str], str] | None, text: object) -> object:
    """Display text for a stored factory string; anything unknown is returned unchanged."""
    if not isinstance(text, str) or not text or translate is None:
        return text
    if text not in _KNOWN:
        return text
    key = text_key(text)
    try:
        shown = translate(key)
    except KeyError:
        return text
    return text if shown == key else shown


def fluid_display_name(code: str | None, stored_name: str | None) -> str | None:
    """Turkish name for an unedited factory fluid; edited or unknown names are kept."""
    entry = FLUID_DISPLAY_NAMES.get(code or "")
    if entry is not None and stored_name == entry[0]:
        return entry[1]
    return stored_name
