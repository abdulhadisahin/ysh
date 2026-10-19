# D243 V2 Faz 18 — Snapshot tabanlı PDF raporları

## Mimari ve kullanım

`CalculationSnapshot → adapt_snapshot → EngineeringReport → render_pdf / export_pdf`.
`reporting.models` yalnız donmuş domain verisi ve Türkçe etiketlerden oluşur.
Model değişmez, JSON olarak serileştirilebilir; sayılar gösterimden önce yuvarlanmaz.
Renderer Tk açmadan çağrılabilir. Hesap motoru, güncel Library, proje deposu veya
UI alanlarından değer okumaz. PDF oluşturmak snapshot içeriğini değiştirmez.

Destek: Boru Tasarımı (çap/et/seçim), Transfer DESIGN, Transfer EMPIRICAL,
Basma hidrolik, Emme hidrolik ve ENPY. Ampirik rapor açıkça referans gemi tahminidir.
PDF eylemi dört modülde formül düğmesinin yanında bulunur. Başarılı hesap kaydı
saklandıktan sonra etkinleşir ve **son kayıt** üzerinden çalışır. Form üzerinde
sonradan yapılan değişiklikler rapora girmez; yeni değerler için normal hesap
akışı kullanılmalıdır. Proje açma/kapatma/değiştirme son kayıt işaretçisini temizler.
Geçmiş penceresindeki eylem sadece seçilmiş, eksiksiz snapshot içindir.
Eksik eski kayıtlar için PDF eylemi sunulmaz. Snapshot yoksa boş rapor oluşturulmaz.

## Belge yapısı

A4 dikey, 18 mm yan/alt ve 17 mm üst kenar boşluğu; lacivert başlıklar,
şampanya çizgiler, beyaz zemin. İlk sayfa onaylı `d243_logo_small.png` içerir.
Altbilgi her sayfada D243, kısa snapshot kimliği ve sayfa numarası gösterir.
Filigran, imza, onay mührü, genel hukuki metin ve gömülü PDF görüntüleyici yoktur.

Bölümler: Rapor Bilgileri; Girdi Verileri; Kullanılan Katsayılar / Seçimler;
Hesap Adımları; Sonuçlar; Uyarılar / Uygunluk; Kaynaklar ve Doğrulama;
Rapor Meta Bilgisi. Kaynak tarihleri, doğrulama durumu, kullanılan/önerilen
katsayılar, override gerekçeleri ve bağlı/manuel boru bilgileri yalnız kayıttan gelir.
Mevcut ValidationIssue uyarıları ve FormulaCheck sonuçları tekrar değerlendirilmez.
Bilinmeyen kaynak doğrulanmış sayılmaz; SOURCE_REQUIRED ve diğer kayıt durumları korunur.

Formüller: onaylı PNG → 300 DPI MathText → gerçek PDF metni.
Temel et kalınlığı ve lokal kayıp için karantinadaki PNG'ler kullanılmaz.
Kabul edilmiş MathText eşleştirmesi `reporting/equations.py` üzerinden GUI ile paylaşılır.
PNG kompozisyonu kırpılmaz, oran ve alfa korunur; yalnız bellek içinde baskı boyutuna
uygun küçültülür. Formül ifadelerinin metin sürümü de PDF içinde aranabilir kalır.
Metinler/tabelalar gerçek PDF metnidir. DejaVu Sans regular/bold ve dağıtım lisansı
`resources/fonts` içine eklenmiştir; sistem fontuna bağımlılık yoktur.

## Dosya ve paketleme

Uygulama bağımlılığı: ReportLab >=4.4,<5 (doğrulanan 4.5.1).
Test bağımlılığı: `report-test` ekstra grubunda pypdf >=6,<7.
Görsel geliştirme kontrolü PyMuPDF ile yapılmıştır; uygulama bunu kullanmaz.
Mevcut spec kaynak klasörünü ve yeni modülleri toplar; ReportLab resmi PyInstaller
hook'ları tarafından bulunur. Paket başlangıç köprüsüne `reporting` eklenmiştir.
`D243_BUILD_PROBE=1` geliştirme probu PDF üretimini ve ana/geçmiş eylemlerini sınar;
probun kendisi son kullanıcı dağıtımına dahil değildir. Son sürüm ZIP yeniden üretilmez.

Yerel Tk kaydet diyaloğu: PDF Dosyası (*.pdf). İptal sessizdir. Oluşturma hataları
Türkçe mesaj gösterir. Dosyalar exclusive-create ile açılır; mevcut dosya varsa
`_1`, `_2` ... eklenir. Başarısız yazım artığı temizlenir, formül geçici dosyası yoktur.
Görünen metindeki mutlak Windows dosya yolları gizlenir; metadata sabit D243 alanlarıdır.

## Sınırlar

Snapshot şeması 1 proje adını saklamaz. Tarihsel doğruluğu korumak için güncel proje
adı sorgulanmaz: varsa donmuş proje UUID'si gösterilir, varsayılan dosya adı
`D243_<kısaSnapshotID>_<Modül>_<YYYYMMDD_HHMMSS>.pdf` olur. Windows yasak karakterleri
temizlenir. Kaydedilmemiş bilgi, eksik kaynak veya eksik revizyon uydurulmaz.
Kaynak/bağlam/birimler kayıt içeriğiyle sınırlıdır. Tek hesap/tek snapshot raporlanır.
Sayfa X kullanılır; toplam sayfa sayısı V1 kapsamına alınmamıştır.
Mühendislik hesapları, sayısal sonuçlar, DB/migration, snapshot ve Library semantiği değişmez.
Çok hesaplı proje kitabı, watermark ve tam formül PNG entegrasyonu ertelenmiştir.

## Manuel Windows kabul kontrolü (kullanıcı onayı bekleniyor)

1. D243'ü açın.
2. Proje açın veya oluşturun.
3. Boru hesabını çalıştırın.
4. Son kayıt PDF eylemiyle rapor oluşturun.
5. PDF'yi açın.
6. Logo ve üstbilgiyi kontrol edin.
7. Türkçe karakterleri kontrol edin.
8. Donmuş proje kimliği/sistem/devre/akışkanı kontrol edin.
9. Girdileri kontrol edin.
10. Katsayıları kontrol edin.
11. Formül bloklarını kontrol edin.
12. Yerine koyma ve sonuçları kontrol edin.
13. Uyarıları kontrol edin.
14. Kaynak ve doğrulama durumlarını kontrol edin.
15. Sayfa geçişlerini kontrol edin.
16. Kırpılmış içerik olmadığını kontrol edin.
17. Geçmiş Boru snapshot'ından PDF oluşturun.
18. Transfer DESIGN ve EMPIRICAL PDF oluşturun.
19. Basma PDF oluşturun.
20. Emme/ENPY PDF oluşturun.
21. Güncel verileri değiştirip geçmiş rapor içeriğinin aynı kaldığını kontrol edin.
22. Varsayılan dosya adı ve çakışmada son ek davranışını kontrol edin.
23. Kaydet diyaloğunu iptal edin; hata çıkmadığını kontrol edin.
24. Uygulamayı normal kapatın.

## Doğrulama kaydı

Başlangıç: `d243-v2-handoff`, `ca4b55235c846f1956f7fd5df3b77b4d527448c2`, temiz ağaç.
Python: yalnız `.venv314/Scripts/python.exe`, 3.14.8. Başlangıç: 1432 passed.
14 yeni PDF testi; mevcut MathText sunum testi ortak eşleştirme dosyasına uyarlandı.
Odaklı snapshot/PDF/formül kontrolleri: 79 passed.
Gerçek Library kaynak/malzeme ve proje adı güncellemelerinden sonra saklı PDF baytları
aynı kalır. Türkçe karakter çıkarımı, tam hassasiyet, A4, metadata, kaynak durumları,
karantina/fallback, Tk'siz üretim, uzun kaynak/tablo bölünmesi, iptal, hatalı yol,
readonly dosya çakışması ve başlık/formül sayfa birlikteliği sınanır.

Geliştirme örnekleri (repoya alınmamıştır):

| Rapor | Süre (sn) | Boyut (bayt) | Sayfa |
| --- | ---: | ---: | ---: |
| Boru | 3,513 (ilk üretim) | 573631 | 5 |
| Transfer DESIGN | 0,279 | 217552 | 2 |
| Transfer EMPIRICAL | 0,383 | 229020 | 2 |
| Basma | 0,795 | 369076 | 4 |
| Emme/ENPY | 0,846 | 448076 | 4 |

Tüm örnekler PNG'ye render edilerek incelendi; başlık/formül ayrılması düzeltildi.
Kaynak Tk smoke ve frozen geliştirme payload smoke: PASS. Kaydet diyaloğu callable'ı
otomatik smoke içinde kontrollü dosya hedefiyle değiştirilir; insanın gerçek Windows
kaydet diyaloğu ve PDF okuyucu kabulü yukarıdaki listeyle ayrıca beklenir.
Son sürüm ZIP hash'i korunmuştur:
`a456e014db80ba19237922eac0a85fb9ceee9bd3398261aea972c436f2544263`.
Genel durum: **PENDING_MANUAL_ACCEPTANCE**.

Son tam koşu: **1446 passed, 0 failed**, 75,63 saniye.
