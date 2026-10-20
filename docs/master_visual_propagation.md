# D243 V2 — Master visual yayılım

Başlangıç: `d243-v2-handoff`, `a0fc6023d81a48bedfe5c7c1ceb7bce0e1f7f80f`, temiz çalışma ağacı.
Yalnız `.venv314/Scripts/python.exe` / Python 3.14.8 kullanıldı.
Baseline: **1477 passed, 0 failed** (pytest cache yazma izni uyarısı; test hatası yok).

## Uygulama ve kapsam

Kabul edilmiş Boru pilotunun beyaz yüzey, ince sınır, ferah boşluk, teal kimlik ve
belirgin sonuç hiyerarşisi korunur. Boru sayfası ve `pipe_pilot.py` değiştirilmedi.

`ui/theme/module_visuals.py` ortak kart, kontrol, başlık, sonuç ve ikincil PDF
stillerini mevcut ttk sistemine ekler. Boru'nun çalışma zemini/sınır tokenları
paylaşılır; eski global uyumluluk renkleri değiştirilmez. Sayfalara yeni ham hex
kodları dağıtılmadı. Mevcut `InputCard`, `ResultCard`, `SectionHeader`, `ResultMetric`
bileşenleri kullanılır; yeni bir UI framework veya görsel bağımlılık eklenmedi.

`ui/widgets/module_visuals.py` yalnız açıkça katılan üç sayfanın mevcut widgetlarını
kurulum sonunda bir kez stiller. Değişkenler, widget kimlikleri, grid yerleşimleri,
callbackler, readonly/disabled durumları korunur. FormulaReferencePanel,
EngineeringWarningPanel ve ResultMetric durum yönetimine girilmez. Yeni polling,
arka plan resmi veya animasyon yoktur.

| Modül | Vurgu | Koyu metin/eylem | Sonuç yüzeyi |
| --- | --- | --- | --- |
| Transfer | `#2563EB` | `#1D4ED8` | `#EFF6FF` |
| Basma | `#6366F1` | `#4338CA` | `#F1F0FF` |
| Emme/ENPY | `#EA7C32` | `#9A3412` | `#FFF4EB` |

Seçili sekme, kart başlığı, odak çizgisi, ana hesap eylemi ve birincil sonuç aynı
modül kimliğini kullanır. Beyaz girişler ve sakin yüzeyler baskındır. Mevcut
uyarı/hata/kritik anlamları korunur. Boş sonuçlar önceki nötr unavailable durumunda kalır.

- Transfer: Tasarım ve Ampirik / Referans Gemi Tahmini seçimi/açıklaması aynıdır.
  Tasarım girdileri/kapasite-süre sonucu; ampirik girdiler/sonuç/referans tablo/grafik
  kendi mevcut alanlarında korunur. Ampirik yönteme TL iddiası eklenmedi.
- Basma: bağlı/manuel kaynak alanı, akış/boru hattı girdileri, lokal kayıp tablosu ve
  Hs sonucu korunur. hf/hL/hhat ve teknik değerler ikincil hiyerarşidedir.
- Emme: kaynak/akış/emme hattı, lokal kayıplar ve statik/basınç ENPY girdileri
  ayrıdır. ENPYm ana sonuç, he ve mevcut ΔENPY/teknik detaylar destekleyicidir.
- Birimler ilgili girdi kontrollerinin sağındaki kolonlara taşındı. Tasarım transfer
  etiketleri ve isteğe bağlı NPSHr etiketi TR/EN kaynaklarına bağlıdır.
- Kaynak durumu kompakt bilgi şeridindedir. Güncelle / Mevcut değeri koru eylemleri
  ve stale/linked/manual anlamları aynıdır; otomatik uygulama eklenmedi.
- Header, sol proje paneli ve System Context bu görevde değiştirilmedi. İkon
  boyutları, tab geometrisi ve proje yaşam döngüsü aynıdır. Watermark yoktur.
- Formül ayrı pencerededir. Yalnız PDF giriş düğmesi eşleşen ikincil stil alır.

Mühendislik, hesaplayıcılar, FormulaStep, snapshot, PDF üretim mimarisi, History,
Library, DB şeması/migration, TL verisi ve qallow değişmedi/eklenmedi.

## Otomatik doğrulama

12 yeni test: ortak renk/kart/kontrol/sonuç/eylem hiyerarşisi; sayfa kapsamı;
TR/EN alan adları; gerçek sunum walker'ının değişken, callback, readonly/disabled
ve dışarıda tutulan bileşenleri koruması; yöntem/aşama ayrımı. Eski sabit palet
beklentileri güncellendi; mevcut testler silinmedi.

Odaklı paket: **339 passed**.
Tam paket: **1489 passed, 0 failed**.

Gerçek Tk smoke testi yalıtılmış LOCALAPPDATA profiliyle yürütüldü. Normal kullanıcı
verisi kullanılmadı. Boru, Transfer tasarım/ampirik, Basma ve Emme+ENPY hesapladı.
Boru sonucu referans hesaplayıcıyla birebir, Transfer 120/3=40 m³/h ve 120/60=2 h,
Basma ve Emme sonuçları doğrudan servis referanslarıyla tam eşit çıktı.
Dört modülde ayrı Formula View ve snapshot PDF üretimi geçti. Proje kaydetme,
başka projeye geçiş ve geri yükleme, History, Library ve normal kapanış geçti.

| Boyut | Boru | Transfer tasarım/ampirik | Basma | Emme/ENPY |
| --- | --- | --- | --- | --- |
| 1200×700 | PASS | PASS | iki kolon, PASS | iki kolon, PASS |
| 1366×768 | PASS | PASS | iki kolon, PASS | iki kolon, PASS |
| 1600×900 | PASS | PASS | geniş, PASS | iki kolon, PASS |
| 1700×1000 | PASS | PASS | geniş, PASS | geniş, PASS |

Pencere boyutları gerçekten oluşturuldu; test root maxsize sınırı yalnız fixture'da
artırıldı. Üretim pencere limitleri değişmedi. Kart sınırları, kart çakışmaları,
çocuk kontrollerin yatay erişimi ve aşağı kaydırmayla Formula/PDF erişimi denetlendi.
Geometri kontrolleri görsel denge için insan onayının yerine geçmez.
Açılış ölçümü son smoke koşusunda **6,383 s**; önceki pilot ölçümü 7,583 s idi.
Bu koşuda gerileme görülmedi; istatistiksel performans iyileşmesi iddiası yoktur.

## Manuel kabul

**PENDING_MANUAL_ACCEPTANCE.** Kaynak uygulamayı onaylı Python ile açarak aşağıdaki
listeyi değerlendirin. Bu görevde yeni release EXE/ZIP üretilmedi; önceki pilot
önizlemesi bu yayılımın güncel görünümünü temsil etmez.

```powershell
Set-Location 'C:\Users\Özberk\Documents\ysh'
& 'C:\Users\Özberk\Documents\ysh\.venv314\Scripts\python.exe' main.py
```

1. Transfer mavi kimliği belirgin.
2. Tasarım/ampirik ayrımı açık.
3. Transfer sonuç kartı açık.
4. Transfer yerleşimi ferah.
5. Transfer karmaşık görünmüyor.
6. Basma indigo kimliği belirgin.
7. Boru/hat/lokal kayıp grupları anlaşılır.
8. Hs sonucu hemen fark ediliyor.
9. Bağlı/manuel durum kolay anlaşılır.
10. Basma karmaşık görünmüyor.
11. Emme turuncu vurgusu dengeli.
12. Emme ve ENPY alanları mantıklı ayrılıyor.
13. ENPY sonucu belirgin.
14. Durum metni okunaklı.
15. Emme karmaşık görünmüyor.
16. Dört modül aynı uygulamaya ait görünüyor.
17. Renkler modülleri aşırı renk kullanımı olmadan ayırıyor.
18. Sol proje paneli tutarlı.
19. Header tutarlı.
20. System Context tutarlı.
21. Düğmeler tutarlı.
22. Sonuç kartları tutarlı.
23. 1200×700 kullanılabilir.
24. 1700×1000 dengeli.
25. Watermark yok.
26. Sayısal sonuçlar değişmedi.
27. Traceback yok.

Bu görev burada durur. Library, Formula View, History veya PDF belgesi görsel
yayılımına başlanmadı. Kullanıcı kabulünden sonra ayrı görevde Formula View giriş
ritmi/görsel uyumu değerlendirilebilir; mühendislik mimarisi korunmalıdır.
