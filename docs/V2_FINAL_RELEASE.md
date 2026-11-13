# D243 V2 Final — Release ve Devir Özeti

Kabul kaydı: **2026-11-13**. Bu kayıt mevcut Windows ortamındaki doğrulanmış
release/smoke kapsamını anlatır; yeni test veya build koşusu değildir.

| Alan | Kabul edilen değer |
| --- | --- |
| Version | **D243 V2 Final** |
| Repository / branch | `C:\Users\Özberk\Documents\ysh` / `d243-v2-handoff` |
| Açıklamalı tag | **D243-V2-FINAL**, origin'de doğrulandı |
| Kod/test baseline | `c9c8dfe8096a128302867d2ece630d9ebb3b5dd7` |
| Regression | **2080 passed, 0 failed**; **1327.19 s (22:07)** |
| Packaging | **PyInstaller 6.22.3 onedir**, mevcut `build/ysh.spec` |
| Windows ZIP | `dist/D243_V2_Windows_x64.zip` |
| EXE | `dist/D243/D243.exe` — yanında tam `_internal` klasörü gerekir |
| Startup | **5.76 seconds**, doğrulanmış ortamda tek normal packaged launch |
| Status | **RELEASE_READY** |

Release etiketi kod/test baseline'ında sabittir. Bu belgenin dokümantasyon
commit'i release etiketinin taşınması veya yeni mühendislik sürümü anlamına gelmez.
Branch release sırasında GitHub ile senkrondu; etiket push ve peeled commit'i
ayrıca origin üzerinden doğrulandı.

## Windows doğrulama kapsamı

Fuel/Boru ve Fire/Köpük/Hazen-Williams sayfaları, hesap düğmeleri ve sonuç
panelleri; Formula View, History, geçerli sonuçta PDF eylemi; proje oluşturma,
kaydetme, yeniden açma; Library ve normal kapanış **PASS**.
Sidebar, logo/filigran ve sağ üst gemi **PASS**. Görsel/etkileşimli smoke,
ekran yakalama zaman aşımı nedeniyle kullanıcı destekli doğrulandı. Temiz makine,
Python kurulu olmayan makine ve her DPI kombinasyonu için yeni kabul iddiası yoktur.
PDF eylemi erişimi doğrulanmıştır; bu smoke bütün PDF sayfalarının baskı incelemesi
yerine geçmez. Paket unsigned durumdadır.

Tek normal açılış 5.7648433 s ölçüldü. İzole LOCALAPPDATA profilinde
`YSH/data/projects.db` ve `libraries.db` oluştu; ikisinde SQLite integrity `ok`,
runtime logunda hata yoktu. Geliştirme DB'leri kullanılmadı. Paket 58 resource
dosyasını kaynaklarıyla birebir içeriyor; TR/EN, Tcl/Tk 9.0.4 script/DLL,
SQLite, TkAgg/Matplotlib ve ReportLab bileşenleri denetlendi.

- EXE: **11,234,865 bytes**.
- Onedir payload: **171,315,022 bytes**.
- ZIP: **113,557,673 bytes**, **1440 entries**.
- ZIP SHA256: `83f9bcfceb9a6edf3c7aa1da329ab86ade4b4d5452c579d7efa5ff67c574cc99`.
- Paket/ZIP içinde kullanıcı DB'si veya referans Excel yoktur.
- Build logunda fatal hata/uyarı yok; analiz dosyasındaki platform-conditional,
  opsiyonel bağımlılık ve statik export notları smoke kapsamında değerlendirildi.

Build, wrapper'ın tam pytest adımı tekrarlanmadan, mevcut spec'in aşağıdaki
komutuyla yapılmıştır. Build sürecinde mevcut, DLL'lerle eşleşen standalone
Tcl/Tk 9.0.4 script dizinleri `TCL_LIBRARY` / `TK_LIBRARY` olarak verilmiştir;
release runtime'ı kendi bundled dizinlerini kullanır. Son kabulde eski optional
package probe çalıştırıldığı iddia edilmez.

```powershell
& 'C:\Users\Özberk\Documents\ysh\.venv314\Scripts\python.exe' -m PyInstaller .\build\ysh.spec --noconfirm --clean --workpath .\build\pyinstaller --distpath .\dist
```

## Bilerek açık kalan mühendislik konuları

- **Nozzle:** formül/kaynak **BLOCKED / SOURCE_REQUIRED**.
- **Seawater hydraulic method/source applicability:** **BLOCKED / SOURCE_REQUIRED**.
- Kaynak bağımlı, doğrulanmış üretim verisi bulunmayan TL A/B, CuNi sıcaklık
  tablosu, manufacturing tolerance ve minimum-wall kuralları varsayımla doldurulmaz.

Bunlar ürün hatası veya rastgele defaultla giderilecek konular değildir.
Kaynak ve uygulanabilirlik kararı olmadan genişletilmez. Kabul edilmiş tanım
olmadan qallow/qmüs kullanılmaz.

## Devir bağlantıları ve referans dosyası

[Kullanıcı kılavuzu](../README.md) ·
[Geliştirici handoff'u](../YSH/docs/AI_HANDOVER.md) ·
[Mimari](../ARCHITECTURE.md) · [Paketleme](../build/README_BUILD.md).
Eski faz belgelerindeki test sayıları ve bekleyen kabuller tarihsel kayıtlardır.

`docs/references/Yangın Söndürme.xlsx`: **approved untracked reference input**;
değişmemiş, untracked ve paket dışında. SHA256:
`BD9AA871454C184AFDB45E14BD0C008818D49701D5CC92E1DE7CA89126159474`.
Kaynak-only dosya production mühendislik verisine dönüştürülmez veya commit edilmez.
