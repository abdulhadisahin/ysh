# D243 V2 — Boru master görsel pilot

Başlangıç: `e4a0a8a872549d5a318c45cb86b6e646822e2588`, `d243-v2-handoff`, temiz ağaç.
Python yalnız `.venv314/Scripts/python.exe` (3.14.8). Başlangıç: **1467 passed**.

## Görsel yön ve sınır

Yalnız Boru Tasarımı, aday master şablon olarak turkuaz/teal vurgulu modern
mühendislik kartlarına geçirildi. “Renkli Uygulama Alternatifi” görseli bu istekte
ekli değildi; modern/canlı ama dengeli, ferah ve teknik yönündeki ayrıntılı tarif
esas alındı. Birebir görsel kopyalama yapılmadı.

`ui/theme/pipe_pilot.py` mevcut ttk sistemine yalnız Pipe-prefiksli stiller ekler.
Diğer modül renkleri geleceğe dönük token planında tutulur, uygulanmaz. Global
uyumluluk renkleri, Transfer/Basma/Emme sayfaları ve bu modüllerin stilleri korunur.

- Açık soğuk çalışma zemini, beyaz giriş kartları, ince sınırlar; iç gruplar temiz ayrılır.
- Teal kart başlıkları, büyük koyu teal sonuç, sol accent çizgisi ve hafif sonuç yüzeyi.
- Birincil hesap düğmesi koyu teal; hover lacivert. Temizle ve formül eylemi daha hafif.
- Beyaz girişler, teal odak çerçevesi, hizalı dropdown ve duvar hesabında ayrı birim kolonu.
- Kaynak doğrulama bilgisi okunaklı amber bilgi şeridi; diğer açıklamalar açık mavi şerit.
- Mevcut durum renkleri korunur; yeni uygunluk sonucu veya doğrulanmış TL iddiası üretilmez.
- Segoe UI ve mevcut 4/8/12/16/24 px boşluk ölçeği kullanılır. Yeni görsel/animasyon yoktur.

Ortak kabukta yalnız header grupları arasındaki ritim ve proje başlığı boşluğu
hafifçe düzenlendi. Header 79 px ikon / 86 px yüzey; sidebar 40 px ikon / 52 px
asgari satır boyutları aynıdır. Proje arama, liste, seçili proje, işlemler ve aktif
proje akışı değişmedi. Sistem/Devre/Akışkan kontrolleri ortak kompakt tek satırda;
mevcut uyarılar alt satırda korunur. Seçili Boru sekmesi teal, diğer seçili sekmeler
kabul edilmiş lacivert/altın davranışına döner. Diğer modül içeriklerine pilot yayılmadı.

## Korunan sözleşmeler

Malzeme/Rp0,2/kaynak, emniyet/kaynak faktörü/tablo, korozyon ve bükme grupları
korunur. **Kullanılan c görünür satırı yoktur.** “Emniyet katsayısı tablosu” adı ve
kaynak doğrulama uyarısı aynıdır. Varsayılan c ve c girdisi değişmedi.
Sonuç değerleri yalnız mevcut çıktılara bağlıdır. b=0 davranışı aynıdır.
Formül ayrı açıklama penceresinde kalır; snapshot tabanlı PDF eylemi ikincil stildedir.
Watermark yoktur. Mühendislik, FormulaStep, snapshot, PDF modeli, Library, DB,
proje kalıcılığı ve TL veri içeriği değişmedi.

## Otomatik doğrulama

10 yeni pilot testi: stil kapsamı, yalnız Boru sekmesi rengi, diğer modüllere
bulaşmama, semantik gruplar, birimler, ikon ölçüleri, formül/PDF girişi ve bağlam
seçim akışının korunması. Eski altın düğme/sekme sunum beklentileri yeni pilot
rengini denetleyecek şekilde güncellendi; testler silinmedi.

Odaklı testler: **105 passed**. Tam testler: **1477 passed, 0 failed**.
Gerçek Tk testinde referans hesapla tam sonuç eşitliği, b=0, Formula View,
snapshot PDF üretimi ve normal kapanış: **PASS**.

| Boyut | Sonuç | Yerleşim |
| --- | --- | --- |
| 1200×700 | PASS | İki kolon; kaydırmayla sonuç ve eylemler erişilebilir |
| 1366×768 | PASS | İki kolon |
| 1600×900 | PASS | Geniş yerleşim |
| 1700×1000 | PASS | Geniş yerleşim |

Test root'unun geçici maxsize sınırı yalnız fixture içinde artırılarak fiziksel
test ekranından büyük boyutların gerçekten oluşması sağlandı. Üretim pencere
sınırları değiştirilmedi. Grup içi taşma/çakışma ve alt eylemlerin erişimi denetlendi.
Temsilî kaynak açılışı 7,583 saniye; gerileme gözlenmedi, istatistiksel hızlanma
iddiası yoktur. Ek resampling, arka plan resmi veya polling eklenmedi.

## Görsel inceleme ve geliştirme önizlemesi

Computer Use ile yalıtılmış geliştirme önizlemesi açıldı. Pencere bulundu; ekran
yakalama `FrameArrived timed out: timed out waiting on channel` ve tekrarında
`window capture timed out: timed out waiting on channel` hataları verdi. Bu nedenle
renk dengesi veya görsel kalite için insan onayı verilmiş gibi raporlanmaz.

Ayrı geliştirme önizlemesi normal kullanıcı verisini kullanmaz; bu görevin workspace
altındaki `preview_profile` klasörünü kullanır. Örnek proje ve elle girilmiş sayılar
sadece gösterim fikstürüdür. Son release EXE/ZIP yeniden üretilmedi.
**Genel durum: PENDING_MANUAL_ACCEPTANCE.**

## Kullanıcı görsel kabul listesi

1. Boru sayfası daha modern görünüyor.
2. Sayfa belirgin biçimde daha renkli.
3. Renk kullanımı aşırı değil.
4. Sol proje alanı ferah.
5. Header temiz ve düzenli.
6. Kabul edilmiş büyük ikonlar korunuyor.
7. Seçili Boru sekmesinin kimliği belirgin.
8. Girdiler kolay taranıyor.
9. Malzeme/Rp0,2 grubu anlaşılır.
10. Emniyet katsayısı tablosu ve kaynak durumu okunaklı.
11. Korozyon alanları tutarlı; Kullanılan c satırı yok.
12. Bükme alanları tutarlı.
13. Sonuç kartı hemen fark ediliyor.
14. Et Kalınlığını Hesapla eylemi belirgin.
15. Formül eylemi bulunabilir ama baskın değil.
16. PDF eylemi erişilebilir.
17. Türkçe arayüz korunuyor.
18. Watermark yok.
19. 1200×700 kullanılabilir.
20. 1700×1000 dengeli görünüyor.
21. Mühendislik sonucu aynı.
22. Traceback yok; uygulama normal kapanıyor.

Kullanıcı onayı olmadan Transfer, Basma, Emme/ENPY, Library veya Formula View'a
bu tasarım yayılmaz. Kabul edilirse bir sonraki ayrı görevde yayılım planlanabilir.
