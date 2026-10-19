# Faz 16 — Proje listesi ve ikon kontrolleri düzeltmesi

Başlangıç: `b52a585dc8c24af2ebc36102a8eac21f79c78434`, `d243-v2-handoff`, temiz ağaç.
Yalnız `.venv314/Scripts/python.exe` (Python 3.14.8) kullanıldı. Baseline:
1342 passed, 44.34 s; sandbox pytest cache yazma uyarısı vardı.
Kullanıcı önceki startup blocker düzeltmesinden sonra gerçek Windows açılışını doğruladı.

## Kök neden ve düzeltme

Repository/service yenilemesi ve Treeview insert akışı zaten vardı. Aktif proje
özeti aynı sidebar'da sınırsız büyüyen bir grid satırıydı; kalan yüksekliği alan
proje listesi aktif proje sonrasında sıkışabiliyordu. Etiket/değerler ayrıca aynı
grid hücresini paylaşıyordu. Arama filtresi yeni projeyi gizleyebiliyor; yenileme
ise yeni aktif proje yerine eski satır seçimini geri getiriyordu.

- Liste satırında 120 px minimum korundu. Düğmeler ve özet 200 px yüksekliğinde,
  geometry propagation kapalı, bağımsız kaydırılabilir alt alana taşındı.
  Özet etiket/değerleri ayrı satırlarda; uzun açıklama/notlar kesilmeden korunur.
- Başarılı aktivasyonda gizleyen filtre temizlenir; metadata tekrar okunur,
  liste/empty-state görünürlüğü belirlenir, aktif satır seçilir, focus/see uygulanır.
  Normal refresh geçerli seçimi korur; silinen seçim yerine aktif satıra döner.
  Seçim geri yükleme proje yüklemez veya hesap çalıştırmaz. Widget yeniden yaratılmaz.
- Üst ikon isteği 72→79 px (+%9.72), sidebar 36→40 px (+%11.11).
  Gerçek Yeni asset alfa sınırında görünür çizim yaklaşık 65→72 ve 33→36 px.
  Header alanı 86 px kaldı; sidebar minimumu 48→52 px. Ölçülen 10 px metin
  aralığı, aspect-safe loader, mapping ve silüet güvenliği değişmedi.
- Normal header dış kenarlığı lacivert zeminle, sidebar dış yüzeyi panelle birleşir.
  Hover/pressed/disabled/focus paletleri ve semantik metin renkleri korunur.
  PNG içindeki onaylı çerçeve çizimi kırpılmadı; kaldırılan, ek çizilen dış kutudur.
- Compact/status/Formula boyutları korunur. Rounded button API değişmedi.
  Watermark, FormulaStep/FV, mühendislik, DB, history, Context ve Library değişmedi.

## Otomatik ve görsel doğrulama

15 yeni vaka: başlangıç empty-state, ilk/ikinci proje, normal switch/open/refresh,
tek/son proje silme, boş durumdan yeniden oluşturma, filtreli yeni proje, gerçek
factory ile header/sidebar constructor'ları, alfa/geometri ve uzun proje özeti.
Mevcut MainWindow constructor testi footer sınırını ve liste minimumunu da denetler.
Önceki startup constructor/imza testleri aktiftir. Odaklı koşu: **42 passed in 4.89s**.

Whole/hydraulic/legacy sayısal freeze ve orijinal Pipe V2 12, Transfer design 36,
empirical 36 vaka birebir eşittir. Son tam suite sonucu aşağıda kayıtlıdır.
İkon/yerleşim sözleşme testleri yalnız onaylı yeni boyut/parent beklentilerine
güncellendi; test veya regresyon kapsamı kaldırılmadı.

İzole LOCALAPPDATA profiliyle gerçek main.py denendi; Tk() usable init.tcl
bulamadığından **BLOCKED_ENVIRONMENT**. Tk kurulumu değiştirilmedi. Gerçek liste
geometrisi ve görsel sadeleşme **PENDING_MANUAL_ACCEPTANCE**; headless testler görsel PASS değildir.

## Manuel Windows kontrol listesi

Depo dizininde çalıştırın:

```powershell
& 'C:\Users\Özberk\Documents\ysh\.venv314\Scripts\python.exe' main.py
```

1. Uygulama açılır.
2. Mevcut projeler görünür; boş DB'de doğru empty-state vardır.
3. Yeni proje oluşturulur.
4. Yeni proje hemen listede görünür ve seçilir.
5. İkinci proje ilkini gizlemeden görünür.
6. Proje değiştirme/açma listeyi gizlemez; uzun özet alt alanda kaydırılabilir.
7. Yenile listeyi ve geçerli seçimi korur.
8. Silme sonrası kalan liste, son silmede empty-state, yeniden oluşturmada liste görünür.
9. Üst ikonlar yaklaşık %10 büyüktür.
10. Sidebar ikonları yaklaşık %10 büyüktür.
11. İkonlarda kesilme/esneme yoktur.
12. İkon/metin çakışması yoktur.
13. Header ek dış kutuları belirgin biçimde azalmıştır.
14. Sol proje düğmelerinin ek dış kutuları azalmıştır; etiketler okunur.
15. Hover/pressed/disabled/focus durumları hâlâ anlaşılırdır.
16. D243 branding korunur.
17. Startup traceback yoktur.
18. Uygulama normal kapanır; 1200×700 ve normal boyutta liste/alt alan erişilir.

Faz 17, watermark/layout veya Formula View yeniden tasarımı başlatılmadı.

Son tam suite: **1357 passed in 58.85s**, 0 failed, uyarı yok. Yeni skip/xfail yok.
Git diff kontrolü temiz. Otomatik kabul PASS; görsel Windows kabulü bekliyor.
