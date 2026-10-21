# D243 V2 — History görsel uyumu

Başlangıç: `d243-v2-handoff`, `95d90baf1213930303cc06e21735562eae7f19cd`, temiz ağaç.
Yalnız `.venv314/Scripts/python.exe`, Python 3.14.8 kullanıldı.
Baseline: **1531 passed, 0 failed** (yalnız pytest cache yazma izni uyarısı).

## Görsel uygulama

History frozen hesap tarayıcısı olarak kalır. Kompakt “Hesap Geçmişi” başlığı,
“Kaydedilmiş mühendislik hesapları” alt metni, yüklenmiş kayıtlar üzerinde arama
ve modül seçici eklendi. Tarih/ek filtre repository sorgusu eklenmedi. Filtreleri
boşaltmak için arama temizlenir ve Tüm modüller seçilir; yeni veri işlemi yoktur.

Eski dikey tablo/büyük inline açıklama yerine solda kayıt listesi, sağda bağımsız
kaydırılan seçili kayıt özeti vardır. Yaklaşık %55/%45 pane oranı yeniden
boyutlandırmada uygulanır; aynı boyutta elle sash ayarı korunur. Formül/PDF
bağlamsal eylemleri sabit alt satırda erişilebilir kalır.

`ui/theme/history_visuals.py` yalnız History-prefiksli stilleri açık pencere
kurulumunda kaydeder. Master tipografi, beyaz yüzey, ince sınır, 4/8/12/16 px
boşluklar ve mevcut ikon/ƒx ailesi korunur. Yeni görsel/ikon paketi yoktur.
Global History vurgu tonu lacivert + muted slate/cyan `#526F86` / `#EDF4F8`.
Modül kimlikleri kayıtta ve seçili detay başlığında korunur:

| Modül | Vurgu |
| --- | --- |
| Boru | `#0D9488` |
| Transfer | `#2563EB` |
| Basma | `#6366F1` |
| Emme/ENPY | `#EA7C32` |

Tablo 32 px satırlar, hafif zebra, açık seçili zemin ve kaydedilmiş ana sonuç
kullanır. Modül hücresi bilinen kayıtlı hesap/mod adını da içerir; Transfer Tasarım
ve Ampirik birbirinden ayrılır. Sistem/devre adları frozen context'ten gelir.
Gereken dar alanlarda yatay tablo kaydırması vardır.

Mevcut “modüldeki son kayıt / tarihsel kayıt” etiketleri kayıt sırasını anlatmaya
devam eder. Bunlar uygunluk sonucu sayılmaz. Uygunluk metni yalnız snapshot'ta
kaydedilmiş kontrol statülerinden alınır; yoksa — / kaydedilmemiş açıklaması vardır.

Seçili detayda:

- Modül/mod başlığı ve “Geçmiş Kayıt · Salt Okunur” şeridi.
- Yalnız kayıtlı özetten ana sonuç ve destekleyici sonuçlar.
- Frozen sistem/devre/akışkan; mevcutsa frozen boru mode/status/revision.
- Kayıtlı kontroller, findings ve eski metin/dict uyarılar; yeni kural değerlendirmesi yoktur.
- Kaynak/doğrulama ve override bilgisi ikincil disclosure; zengin açıklama Formula View'dadır.
- Tarih, kısa kayıt kimliği ve model sürümü; tam ID/özgün veri mevcut ham ayrıntıdadır.

Ana sonuç için sadece kayıtlı summary içinden modüle uygun sembol seçilir (s/D,
Qgerekli/Qpump, Hs, ENPYm/he); bulunmazsa mevcut ilk kayıtlı özet, hiç yoksa —.
Yeni sonuç hesaplanmaz. Null/eksik optional alanlarda placeholder kullanılır.
Timestamp'larda önceki frozen-record local dönüşümü korunur; gösterim
`gg.aa.yyyy · ss:dd:ss ±offset` biçimindedir. Legacy kayıtta saklı saat/offset
korunur; tarih/saat değeri değiştirilmez.

## Frozen Formula View / PDF

Formula View mimarisi değiştirilmedi. History'deki mevcut panel, aynı frozen
`step_provider=lambda:snapshot.formula_steps`, module_key ve historical bayrağıyla
mevcut ayrı pencere API'sini kullanır. Artık seçimde otomatik inline açıklama
çizilmez; kullanıcı Formülü Göster eylemine basar. Bu, dar detay alanını ve lazy
çizimi koruyan bir History sunum değişikliğidir.

PDF düğmesi doğrudan seçili CalculationSnapshot'ı mevcut `save_snapshot_pdf`
fonksiyonuna verir. Native save dialog, rapor modeli ve PDF üretim mimarisi aynıdır.
Edit/recalculate/delete/save/overwrite eylemi eklenmedi.

CalculationSnapshot, serialization, schema, DB/migration, repository/service,
Library, ana hesap sayfaları, FormulaStep ve mühendislik hesapları değiştirilmedi.
Yeni TL verisi, marj, eşik, qallow/qmüs veya watermark eklenmedi. Canlı Library,
proje adı veya güncel boru revizyonu sorgulanıp geçmişe uygulanmaz.

## Lazy davranış ve performans

Yalnız açık projenin mevcut History servisi explicit refresh ile sorgulanır.
Liste için FormulaStep dataclass'ları veya Formula View paneli decode/çizilmez.
Detached satır özetleri arama/filtre süresince cache edilir; refresh/dil değişimi
cache'i temizler. Yalnız seçili detay çizilir. Formula View ve ham JSON metin
kontrolü açık kullanıcı eylemiyle oluşturulur. PDF ön üretilmez. Polling yoktur.

Gerçek Tk'de minimal frozen kayıt setleri:

| Satır | Pencere açılışı + liste çizimi |
| --- | --- |
| 100 | 0,812 s |
| 500 | 0,864 s |
| 1000 | 0,937 s |

1000 detay paneli veya Formula View oluşturulmadı. Bu ölçüm minimal fixture içindir;
büyük/çok adımlı üretim kayıtları için aynı süre iddia edilmez.

Aynı beş kayıt ve 1366×768 boyutuyla ayrı süreç karşılaştırması:

| Ölçüm | Başlangıç | Yeni |
| --- | --- | --- |
| İlk açılış | 0,1059 s | 0,1916 s |
| İlk kayıt seçimi | 0,4171 s | 0,2099 s |

İlk açılışta yaklaşık **+86 ms** ek maliyet gözlendi; kayıt seçimi daha kısa ölçüldü.
İstatistiksel hızlanma veya sıfır gerileme iddiası yoktur. Uygulama içi smoke
History açılışı 0,835 s ölçüldü. Başlangıçta History veya PDF/Formula asset yükleme
yolu eklenmedi.

## Doğrulama

21 yeni History testi: beş modül/yöntem, snapshot byte eşitliği, hesaplayıcı/canlı
Library çağrılarını engelleme, frozen Formula/PDF provider, context ve linked boru
revizyonu, minimal snapshot, stored uyarı/statü, TR denylist, timestamp, boş/filtre
sonucu ve 100/500/1000 satırda lazy/cache davranışı. Eski otomatik inline History
beklentisi açık Formula eylemine güncellendi; frozen provider/historical güvencesi
korundu. Diğer testler silinmedi veya gevşetilmedi.

- History odaklı: **21 passed**.
- İlgili Snapshot / Formula / PDF / Main shell / master / Library regresyonu: **138 passed**.
- Tam paket: **1552 passed, 0 failed**.
- Runtime: beş hesap türü + eski/minimal + incomplete legacy kayıt PASS.
- Kaynak disclosure, sonuç, Formula aç/kapat ve beş tarihsel PDF üretimi PASS.
- Arama/modül filtresi/temizleme PASS.
- Hesaplayıcılar ve Library factory hata fırlatacak şekilde bloke iken historical
  inceleme/Formula/PDF geçti; immutable snapshot JSON'u değişmedi.
- Hesap modülüne dönüş, yeni Boru hesabı, live Formula View, Library ve normal kapanış PASS.

| History boyutu | Sonuç |
| --- | --- |
| 1000×650 | PASS |
| 1200×700 | PASS |
| 1366×768 | PASS |
| 1600×900 | PASS |
| 1700×1000 | PASS |

Boyutlar gerçekten oluşturuldu; test maxsize sınırı yalnız fixture'da artırıldı.
Pane sınırları, detay viewport'u, kaydırma ve sabit eylemler doğrulandı. Üretim
pencere minimum sınırı değiştirilmedi. Tüm yazmalı testler yalıtılmış profil/DB'de
sentetik veriyle yapıldı; kullanıcının normal geçmişi değişmedi.

## Manuel görsel kabul

**PENDING_MANUAL_ACCEPTANCE.** Geometri/davranış testleri insanın görsel kabulünün
yerine geçmez. Release EXE/ZIP yeniden üretilmedi; kaynak uygulamadaki History'yi
inceleyin.

1. History D243 ailesine ait görünüyor.
2. Liste temiz.
3. Modül renkleri taramayı kolaylaştırıyor.
4. Tarih/saat okunaklı.
5. Ana sonuç kolay fark ediliyor.
6. Seçili kayıt belirgin.
7. Detay paneli kalabalık değil.
8. Geçmiş Kayıt / Salt Okunur açık.
9. Kayıt kimliği ikincil.
10. Provenance ikincil.
11. Uyarılar ve statü okunaklı.
12. Formül eylemi kolay bulunuyor.
13. PDF eylemi kolay bulunuyor.
14. Düzenleme/yeniden hesaplama çağrışımı yok.
15. Boru kaydı doğru görünüyor.
16. Transfer Tasarım doğru görünüyor.
17. Transfer Ampirik doğru görünüyor.
18. Basma doğru görünüyor.
19. Emme/ENPY doğru görünüyor.
20. Boş durum temiz.
21. 1000×650 kullanılabilir.
22. 1700×1000 dengeli.
23. Watermark yok.
24. Kazara İngilizce chrome yok.
25. Sayısal sonuçlar aynı.
26. Traceback yok.

Burada duruldu. Önerilen sonraki ayrı faz:
**D243 V2 — Yangın Söndürme Modülü Teknik Analiz ve Mimari Tasarım**.
Bu faza, yeni sekmeye/veriye veya workbook analizine otomatik başlanmadı.
