# D243 V2 — FIRE PHASE 4 — Snapshot / History / PDF Integration

Tarih 2026-10-21. Branch `d243-v2-handoff`, başlangıç
`a7936f16a89dd9b032ade843988bd95ebcf65394`.
Tek Python `.venv314/Scripts/python.exe`, 3.14.8.
Baseline **1755 passed, 0 failed**, 64.82 s; sandbox pytest cache yazma uyarısı.
Tek başlangıç istisnası `docs/references/Yangın Söndürme.xlsx`:
**approved untracked reference input**, değişmez/stage edilmez/commit edilmez.
SHA-256 `bd9aa871454c184afdb45e14bd0c008818d49701d5cc92e1de7ca89126159474`.

Yetkili kontratlar: [analiz](fire_fighting_module_analysis.md),
[kaynak kararları](fire_fighting_source_decisions.md),
[Phase1](fire_phase1_domain_contracts.md), [Foam workflow](fire_phase2_foam_workflow.md),
[HW workflow](fire_phase3_hazen_williams_workflow.md).
Formüller, source kararları ve su kapsamı bu fazda değiştirilmez.

## Snapshot mapping ve kayıt

Yeni API: `engineering.snapshots.fire.build_fire_snapshot(result, project_id=None)`.
FoamWorkflowResult ve HazenWilliamsWorkflowResult için iki typed adaptation
dalı vardır. NozzleRequest/başka nesne reddedilir. HW result WATER ve WATER_ONLY
olmalıdır; uygunsuz değiştirilmiş result başarı snapshot'ına çevrilmez.
Workflow payload calculation_validity=VALID ve hesap kimliği eşleşmesi istenir.

ModuleCode'a **FIRE_FOAM_SYSTEM=fire_foam_system** ve
**FIRE_HAZEN_WILLIAMS=fire_hazen_williams** tarihsel kimlikleri eklendi.
Canlı navigasyon MODULES tuple'ı aynı dört modül kalır. Nozul enum kaydı yoktur.
CalculationSnapshot **schema_version=1** aynen korunur; serializer allowlist,
SQL şeması, migration veya repository değişikliği yoktur.

| Snapshot alanı | Kaynak |
|---|---|
| module_code | Typed başarılı workflow türü |
| stage | workflow |
| model_version | Saklanan workflow_version |
| project_id | Çağıranın açık sahiplik argümanı |
| snapshot_id / created_at | Mevcut snapshot identity/UTC davranışı |
| facts.fire | Workflow'un detached canonical payload'ının bütünü |
| steps | Payload'daki hazır FormulaSteps; yeni builder çalışmaz |
| context | Hesap anında payload'a kaydedilmiş SystemContext |
| summary | Hazır numeric/unit/symbol/label-key summary |

Payload ham/gösterim ve normalized girdileri, unitleri, workflow/formula sürümünü,
rule ID'lerini, provenance, used/recommended/override reason, warning/readiness,
context, case/revision, applicability ve HW applied pipe durumunu aynen taşır.
Schema sürümü workflow sürümünden bağımsızdır. primitive/asdict hazırlığı önceki
workflow sınırında yapıldığı için Fire dataclass'larını global codec'e eklemek gerekmez.

Mevcut `to_payload/to_json/from_payload` yolu round-trip sağlar. Evidence her
erişimde detached JSON kopyasıdır; input/result yerine yeni nesne üretmek veya
dışarı alınan dict'i değiştirmek snapshot'ı değiştirmez. Canonical sayılar tam
hassasiyetli kalır; repr/object handle/callback yoktur.

Mevcut SnapshotHistoryService append-only ve CalculationRepository
`snapshot:<module>:<UUID>` JSON namespace yolu kullanılır. Proje sahipliği,
session-only projectless history, duplicate/legacy davranışı değişmez. Canlı
Fire form/project-state persistence eklenmedi.

## History ve historical Formula View

Kimlikler **Yangın — Köpük Sistemi**, **Yangın — Hazen-Williams**.
Mevcut loaded-record modül filtresi iki kaydı ayrı seçebilir; yeni sorgu yoktur.
Primary Foam **Vfoam / Gerekli Köpük Konsantresi Hacmi**; Qsolution/Qfoam/Qwater
summary'de kalır. Primary HW **ΔpHW / Toplam Basınç Kaybı [bar]**;
rHW,Q,Di,L,CHW destek değerleri korunur. Head loss etiketi kullanılmaz.

History mevcut read-only detay yapısını kullanır: summary, frozen context,
explicit Fire inputs, mixture/applicability/readiness/version, kaynak statüleri,
warnings, pipe mode/status/applied revision, override gerekçesi ve snapshot
metadata gösterilir. Eksik opsiyonel context/case/source/pipe kimliği güvenli
placeholder veya satır atlama ile ele alınır; None/null gösterilmez.

Fire tarihsel renkleri tek `ui/theme/fire_identity.py` dosyasındadır:
accent **#C65D4B**, dark **#963E32**, soft **#FFF2EE**. Mevcut dört sayfanın
MODULE_ACCENTS veya renkleri değişmez; History ayrı merged map kullanır.
Formula View historical identity map'i aynı tokenları kullanır. Canlı sayfa
IDENTITIES ve navigasyon kaydı genişletilmez.

History mevcut FormulaReferencePanel'i `historical=True`,
`separate_window=True`, `step_provider=lambda:snapshot.formula_steps` ile açar.
Foam'ın dört ve HW'nin iki hazır stable adımı decode edilir; bugünkü formül
builder'ı çağrılmaz. “Geçmiş Kayıt · Salt Okunur” yolu korunur. Yeniden hesapla,
Library update veya pipe refresh eylemi yoktur. History/Formula View tasarımı
değişmez; PNG/asset mapping değişikliği yoktur.

## Snapshot-only PDF

Mevcut `CalculationSnapshot → adapt_snapshot → EngineeringReport → render_pdf`
yolu kullanılır. `reporting/fire.py` yalnız saklanmış scalar alanları explicit
whitelist ile eşler. Renderer/A4 style/font/numara biçimi değişmedi; yeni PDF
motoru yoktur. Fire için mevcut text fallback kullanılır; PNG eklenmez.

Rapor, Yangın Söndürme sistem ailesini, Türkçe hesap adını, normalized inputları
ve unitlerini, mixture basis veya water-only service/applicability'yi, donmuş
FormulaSteps/substitution/resultları, sources/verification/override'ları,
source readiness/warnings, snapshot UUID, workflow version, rule IDs ve varsa
case/revision ile applied pipe metadata'yı gösterir. Foam dört sonucu, HW iki
basınç sonucu korur. Source status kodları audit amacıyla açık kalır; VERIFIED
durumu türetilmez. Kaynak metinleri veya kullanıcının gerekçesi çevrilerek
anlamı değiştirilmez; yeni chrome etiketleri TR/EN kataloglarındadır. Mevcut PDF
altyapısı Türkçe rapor üretir; yeni bağımsız EN PDF motoru eklenmez.

Generic raporun legacy faktör ziyareti Fire payload üzerinde çalıştırılmaz;
böylece case revision yanlışlıkla “Boru seçimi revizyonu” olarak etiketlenmez.
Live Library/project/PipeSelection sorgusu ve yeniden hesaplama yoktur.
Sonuç gösterimi mevcut format_number ile yapılır; Fire rounding kuralı yoktur.

## Testler ve smoke

Yeni `tests/test_fire_phase4_snapshot_history_pdf.py`: **18 test**.

- Foam1050/31.5/1018.5 L/min ve945L round-trip; override used.06,
  recommended.03, reason/source ve1890L PDF'de korunur.
- HW C120/C140 referansları2.3717829024660286/1.7832957445009588bar,
  rel1e-13; aynı frozen result Formula View/PDF'ye gider.
- Applied Di105/revision3/stale-kept state, dışarıda Di110/revision4'e update
  edilse de tarihi değiştirmez; source/observed revizyonlar payload'da kalır.
- SOURCE_REQUIRED ve diğer kayıtlı source durumları yükseltilmez.
- Mevcut SQLite persistence/load, History liste/filtre/selection,
  historical step_provider ve gerçek PDF üretimi headless çalışır.
- Calculator/service/formula builder, Library details, tüm context-service
  read/selection yöntemleri ve pipe observe/update spy'ları çağrılırsa test
  fail olur. Historical yol bunları çağırmaz. Detached context değişimi etkisizdir.
- Eksik opsiyonel metadata ve eski minimal snapshot güvenli kalır.
- Gerçek pypdf extraction Türkçe glyph/searchable text, frozen sayılar,
  UUID/version, A4 boyutu ve None/null/WORKFLOW chrome bulunmamasını doğrular.
- Nozzle historical identity yok; seawater HW adaptation reddedilir.
- Snapshot adaptation sırasında file/network I/O engelleme testi geçer.

Phase4+Phase2+Phase3 odaklı: **111 passed**. Mevcut snapshot/History/Formula
View/PDF odaklı regresyon: **99 passed**. Son tam regresyon:
**1773 passed, 0 failed**, **66.62 s**, uyarı yok;1755 mevcut ve18 yeni test.
Headless smoke gerçek persistence → load → History list/select → frozen
Formula View provider → gerçek PDF üretimini iki Fire türünde tamamladı.
Native Windows penceresi üzerinden etkileşimli smoke yapılmadı.

İki örnek PDF mevcut renderer ile üretildi: Foam override5sayfa, HW4sayfa.
Poppler ile dokuz sayfanın tamamı PNG'ye dönüştürülüp görsel incelendi:
tablo/sayfa sonları, glyph'ler, footer ve metinler okunabilir; taşma yok.
Örnekler çalışma çıktısı klasöründe, repository commit'i dışındadır.
Yerel ölçüm500 adaptation: yaklaşık **25.25 ms/kayıt**;1000 summary okuması
(JSON decode dahil) yaklaşık **0.53 ms/kayıt**. Bu tanısal ölçümdür;
workbook/network/query veya eager PDF generation adaptation yolunda yoktur.

## Donmuş sınırlar, engeller ve sonraki faz

Fire Phase2/3 hesap kodları/formülleri değişmez. Boru/Transfer/Basma/Emme,
Darcy, Library/seed, DB/migration, live project persistence, watermark ve canlı
Fire UI değişmez. Güncel Library önerisi eski kaydı etkileyemez.

Kalan source blocker'ları Phase0 ile aynıdır: seawater HW, C exact normative
edition/applicability/galvanized conflict, nozzle device/K mapping, güncel
normatif metin erişimi, proje/ürün foam kriterleri. Nozzle SOURCE_REQUIRED
ve seawater BLOCKED kalır; compliance iddiası yoktur.

Öneri: kullanıcı ayrıca başlatırsa Fire canlı UI/application entegrasyonu;
bu fazda hazır historical kontratları kullanmak ve live state persistence'i
ayrı versioned testlerle ele almak. UI otomatik başlatılmaz.
Genel sonuç **PHASE4_PASS_WITH_BLOCKERS**.
