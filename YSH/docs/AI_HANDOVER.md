# D243 V2 Final — Geliştirici Handoff'u

## Sabit release referansı

- Ürün: **D243 — Boru ve Tulumba Boyutlandırma Programı**.
- Repository: `C:\Users\Özberk\Documents\ysh`; branch: `d243-v2-handoff`.
- Açıklamalı release etiketi: **D243-V2-FINAL**, origin'e gönderildi ve doğrulandı.
- Güvenilir kod/test commit'i: `c9c8dfe8096a128302867d2ece630d9ebb3b5dd7`.
- Tam regresyon: **2080 passed, 0 failed**, **1327.19 s (22:07)**.
- Windows PyInstaller paketi: **RELEASE_READY**; tek normal açılış **5.76 s**.

Bu belge eski 96/116 testlik handoff'un yerini alır. Etiket mevcut release
commit'inde kalır; bu dokümantasyon commit'i etiketi veya güvenilir
mühendislik baseline'ını değiştirmez. Test/packaging sonuçları önceki
kabul koşularıdır; dokümantasyon görevi için yeniden pytest çalıştırılmamıştır.
[Release kaydı](../../docs/V2_FINAL_RELEASE.md) · [Kullanıcı kılavuzu](../../README.md).

## Ortam ve çalıştırma

Bu checkout için yalnız **Python 3.14.8** ortamını kullanın:

```powershell
Set-Location -LiteralPath 'C:\Users\Özberk\Documents\ysh'
& 'C:\Users\Özberk\Documents\ysh\.venv314\Scripts\python.exe' main.py
```

Test komutu gerektiğinde aynı interpreter ile `-m pytest -q` olur. Eski `.venv`
ve sistem Python 3.15 kullanılmaz. Tam regresyon her dokümantasyon/görsel görevde
tekrar edilmez; görev kapsamı ve son kabul kaydı esas alınır.

## Mimari ve bağımlılık sınırları

| Katman | Konum ve sorumluluk |
| --- | --- |
| Başlatma / bileşim | `main.py`, `YSH/app.py`: servisler, depolar, yollar ve Tk yaşam döngüsü. |
| UI | `YSH/ui`: girdiler, locale parsing sunumu, gezinme, görünürlük/uyarılar; hesap veya SQL kaynağı değildir. |
| Uygulama servisleri / workflow | `YSH/services`: domain çağrısını koordine eder; kaynak seçimi, bağlantı, context, snapshot ve proje akışlarını yönetir. |
| Domain | `YSH/engineering`: tipli girdiler/sonuçlar, birimler, doğrulama, saf hesaplar, kaynak/selection/snapshot sözleşmeleri. `YSH/core` mevcut/legacy modelleri korur. |
| Kalıcılık | `YSH/repositories` → `YSH/database`: sorgular, işlemler ve mevcut migration'lar; domain veya UI doğrudan SQL kullanmaz. |
| Açıklama / çıktı | `YSH/engineering/formula`, `YSH/reporting`: önceden hesaplanmış/frozen veriyi açıklar veya raporlar; yeniden hesap yapmaz. |

Akış: **UI → servis/workflow → saf domain**; veri gerektiğinde servis
**repository → SQLite** sınırını kullanır. Domain Tkinter, SQLite ve güncel
Library erişiminden bağımsızdır. Hesaplar FormulaStep üreticisinde, UI callback'inde
ve PDF renderer'ında tekrar uygulanmaz. Kullanıcı sunumu için yuvarlama, saklanan
sayısal hassasiyeti değiştirmez. [Mimari](../../ARCHITECTURE.md).

## System Family ve System Profile

Sol kenardaki tek System Family seçicisi `fuel` / `fire` gezinme ailesini seçer;
proje gezinme tercihleri son kullanılan modülü aile bazında saklar. Mühendislik
System Profile / Devre / Akışkan ise ayrı `SystemContext` bilgisidir. Aile,
Library uygulanabilirlik metni ve HW su servisi birbirinin yerine geçmez.

Tanımsız context sayıdan tahmin edilmez. `FUEL`, `FRESH_WATER`, `OIL` uygulama
fallback kimlikleri üretim standart/katsayı seed'i veya otomatik DB foreign key'i
sayılmaz. Context seçimi yoğunluk, viskozite, c, gerilme veya C katsayısını
kendiliğinden doldurmaz. Modül kullanılabilirliği ürün kapsamıdır, TL onayı değildir.
[SystemContext ayrıntıları](../services/SYSTEM_CONTEXT.md).

## Modüller ve kritik mühendislik sözleşmeleri

- **Boru Tasarımı:** Çap ve et/bükme aşamaları ayrıdır. Teorik çap, DN ve gerçek
  iç çap farklıdır; PipeSelection'a gerçek seçilmiş geometri taşınır. Gerçek
  kütüphane adayları dışında ölçü/et yaratılmaz; uygun et bulunmayınca otomatik
  nominal boy büyütülmez. `NO_BEND` b=0 verir; mevcut corrosion c ve bükme
  semantiği korunur. Boyut standardı, malzeme kaynağı ve mühendislik kuralı farklı
  dayanaklardır. [Boru çekirdeği](PIPE_DESIGN_V2_CORE.md).
- **Yakıt Transfer Tulumbası:** DESIGN kapasite/süre hesabı ile EMPIRICAL
  referans-gemi tahmini ayrı girdiler ve sonuçlar kullanır. Mod değiştirmek hesap
  yapmaz. İsteğe bağlı gerçek pompa kapasitesi, gerekli tasarım kapasitesi yerine
  geçirilmez. Ampirik sonuç normatif TL kapasitesi değildir.
  [Transfer sözleşmesi](../engineering/transfer_pump/PHASE10_TRANSFER.md).
- **Basma:** Manuel/Linked boru değerleri, yerel hidrolik girdiler ve lokal
  kayıplar korunur. Kaynak gözlemi otomatik hesap başlatmaz.
- **Emme/ENPY:** Önce hidrolik kayıp, ardından ENPY aşaması. Hidrolik girdi
  değişimi iki aşamayı; yalnız ENPY girdisi değişimi ilgili ENPY sonucunu etkiler.
  İsteğe bağlı NPSHr yokluğu olumlu pompa uygunluk kararı üretmez.
- **Köpük:** Alan, uygulama yoğunluğu, süre ve konsantre oranı açık girdilerdir.
  Ekrandaki yüzde 3, canonical fraction .03'tür. Karışım temeli konsantre/nihai
  çözelti hacim oranıdır; expanded foam hacmi değildir. Örnek 5/30/3 değerleri
  genel üretim veya mevzuat defaultu değildir.
  [Foam workflow](../../docs/fire_phase2_foam_workflow.md).
- **Hazen-Williams:** Hesap kapısı açık `HWService.WATER` ve
  `HWApplicability.WATER_ONLY` ister. CHW, Darcy pürüzlülüğü değildir. Linked
  Q/Di mevcut adapter ve birim dönüşümüyle alınır; teorik çap kullanılmaz.
  Su yöntemi başka akışkana veya deniz suyuna sessizce genişletilmez.
  [HW workflow](../../docs/fire_phase3_hazen_williams_workflow.md).

Basma/Emme ayrıntıları: [Basma](../engineering/head_loss/PHASE8_DISCHARGE.md),
[Emme](../engineering/suction_npsh/PHASE9_SUCTION.md).

## Library, provenance ve kısa durum etiketleri

Library globaldir; gezinmek aktif projenin ailesini veya uygulanan girdisini
kendiliğinden değiştirmez. Fire kaydı parametre, açık context/service,
uygulanabilirlik, kaynak ve revizyon taşır. Eşleşmeyen veya birden çok adaydan
rastgele öneri seçilmez. Yeni veri şeması icat edilmeden mevcut repository
sözleşmeleri kullanılır. [Fire Library](../../docs/fire_phase6_library.md).

| UI durumu | Sözleşme |
| --- | --- |
| Manual / Manuel | Açık kullanıcı girdisi. Öneri bulunmaması override oluşturmaz. |
| Library / Kütüphane | Açıkça uygulanan Library önerisi/kaynak; tek başına VERIFIED değildir. |
| Linked / Bağlı | Kaynak kimliği ve uygulanmış revizyon/değerler ayrı saklanır. |
| Override / Değiştirildi | Kullanılan değer gerçek öneriden farklıdır; mevcut politika gerektiriyorsa gerekçe zorunludur. Hesap used_value kullanır. |
| Stale / Güncel değil | Değişmiş/eksik/kullanılamayan kaynak gözlenmiştir; applied değerler korunur. |

Bu sunum etiketleri `VerificationStatus`, source readiness ve engineering
uygunluk kararlarının yerine geçmez. Doğrulanmış iddia gerçek kaynak, locator ve
uygulanabilirlik gerektirir. Workbook veya serbest metin kendiliğinden VERIFIED
olamaz. UUID ve rule key'ler normal sonuç özetinde değil teknik ayrıntılardadır.

**PipeSelection:** Bağlantı UUID/revizyon/zaman ve gerçek Q/Di snapshot'ı alır.
Gözlem applied snapshot'ı değiştirmez veya hesap yapmaz. **Update**, aynı kaynağın
yeni uygulanmış Q/Di değerlerini açıkça alır; farklı kaynak için yeni link gerekir.
**Keep Current**, eski snapshot'ı tutar ve stale durumunu silmez. Eksik kaynakta
son değerler korunur; rastgele en yeni boru seçilmez. Basma ve Emme applied
state'leri bağımsızdır. [Transfer kontratı](../engineering/pipe_design/PHASE7_TRANSFER.md).

**Fire Library Update** bundan farklıdır: yeni öneri/provenance revizyonunu alır,
fakat used value'yu korur. Yeni öneri ile fark varsa override gerekçesi gerekebilir.
Keep Current eski applied kaydı korur. Yalnız gözlem/refresh mevcut sonucu
ve tarihsel snapshot'ı değiştirmez; açık girdi/link/context değişiklikleri mevcut
workflow'un invalidation kurallarına tabidir.

## Snapshot, Formula View, History ve PDF

Başarılı açık hesap aşaması gerçek kullanılan girdileri, tam hassasiyetli sonucu,
context/provenance ve FormulaStep'leri `CalculationSnapshot` içinde dondurur.
Canonical JSON derin immutability sınırıdır; okuyucu detached kopya alır. Proje
load, girdi düzenleme veya başarısız hesap yeni başarılı snapshot yaratmaz.
Proje açıkken geçmiş proje sahibine aittir; projesiz kayıtlar oturumluk kalır,
sonradan oluşturulan projeye sessizce bağlanmaz.

- Formula View geçerli mevcut sonucun veya seçilmiş tarihsel snapshot'ın kayıtlı
  adımlarını gösterir; hesap motorunu çağırmaz. Sonuç yoksa mevcut sonuç eylemi disabled.
- History mevcut sonuçtan bağımsız açılır; salt okunurdur. Güncel Library veya
  upstream boru sorgusuyla tarihsel sonuç/kaynak yeniden oluşturulmaz.
- Sayfadaki PDF yalnız geçerli/güncel sonuçla eşleşen snapshot üzerinden çalışır;
  stale sonuç güncelmiş gibi export edilmez. History'de eksiksiz eski snapshot'ın
  PDF'si alınabilir; renderer güncel girdilere/Library'ye başvurmaz.

[Snapshot sözleşmesi](../engineering/snapshots/PHASE14_HISTORY.md),
[PDF açıklaması](../../docs/phase18_pdf_reports.md). Eski faz kayıtlarındaki
bekleyen görsel kabul ve test sayıları kendi tarihlerine aittir.

## Kabul edilen UI ve runtime

Tam boy lacivert sol sidebar, D243 logo, turkuaz üst kabuk ve dekoratif sağ üst
gemi korunur. Filigran viewport arka planındadır; sayısal giriş alanları çevre
alanlardan daha solid, boş sonuç alanları geçirgen görünümlüdür. Hesaplanmış
sonuçlar, metin/kontrol/ikon/uyarılar opaktır. Sayısal alanlar ortak compact
ölçülendirme kullanır; sidebar ikon kolonu ve metin başlangıcı sabittir. Hesapla
primary; Formula View / Geçmiş / PDF tek ikincil araç grubudur. Tek aile seçicisi
vardır. TR/EN kaynaklar korunur; mevcut ürün dil politikası varsayılan TR'dir.

Yazılabilir veri `%LOCALAPPDATA%\YSH\data\projects.db` ve `libraries.db`;
log `%LOCALAPPDATA%\YSH\logs\ysh.log`. `ApplicationPaths` frozen kaynakları
`_MEIPASS` altında read-only çözer; kurulum klasörü kullanıcı DB'si değildir.
İç `YSH` paket/dizin adlarını görünür eski marka sanıp yeniden adlandırmayın.

Paketleme: **PyInstaller 6.22.3 onedir**, mevcut `build/ysh.spec`, `main.py` giriş,
D243 ICO ve resources, TR/EN, TkAgg/Matplotlib, ReportLab, Tcl/Tk ve SQLite runtime.
[Build yönergesi](../../build/README_BUILD.md). Tam `D243` klasörü dağıtılır;
yalnız EXE kopyalanmaz. Son Windows smoke izole LOCALAPPDATA kullanmış, normal
kullanıcı DB'lerini kullanmamıştır. Grafik yakalama sınırlaması nedeniyle görsel
ve etkileşimli akışlar kullanıcı destekli doğrulanmıştır; tüm DPI/temiz makine
senaryolarının test edildiği iddia edilmez.

## Açık mühendislik blocker'ları — hata değildir

| Konu | Mevcut güvenli sınır |
| --- | --- |
| Nozzle formül/kaynak | **BLOCKED / SOURCE_REQUIRED**. Cihaza özgü kabul edilmiş bağıntı/kaynak olmadan sonuç veya başarılı snapshot üretilmez. |
| Deniz suyu hidrolik yöntemi / HW uygulanabilirliği | **BLOCKED / SOURCE_REQUIRED**. Water-only izni marine/seawater izni değildir. |
| Türk Loydu kaynak bağımlı kurallar | Steel A/B terimleri, CuNi sıcaklık tablosu, manufacturing tolerance formülü/değeri ve minimum wall gibi kabul edilmiş üretim dayanağı olmayan içerikler yapılandırılmamış/kaynak gerekli kalır. Legacy Rp0.2/B güncel doğrulanmış TL kuralı diye sunulmaz. |

Bunlar varsayımla tamamlanacak eksik kodlar değildir. Kaynak, sürüm/locator,
uygulanabilirlik ve ayrı kabul kararı gerektirir.
[Kaynak kararları](../../docs/fire_fighting_source_decisions.md).

## DO NOT BREAK — sonraki geliştirici için

- Bağlı mühendislik değerlerini sessizce overwrite etmeyin.
- Tarihsel snapshot'ı yeniden hesaplamayın; geçmişi güncel Library ile kurmayın.
- Kaynaksız değeri VERIFIED yapmayın; TL kuralı veya üretim değeri uydurmayın.
- Kabul edilmiş tanım olmadan qallow/qmüs kullanmayın.
- Yinelenen System Family seçicisi eklemeyin.
- Kaldırılan görünür YSH branding'ini veya kabul edilen UI ile çelişen watermark
  davranışını geri getirmeyin.
- Formül, schema, snapshot, History/PDF/Formula View ve provenance sözleşmelerini
  salt görsel/dokümantasyon işi sırasında değiştirmeyin.

`docs/references/Yangın Söndürme.xlsx` **approved untracked reference input**'tur:
read-only analiz girdisi; production data değildir. Değiştirmeyin, taşımayın,
commit'e veya pakete eklemeyin. Kabul edilmiş SHA256:
`BD9AA871454C184AFDB45E14BD0C008818D49701D5CC92E1DE7CA89126159474`.
