# D243 V2 — Final Windows Acceptance / Faz 16

Başlangıç checkpoint: `d243-v2-handoff`, `03488ec76745a3c48d1384d6e0be1bb81203a135`,
temiz ağaç. Yalnız `C:\Users\Özberk\Documents\ysh\.venv314\Scripts\python.exe`
kullanıldı: Python 3.14.8. Baseline: **1336 passed in 57.70s**; tek uyarı sandbox
pytest cache yazma izniydi, ürün hatası değildi. Faz 15 BendState/NO_BEND,
dekoratif watermark Canvas'ı, 72/86 px üst ikon ve 36/48 px yan menü ayarları doğrulandı.

## Kabul matrisi

PASS burada belirtilen otomatik/service/headless kapsam içindir. Gerçek pencere,
ikon ve yerleşim kabulü ayrı satırlardadır; otomatik PASS bunların yerine geçmez.

| Test alanı | Senaryo | Beklenen | Gerçek sonuç | Durum | Kanıt / sınır |
|---|---|---|---|---|---|
| Checkpoint | Faz 15 SHA, Python, temiz Git | Tam eşleşme | Eşleşti; 1336 baseline testi geçti | PASS | Başlangıç komutları |
| Pipe | Q, D, stress, s0, b, c, wall, Di, hız ve seçim | Kilitli sonuçlar | Sayısal freeze birebir eşit | PASS | Whole/legacy ve 12 orijinal Pipe V2 vektörü |
| Bükme | Aktif ve NO_BEND, geçiş, eski/yeni state | Aktif formül aynı; NO_BEND b=0 | R bayrağı yok; round-trip ve geçmiş korunuyor | PASS | Faz 15 testleri ve yeni iki uçtan uca vaka |
| Basma | V/Re/f/hf/hL/hhat/Hs | Kabul edilmiş değerler | Tam eşitlik | PASS | Faz 5/8, hydraulic freeze |
| Hidrolik yasalar | D^5 pipe, D^4 local, laminar, Colebrook | Mevcut yollar korunur | Katsayılar, çap ölçeği ve rejimler geçti | PASS | test_hydraulic_core_phase5_v2 |
| Emme/ENPY | PE/Pb/HEgeo/rho, NPSHr üst/eşit/alt | Tek hesap yolu; otomatik +1 m yok | Sayısal ve FormulaStep kontrolleri geçti | PASS | Faz 5/9/11 testleri |
| Transfer tasarım | V/t, ttransfer ve kapasite karşılaştırması | Marjsız authoritative hesap | 36 orijinal vektör aynı | PASS | Design freeze, Faz 10 |
| Transfer ampirik | OLS, referanslar, eski state | Ampirik kalır; TL/required capacity olmaz | 36 orijinal vektör aynı | PASS | Empirical freeze, Faz 10/11 |
| PipeSelection | Manual/linked/stale/update/keep/missing/geçişler | Gerçek Di; sessiz uygulama/hesap yok | Q/Di ve revizyon sahipliği korunuyor | PASS | Faz 7/8/9 ve yeni reopen testi |
| Discovery | 0/1/çok kaynak | Otomatik keşif; açık kullanıcı uygulaması | Headless normal sayfa olayları geçti | PASS | Faz 9, polling yok; görsel akış bekliyor |
| Context | Yakıt/Su/Yağ/undefined, save/open | Ayrı system/circuit/fluid; özellik enjeksiyonu yok | Availability ve değişiklik güvenliği geçti | PASS | Faz 12; transfer non-fuel disabled |
| Library iş akışı | Tüm kategoriler, browse/edit/cancel | Read-first, factory koruması, kontrollü hata | Service/controller ve sayfa sözleşmeleri geçti | PASS | Faz 13; gerçek pencere incelemesi bekliyor |
| Library güvenliği | Duplicate/FK/inactive/NULL/provenance | Atomiklik ve kaynak doğruluğu | Mevcut testler geçti | PASS | Kullanıcının gerçek DB'si kullanılmadı |
| Formula View | Dört modül, kaynak/override/check | Yalnız kullanılan veri; renderer hesaplamaz | TR/EN FormulaStep render testleri geçti | PASS | Faz 11/14; gerçek panel görünümü bekliyor |
| Tarihçe | Beş modül/mod, yeniden açma, canlı değişiklik | Değişmez, çoklu, salt okunur, doğru sıra | Tüm beş snapshot byte içeriği korundu | PASS | Yeni Faz 16 entegrasyonu ve Faz 14 |
| Tarihsel kaynak | Canlı Library/source değişimi | Eski metadata ve override sabit | Önceki provenance olduğu gibi kaldı | PASS | Faz 13/14; canlı lookup engellenerek render |
| Tarihsel bağlantı | Upstream N→N+1 | Geçmiş N, current stale | Reopen sonrası applied N=1, upstream N=2 | PASS | Yeni Faz 16 entegrasyonu |
| Legacy | Contextsiz proje, eski bend/transfer state | Uyumluluk; sahte snapshot yok | Legacy testleri geçti | PASS | Faz 10/12/14/15 ve persistence testleri |
| Yeni proje | Save/close/reopen, modüller/link/history | Tam veri korunması | Gerçek repository ile geçti | PASS | Yeni Faz 16; GUI dosya diyalogları bekliyor |
| Runtime DB | Fresh/reopen/idempotence/FK/integrity | Library v5, projects v1, veri kaybı yok | Schema/count korunuyor; integrity/FK kontrolü temiz | PASS | İzole LOCALAPPDATA altında temp DB testi |
| Runtime konumu | Kaynak/build/dist yerine kullanıcı data | %LOCALAPPDATA%/YSH/data | Path resolver ve temp runtime doğrulandı | PASS | Gerçek kullanıcı DB'sine dokunulmadı |
| Kaynak ağacı | Test/smoke artıkları | Yeni DB/log/profile olmamalı | Yalnız iki Faz 16 dosyası değişti | PASS | Git status; önceden tracked DB aşağıda kayıtlı |
| Hata yönetimi | Invalid input/link, duplicate/FK, bozuk snapshot/proje | Kontrollü hata, partial write yok | Otomatik hata yolları geçti | PASS | Görsel messagebox kabulü bekliyor |
| Sayı gösterimi | Dört modül/FV, TR virgül, küçük değer | Genelde 2 ondalık; iç hassasiyet sabit | Formatter, page doubles ve FV testleri geçti | PASS | Faz 1/10/11/14/15 |
| Lazy yükleme | Library, history, Formula View içeriği | Açılışta tüm veri/render yüklenmez | Mevcut lazy testleri ve composition incelemesi geçti | PASS | Önceden mevcut chart importu ayrı aday |
| Başlık/çeviri kodu | TR/EN temel anahtarlar | D243, Bükme yok/No bend, doğru terimler | Katalog ve render testleri geçti | PASS | Gerçek ekrandaki metin ayrıca bekliyor |
| Logo/branding | Tam D243 logo ve başlık; görünür YSH yok | Gerçek GUI kabulü | Tk penceresi oluşmadı | BLOCKED_ENVIRONMENT | Manuel 2–3 |
| İkonlar | Üst/yan/status/formula ve action mapping | Büyük, okunur, oranlı, kesilme yok | Render incelenemedi | BLOCKED_ENVIRONMENT | Manuel 4–7 |
| Watermark | Dört sayfa ve resize | Görünür, hafif, tam, formu örtmez | Render incelenemedi; %14 değiştirilmedi | BLOCKED_ENVIRONMENT | Manuel 8–11; kör opacity düzeltmesi yok |
| Pencere/navigation | 1200×700, resize, tekrar gezinme | Tüm ana akışlar erişilir, duplicate yok | Pencere oluşmadı | BLOCKED_ENVIRONMENT | Manuel 12–33 |
| DPI | 100% | Gerçek Windows gözlemi | Denenmedi | NOT_TESTED | Manuel ölçek testi gerekli |
| DPI | 125% | Gerçek Windows gözlemi | Denenmedi | NOT_TESTED | Manuel ölçek testi gerekli |
| DPI | 150% | Gerçek Windows gözlemi | Denenmedi | NOT_TESTED | Manuel ölçek testi gerekli |
| TR/EN görünür metin | Bozuk karakter/eksik anahtar/kesilme yok | Gerçek ekran gözlemi | Katalog testleri geçti, ekran doğrulanamadı | BLOCKED_ENVIRONMENT | Katalog sonucu görsel PASS değildir |
| Startup | Cold-ish, warm, usable | Pencereye kadar süre | init.tcl öncesinde durdu; süreler elde edilemedi | BLOCKED_ENVIRONMENT | Hata yolu ~5.08 s, startup süresi değildir |

## Kanıt, kusur ve kaynak sınırları

- Sayısal karşılaştırma: whole/legacy/hydraulic kayıtları önceki kabul edilmiş
  verilerle birebir eşit; aktif bükme ve NO_BEND beklenen ayrımı korundu.
- Yeni test modülünde yalnız 3 yüksek değerli vaka var: bükmeli/bükmesiz Pipe →
  linked Basma/Emme → iki Transfer modu → beş snapshot → upstream/context değişimi
  → gerçek proje close/reopen → tarihsel FV. Üçüncü vaka temp runtime DB bütünlüğü.
- Bu incelemede doğrulanmış ürün kusuru: BLOCKER 0, HIGH 0, MEDIUM 0, LOW 0.
  Bu sayılar test edilmemiş görsel alanların kusursuz olduğu anlamına gelmez.
  Üretim kodunda düzeltme veya değişiklik gerekmedi.
- TL steel A/B üretim gerilme içeriği, CuNi üretim sıcaklık tablosu, manufacturing
  tolerance ve TL minimum wall üretim kural/değerleri **NOT_CONFIGURED /
  SOURCE_REQUIRED** olarak kalır. Legacy Rp0.2/B, doğrulanmış güncel TL diye sunulmaz.
  Testlerdeki sentetik kaynaklar/kurallar üretim verisi değildir.
- Yeni kural/veri, DB şeması/migration, bağımlılık veya qallow eklenmedi.
- İzole gerçek main.py açılışı Tk() içinde usable init.tcl bulunamadığından durdu.
  Python/Tk değiştirilmedi. Başarılı cold/warm/usable ölçümü veya normal GUI
  kapanışı iddia edilmez; tekrarlanan aynı başarısız deneme ölçüm yerine sayılmadı.

## Faz 17 için yalnız gözlem — değişiklik yapılmadı

- transfer_pump_chart.py, Matplotlib backend/Axes/Figure sınıflarını modül importunda
  getiriyor; Transfer sayfası MainWindow ile import ediliyor. Import/chart oluşturma
  maliyeti profilleme adayıdır; ölçülmüş startup nedeni olarak sunulmaz.
- App constructor LibraryDatabase.initialize(), run başlangıcında tekrar init
  yapıyor. İdempotent; startup ölçümünde maliyetine bakılabilir.
- build/ysh.spec tüm Matplotlib'i collect_all ile topluyor ve Tcl/Tk 8.6 dosya
  adlarını kullanıyor. Python 3.14 paketleme uyumu Faz 17'de ayrıca doğrulanmalı;
  bu fazda build/spec çalıştırılmadı veya değiştirilmedi.
- Önceden tracked `YSH/work/verification-localappdata/YSH/data/projects.sqlite3`
  var. Aktif runtime yolu değildir; bu fazda oluşturulmadı/değiştirilmedi.
- resources kökündeki ve branding altındaki logo/ico türevleri, libraries/
  illüstrasyonları ve ysh_ship_* dosyaları bağımlılık/hash/paket kapsamı auditi
  adaylarıdır. Dosya adından kullanılmadığı sonucuna varılmadı; hiçbir asset silinmedi.

## MANUAL WINDOWS ACCEPTANCE REQUIRED

Repo dizininde aşağıdaki komutu çalıştırın. Yalnız denediğiniz maddeleri PASS/FAIL
olarak bildirin; diğerleri NOT_TESTED kalsın. Başarısız maddede sayfa, ölçek ve
pencere boyutunu yazın. Gerçek kullanıcı projelerinde Library testi yerine bir
deneme projesi/kullanıcı kaydı kullanın.

```powershell
& 'C:\Users\Özberk\Documents\ysh\.venv314\Scripts\python.exe' main.py
```

1. Uygulama normal açılır; ilk açılış süresini yaklaşık saniye olarak kaydedin.
2. D243 başlık/logo doğru, oranlı ve tamdır; pencere ikonu uygundur.
3. Görünür eski YSH markası yoktur.
4. Üst ikonlar büyük/okunur; kesilme ve bozulma yoktur.
5. Yan menü ikonları büyük/okunur; kesilme yoktur.
6. İkon ve etiketler çakışmaz; Yeni/Aç/Kaydet/Farklı Kaydet eşlemeleri ayrıdır.
7. Status/Formula ikonları kesilmez; tam silüet görünür.
8. Pipe watermark görünür ve hafiftir; girdileri engellemez.
9. Transfer watermark görünür ve hafiftir.
10. Basma watermark görünür ve hafiftir.
11. Emme watermark görünür ve hafiftir; resize sırasında kaybolma/flicker olmaz.
12. Pipe sayfası normal açılır.
13. Bükme yok seçimi vardır; ayrı aktif/pasif kutusu yoktur.
14. Bükme yok hesabı R gerektirmeden b=0 verir.
15. 3D/Manuel bükme normal b verir; manuel R seçenekler arasında korunur.
16. Pipe Formula View doğru bükme durumunu ve v faktörünü gösterir.
17. Basma Manual hesabı çalışır; Q/Di düzenlenebilir.
18. Basma Linked gerçek Di/Q kullanır; alanlar salt okunurdur.
19. Upstream değişince Stale görülür; Keep Current değiştirmez, Update açıkça uygular.
20. Emme Manual hesabı çalışır.
21. Emme Linked çalışır; yerel girdiler bağımsız kalır.
22. ENPY sonucu/NPSHr kontrolü görünür; eşitlik ve eksik NPSHr açıkça gösterilir.
23. Transfer Design kapasite ve süre hesabı çalışır.
24. Transfer Empirical çalışır, açıkça ampiriktir; TL gereksinimi gibi sunulmaz.
25. System/Circuit/Fluid seçimleri çalışır; TR ve EN temel metinler bozulmaz.
26. Tatlı Su/Yağ bağlamında Transfer disabled, nedeni okunur; Undefined erişimi korur.
27. Kütüphaneler açılır; kategoriler, provenance, filtreler ve edit/cancel okunur.
28. Hesap Geçmişi açılır; çoklu kayıt, tarih/modül/özet ve salt okunurluk açıktır.
29. Tarihsel Formula View açılır; canlı girdi/source değişince eski değer değişmez.
30. Deneme projesi save/close/reopen; context, bend, link ve geçmiş korunur.
31. 1200×700 ve büyütülmüş pencerede ana kontroller, uzun TR etiketler ve scroll
    kullanılabilir. 100/125/150% DPI sonuçlarını ayrı ayrı PASS/FAIL/NOT_TESTED yazın.
32. Gezinmeyi üç kez tekrarlayın; duplicate pencere, hata ileti döngüsü ve traceback yoktur.
33. Uygulama normal kapanır. İkinci açılış ve kullanılabilir olma sürelerini de
    yaklaşık kaydedin; mümkünse üç başarılı açılışı ayrı raporlayın.

Manuel yanıt gelmeden final Windows/RC kabulü: **PENDING_MANUAL_ACCEPTANCE**.
Faz 17 başlatılmadı.

## Son otomatik doğrulama

Tam suite: **1339 passed in 59.85s**, 0 failed, uyarı yok. Yeni skip/xfail veya
test kaldırma yok. Yeni odaklı modül ayrıca **3 passed in 4.04s** verdi.
Git fark kontrolü temiz; yalnız bu kabul kaydı ve üç testi içeren modül eklendi.
Üretim dosyaları, veri, asset, ortam ve paketleme dosyaları değişmedi.
Otomatik kabul PASS; final Windows/RC ve genel Faz 16 sonucu kullanıcı görsel/runtime
yanıtına kadar **PENDING_MANUAL_ACCEPTANCE**. Manuel sonuç uydurulmadı.


## Phase 17 release engineering — 2026-10-19

The preceding Phase 16 record is retained as historical evidence. Phase 17 now
has **1379 passing tests (42.57 s)** and a successful Windows onedir build.
Actual D243.exe launches/closes from an isolated copy; frozen Tcl/Tk 9.0.4,
PNG/MathText/TkAgg, SQLite, project persistence and module/Library/History checks
pass. Final runtime: 167,380,009 bytes / 1417 files; ZIP: 110,774,019 bytes.
Controlled first-drawing startup improves from approximately 24–26 s to 4.8–6.6 s.
No UI redesign, calculation, schema or engineering data change is included.

Exact build command, dependency/asset audits, checksums, deferred items and the
20-item packaged-EXE checklist are in [V2_RELEASE_PHASE17.md](V2_RELEASE_PHASE17.md).
Final status remains **PENDING_MANUAL_ACCEPTANCE** until human Windows acceptance;
no later phase is started.
