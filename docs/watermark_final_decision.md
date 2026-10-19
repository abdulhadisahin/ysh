# D243 V2 — Watermark nihai kararı

**FINAL WATERMARK DECISION: REMOVE COMPLETELY**

Başlangıç: `8f9121ac7fb2e854031172db42d28be0f444c8eb`,
`d243-v2-handoff`, temiz ağaç. Python: yalnız `.venv314/Scripts/python.exe`, 3.14.8.
Başlangıç test sonucu: **1459 passed**.

## Kontrollü son deneme ve karar

Önceki yapı ortak helper kullanmasına rağmen her modülün farklı kartına küçük,
sağ alta bağlı bir Label yerleştiriyordu; sayfa/kart yüzeyi seçimi gerekiyordu.

Gerçek Tk denemesinde mevcut Canvas'ın en altına kanonik watermark görseli kondu:
çalışma alanı genişliğinin %55'i, %8 etkin alfa, merkez (%58, %60), oran korunarak.
Dört modülün tamamında opak içerik penceresi, görselin görünür sınırlar içindeki
alanının %100'ünü kapladı. İçerik çerçevesinin arka planı `#EEF2F5` idi. Bu,
ekran görüntüsü değerlendirmesi değil; Canvas katman sırası, pencere sınırları ve
Tk'nin opak native içerik penceresi üzerinden yapılan teknik kontroldür.

Görseli görünür kılmak için kabul edilmiş kartları/çerçeveleri yeniden boyamak,
şeffaflaştırmak veya sayfa bazlı çözümler eklemek gerekecekti. Talimattaki fallback
uygulanarak üçüncü bir tasarım üretilmedi; watermark dört modülden tamamen kaldırıldı.

## Uygulanan kaldırma

- Ortak sayfa host'unun watermark çağrısı ve varlık import'u kaldırıldı.
- Dört modülün `watermark_surfaces` tanımları kaldırıldı.
- ScrollableFrame içindeki watermark listesi, helper import'u ve bağlama metodu kaldırıldı.
- Artık kullanılmayan `workspace_watermark.py` renderer'ları kaldırıldı.
- Watermark'a ait widget, odak/tıklama katmanı, timer, resampling ve cache kalmadı.
- Kanonik watermark dosyaları ve asset resolver'ları korundu; header ve PDF logolarına dokunulmadı.

Çalışma alanında dekorasyon için yatay/dikey alan: **0 px**.
Kaldırma sonrası anchor, ölçek, opaklık ve resize cache uygulanmaz.
Var olan geometri, kaydırma ve klavye/fare yönlendirmesi aynen korunur.
Mühendislik, sayısal sonuçlar, FormulaStep, PDF, Library, snapshot, DB, proje ve
Türkçe yerelleştirme değişmedi. Paket/release ZIP yeniden üretilmedi.

## Doğrulama

Eski renderer'a bağlı 20 test vakası 28 kaldırma/yerleşim sözleşmesiyle değiştirildi;
mühendislik ve kanonik görsel testleri korunmuştur. Testler çeşitli viewportlarda
tek Canvas içerik penceresini, mevcut grid hücrelerini, orijinal olay yönlendirmesini,
dört modülün ortak host fabrikasını ve renderer/cache/polling yokluğunu doğrular.
Odaklı kontrol: **56 passed**. Tam kontrol: **1467 passed, 0 failed**.

Gerçek Tk karşılaştırmasında dört modülün sayfa boyutları ve tüm ölçülen
Entry/Combobox/Button/Treeview/Canvas dikdörtgenleri başlangıçla birebir eşitti.
Dört modül açıldı, dekorasyon öğesi bulunmadığı ve normal kapanış doğrulandı.
Temsilî başlangıç süresi: önce 9,861 sn, sonra 8,977 sn. Bu tekil ölçümlerde
gerileme görülmedi; istatistiksel performans iyileştirmesi iddiası değildir.

## Manuel görsel kabul

Boru, Transfer, Basma ve Emme/ENPY sayfalarının her birinde:

1. Çalışma alanında dekoratif watermark kalmadığını kontrol edin.
2. Normal D243 header logosunun korunduğunu kontrol edin.
3. Ayrı sağ şerit/kolon veya boş rezerv alan bulunmadığını kontrol edin.
4. Çalışma alanı, giriş ve sonuç kartlarının genişliğinin aynı kaldığını kontrol edin.
5. Yazıların ve sonuçların okunabilirliğini kontrol edin.
6. Pencereyi daraltıp genişletin; kontrol yerleşiminin aynı davrandığını kontrol edin.
7. Alanlara ve düğmelere tıklayın; engellenen tıklama bulunmadığını kontrol edin.
8. Sekme/klavye dolaşımını ve kaydırmayı kontrol edin.
9. Formula View ve PDF eylemlerinin normal çalıştığını kontrol edin.

Büyük görselin konumu, alfa değeri, örtülmesi ve kırpılmasıyla ilgili KEEP kontrol
maddeleri REMOVE kararı nedeniyle uygulanmaz. İnsan tarafından dört sayfanın görsel
kabulü beklenir; nihai teknik karar **REMOVE COMPLETELY** olarak sabittir.
