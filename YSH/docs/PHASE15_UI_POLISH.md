# D243 V2 — Faz 15 UI polish

Başlangıç: `d243-v2-handoff`, `40a8bf8c5135b95a772c1dc708c199d892722ac7`, temiz ağaç.
Python: yalnız `.venv314/Scripts/python.exe`, 3.14.8. Baseline: 1311 passed
(56.37 s; sandbox pytest cache yazma uyarısı). Yeni Faz 15 testleri: 25.

## Uygulanan değişiklikler

- Onaylı logo dosyaları değiştirilmedi. Header `resources/branding/d243_logo_main.png`,
  watermark `resources/branding/d243_logo_watermark.png`, Windows simgesi aynı
  klasördeki `d243_logo.ico`; oran korunarak LANCZOS ile sığdırılır.
- Üst komutların 86 px yüzeyi / 72 px istek boyutu ve yan menünün 48 px minimum
  satırı / 36 px isteği korundu. Görünür alfa sınırı 8 ve %5 güvenli kenar,
  geniş saydam dış alanın çizimi küçültmesini giderir. Gerçek Yeni assetinde
  görünür çizim yaklaşık 53 px yerine 65 px; yan menüde yaklaşık 33 px olur.
  İkonla birlikte düğme yüksekliği büyür; 10 px ikon/metin aralığı korunur.
  Kompakt çizim yaklaşık 20–24 px; status 34 px canvas/40 px alan;
  Formula 32 px canvas/36 px alan. Status/Formula silhouette_safe değişmedi.
- Asset cache 128 girişle sınırlı; mevcut widget referansları geçerlidir.
  Logo canvas, action full_asset_safe, status/formula silhouette_safe kullanır.
- Eski watermark, opak content window altında kaldığından görünmüyordu;
  %100 tanı opaklığı da kodda kalmıştı. Dört modülün ortak scroll host'unda
  ayrı bir dekoratif Canvas grid hücresi ayrıldı. Kontroller bu alanı kapatamaz,
  görsel de kontrollerin üstüne gelemez. Sağ alan genişliği viewport'un %20'si,
  120–280 px aralığında; logo her iki eksene 12 px boşlukla sığar.
  Nihai alfa çarpanı %14; kaynak alfa ayrıca korunur. Boyutlar 8 px dilimlidir,
  resize after_idle ile birleştirilir, kaynak bir kere okunur, en fazla 6 boyut
  tutulur. Polling/lift döngüsü veya diske üretilen görsel yoktur.
- Şampanya altın dekoratif vurgular kullanıldı; açık zemindeki sonuç metni koyu,
  birincil düğmeler lacivert üzerinde açık metin olarak kaldı.
- İngilizce app.title artık D243. İç paket adı YSH değişmedi.
- Bükme yarıçap seçimine açık NO_BEND / Bükme yok / No bend eklendi; ayrı checkbox
  kaldırıldı. Domain BendState, mevcut authoritative boolean girdiden türetilir.
  NO_BEND: R gerekmez, b=0. Aktif: b=0.4*(da/R)*s0 aynen korunur. R=1 bir OFF
  bayrağı değildir. Manuel R seçenekler arasında korunur. Legacy açık bükme ve
  yalnız R içeren eski kayıtlar manuel olarak yüklenir; yeni state round-trip olur.
  Sonuç trace'i ve immutable snapshot kullanılan bükme durumunu saklar.
- Formula View b=0 nedenini lokalize gösterir; hesap/renderer mimarisi aynı.
  Kütüphane filtreleri genişliğe yayılır, detay alanı scroll eder; geçmişin uzun
  tarih/özet satırları yatay scroll ile erişilir; context etiket aralığı düzenlendi.
  Dört sayfa ortak düğme/geometri düzeltmelerinden yararlanır.

## Doğrulama ve sınırlar

Sayısal freeze: legacy/whole/hydraulic Phase 13 verileriyle birebir eşit.
Orijinal Pipe V2 12, transfer design 36 ve empirical 36 vaka birebir eşit.
Yeni testler bükme geçişleri, b=0, aktif formül, snapshot freeze, legacy/new
state round-trip, alfa sınırları, gerçek asset görünür alanı, cache sınırları,
düğme yüksekliği ve watermark'ın ayrı widget hücresini doğrular.
Önceki UI contract testleri yalnız onaylı değişen başlık/bükme/palet/watermark
beklentilerine güncellendi; anlamlı regresyon kapsamı kaldırılmadı.

GUI smoke: gerçek main.py, izole LOCALAPPDATA profiliyle denendi.
Tk oluşturulurken kullanılabilir init.tcl bulunamadı: **BLOCKED_ENVIRONMENT**.
Python/Tk kurulumu değiştirilmedi. İkon, watermark, logo ve DPI için gerçek
render kabulü **MANUAL_ACCEPTANCE_REQUIRED**; testler görsel PASS sayılmaz.
Mevcut ana pencere minimumu 1200×700 korunur; sağ dekorasyonun dar ekrandaki
yerleşimi de aşağıdaki manuel kontrolde değerlendirilmelidir.

DB şema/migration, hesap formülleri, Library/Context anlamı ve bağımlılıklar
değişmedi. Yeni mühendislik verisi veya qallow yok. Faz 16 başlatılmadı.

## Manuel Windows kabul listesi

Repo dizininde PowerShell ile çalıştırın:

```powershell
& 'C:\Users\Özberk\Documents\ysh\.venv314\Scripts\python.exe' main.py
```

Her madde için PASS/FAIL kaydedin; başarısız maddede sayfa ve pencere boyutunu belirtin.

1. Ana pencere normal açılıyor.
2. D243 logo doğru, tam ve oranı bozulmamış.
3. Üst ikonlar belirgin büyük ve okunur.
4. Üst ikonlarda kesilme yok.
5. Yan menü ikonları büyük ve okunur.
6. Yan menü ikon/metin çakışması yok.
7. Status/uyarı silüeti kare biçimde kesilmiyor.
8. Formula ikonları kesilmiyor.
9. Pipe sağ dekorasyon alanında watermark görünüyor.
10. Transfer sayfasında watermark görünüyor.
11. Basma sayfasında watermark görünüyor.
12. Emme sayfasında watermark görünüyor.
13. Watermark belli oluyor, alan/metinleri engellemiyor; dar boyutta form scroll kullanılabiliyor.
14. Pipe seçiminde Bükme yok var; ayrı aktif/pasif kutusu yok.
15. Bükme yok ile b=0; sahte R gerekmiyor.
16. 3D/Manuel bükme ile normal b hesaplanıyor; manuel R geçişte korunuyor.
17. Formula View kullanılan bükme durumunu doğru gösteriyor; eski geçmiş değişmiyor.
18. Library liste, filtre ve editör okunur.
19. History tarih/modül/özet ve tarihsel Formula View okunur.
20. System/Circuit/Fluid alanları ve disabled Transfer gerekçesi okunur.
21. TR ve EN başlıklarda görünür YSH markası yok.
22. 1200×700 ve daha büyük pencerede önemli metin/kontrol kesilmesi yok;
    100/125/150% DPI seviyelerini yalnız gerçekten denenirse PASS işaretleyin.
23. Uygulama normal kapanıyor; traceback yok.

## Son otomatik sonuç

Tam suite: **1336 passed in 55.77s**; yeni skip/xfail yok. `git diff --check` temiz.
Otomatik kabul PASS; görsel kabul BLOCKED_ENVIRONMENT / MANUAL_ACCEPTANCE_REQUIRED.

Değiştirilen mevcut dosyalar:

- YSH/core/bend_radius.py
- YSH/engineering/formula/pipe.py
- YSH/engineering/pipe_design/models.py
- YSH/i18n/messages_en.py
- YSH/i18n/messages_tr.py
- YSH/services/pipe_design_service.py
- YSH/tests/test_bend_radius_phase6.py
- YSH/tests/test_formula_v2_phase11.py
- YSH/tests/test_header_icon_only_phase9ui_b3.py
- YSH/tests/test_shell_navigation_phase5b.py
- YSH/tests/test_ui_theme_contract.py
- YSH/tests/test_workspace_watermark_phase9g.py
- YSH/ui/dialogs/calculation_history.py
- YSH/ui/dialogs/engineering_library_workspace.py
- YSH/ui/pages/pipe_design_page.py
- YSH/ui/theme/colors.py
- YSH/ui/theme/styles.py
- YSH/ui/widgets/asset_loader.py
- YSH/ui/widgets/formula_steps.py
- YSH/ui/widgets/rounded_button.py
- YSH/ui/widgets/scrollable_frame.py
- YSH/ui/widgets/system_context_panel.py
- YSH/ui/widgets/workspace_watermark.py

Yeni dosyalar: bu not ve YSH/tests/test_ui_polish_phase15.py.
