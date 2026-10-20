# D243 V2 — Library görsel uyumu

Başlangıç: `d243-v2-handoff`, `b2fa3dc92a5522d1384f29c9efb32a20b843cf58`, temiz ağaç.
Yalnız `.venv314/Scripts/python.exe`, Python 3.14.8 kullanıldı.
Baseline: **1506 passed, 0 failed** (yalnız pytest cache yazma izni uyarısı).

## Görsel uygulama

Kütüphaneler başlığı ve “Mühendislik verileri ve referans kaynakları” alt metniyle
kompakt bir üst alan eklendi. Library global kimliği lacivert ve kontrollü cyan
`#0E7490`, açık seçili yüzey `#ECF7FA` kullanır; modül renkleri Library'ye atanmaz.

`ui/theme/library_visuals.py` yalnız Library-prefiksli stilleri açık Library
kurulumunda kaydeder. Master beyaz yüzey, ince sınır, Segoe UI, giriş padding/focus
geometrisi ve 4/8/12/16 px boşluk ritmi yeniden kullanılır. Global tema, modül
sayfaları ve Formula View stilleri değiştirilmedi. Yeni ikon/görsel paketi yoktur.

Üç kolon korunur: kategori, kayıt tablosu, seçili kayıt detay/editörü. Ağırlıklar
2:4:3 (yaklaşık %22/%44/%33); pencere boyutlandırıldığında uygulanır, aynı boyutta
elle yapılan sash ayarı korunur. Dar görünümde nav/tablo/detay için okunabilir
asgari alan bırakılır. Kategoriler, tablo ve sağ detay ayrı kaydırılır.

- Sekiz grup ve 17 kategori, mevcut adları/kimlikleriyle korunur.
- Arama daima görünür; mevcut gelişmiş filtreler açılır/kapanır. Arama/filtre
  sorguları değişmedi; yeni reset veya filtre davranışı eklenmedi.
- Ekle ve editörde Kaydet ana eylemdir; Düzenle/İptal/Yenile ikincildir. Mevcut
  disabled/readonly koşulları ve callbackler aynıdır. Genel hard delete eklenmedi.
- Tablo: 32 px satırlar, açık nötr başlık, hafif zebra ve açık cyan seçili satır.
  Ad/değer/sahiplik/aktif durum korunur; mevcut kayıtta bulunan doğrulama durumu
  ayrı metin kolonu olarak gösterilir. Bu kolon bağlı kaynaklara satır başına
  sorgu yapmaz; eksik status doğrulanmış sayılmaz.
- Mevcut filtrelenmiş kayıt sayısı kompakt gösterilir. Boş arama/filtre sonucu için
  ayrı Türkçe açıklama vardır. Yeni istatistik veya veri yüklemesi eklenmedi.
- Sağ panel: temel/mühendislik/sahiplik/doğrulama grupları; kaynak, ilişkiler ve
  teknik ayrıntılar ikincil disclosure alanlarıdır. Null/boş metadata gizlenir;
  sayısal 0 ve False korunur. Kaynak doğrulama özeti renkli, tam metadata açılabilir.
- Salt okunur durum metinle ve sakin sahiplik şeridiyle görünür; provenance
  incelemesi açık kalır. Gerçek enum durumları yeşil/amber/mavi/muted kırmızıyla
  sunulur; yeni doğrulama yorumu üretilmez.
- Editör başlığı “Düzenleme Modu”/“Yeni Kayıt”; alanlar aynı allowlist ile tek
  kolon label/control düzenine alındı. Gruplar tekrarlanmaz, ham hassasiyet korunur.
- Detay metni yalnız yerel viewport'a göre sarılır; veri tekrar okunmaz. Boş
  native wraplength seçeneği güvenle ele alınır. Polling veya animasyon eklenmedi.

## Freeze

LibraryController, servisler, repository'ler, DB şeması/migration, mühendislik
verisi, provenance/ownership politikaları, TL verisi, hesaplar, FormulaStep,
snapshot/history semantiği ve PDF değiştirilmedi. Malzeme sıcaklık tablosuna
interpolasyon, CuNi üretim verisi veya yeni kategori eklenmedi.

Başlangıç commit'i ile AST karşılaştırmasında 15 işleyici birebir aynı:
`_capture_draft`, `_editor_system_changed`, `_choose_group`, `_choose_category`,
`_choose_parent`, `_select_record`, `_new`, `_edit`, `_begin`, `_save`, `_cancel`,
`_reload`, `_close`, `_reference_choices`, `_choose_navigation`.

Yalnız tablo sunumu, detay/editör çizimi ve pencere geometrisi değişti. Factory,
User, Reference ve application sahipliklerinin mevcut Türkçe etiketleri korunur.
Watermark yoktur. Main header/sidebar, History, Formula View ve ana modüller
bu görevde yeniden tasarlanmadı.

## Doğrulama

25 yeni test: scope/tokenlar, pane oranları, boş metadata/0/False, gerçek
verification durumu, tablo arama/filtre/empty/count, satır başına kaynak sorgusu
yapılmaması, editör stili/koruma, TR denylist, alan allowlist/gruplama ve boş
native wraplength. Mevcut testler silinmedi veya gevşetilmedi.

- Odaklı Library + master/Formula regresyonu: **150 passed**.
- Tam paket: **1531 passed, 0 failed**, 62,52 s.
- İlk açılışta yalnız systems kategorisi sorgulandı: lazy davranış PASS.
- Gerçek Tk'de tüm 8 grup/17 kategori, seçili kayıt detayları, provenance ve
  ilişkiler PASS. Arama, filtreler, boş durum ve kayıt sayısı PASS.
- Kontrollü sentetik kullanıcı kaydı: Düzenle → İptal yazmadı; Düzenle → Kaydet
  yalnız izinli değişikliği yazdı. Korunan boru ölçüsü salt okunur kaldı.
- Library kapat/yeniden aç ve normal uygulama kapanışı PASS.
- Dört ana hesap sayfası, Formula View, snapshot PDF ve proje geçişi smoke PASS.

| Library boyutu | Sonuç |
| --- | --- |
| 1100×700 | PASS — üç panel, detail/editor ve eylemler erişilebilir |
| 1366×768 | PASS |
| 1600×900 | PASS |
| 1700×1000 | PASS |

Boyutlar testte gerçekten oluşturuldu; maxsize yalnız fixture'da artırıldı.
Üretim pencere sınırları aynı kaldı. Pane sınırları, detay yatay erişimi, scrollbar
ve sabit alt eylemler doğrulandı. Son final Library runtime açılışı 0,777 saniye.

Aynı sentetik veri ve 1366×768 boyutuyla ayrı süreç karşılaştırmasında başlangıç
Library 0,2264 s, yeni Library 0,3041 s: **+0,0777 s**. Küçük bir ilk açılış ek
maliyeti gözlendi; hızlanma/hiç gerileme yok iddiası yapılmaz. Açılış responsive
kalır; eager veri/asset yükleme eklenmedi ve uygulama başlangıç yolu değişmedi.

Tüm yazmalı kontroller yalıtılmış LOCALAPPDATA / test DB üzerinde yapıldı.
Sentetik veriler üretim seed'i değildir; normal kullanıcı Library verisi değişmedi.

## Manuel görsel kabul

**PENDING_MANUAL_ACCEPTANCE.** Geometri ve davranış testleri insanın görsel
kabulünün yerine geçmez. Release EXE/ZIP üretilmedi; kaynak uygulamadaki Library'yi
inceleyin.

1. Library D243 ailesine ait görünüyor.
2. Kategori navigasyonu kolay taranıyor.
3. Sekiz grup kalabalık hissettirmiyor.
4. Arama kolay bulunuyor.
5. Filtreler baskın değil.
6. Tablo daha temiz.
7. Seçili satır belirgin.
8. Sağ detay okunaklı.
9. Sahiplik anlaşılır.
10. Salt okunur durum açık.
11. Doğrulama durumu açık.
12. Provenance baskın değil.
13. Düzenleme modu anlaşılır.
14. Düğmeler D243 ile uyumlu.
15. Renkler kontrollü.
16. Kazara İngilizce chrome yok.
17. 1100×700 kullanılabilir.
18. 1700×1000 dengeli.
19. Semantik davranış aynı.
20. Traceback yok.

Burada duruldu. Sonraki ayrı görsel görev için History önerilir; otomatik olarak
başlatılmadı. İlk açılışta ölçülen yaklaşık 78 ms ek maliyet de kabul incelemesine
sunulur.
