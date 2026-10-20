# D243 V2 — Formula View görsel uyumu

Başlangıç: `d243-v2-handoff`, `ec117ea592199271045d98d065b3e4dc3b7ef590`, temiz ağaç.
Python yalnız `.venv314/Scripts/python.exe`, sürüm 3.14.8.
Baseline: **1489 passed, 0 failed** (yalnız pytest cache yazma izni uyarısı).

## Görsel uygulama

Formula View, ayrı açıklama penceresi olarak kalır. Başlangıç boyutu 1100×750;
700×450 minimum ve native yeniden boyutlandırma/kaydırma davranışı korunur.
Üstte kompakt ƒx başlığı, Türkçe “Formül Görünümü”, modül adı ve üst adım seçici
bulunur. Önceki/Sonraki düğmeleri sınır adımlarda devre dışıdır. Seçili adım renkli
seçicide ve kart başlığında açıktır; iç step ID görünür başlıklara eklenmez.

`ui/theme/formula_visuals.py`, mevcut master tokenlarını kullanır:

| Modül | Vurgu | Koyu sonuç/başlık |
| --- | --- | --- |
| Boru | `#0D9488` | `#0F766E` |
| Transfer | `#2563EB` | `#1D4ED8` |
| Basma | `#6366F1` | `#4338CA` |
| Emme/ENPY | `#EA7C32` | `#9A3412` |

Beyaz kart, ince sınır ve küçük modül accent çizgisi; Segoe UI; mevcut
4/8/12/16 px boşluk tokenları kullanılır. Sonuç mevcut büyük/bold tipografiyle
vurgulanır. Header ve proje paneli değiştirilmedi. Watermark yoktur.

Sekiz bölüm korunur: Formül, Değişkenler, Kullanılan Değerler, Bu değer neden
seçildi?, Kaynak, Yerine Koyma, Sonuç ve Uygunluk Kontrolü. Mevcut opsiyonel
referans/teknik ayrıntılar da korunur. Yalnız mevcut veri olan bölümler çizilir.

- Değişkenler ve kullanılan değerler kompakt native kolonlarda; uzun hücreler sarılır.
- Önerilen/kullanılan değerler ve override gerekçesi mevcut kayıttan gösterilir.
  Gerçek override satırları hafif amber; yeni override yorumu üretilmez.
- Seçim gerekçesi açık mavi açıklama alanındadır.
- Kaynak özeti kısa tutulur; doğrulama durumu uzun belge adı yüzünden kaybolmaz.
  Tüm özgün metadata açılır/kapanır ayrıntıda bulunur. Null alanlar önceden olduğu
  gibi gösterilmez. Doğrulanmış/kısmi/kullanıcı sağladı/doğrulanmamış/deprecated
  renkleri yalnız kayıtlı statüden alınır; kaynağın varlığı doğrulama sayılmaz.
- Yerine koyma nötr yüzeyde ve okunaklı Consolas metnindedir.
- Sonuç yalnız FormulaStep değerinden; uygunluk yalnız kayıtlı kontrolden gelir.
- Geçmiş panelde “Geçmiş Kayıt · Salt Okunur” rozeti vardır. History görünümüne
  yalnız module_key/historical parametreleri bağlandı; History yeniden tasarlanmadı.

## Lazy çizim ve freeze

Yalnız seçili FormulaStep çizilir. Veri/adım değişmeyen yenileme açık disclosure ve
odağı korur. Sonuç yokken veya pencere kapanınca eski kontrol referansları temizlenir.
Dil değişimi görünümü yeniden yerelleştirir. Yeni polling, eager Matplotlib, asset
ön yüklemesi veya cache eklenmedi. Mevcut bounded asset cache korunur.

Formül görsel ölçüsü mevcut aspect-safe **en çok 560×280**, büyütmesiz stratejide
kalır. PNG mapping, karantina, PNG → MathText → native metin sırası değişmedi.
Yeni/deneysel PNG veya ikon paketi eklenmedi.

Başlangıç commit'i ile AST karşılaştırması şu fonksiyonların birebir aynı olduğunu
doğruladı: `number`, `source_rows`, `step_sections`, `_render_section_content`,
`_render_formula_assets`, `_render_mathtext_equations`, `_render_mathtext_image`.

Mühendislik hesapları/FormulaStep modeli, sayısal değerler, PDF modeli/üretimi,
Library, snapshot/history semantiği, DB şeması/migration, TL verisi ve qallow/qmüs
bu görevde değiştirilmedi/eklenmedi. Ana modül sayfalarının yalnız Formula View
çağrılarına modül kimliği eklendi.

## Doğrulama

17 yeni test: dört modül kimliği, kaynak statü renkleri, uzun kaynak özetinde
statünün korunması, sekiz bölüm ve hassasiyet, aktif adım seçimi, gereksiz yeniden
çizimden kaçınma, boş sonuçta eski kontrollerin bırakılmaması, historical wiring,
TR/EN chrome ve tek adım çizimi. Mevcut renderer test double'ı yeni opsiyonel stil
parametrelerini kabul edecek biçimde güncellendi; mevcut testler silinmedi.

- Odaklı: **226 passed**.
- Tam paket: **1506 passed, 0 failed**, 64,39 s.
- Gerçek Tk: Boru, Transfer Tasarım, Transfer Ampirik, Basma, Emme/ENPY adımları PASS.
- Tüm adımlarda kaynak ayrıntıları açıldı/kapatıldı; sonuca kaydırma ve normal kapanış PASS.
- No-bend adımında `b=0`, mevcut “Bükme yok” açıklaması ve karantinalı fallback korunur.
- Historical panel, frozen snapshot byte eşitliği ve salt okunur gösterim PASS.
- Dört modülde hesap referans eşitliği, snapshot PDF, proje geçişi, History ve Library smoke PASS.

| Pencere | Beş canlı formül yolu | Historical frozen panel |
| --- | --- | --- |
| 900×650 | PASS | PASS |
| 1100×750 | PASS | PASS |
| 1400×900 | PASS | PASS |

Geometri testlerinde istenen boyutlar gerçekten oluşturuldu; test maxsize sınırı
yalnız fixture'da artırıldı. İçeriğin yatay sınırları, kaydırma, sonuç erişimi ve
source disclosure kontrolleri geçti. Renk dengesi için insan incelemesi hâlâ gereklidir.

Smoke ölçümleri: Boru 1,072 s, Transfer Tasarım 0,757 s, Basma 0,639 s,
Emme/ENPY 0,643 s, Transfer Ampirik 1,706 s. Aynı yedi adımlı Basma örneğiyle ayrı
süreç karşılaştırması: başlangıç 3,5205 s, yeni görünüm 2,1903 s. Bu ölçümlerde
ilk açılış gerilemesi gözlenmedi; istatistiksel hızlanma iddiası yoktur.

Runtime profilleri workspace altında yalıtılmıştır; normal kullanıcı verisine
dokunulmadı. Ampirik başarı yolu açık sentetik üç referans gemi fikstürü kullanır;
bunlar Library/seed/TL verisi olarak eklenmedi. Referanssız ampirik boş sonuç yolu
eski tasarım kontrollerini tutmama testiyle ayrıca korunur.

## Manuel görsel kabul

**PENDING_MANUAL_ACCEPTANCE.** Release EXE/ZIP yeniden üretilmedi. Kaynak uygulamada
onaylı Python ile hesap yapıp Formülü Göster eylemini açın.

1. Görünüm D243 ailesine ait görünüyor.
2. Modül rengi belirgin ve dengeli.
3. Formül ana odak noktası.
4. Değişkenler okunaklı.
5. Kullanılan/önerilen değerler açık.
6. Gerekçe alanı kısa ve anlaşılır.
7. Kaynak ayrıntıları baskın değil.
8. Sonuç kolay fark ediliyor.
9. Uygunluk durumu açık.
10. Adım geçişleri kolay.
11. Geçmiş kayıt salt okunur görünüyor.
12. Bükme yok / b=0 açık.
13. Boru teal kimliğinde.
14. Transfer mavi kimliğinde.
15. Basma indigo kimliğinde.
16. Emme turuncu kimliğinde.
17. Türkçe etiketler tam.
18. Watermark yok.
19. Büyük boş alanlar yok.
20. Kırpılma yok.
21. 900×650 kullanılabilir.
22. 1400×900 dengeli.
23. Sayısal sonuçlar aynı.
24. Traceback yok.

Burada duruldu. Library/History/PDF belgesi, ana header veya proje sidebar'ına
yeni görsel yayılım yapılmadı. Kabul sonrası ayrı görev için Library önerilebilir.
