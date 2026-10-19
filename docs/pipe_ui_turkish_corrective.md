# Boru UI semantik gruplama ve Türkçe yerelleştirme düzeltmesi

Başlangıç: `d243-v2-handoff`, `74d73cdfce1877081b23ad3d0e612b8e3372c5c8`, temiz ağaç.
Python: yalnız `.venv314/Scripts/python.exe`, 3.14.8. Başlangıç testleri: 1446 passed.

## Yerleşim

Boru/tasarım verileri, malzeme/dayanım, emniyet/gerilme, korozyon ve bükme ayrı
semantik gruplardır. Mevcut üç dış kolonun içerik genişliğine göre dört kolon,
iki kolon veya tek yığın yerleşimine geçişi korunur. Sonuç kartı ayrı ve salt okunurdur.

Malzeme, Rp0,2 ve kaynak seçicisi aynı gruptadır. Emniyet katsayısı ile kaynak
faktörünün yanında A/B doğrulama durumu ve mevcut kaynak notları düğmesi bulunur.
Yeni A/B sayısı veya TL kuralı eklenmedi; eski notların doğrulanmamış niteliği korunur.
Korozyon c girdisi, varsayılan c ve kullanılan c aynı gruptadır; kaynak açıklaması
seçili devre varsayılanı ve mevcut hesap girdisini ayırt eder. Bükme durumu, R,
b ve b=0 açıklaması birlikte gösterilir. Sonuç kartına mevcut kayıttaki c değeri
salt okunur olarak eklendi; canlı c girdisinden yeni sonuç türetilmez.

## Yerelleştirme denetimi

Üç hesap sayfasında kaynak seçicilerinin başlangıç seçeneklerindeki sabit
`Material Library / Manual` ifadeleri TR/EN kaynak anahtarlarıyla değiştirildi.
Türkçe karşılıklar: **Malzeme Kütüphanesi / Manuel**. Eski projelerin kaynak
etiketleri yüklenirken görünür dilde gösterilir; manuel giriş modu korunur.
Boru durum mesajlarındaki `Error:` kaldırıldı; beklenmeyen hata mesajı ortak kaynaktan
gelir. Hesap tamamlanma mesajı parametreli TR/EN kaynak anahtarına taşındı.
Eski `Ready` yükleme varsayılanı Türkçe hazır mesajıyla gösterilir.
Proje aç düğmesinin ilk metni ortak `action.open` anahtarını kullanır.
Türkçe kaynakta `English → İngilizce`, `Schedule → Et kalınlığı serisi`,
`Rp0.2 Kaynağı → Rp0,2 Kaynağı` düzeltildi.

Bilinen yanlış İngilizce etiketler için açık denylist testi ve üretim widget
kurucularına AST taraması eklendi. Dahili adlar, eski kayıt tanımları, kullanıcı
verileri, doküman/standart adları, D243, PDF, UUID, NPS/NPSHr, ENPY ve mühendislik
sembolleri çevrilmez. İngilizce katalog korunur; katalog anahtarları eşittir.
Uygulamanın önceki V1 Türkçe dil politikası değiştirilmedi.

Formula View tasarımı, FormulaStep, PDF mimarisi/davranışı, Library semantiği,
watermark, DB, migration ve bütün mühendislik formülleri değişmedi.
Deneysel PNG, yeni TL verisi ve qallow eklenmedi. Dağıtım paketi yeniden üretilmedi.

## Doğrulama ve ortam sınırı

11 yeni semantik/yerelleştirme regresyon testi eklendi. Gerçek Tk smoke;
widget sahipliğini, manuel hesap sonucunun referans hesapla tam eşitliğini,
b=0, kaynak modu/dil yenileme, eski kayıt yükleme, PDF eylemi, Formula View,
Library açılışı ve normal kapanışı kontrol eder. 1200×700 ve 1700×1000 boyutlarında
grup çocuklarında taşma ve dikdörtgen çakışması kontrol edildi.

Tk çalışır; masaüstü ekran yakalama bu ortamda `screen grab failed` hatası verir.
Bu nedenle otomatik geometri kontrolleri insanın görsel kabulü yerine sayılmamıştır.
Manuel kabul bekleniyor. Sayısal referanslar ve PDF regresyon testleri korunur.

## Manuel kabul listesi

1. Boru Tasarımı'nı açın.
2. Malzeme seçiminin Rp0,2 yanında/altında olduğunu kontrol edin.
3. Rp0,2 kaynağının aynı grupta olduğunu kontrol edin.
4. Emniyet Katsayısı grubundaki A/B kaynak bilgisini kontrol edin.
5. Doğrulanmış TL değeri iddiası bulunmadığını kontrol edin.
6. c / Varsayılan c / Kullanılan c birlikteliğini kontrol edin.
7. Bükme kontrollerinin birlikteliğini kontrol edin.
8. Sonuç alanının ayrı ve salt okunur olduğunu kontrol edin.
9. Alanların üst üste gelmediğini kontrol edin.
10. 1200×700 boyutunda kaydırmayla kullanılabilirliği kontrol edin.
11. Daha geniş pencereyi kontrol edin.
12. Görünür Material Library ifadesinin bulunmadığını kontrol edin.
13. Boru sayfasındaki Türkçe etiketleri kontrol edin.
14. Library Türkçe etiketlerini kontrol edin.
15. Formula View'ı açın.
16. PDF raporu oluşturun.
17. Boru sayısal sonucunu önceki kabul edilmiş sonuçla karşılaştırın.
18. Bükme yok için b=0 sonucunu kontrol edin.
19. Hata/traceback bulunmadığını kontrol edin.
20. Uygulamayı normal kapatın.

Son odaklı kontrol: **158 passed** (semantik gruplama, yerelleştirme, gerçek hesap/snapshot ve PDF regresyonları).

Son tam test: **1457 passed, 0 failed**, 78,71 saniye.
Otomatik runtime smoke: **PASS**; ekran yakalama görsel kısmı **BLOCKED_ENVIRONMENT**.
Genel durum: **PENDING_MANUAL_ACCEPTANCE**.
