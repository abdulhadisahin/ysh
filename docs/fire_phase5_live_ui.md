# D243 V2 — FIRE PHASE 5 — Live Workspace / Navigation / Application UI

Tarih: 2026-10-26. Dal `d243-v2-handoff`; başlangıç commit
`dc5f2059ec15ce140d9d60d4bfe4fbe0c2ed69ea`.
Yalnız `.venv314/Scripts/python.exe` (3.14.8), normal kullanıcı erişiminde
Tcl/Tk9.0.4 kullanıldı. Baseline **1773 passed, 0 failed**,102.03s.
Başlangıçta yalnız `docs/references/Yangın Söndürme.xlsx` izlenmiyordu:
**approved untracked reference input**. Workbook değiştirilmez/stage edilmez.

Bağlayıcı kontratlar: [analiz](fire_fighting_module_analysis.md),
[kaynak kararları](fire_fighting_source_decisions.md),
[Phase1](fire_phase1_domain_contracts.md), [Phase2](fire_phase2_foam_workflow.md),
[Phase3](fire_phase3_hazen_williams_workflow.md),
[Phase4](fire_phase4_snapshot_history_pdf.md). Domain/workflow hesapları değişmedi.

## Navigasyon ve yaşam döngüsü

Ana içerik üstünde **Mevcut Hesaplar / Yangın Söndürme** aile seçimi bulunur.
Mevcut dört sekme aynı ScrollablePageHost ve aynı page nesneleriyle korunur.
Fire ilk aile erişiminde lazy import edilir ve bir defa oluşturulur;
sonraki geçişler grid göster/gizle kullanır. Yeni üst düzey hesap sekmesi
çoğaltılmaz. Fire içinde **Köpük Sistemi / Hazen-Williams** iki alt sekmesi vardır;
ilk alt görünüm Foam'dır. Nozul placeholder veya aktif calculator eklenmedi.

Yeni namespace/modüller:

- `services/fire_workspace.py`: editable draft/controller, parsing ve workflow koordinasyonu;
- `ui/pages/fire_workspace_page.py`: gerçek ttk widget'ları, alt görünümler, action/state rendering;
- `ui/theme/fire_visuals.py`: yalnız Fire opt-in stil rolleri;
- `tests/test_fire_phase5_live_ui.py`: controller, gerçek Tk UI, state, report testleri.

MainWindow'a küçük aile ve state bağlantıları eklendi. Eski dört page dosyası,
formülleri, renkleri veya canlı layout'ları değiştirilmedi; shell'e aile satırı
eklendi. System Profile ayrı mühendislik bağlamı olarak kalır. Fire family açmak
context'i değiştirmez; Fire'a özel default system/fluid kaydı veya DB seed gerekmedi.

## Köpük canlı UI

A m², q L/(min·m²), t min ve Cfoam **%** boş alanlarla başlar. Karışım temeli
concentrate-volume/solution-volume olarak açıkça gösterilir. Kullanıcı yüzdesi
mevcut percent_to_fraction helper'ıyla normalize edilir; raw numeric yüzde
workflow evidence'inde saklanır. 3→.03 ve virgüllü6,00→.06 test edilmiştir.
q5/t30/%3 örnekleri başlangıç defaultu değildir. Auto-calculate yoktur.

Hesapla → typed FoamWorkflowInput → mevcut FoamCalculationService.
UI/controller A×q veya başka domain formülü uygulamaz. Sonuç kartında primary
Vfoam, destek Qsolution/Qfoam/Qwater görünür. Ham sonuçlar değiştirilmez;
görünür sayılar mevcut Formula View number formatter'ını kullanır.

Validation errors kullanıcıya çevrilmiş alan/mesaj ile döner; Python traceback
gösterilmez. Kaynak/Seçim Bilgisi disclosure'ında her parametrenin source status,
belge, opsiyonel önerilen değer ve değişiklik gerekçesi düzenlenebilir.
Öneri varsa input birimindedir (Cfoam için yüzde); recommendation normalize edilir.
Kullanılan değer öneriden farklıysa nonempty reason gerekir; öneri yoksa gerekçe
zorunlu değildir. Mevcut EngineeringValue policy/used/recommended modeli kullanılır.

Source classification çağıranın/kullanıcının açık beyanıdır; bağımsız bir source
audit motoru eklenmez. SourceReference verification USER_SUPPLIED kalır;
aritmetik veya dropdown seçimi bunu VERIFIED'a yükseltmez. Default manual girdiler
USER_PROJECT_ASSUMPTION; CHW SOURCE_REQUIRED olur. Workflow kaynak mesajları amber
şeritte gösterilir; compliance/uygunluk onayı üretilmez.

## HW canlı UI ve boru bağlantısı

Q L/min, Di mm, L m ve CHW açık girdidir; C defaultu yoktur. Servis UNKNOWN
başlar. Su açıkça seçilmelidir. Seawater/fuel/unknown servis veya bilinen uyumsuz
fluid context hesap çağrısından önce blocked olur. Context'te tanımsız/desteksiz
fluid code varsa suya sessiz fallback yoktur. Mevcut water-only applicability
ve HW domain/service kodu değişmez. CHW hiçbir k/ε alanına aktarılmaz.

Manual Di/Q editable; Bağlı Boru modunda ikisi readonly'dir çünkü Phase1 pipe
adapter uygulanmış Di ve Q'yu birlikte tüketir. Mevcut PipeSourceDiscovery
available selections yalnız okuma amaçlı kullanılır; ayrı katalog/DB sorgusu yok.
Boruyu Bağla açık apply, Güncelle aynı lineage'a explicit update, Mevcut Değeri
Koru eski applied değerleri tutar. Dropdown seçmek otomatik apply değildir.
Kaynak yoksa linked hesap validation hatasıdır; manual fallback yoktur.

Kaynak bildirimleri yalnız supplied applied/observed state'i karşılaştırır;
Di/Q değişmez. Stale/missing/different durumda link şeridi ve revizyon gösterilir,
canlı sonuç geçersiz kılınır. Güncelle/keep-current mevcut PipeInputState yöntemlerini
kullanır. Manual'a dönmek driving link'i ayırır. Explicit actual Di kullanılır;
OD−2t veya theoretical diameter hesaplanmaz. Linked Q'nun tam helper hassasiyeti
korunur. Unit-loss bar/m ve primary total-pressure-loss bar olarak sunulur.

## Canlı state, snapshot ve işlemler

FireWorkspace.results/snapshots yalnız son başarılı workflow'u tutar. Alan,
metadata, servis, mode, context veya observed linked durum değişince o hesap
geçersiz olur. Eski kart yerine yeniden hesaplama mesajı; Formula/PDF disabled.
Formula dialog açıksa kapanır. Reset girişleri/metadata/sonucu temizler;
workbook defaultu geri yüklemez ve History silmez.

Her başarılı hesap mevcut Phase4 build_fire_snapshot adaptörüne gider;
MainWindow mevcut SnapshotHistoryService.append yolunu kullanır. Projectless
session-only, project-owned append-only davranışı aynıdır. History yazma hatası
hesap sonucunu değiştirmez ve kullanıcıya storage hatası gösterilir.
Global History action korunur; ayrı Fire history store yoktur.

Formülü Göster mevcut FormulaReferencePanel'e hesaplanmış result.formula_steps
verir. PDF düğmesi saklanmış CalculationSnapshot'ı mevcut save_snapshot_pdf
yoluna gönderir; widget scraping veya tekrar hesaplama yoktur. PDF için ikinci
snapshot formatı üretilmez. Sonradan alan değiştirme geçmiş kaydı etkilemez.
Snapshot/History/PDF/FormulaStep şemaları ve asset/PNG mapping değişmedi.

Mevcut project JSON içinde **fire_workspace.version=1** namespace'i:
active subview, raw text fields, per-field status/document/recommended/reason,
service/mode ve frozen applied PipeInputState taşır. Sonuç/widget/history
nesneleri live form state'e konmaz. Load boş/legacy namespace'i boş draft'a
çevirir; desteklenmeyen sürümü reddeder. Lazily açılmayan saved Fire state
shell'de korunur. ProjectPersistenceService eski sayfa save'lerinde bu opt-in
namespace'i diğer namespace'ler gibi korur. DB schema/migration yoktur.

Tek PipeInputState için mevcut transfer codec'ine iki public wrapper eklendi:
pipe_input_to_dict/from_dict. Exact applied/observed state restore edilir,
decode sırasında refresh yapılmaz. Fire kendi downstream state'ini tutar;
discharge/suction state'inin anlamı değişmez.

## Yerelleştirme ve görsel sınırlar

Yeni chrome anahtarları TR/EN `fire.ui.*`; symbols/unitler universal.
Fire accent#C65D4B, dark#963E32, result surface#FFF2EE; beyaz kartlar, semantic
gruplar, disclosure ve primary result kullanılır. Mevcut tema veya watermark
kararı değişmedi. Fire kendi ScrollablePageHost'uyla scroll ownership alır;
uzun provenance ve sonuçlar scroll içinde kalır. Nozul görünmez ve blocked kalır.

## Testler ve doğrulama

35 yeni Phase5 testi:

- Empty/no-default, explicit percent/raw evidence ve 210/1660m² vakaları;
- invalid/finite/fraction sınırları, override recommendation/used/reason;
- HW C120/C140, SOURCE_REQUIRED C, water/seawater/fuel/unknown gate;
- context engelleri, missing link, actual Di/revision, stale/update/keep/manual;
- immutable live-created snapshot, real PDF text/frozen results;
- real Tk initial/calculation/result/actions/stale/reset/Formula dialog;
- subview localization, project state/namespace round-trip ve cache reuse;
- 1100×700,1280×800,1440×900,1700×1000 widget horizontal bounds/scrollregion;
- UI source'unda denklem sabitleri/Excel/PNG/workbook bağımlılığı bulunmaması.

Son tam regresyon: **1808 passed, 0 failed**,108.79s;1773 eski+35 yeni.
Mevcut Boru/Transfer/Basma/Emme, Library/History/Formula View/PDF regresyonları
aynı tam suite içindedir. Phase2/3/4 hesap kodları değişmedi.
Odaklı35 test17.18s; bu alt komutta nested pytest cache uyarısı vardı,
test hatası yoktu. Phase2–5 birleşik regresyon: **146 passed**,21.78s;
aynı nested cache yazma uyarısı vardı.

Gerçek main.py entry ile izole LOCALAPPDATA altında automated Windows smoke:
Foam210 ve1660, Formula View, iki live PDF action, HW C120/C140, linked pipe,
seawater block, gerçek History selection, Library, dört pencere boyutu,
Fire→mevcut dört modül→Fire üç tur, nesne cache, export/clear/load ve temiz
kapanış başarılı. Kullanıcının DB'leri değiştirilmedi; smoke verileri/artifact'lar
repository dışındaki görev çalışma alanındadır. İki4sayfalık PDF Poppler ile
render edilip sekiz sayfanın tamamı görsel incelendi; glyph/tablolar okunabilir.

Startup-to-mainloop ölçümü **5.17s**, önceki yaklaşık5–7s sınıfıyla uyumlu;
bu fazın before ölçümü ayrıca alınmadı. Fire constructor **0.345s**,
cached family switch **0.0065s**; ilk root.update boyama/yerleşim **2.35s**.
İlk etkileşimli boyama gecikmesi hedefin üzerindedir, performans notu olarak kalır;
startup'a eager Fire/PDF/Matplotlib/workbook işi eklenmedi.

**Manuel görsel kabul tamamlanamadı.** Computer Use Windows capture,
gizli ve görünür gerçek D243 pencerelerinde `FrameArrived timed out` /
`window capture timed out` verdi. Doğrulanan widget bounds/gerçek Tk smoke,
insan görsel incelemesi yerine geçmiş gösterilmez. Dört ekran boyutunda
otomatik field/action bounds PASS; tam görsel clipping/redraw değerlendirmesi açık.

## Kalan engeller ve sonraki adım

Manual Windows visual acceptance ve first-paint latency takibi gerekir.
Phase0 source blocker'ları (seawater HW, normative C source/context, nozzle
device/K mapping, güncel normatif metin erişimi ve proje/ürün foam kriterleri)
korunur. Nozzle/seawater etkinleştirilmedi; Library verisi veya regulatory
compliance eklenmedi. Referans workbook runtime bağımlılığı yoktur.

Önerilen sonraki adım: kullanıcı ortamında manuel Fire UI kabulü ve ölçülen
first-paint davranışının incelenmesi. Fire Library genişlemesi/nozul uygulaması
otomatik başlatılmaz. Sonuç: **PHASE5_PASS_WITH_BLOCKERS**.
