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

## PHASE 5A — Visual Acceptance & First-Paint Review

Tarih2026-10-26. Başlangıç `1b52ff9d0a30bb5c68b6238c9a7fe4ca4e29216a`.
Baseline **1808 passed, 0 failed**,106.17s. Tek Python3.14.8/Tcl-Tk9.0.4.
Workbook önceki SHA-256 ile aynı ve approved untracked reference input kalır.

### Gerçek Windows görsel kabul sınırı

Gerçek main.py ayrı LOCALAPPDATA ve görünür pencere ile açıldı. Computer Use
oturumu sıfırlanıp returned window yeniden seçildi/activate edildi. İki ekran
yakalama denemesi yine `FrameArrived timed out: timed out waiting on channel`
ve `window capture timed out: timed out waiting on channel` verdi.
Bu nedenle Foam/HW/TR/EN, dört pencere boyutu, navigation/style/contrast/DPI
görsel kabulü **DOĞRULANAMADI**. MANUAL_VISUAL_PASS verilmez. Kullanıcıdan
gerçek görsel bulgular istendi; yanıt gelmeden görsel onay varsayılmaz.
Görsel bulgu olmadan padding/radius/color veya mevcut modüller değiştirilmedi.

### Ölçüm yöntemi ve kanıt

Enstrümantasyon yalnız repository dışındaki geliştirme harness'indedir;
production timing/logging/update çağrısı eklenmedi. Aynı normal Windows/Tk
ortamında cProfile ve perf_counter kullanıldı. Navigation çağrısı, constructor,
alt görünüm, ilk update_idletasks ve sonra update ayrı ölçüldü. Bu senkron
Tk event-drain süreleri, ekranda görülen ilk piksel zamanıyla aynı kabul edilmez.
Native Tcl/Tk çağrısı içindeki OS boyama/bekleme ayrımını Python profiler çözmez.

| Adım | Önce | Sonra | İkinci sonra ölçümü |
|---|---:|---:|---:|
| Navigation/Fire constructor | .206312s | .139298s | .140867s |
| Foam constructor | .086125s | .102779s | .102169s |
| HW constructor, ilk Foam açılışında | .083713s | oluşturulmadı | oluşturulmadı |
| update_idletasks / idle yerleşim | 1.754093s | 1.773141s | 1.771656s |
| Sonraki update/event döngüsü | 1.079150s | 1.035797s | 1.169763s |
| İlk açılış toplamı | 3.039555s | 2.948236s | 3.082286s |
| Cached family dönüşü | .003945s | .003914s | .005198s |
| Scroll host init (2 hafif host) | .007728s | .009697s | .013701s |
| Scroll configure toplamı | .022341s/7 | .011032s/4 | .013086s/4 |
| Canvas genişlik sync | .000240s | .000270s | .000233s |
| Fire style init | .001582s | .000819s | .001002s |
| Localization setup | .054996s/6 | .017358s/2 | .017936s/2 |
| Translation lookups | .002527s/302 | .000831s/90 | .000776s/90 |
| Formula shell construction | .004729s/2 | .003542s/1 | .002946s/1 |
| Font object construction | .000531s/5 | .000585s/5 | .000501s/5 |
| Controller/state hydration | ölçülmedi | ölçülmedi | .000233s/1 |
| ttk widget construction count |151|77|77|

İlk açılış aralığında PhotoImage construction0; Fire path'inde resim/asset
ön yüklemesi veya workbook/History/PDF üretimi yoktur. Formula shell yalnız
toggle/provider taşır; formula render/Matplotlib/PDF üretimi açılışta çalışmaz.
Scroll tree recursion'ın inclusive süreleri iç içe toplandığı için tabloda
parent scroll-configure toplamı kullanıldı. Geometri callback'leri ölçümde
onlarca milisaniyedir; saniyelik Python Configure döngüsü saptanmadı.

Profilin çoğu `_tkinter.tkapp.call` native sınırındadır (önce cumulative2.990s,
sonra2.923s). Bu, gecikmenin native Tk idle/update yolunda kaldığını gösterir;
tek başına belirli bir Windows scheduling/driver hatasını kanıtlamaz.
Safe software fix ile çok saniyelik gecikmenin çözüldüğü iddia edilmez.

### Hedefli düzeltme

İki alt görünümün eager creation'ı kaldırıldı. Fire shell iki hafif viewport
slot'u oluşturur; yalnız model.active alt görünümü gerçek widget'lara dönüşür.
İlk diğer sekme seçimi bir defa oluşturur; sonraki dönüşler cached nesneyi kullanır.
Language refresh/observe/export açılmamış alt görünümü oluşturmaz. Kaydedilmiş
active HW ile doğrudan HW açılışı desteklenir. Pasif işlemler yalnız created
view'ları yeniler; public keyed lookup gerektiğinde oluşturur. Constructor'daki
yinelenen localization refresh kaldırıldı. Paylaşılan scroll host, tema, mevcut
modüller, mühendislik/controller/state/snapshot anlamları değiştirilmedi.

Sonuç: Python/widget işi belirgin azalır; constructor yaklaşık üçte bir kısalır.
Native idle/update değişimi ölçüm varyansı içindedir. İlk açılış hâlâ yaklaşık3s;
2.35s historical paint notunun kapandığı söylenemez. Daha geniş shared-scroll
rewrite veya after/update workaround'ı için ölçüm dayanağı yoktur.

### Startup, scaling ve regresyon

Phase5 source-startup5.17s idi. Bu fazda gerçek main.py source-entry→mainloop
ölçümü **5.69s**; aynı5–7s sınıfında, yapısal startup regresyonu görülmedi.
Profiler'ın app.run→mainloop ayrı saati before4.463s/after4.112s/3.889s'dir;
bu saat app construction/import süresini kapsamaz, source-startup ile karıştırılmaz.
Gözlenen Tk scaling **1.334647**, winfo_fpixels(1i) **96.09DPI**.
Başka Windows scaling ayarı değiştirilmedi veya doğrulanmış gösterilmedi.

5 yeni lifecycle testi: yalnız ilk view, passive refresh, cached selection,
uncreated view state/dil korunması, saved-HW-first, stale Formula/PDF semantiği.
Mevcut Phase5 testi35 ile odaklı **40 passed**,16.51s; nested cache yazma
uyarısı vardı. Tam regresyon **1813 passed, 0 failed**,109.60s; uyarı yok.
Eski sayısal/historical testler bu tam suite kapsamındadır; elle görsel PASS
bu testlerden türetilmez. Hiçbir görsel spacing/color correction yapılmadı.

**Final acceptance: MANUAL_VISUAL_BLOCKED. Overall: PHASE5A_BLOCKED.**
Kalan işler: capture ortamı veya kullanıcı tarafından gerçek görsel inceleme;
native Tk event-drain gecikmesinin daha alt seviyede incelenmesi. Sonraki adım
bu kabulün tamamlanmasıdır. Fire Library/nozzle/seawater geliştirmesi başlatılmaz.

## PHASE 5B — Foam Concentration Percent Input Clarification

Tarih2026-10-26. Başlangıç `bf31d46366c3587dd59e841a86f510b7e6afb824`.
Baseline **1813 passed, 0 failed**,82.48s. Python yalnız `.venv314/Scripts/python.exe`
(3.14.8). Başlangıçta yalnız approved untracked reference input workbook vardı.

### Tek giriş konvansiyonu

Workbook temsilindeki **.03 fraction**, canlı UI'da **3 percent** ile aynıdır.
İç kontrat **0<foam_fraction<1** kalır. Görünür alan her zaman yüzde bekler;
3→.03,3,00→.03,6→.06,0,03→.0003. Sessiz çift yorum, değer değiştirme,
heuristic, yeni parser veya mühendislik defaultu yoktur. Kullanıcı0,03 girerse
bu0.03% olur; yazılım niyetini3% olarak tahmin etmez.

Alan yanındaki `%` birimi korundu. Doğrudan altında TR yardım:
**Yüzde olarak giriniz. Örnek: %3 için 3 yazın.**
EN: **Enter as percent. Example: enter 3 for 3%.**
Placeholder için native Entry'ye yapay metin yazılmadı; gerçek değer boş başlar.
Konsantrasyon provenance'ındaki öneri etiketi de **Önerilen (%) / Recommended (%)**
oldu. Kullanılan değer ana inputta, yüzde birimiyle görünür; öneri fraksiyonmuş
gibi yanlış etiketlenmez. Recommendation yokken gerekçe zorunluluğu eklenmedi.

### Engellemeyen açıklama uyarısı

Yalnız **0<visible_percent<1** koşulunda amber sunum uyarısı:
**Girilen değer %1'in altında. Bu alan yüzde bekler; %3 için 3 giriniz.**
EN: **The entered value is below 1%. This field expects a percentage; enter 3
for 3%.**

`ui/fire_input_presentation.py` küçük immutable InputClarification kaydı üretir;
category **UI_INPUT_CLARIFICATION**. Mevcut parse_engineering_float kullanılır.
Bu kayıt mühendislik ValidationError, SOURCE_REQUIRED veya mevzuat bulgusu
değildir. Hesabı/PDF'yi engellemez, değeri değiştirmez, workflow warnings veya
snapshot source statüsüne karışmaz. Boş/invalid input mevcut doğrulamaya bırakılır.
1 ve üzerindeki yüzdelerde bu uyarı kalkar. %1 altı ürün girdileri geçerli kalır.

### Snapshot, Formula View, History ve PDF

Snapshot şeması/verisi değişmedi: raw_inputs.foam_fraction `{value:3,unit:'%'}`,
normalized_inputs.foam_fraction `.03`; EngineeringValue.used_value `.03`,unit1.
History saklanan normalize inputtan yalnız görüntü kopyasını yüzdeye çevirir:
**Köpük Konsantrasyonu:3,00 %**. Cfoam override satırları önerilen3,00% /
kullanılan6,00% gösterir; gerçek `.03/.06` ve gerekçe snapshot'ta kalır.
Eski snapshot JSON'ları yeniden yazılmaz, current Library/proje verisi okunmaz.

Fire PDF adapter'ında yalnız input/selections Cfoam numeric unit1 satırları
mevcut fraction_to_percent helper'ıyla yüzde görünümüne çevrilir. Öneri/kullanılan
değer için de aynı display-only kural uygulanır. Report hesap sonuçları değişmez.
Formula View ve PDF equation adımları mevcut kanonik FormulaStep'leri aynen
tutar: **Cfoam=.03 [1]**. Yüzde label'ıyla `.03%` gösterilmez; canonical0.03
ve percent3 sunumu birbirinden ayrıdır. Formula View/History/PDF mimarisi veya
renderer tasarımı değiştirilmedi. HW/PipeSelection/nozzle/seawater/DB/Library yok.

### Regresyon ve kabul

| A/q/t | Görünür konsantrasyon | İç fraksiyon | Sonuç / davranış |
|---|---|---|---|
|210/5/30|3 veya3,00|.03|1050/31.5/1018.5 L/min;945L; low-percent uyarısı yok|
|210/5/30|6|.06|1890L; önerilen3%,used6%,gerekçe korunur|
|210/5/30|0,03|.0003|9.45L; yalnız giriş konvansiyonu uyarısı|
|210/5/30|0.5|.005|Geçerli hesap + giriş konvansiyonu uyarısı|
|210/5/30|1|.01|Geçerli; low-percent uyarısı yok|
|210/5/30|0/100/120/negatif|—|Mevcut validation hatası|

19 yeni test conversion/threshold/classification, gerçek Tk yardım/adjacent%,
nonblocking düşük yüzde hesabı, invalid boundary, TR/EN, narrow viewport help/
warning sırası, canonical FormulaSteps, detached snapshot, History/override ve
gerçek pypdf metnini doğrular. Önceki Phase4 PDF presentation testinin beklediği
fraksiyon gösterimi3%/6%'ye güncellendi; numeric/workbook regression assert'leri
değişmedi. Phase5B odaklı **19 passed**,5.33s; nested cache yazma uyarısı vardı.
İlk geniş odaklı paket76 test geçti; son eklenen layout testiyle toplam19 yeni
test vardır. Tam regresyon: **1832 passed, 0 failed**,91.72s; uyarı yok.

İki örnek PDF (3% reference ve3%→6% override), mevcut renderer ile üretildi;
4+5sayfanın tamamı Poppler PNG'lerinden görsel incelendi. Yüzde değerleri/birimleri,
canonical formula değerleri, gerekçe ve sonuçlar okunabilir; rapor layout'u korunur.

Gerçek main.py izole verilerle görünür açıldı. Windows Computer Use screenshot
iki denemede `FrameArrived timed out` / `window capture timed out` verdi.
Güncel yerleşik CUA app binding/accessibility tree çalıştı, screenshot yine
`window capture timed out` verdi. Bu nedenle manuel alan girişi/görsel crowding
kabulü doğrulanmış gösterilmez. Gerçek Tk otomatik testlerinde0,03% uyarısı,
9.45L sonucu, PDF enabled, TR/EN metin ve1100×700 bounds/overlap kontrolü PASS.

Foam domain/workflow formülleri ve iç fraction kontratı, q/t/c defaultları,
workbook, HW, nozul/deniz suyu engelleri ve DB/Library değişmedi. Workbook hash'i
`bd9aa871454c184afdb45e14bd0c008818d49701d5cc92e1de7ca89126159474` olarak kalır;
approved untracked reference input, commit dışı.
Sonuç **PHASE5B_PASS_WITH_MINOR_ISSUES**: istenen düzeltme ve regresyonlar geçti;
manuel Windows görsel kontrolü erişim hatası nedeniyle açık. Sonraki adım bu
dar görsel kontrolün tamamlanmasıdır; başka Fire özelliği başlatılmaz.

## PHASE 5C — Foam Warning Cleanup

Starting commit: `f0d8d76c2f6b8f6c00c789702fc8c82bb52497e6`, branch
`d243-v2-handoff`, Python 3.14.8 from `.venv314`. Baseline: **1832 passed**
(89.05 s). Only the approved untracked reference workbook was present.

Normal/empty input shows one neutral helper:
- TR: **Köpük konsantrasyonunu yüzde olarak giriniz.**
- EN: **Enter foam concentration as percent.**

For `0 < visible_percent < 1`, the helper is hidden and replaced by one amber,
nonblocking clarification:
- TR: **Bu alan yüzde bekler. %3 için 3 giriniz.**
- EN: **This field expects percent. Enter 3 for 3%.**

The mixture caption contains only the mixture basis. Correction to 3 or empty
removes the warning and restores the helper. Empty/3/3,00/1 have zero warnings;
0,5/0,03 have exactly one. Parsing and normalization remain deterministic:
3 -> 0.03 and 0,03 -> 0.0003. Formula steps, provenance and results are unchanged.

## PHASE 5D — Project-Level System Selection & Contextual Navigation

### Semantic decision (reviewed before UI changes)

A. The top `SystemContextPanel` selects `SystemContext.system`, a UUID-backed
engineering system profile. Circuit and fluid are independent optional
references. Existing applicability and engineering-context checks retain them.
B. The former two-button family row only switched cached notebook hosts.
C. The project sidebar now owns the navigation family (`fuel` / `fire`).
D. Top profile/circuit/fluid controls remain engineering context. The profile
caption explicitly says **Mühendislik profili / Engineering profile**. A family
change never selects a profile, circuit or fluid, calculates, or clears results.

### Navigation, visibility and compatibility

One readonly combobox, labelled **Sistem / System**, selects **Yakıt Sistemi /
Fuel System** or **Yangın Söndürme / Fire Fighting**. It sits in a fixed frame
immediately below the project list and above project actions. Scrolling project
details cannot hide it. The list retains its expanding row and 120px minimum;
the actions/details viewport is 144px, reserving roughly the previous lower-panel
budget for that viewport plus the compact fixed selector.

The old central family row, buttons and unused localization key are removed,
recovering one content row. Existing cached hosts are reused:
- Fuel: Pipe, Transfer, Discharge, Suction/ENPY only.
- Fire: Foam, Hazen-Williams only; subviews remain lazy and cached once.

Last selected module is remembered independently for each family. Live inputs,
valid results and frozen snapshots survive family switching. History and
Library remain global. Family/profile conflicts (Fire/FUEL or Fuel/FIRE) produce
a concise sidebar notice and retain the original engineering context.

### Project state

Existing project JSON contains an additive `navigation` version-1 namespace:
`active_system_family` and `last_active_module_by_family`. Stored values are
stable IDs, never widgets or translated labels. Partial saves preserve it.
Missing/unknown navigation preferences use Fuel/Pipe and Fire/Foam defaults;
new/cleared projects default to Fuel. No DB schema or migration was added.
Fresh application restore directly into Fire/HW creates only the HW subview.

### User-approved shell visual correction

The user reported difficulty finding Fire and explicitly requested a navy left
panel and gold top, retaining the accepted icon sizes. This extends the original
phase's shell visual scope. Header/ribbon/logo/command hosts now share GOLD with
navy text; the sidebar uses NAVY, gold titles and white labels. Its scroll canvas
and content match. Data and summary cards retain light, readable surfaces.
Sidebar action text is white normally and navy on light active surfaces.
Upper artwork remains 79px on 86px targets; sidebar artwork remains 40px with a
52px minimum control height. No icon assets were changed.

The user reviewed the isolated current-build window and answered
**Evet, görünüm uygun** for selector discoverability and the requested colors.
The reported visual issue is resolved. Computer Use screenshots failed twice
with `window capture timed out: timed out waiting on channel`. The remaining
interaction/regression evidence comes from real-Tk/service tests; this is not a
claim that all 19 manual acceptance steps were performed by the agent.

### Validation and timings

25 added tests cover warning counts/correction/localization, actual shell
visibility, cached page identity, valid Pipe/Foam results, per-family module
memory, project save/open, legacy/default preferences, partial saves, profile
compatibility, fixed-selector visibility during footer scrolling, shell contrast,
and TR/EN geometry at 1100x700 and 1440x900. Existing text/layout expectations
were updated for the accepted labels and user-approved shell colors.

Focused runs: **128 passed** (initial Fire/context/navigation suite, 47.16 s),
then **81 passed** (final shell/theme/navigation suite, 24.83 s). A separate
fresh-shell Fire/HW restore also passed. Final full regression: **1857 passed,
0 failed (110.73 s)**, comprising 1832 existing and 25 new tests.

Single local runtime samples (not a controlled benchmark):
- Startup before 3.334 s; final 3.516 s.
- Fuel -> Fire first: command 0.160 s, settled 2.393 s.
- Fire -> Fuel: command 0.015 s, settled 0.477 s.
- Cached Fuel -> Fire: command 0.005 s, settled 0.129 s.

Settled includes Tk idle/update work. Lazy construction remains; there is no
workbook, PDF or History preload. Four Fuel pages and at most two cached Fire
subviews are retained without duplication.

Engineering/domain/workflow formulas, numerical semantics, nozzle and seawater
HW restrictions, snapshot schema, Formula View, PDF, History, Library and TL
data are unchanged. The only persistence addition is navigation JSON.

Reference workbook: **approved untracked reference input**, unchanged and
excluded from staging/commit. SHA256:
`bd9aa871454c184afdb45e14bd0c008818d49701d5cc92e1de7ca89126159474`.

Remaining limitation: agent screenshot capture is unavailable; user visual
approval covers the corrected selector/color layout. A complete human 19-step
acceptance record is still optional follow-up; no further Fire feature is
started. Recommended next step is recording that broader manual checklist.

Overall: **PHASE5C5D_PASS_WITH_MINOR_ISSUES**. Implementation, regressions and
user-approved visual corrections pass; the remaining limitation is the broader
human acceptance record and unavailable agent screenshot capture.
