# D243 V2 — Yangın Söndürme Modülü Teknik Analiz ve Mimari Tasarım

Tarih: 2026-10-21. Kapsam: **ANALYSIS / SPECIFICATION ONLY**.
Sonuç: **ANALYSIS_PASS_WITH_SOURCE_BLOCKERS**. Bu belge uygulama izni değildir.
Fire Phase 1 başlamadan kullanıcı onayı gereklidir.

## 1. Başlangıç, sınırlar ve kanıt yöntemi

- Repository: `C:\Users\Özberk\Documents\ysh`.
- Branch: `d243-v2-handoff`.
- Başlangıç HEAD: `dd2df16b0c30a83ba34bef05f31986fc14a2b5d2`.
- Python: yalnızca `.venv314\Scripts\python.exe`, doğrulanan sürüm 3.14.8.
- Baseline: **1552 passed, 0 failed**, 63.68 s. Sandbox nedeniyle pytest cache yazma uyarısı vardı; test hatası yoktu.
- Başlangıçtaki tek değişiklik `?? docs/references/Yangın Söndürme.xlsx` idi.
  Kullanıcı bu dosyayı temiz ağaç kontrolünden açıkça istisna tuttu:
  **approved untracked reference input**. Dosya bu commit'e eklenmez.
- Kaynak: `docs/references/Yangın Söndürme.xlsx`, 6922 bayt.
- SHA-256: `bd9aa871454c184afdb45e14bd0c008818d49701d5cc92e1de7ca89126159474`.
- Dosya salt okunur ZIP/XML olarak incelendi: workbook, worksheet, shared strings,
  styles, relationships ve drawing parçaları. Kaynak dosya kaydedilmedi, taşınmadı,
  silinmedi veya yeniden hesaplatılmadı. Kayıtlı Excel sonuçları bağımsız Python
  aritmetiğiyle karşılaştırıldı. Native Excel hesaplama motoru çalıştırılmadı.
- İnternet araştırması yapılmadı. Workbook ve repository dışından standart alınmadı.
- Yalnızca bu belge eklenir. Production kodu, hesap sekmesi, DB, migration,
  Library seed, snapshot şeması, Formula View, PDF ve mevcut sayılar değişmez.

### Kanıt dili ve durum sözlüğü

**VERIFIED FROM WORKBOOK** hücrenin/formülün dosyada gerçekten bulunduğunu söyler;
standart onayı anlamına gelmez. **DERIVED / INFERRED** açıkça yapılan matematiksel
türetimi/yorumu, **UNRESOLVED** eksik anlamı, **SOURCE REQUIRED** kaynak ihtiyacını,
**ARCHITECTURAL RECOMMENDATION** gelecekte uygulanabilecek tasarımı belirtir.

Her mühendislik bilgisi için şu kaynak sınıfları kullanılır:

| Durum | Anlamı |
|---|---|
| SOURCE_VERIFIED | Yetkili kaynak, sürüm, ilgili madde ve uygulanabilirliği doğrulanmış |
| WORKBOOK_REFERENCE_ONLY | Workbook'ta var; mühendislik otoritesi doğrulanmamış |
| USER_PROJECT_ASSUMPTION | Kullanıcının/projenin açıkça seçtiği girdi; standart varsayılmaz |
| DERIVED_FROM_WORKBOOK | Workbook ilişkilerinden türetilmiş matematik |
| SOURCE_REQUIRED | Formül, birim, uygulanabilirlik veya seçim dayanağı eksik |
| NOT_CONFIGURED | Hesap için gerekli ayar/değer henüz yok |
| OUT_OF_SCOPE | İlk sürümün kapsamı dışında |

MATCH / ROUNDING_ONLY sayısal karşılaştırma sonuçlarıdır, kaynak durumu değildir.
FORMULA_UNVERIFIED ve UNIT_UNCLEAR gibi tanılar kaynak durumuna eklenir.
Bu incelemede hiçbir yangın kuralı **SOURCE_VERIFIED** düzeyine yükseltilmedi.

## 2. Workbook envanteri — VERIFIED FROM WORKBOOK

Tek çalışma sayfası: **Sayfa1**, `state=visible`. Beş hesap grubu ve bir C tablosu var.
XML'de `dimension` öğesi yok. Hücre kayıtlarının kapsadığı alan **A1:M30**,
117 hücre kaydıdır. Bu alan boş ara hücreler de içerir; 117 bağımsız veri değildir.

| Aralık | İçerik |
|---|---|
| A1:F8 | 1. hesap: Köpük Konsantresi Miktarı Hesabı, altı örnek |
| A10:H12 | 2. hesap: Köpük konsantresi Tulumba kapasitesi, bir örnek |
| A14:G17 | 3. hesap (sürtünme kaybı), Hazen-Williams, iki örnek |
| A24:D26 | 4. hesap: nozul bağıntısı ve alan açıklamaları, sayısal örnek yok |
| A28:F30 | 5. hesap: Deniz Suyu Tulumbası, bir örnek |
| L8:M18 | Hazen - Williams C Values; başlıklar ve dokuz referans satırı |

Gizli sayfa/satır/sütun, birleştirilmiş hücre veya named range yok.
Workbook `definedNames` öğesi boş. Excel Table, dış workbook bağlantısı,
yorum veya gömülü resim parçası yok. Worksheet relationship yalnızca boş
`drawing1.xml` kabına gidiyor; burada metin/formül içeren şekil yok.
Sütun genişlikleri tanımlı, gizleme bayrağı yok. Sayısal stiller General
(`numFmtId=0`); özel yuvarlama/ondalık biçimi yok.
Formüller yalnızca çarpma, bölme ve üs işlemleridir; ROUND/CEILING yok.
Ortak formül grupları A3:A8, A16:A17 ve F16:F17'dir. Alt hücre formülleri
Excel shared-formula mekanizmasıyla üst formülün satır kaydırılmış karşılığıdır.

Kaynak kuruluşu, belge adı/sürümü, madde numarası, doğrulama veya uygulanabilirlik
metadatası yok. Dosyanın kendisi kullanıcı mühendislik referansıdır.

## 3. Köpük konsantresi miktarı

**VERIFIED FROM WORKBOOK:** A3 `=C3*D3*E3*F3`; A4:A8 aynı satır örüntüsünde.
C2 `Mahal alanı (m^2)`, D2 `Uygulama Yoğunluğu lt/dk.m^2`,
E2 `uygulama süresi (dk)`, F2 `Köpük uygulama konsantresi`, B3 `lt`.

**DERIVED / INFERRED:** `Vfoam = A × q × t × Cfoam`.
Boyut: m² × L/(min·m²) × min × boyutsuz = L.
`lt/dk.m^2` yazımı uygulama yoğunluğu bağlamında L/(min·m²) olarak yorumlanır;
gelecek UI'da parantezli açık birim kullanılmalıdır.
0.03'ün hacimsel karışım fraksiyonu olması örnekle tutarlıdır; workbook açıkça
`%`, v/v, ürün veya standart tanımı vermiyor. Tasarım onayında karışım temeli teyit edilir.

| Bilgi | Kaynak durumu / gelecek davranış |
|---|---|
| Workbook çarpım formülü | WORKBOOK_REFERENCE_ONLY; yeniden üretimi doğrulandı |
| q=5, t=30, Cfoam=0.03 | WORKBOOK_REFERENCE_ONLY; production varsayılanı olamaz |
| Mahal alanları | WORKBOOK_REFERENCE_ONLY örnekleri; yeni projede USER_PROJECT_ASSUMPTION |
| L→m³: V/1000 | DERIVED_FROM_WORKBOOK birim normalizasyonu; workbook'ta m³ çıktısı yok |
| Qsolution=Aq, Qfoam=AqCfoam, Vsolution=Aqt | DERIVED_FROM_WORKBOOK destek çıktıları; yeni mevzuat gereksinimi değil |
| q/t/Cfoam seçiminin mühendislik dayanağı | SOURCE_REQUIRED |

**ARCHITECTURAL RECOMMENDATION:** temel çıktı Vfoam L, destek çıktı Vfoam m³.
Vsolution ancak “türetilmiş destek sonucu” etiketiyle gösterilebilir. Alanlar ortak
girdi panelinden gelir; hesap yalnızca kullanılan değerleri tüketir.

## 4. Köpük konsantresi tulumba kapasitesi ve yaklaşık değer

**VERIFIED FROM WORKBOOK:** A12 `=C12*D12*E12`, G12 `=A12*0.06`.
C12=1660, D12=5, E12=0.03, A12=249, G12=14.94.
G11 `m^3/saat`. A12 için ayrı L/min birim hücresi yoktur; çarpım biriminden
L/min türetilir. C11 alan etiketi m² içermese de miktar ve deniz suyu gruplarıyla
aynı alan anlamı önerilir; bu semantik açıkça yeni modelde yazılır.

**DERIVED / INFERRED:** `Qfoam=AqCfoam`; m² × L/(min·m²) = L/min.
`1 L/min = 0.001 m³ × 60/h = 0.06 m³/h`.
Formül WORKBOOK_REFERENCE_ONLY; birim dönüşümü DERIVED_FROM_WORKBOOK.

H11 `yaklaşık`, H12 **15 sayısal hardcode**, formül yok.
14.94→15 farkı +0.06 m³/h, hesap değerine göre yaklaşık %0.4016064.
Bu oran **tespit edilen farktır, tasarım marjı değildir**.
Sınıflandırma: **manual approximate value; ENGINEERING_DECISION_REQUIRED /
SOURCE_REQUIRED**. Ekipman seçimi, gösterim yuvarlaması veya marj olduğu
kanıtlanmıyor. Gelecekte 14,94 hesap sonucu korunur. Seçilen kapasite ayrı,
isteğe bağlı kullanıcı alanı ve seçim gerekçesi olur; otomatik 15 uygulanmaz.

## 5. Deniz suyu tulumbası ve ortak köpük modeli

**VERIFIED FROM WORKBOOK:** A30 `=C30*D30*E30`, F30 `=A30*0.06`.
C30=1660, D30=5, E30=**0.97 hardcode**, A30=8051, F30=483.06.
E29 hâlâ `Köpük uygulama konsantresi` yazıyor; su payını tanımlayan doğru bir
etiket değil. E30, E12/F3 ile bağlantılı değil; `=1-E12` formülü yok.
F29 `m^3/saat`. A30 L/min anlamı boyut analizinden türetilir.

As-found denklem `Qwater_candidate=Aq × factor`, factor=0.97:
WORKBOOK_REFERENCE_ONLY. Alan ve yoğunluk aynı anlamdaysa çıktı L/min'dir.
**UNRESOLVED:** 0.97'nin su fraksiyonu olması, E29 etiketinin hatası ve karışım
temeli teyit edilmeli (**FIRE-FOAM-WATER-001 / SOURCE_REQUIRED**).

**DERIVED / INFERRED:** 0.97 = 1−0.03 sayısal olarak doğru. Hacimsel fraksiyon
kabulünde aşağıdaki model tutarlıdır ama workbook bu çapraz bağı kurmuyor:

```
Qsolution = A × q
Qfoam = Qsolution × Cfoam
Qwater = Qsolution × (1 − Cfoam)
Vfoam = Qfoam × t
Qfoam + Qwater = Qsolution
```

Örnek: Qsolution=8300 L/min, Qfoam=249, Qwater=8051.
Bu **WORKBOOK_DERIVED_RELATIONSHIP**, bir SOURCE_VERIFIED_ENGINEERING_RULE değil.
V1'de birleşik türetme ancak bu yorum açıkça onaylandıktan sonra devreye girer.
Onaydan önce bağımsız factor alanını Cfoam'ın türevi gibi göstermemek gerekir.

**ARCHITECTURAL RECOMMENDATION:** tek FoamDesignInput: alan, yoğunluk, süre,
fraksiyon, her alanın kaynağı ve kullanılan değeri. Süre yalnızca hacim hesabını
etkiler, anlık pompa debisini etkilemez. 210 m² örneği ile 1660 m² pompa örneği
ayrı tasarım vakalarıdır; sessizce tek vaka gibi birleştirilmez. Çok mahalde
alanları toplama/eşzamanlılık kuralı workbook'ta yok, V1 kapsamına girmez.

## 6. Hazen–Williams: kayıtlı bağıntı ve boyut engeli

**VERIFIED FROM WORKBOOK:** G15 metni tam olarak:

`P=(6.05×10^5xQm^1,85xL)/(C^1,85xdm^4,87)`

- A15: `P (metre başına basınç kaybı)`.
- F15: `Ptoplam (Toplam basınç kaybı)`.
- B15/C15/D15/E15: `C`, `dm`, `Qm`, `L`.
- A16: `=(6.05*10^5*D16^1.85)/(B16^1.85*C16^4.87)`.
- F16: `=(6.05*10^5*D16^1.85*E16)/(B16^1.85*C16^4.87)`.
- A17/F17 aynı shared-formula satır karşılıkları.

Toplam formül per-length formüle L çarpanı ekler. F16 doğrudan A16*E16 hücre
bağı değildir; cebirsel olarak aynıdır. Her iki örnek bağımsız aritmetikle uyuşur.

| Özellik | Workbook kanıtı | Karar |
|---|---|---|
| Qm birimi | Yalnızca Qm; birim yok | UNIT_UNCLEAR / SOURCE_REQUIRED |
| dm birimi | Yalnızca dm; 105 | UNIT_UNCLEAR; mm tahmini onay değildir |
| dm'nin iç çap olması | Açık tanım yok | SOURCE_REQUIRED; gelecekte Di gerekir |
| L birimi | Metre başına başlığı ve 150 | m yorumu kuvvetli ama L alanının birimi açık değil; SOURCE_REQUIRED |
| P/Ptoplam birimi | “basınç kaybı”; bar/kPa/Pa/m yok | UNIT_UNCLEAR; basınç mı yük mü belirlenemez |
| 6.05×10^5 katsayısı | Metinde ve formülde aynı | WORKBOOK_REFERENCE_ONLY; pratik birim paketi doğrulanmamış |
| 1.85 ve 4.87 üsleri | Formülde var | WORKBOOK_REFERENCE_ONLY; yöntem sürümü doğrulanmalı |
| Akışkan/sıcaklık/rejim | Yok | SOURCE_REQUIRED; deniz suyuna uygunluk kendiliğinden kabul edilmez |
| Boru yaşı/kaplama/servis | C tablosunda kısmi metin | Örnek hesaplara seçili satır bağlantısı yok |

**DIMENSIONAL STATUS: UNRESOLVED / UNIT_UNCLEAR.** Sayısal eşleşme birim onayı değildir.
Q fiziksel debi [L³/T], d ve hat uzunluğu [L], C boyutsuz varsayılırsa
`Q^1.85 × L / d^4.87` boyutu `[L^1.68 T^-1.85]` olur. Sayısal katsayı
boyutsuz alınırsa bu doğrudan ne basınç ne yük verir. Katsayı, kullanılan
pratik birim sistemine ait boyut/dönüşüm taşımak zorundadır.
Örneğin **yalnızca varsayımsal** Q=L/min, d=mm, L=m ve çıktı bar ise katsayı
birimi `bar·mm^4.87 / ((L/min)^1.85·m)` olmalıdır. Workbook bu paketi doğrulamıyor.
Basıncı yüke çevirmek için ayrıca doğrulanmış yoğunluk ve g gerekir;
basınç ile m yük aynı değişken olarak kullanılamaz. `hf_HW` adı ancak yük
çıktısı doğrulanırsa kullanılır, şu anda nötr `loss_value` önerilir.

**FIRE-HW-UNITS-001 / SOURCE_REQUIRED:** Q/d/L/çıktı birim paketi,
katsayı, iç çap tanımı, akışkan ve yöntem uygulanabilirliği çözülmeden
üretim sonucu veya pompa yükü sunulamaz.

### C tablosu — tam workbook yazımı

Başlık L8 `Hazen - Williams C Values`, L9 `Pipe or Tube`, M9 `C Values`.

| Hücreler | Metin (aynen) | C |
|---|---|---:|
| L10:M10 | Unlinen cast or ductile iron | 100 |
| L11:M11 | Black Steel (dry systems including preaction) | 100 |
| L12:M12 | Black Steel (wet systems including deluge) | 120 |
| L13:M13 | Galvanized (all) | 120 |
| L14:M14 | Plastic (listed) all | 150 |
| L15:M15 | Cement-lined cast or ductile iron | 140 |
| L16:M16 | copper tube or stainless steel | 150 |
| L17:M17 | Asbestos Cement | 140 |
| L18:M18 | Concrete | 140 |

Dokuz satırın tamamı **WORKBOOK_REFERENCE_ONLY**. `Unlinen` yazımı sessizce
düzeltilmez; normalleştirilmiş ad ve özgün kaynak metni ayrı tutulabilir.
Concrete satırı ön talimat listesinin ötesinde bulundu. B16=120/B17=140
hardcode; tablodan lookup yok. C'nin hangi malzeme satırından seçildiği bilinmiyor.
Listed, all, wet, dry ifadeleri bir sertifika veya onay kanıtı sayılmaz.

### Mevcut hidrolik çekirdek ve kapsam

**ARCHITECTURAL RECOMMENDATION:** bağımsız `engineering/fire_fighting/`
altında saf HazenWilliamsCalculator + ince `services/fire_hydraulics_service.py`.
İsimler öneridir; bu fazda dosya/sınıf eklenmez. Bu, Fire'a özel yöntem olarak
başlar; yeniden kullanım ihtiyacı doğrulanırsa sonraki fazda ortak yöntem seçimi
değerlendirilir. Şimdi Darcy girişine genel HydraulicMethod anahtarı eklemek
gereksiz risk yaratır. Gelecekteki DARCY_WEISBACH / HAZEN_WILLIAMS enum'u yalnızca
yöntem kimliği olabilir; farklı girdi/çıktı sözleşmelerini ortakmış gibi gösteremez.

Darcy calculator/service, Reynolds, sürtünme faktörü, hf ve lokal kayıplar
değişmez. C ≠ k: CHW boyutsuz yöntem katsayısı, Darcy k uzunluk boyutlu pürüzlülük.
CHW, Material.roughness_mm alanına yazılmaz ve buradan türetilmez.

Lokal kayıp, fitting, eşdeğer uzunluk: **NOT_PRESENT_IN_WORKBOOK**, kaynak sınıfı
OUT_OF_SCOPE. Düz hat kaybı “toplam sistem kaybı” diye sunulamaz.
Tam yangın pompası basma yüksekliği, statik yük, nozul artık basıncı, emiş şartı,
pompa eğrisi/verim/güç/NPSH: **NOT_PRESENT_IN_WORKBOOK** ve
**OUT_OF_SCOPE_FOR_INITIAL_FIRE_MODULE**. Kapasite hesabı pompa yükü hesabı değildir.

## 7. Nozul: çözülmemiş formül

**VERIFIED FROM WORKBOOK:** A25 tam metin `Q = Kx(P^-2)`.
B26 `Debi (litre/dakika)`, C26 `Çalışma Basıncı (bar)`,
D26 `Nozul geçirgenlik katsayısı`. Sayısal girdi/sonuç veya çalıştırılabilir
Excel nozul formülü yok; metin bir denklem tanımıdır.

**FIRE-NOZZLE-FORMULA-001: SOURCE_REQUIRED.** Tanılar:
**FORMULA_UNVERIFIED**, **POTENTIAL_TRANSCRIPTION_ERROR**.
Üretim uygulaması şu anda **YASAK**. Üs düzeltilmedi veya yeniden yorumlanmadı.

Literal yorumda Q=K/P². Pozitif K/P için dQ/dP=−2K/P³<0: basınç arttıkça
debi azalır, P→0+ iken sınırsız büyür. Bu, sabit pasif nozulda basınç farkı
artışıyla artan debi beklentisiyle uyuşmadığından kaynak kontrolü gerektirir.
Bu fiziksel tutarlılık kontrolü alternatif bir formülün onayı değildir.
Boyut tutarlılığı literal bağıntıda K birimini `(L/min)·bar²` gerektirir;
workbook K birimi, basıncın diferansiyel/gösterge/mutlak temeli veya dönüşümlerini
vermiyor. Üs başka bir notasyonu temsil ediyor olabilir; kanıt olmadan karar yok.

Çözüm için üretici nozul tipi/ürün dokümanı, gerçek Q(P) ilişkisi, K tanımı ve
birimi, çalışma aralığı, basınç referansı, sürüm ve örnek doğrulaması gerekir.
Minimum gelecek arayüz: nozzle_type, nozzle_k + birim, working_pressure + birim,
kaynak, formül sürümü, verification state; onaydan sonra yalnızca Q çözümü.
P çözümü sonraki kapsam. V1'de nozul devre dışı/NOT_CONFIGURED açıklamasıyla
kalmalı; sahte sıfır sonuç, başarılı FormulaStep veya snapshot üretilmemeli.

## 8. Workbook regresyon matrisi

Aşağıdaki farklar `yeniden üretim − kayıtlı Excel değeri`dir. Ondalık nokta burada
ham aritmetik içindir. Workbook'un yeniden hesaplandığı iddia edilmez.
Foam hacimlerinde Decimal, diğerlerinde Python float kullanıldı.

| Hesap / hücre | Girdiler | Workbook | Yeniden üretim | Fark | Yorum / sayısal durum |
|---|---|---:|---:|---:|---|
| Miktar A3 | A210,q5,t30,c.03 | 945 L | 945 L | 0 | Aqtc / MATCH |
| Miktar A4 | A230,q5,t30,c.03 | 1035 L | 1035 L | 0 | Aqtc / MATCH |
| Miktar A5 | A223,q5,t30,c.03 | 1003.5 L | 1003.5 L | 0 | Aqtc / MATCH |
| Miktar A6 | A96,q5,t30,c.03 | 432 L | 432 L | 0 | Aqtc / MATCH |
| Miktar A7 | A190,q5,t30,c.03 | 855 L | 855 L | 0 | Aqtc / MATCH |
| Miktar A8 | A358,q5,t30,c.03 | 1611 L | 1611 L | 0 | Aqtc / MATCH |
| Köpük pompa A12 | A1660,q5,c.03 | 249 | 249 L/min | 0 | Aqc / MATCH; birim türetilmiş |
| Dönüşüm G12 | A12=249 | 14.94 m³/h | 14.94 m³/h | 0 | ×0.06 / MATCH |
| Yaklaşık H12 | G12=14.94 | 15 m³/h | 14.94 hesap sonucu | −0.06 | Hardcode; FORMULA_UNCLEAR / SOURCE_REQUIRED |
| HW A16 | C120,d105,Q2000 | 0.01581188602 | 0.015811886016440187 | −3.5598122e−12 | Aritmetik ROUNDING_ONLY; UNIT_UNCLEAR |
| HW F16 | aynı,L150 | 2.371782902 | 2.371782902466028 | +4.6602810e−10 | Aritmetik ROUNDING_ONLY; UNIT_UNCLEAR |
| HW A17 | C140,d105,Q2000 | 0.0118886383 | 0.011888638296673054 | −3.3269464e−12 | Aritmetik ROUNDING_ONLY; UNIT_UNCLEAR |
| HW F17 | aynı,L150 | 1.783295745 | 1.783295744500958 | −4.9904192e−10 | Aritmetik ROUNDING_ONLY; UNIT_UNCLEAR |
| Deniz suyu A30 | A1660,q5,factor.97 | 8051 | 8051 L/min | 0 | Aqfactor / MATCH; su yorumu SOURCE_REQUIRED |
| Dönüşüm F30 | A30=8051 | 483.06 m³/h | 483.06 m³/h | 0 | ×0.06 / MATCH |
| Nozul A25:D26 | yalnızca metin | sonuç yok | hesap yapılmadı | uygulanamaz | FORMULA_UNCLEAR / SOURCE_REQUIRED |

On kullanılabilir sayısal girdi vakası var: altı miktar, bir köpük pompa,
iki HW, bir deniz suyu. Dönüşüm/yardımcı sonuçlar tabloda ayrıca gösterildi.
C tablosu regresyon hesabı değildir; dokuz satırının envanteri §6'dadır.
MATCH satırlarının kaynak sınıfı hâlâ WORKBOOK_REFERENCE_ONLY.
ROUNDING_ONLY burada kayıtlı son basamak farkını açıklar; Excel gösterim
yuvarlaması veya ekipman yuvarlama algoritması kanıtı değildir. General biçimi,
ROUND işlevi bulunmaması ve H12'nin sabit olması ayrı kanıtlardır.
HW toplamlar yuvarlanmış A16/A17 üzerinden değil ham formülden hesaplanmalıdır.

## 9. Mevcut D243 mimarisi — repository incelemesi

| İncelenen dosya/alan | Mevcut sözleşme | Gelecekte küçük ekleme ihtiyacı |
|---|---|---|
| engineering/module_registry.py | Dört ModuleCode, MODULES, fuel_only ve availability | Yeni aile metadatası; eski kodlar sabit kalır |
| engineering/system_context.py | İmmutable SystemContext, UUID/etiket, revision, versioned payload | Fire context ve rolleri açıkça taşımak |
| services/system_context_service.py | System/Circuit/Fluid katalogları; FUEL/FRESH_WATER/OIL application defaults | Yangın profili için onaylı ekleme; şimdi kayıt yok |
| engineering/provenance.py | SourceReference, EngineeringValue, used/recommended/override reason | Aynı sahiplik; source sınıflarını verification ile karıştırmamak |
| engineering/head_loss/calculator.py, services/discharge_head_loss_service.py | Ortak doğrulanmış Darcy yolu, linked/manual adaptörü | Değişmez; ayrı fire calculator/service |
| engineering/pipe_design/transfer.py | PipeValues, PipeSelectionSnapshot, PipeInputState, revision/stale/update/keep | Geometri/debi sınır adaptörü; CHW ayrı |
| engineering/formula/models.py | Önceden hesaplanmış immutable FormulaStep/Variable/Check | Fire builder ve TR/EN anahtarları; renderer hesap yapmaz |
| engineering/units.py, input_parsing.py, precision.py | Açık dönüşüm, parse ve sunum sınırı | L/min, L, m², süre, fraksiyon için dar eklemeler; mevcut alias anlamları değişmez |
| engineering/snapshots/models.py, builders.py, serialization.py | Schema 1, enum doğrulaması, facts/steps/context/summary, allowlist | Fire ModuleCode + builder dispatch + domain allowlist testleri gerekir |
| repositories/calculation_repository.py | snapshot:module:UUID namespace ve mevcut JSON kolonları | Yeni SQL tablo gereği henüz yok; enum desteği otomatik değildir |
| services/snapshot_history_service.py | Append-only, proje izolasyonu, projectless session | Aynı servis; geçmişten yeniden hesaplama yok |
| ui/history_presentation.py, dialogs/calculation_history.py | Dört modül etiketi, summary, stage, filtre, seçili lazy detail | Fire label/filter/primary summary/renk eklemesi gerekir |
| reporting/models.py, dialogs/pdf_report.py | Snapshot-only adapter; dört modül başlığı | Fire etiket/metadata whitelist; yeni PDF motoru gerekmez |
| services/project_persistence_service.py, repositories/project_state_repository.py | Tek workspace JSON, schema_version=1 | Versioned fire namespace; paralel kayıt sistemi yok |
| services/library_catalog.py, engineering_library_service.py | Açık kategoriler/alan allowlist, sahiplik ve source metadatası | Kaynak onayından sonra sınırlı kategori; şimdi seed/schema yok |
| ui/main_window.py | Dört sayfa factory'si/_pages map; export/load ve listener bağlantıları | Aile host'u ve Fire kaydı açık entegrasyon ister |
| ui/widgets/scrollable_page_host.py | ttk.Notebook, factory hemen çağrılır; page_key/scroll ownership | Fire sayfaları ilk aile erişiminde oluşturulabilir; mevcut startup akışı korunur |
| ui/theme/pipe_pilot.py, module_visuals.py, formula_visuals.py | Modül kapsamlı stiller, sabit dört kimlik | Onaylı Fire token ve identity eklemeleri |

Repository'de YSH ve docs metinlerinde foam/fire fighting/yangın/Hazen/nozzle/nozul/
FSS/SOLAS/NFPA araması yapıldı. İlgili mühendislik kaynak metadatası bulunmadı.
Eşleşmelerden history belgesindeki sonraki faz başlığı yalnızca plan;
`Consolas` font adındaki `SOLAS` alt dizgesi kaynak değildir.
Mevcut TL boru kuralları yangın tasarım kaynağı olarak devralınmaz.
Kullanıcının canlı DB'si okunmadı/değiştirilmedi; bu bulgu repository içeriğiyle sınırlıdır.

### Minimum gelecek bileşenler

`engineering/fire_fighting/models.py`, `foam.py`, `hazen_williams.py` saf domain
için adaydır. Servis girdi/kaynak/link koordinasyonunu, mevcut FormulaStep builder
anlatımı, UI sunumu üstlenir. Hesap repository içinde yapılmaz. Nozul sadece
kontrat/engellenmiş durum olarak kalır. Yeni plugin framework, ORM, DI sistemi,
toolkit veya persistence katmanı önerilmez.

## 10. Navigasyon, ortak çalışma alanı ve görsel tasarım

**ARCHITECTURAL RECOMMENDATION:** OPTION B, sistem ailesi ve alt modüller.

| Ölçüt | Beş bağımsız üst sekme | Yangın workspace + ortak köpük |
|---|---|---|
| Kullanım / mühendislik | Aynı alan/yoğunluk üç kez girilir, kopma riski | Tek onaylı vaka ve üç ilişkili sonuç |
| Formula View | Tekil anlatım kolay, ortak girdi tekrarı | Alt sonuç seçicisi ve aynı donmuş girdi izi |
| History/PDF | Bağımsız kayıtların ilişkisi kaybolabilir | Aynı tasarım revizyonu ve çıktı alt türü |
| Genişleme / ekran | Üst sekme çubuğu büyür | Aile→modül→alt tür büyür |
| Kod | Parse/validation/provenance tekrarı | Ortak model, ayrı sonuç sunumu |

Metinsel wireframe:

```
Mevcut proje sidebar'ı ve üst araçlar
Sistem ailesi: [Mevcut hesaplar / Yangın Söndürme / gelecekte diğerleri]
System Profile / Devre / bağlam (aile seçiminden ayrı mühendislik kimliği)
Yangın modülleri: [Köpük Sistemi] [Hidrolik] [Nozul: kaynak gerekli]
Köpük: tek vaka girdileri A, q, Cfoam, t + kaynaklar
Sonuç alanı: Miktar | Köpük tulumbası | Deniz suyu tulumbası
Formula View: seçili sonuç adımları; PDF: seçili donmuş kayıt
```

Hiyerarşi: **Yangın Söndürme → Köpük Sistemi → üç çıktı alt türü**;
**Yangın Söndürme → Hidrolik Hesap → Hazen–Williams düz hat**;
**Yangın Söndürme → Nozul Hesabı → Nozul debisi (blocked)**.
Mevcut Boru/Transfer/Basma/Emme grubunun sırası, stable key'leri, kaydedilmiş state'i
ve erişimi korunur. Bunları körlemesine yalnızca yakıt sistemine kilitlemek doğru
değildir; bugün yalnızca Transfer fuel_only. Aile seçimi SystemContext'i sessizce
değiştirmez; uygun profil seçimi ayrı ve açık bir kullanıcı işlemidir.
Küçük aile seçicisi mevcut proje sidebar'ını kalabalıklaştırmadan içerik üstünde
olabilir. Klavye odağı, scroll, dar pencere ve TR/EN başlıkları kabul testine girer.

Token önerileri: `FIRE_ACCENT=#C65D4B`, `FIRE_ACCENT_DARK=#963E32`,
`FIRE_RESULT_SURFACE=#FFF2EE`. Mevcut navy tipografi/beyaz kartlar korunur;
coral yalnızca kimlik, ince vurgu ve sonuç yüzeyidir. Kaynak/hata durumu renk
anlamı bağımsızdır. Bu fazda stil eklenmez.

## 11. System Profile, akışkan ve PipeSelection sözleşmesi

Mevcut System/Circuit/Fluid UUID'leri, SourceReference ve revision modeli
kullanılır. Gelecek FIRE_FIGHTING profil kodu öneridir, bu fazda DB kaydı yok.
Yangın devresi, korunan mahal/vaka kimliği, servis türü ve seçilmiş yöntem açık
bağlam olur; profil seçmek q=5/t=30/C=.03 yükleyemez.

SystemContext tek fluid taşır. Köpük tasarımında üç rol ayrılmalıdır:
base_water (deniz suyu veya belirtilmiş su), foam_concentrate, foam_solution.
Gelecek fire workspace bu rolleri ayrı ContextReference olarak taşır; aktif
hidrolik hesabın fluid'i SystemContext'e açık seçimle bağlanır. Üçünü mevcut
fuel fluid kaydına eşitlemek veya bir etikete sıkıştırmak doğru değildir.
Yoğunluk/viskozite/sıcaklık/ürün uygunluğu kaynak gerekir; HW bunları input
almıyor diye tüm akışkanlara uygun sayılmaz. Karışım oranı hacim/kütle temeli de kayıtlı olur.

PipeSelection'dan boru kimliği/standardı, OD/et/ID, nominal etiketler, kaynak,
selection_id ve revision tekrar kullanılabilir. Q bağlantısı isteğe bağlı ve
birim dönüşümü açık olmalı; pipe Q m³/h→L/min için ×1000/60 yalnızca doğrulanmış
HW birim paketiyle kullanılır. Mevcut `hydraulic_values()` mm/m³/h verir,
doğrudan birimi belirsiz workbook formülüne takılamaz.
CHW ayrı EngineeringValue'dur; boru malzemesinden kendiliğinden seçilmez.
Farklı sistem/devre/akışkan kaynağı açık uyarı ve kullanıcı seçiminden geçer.

## 12. Sembol, isim ve birim sözleşmesi

Aşağıdakiler **ARCHITECTURAL RECOMMENDATION**. HW/nozul birim adayları source
çözümünü bekler; workbook'tan doğrulanmış gibi kullanılmaz. Foam için dar
domain birimleri tercih edilir; Darcy SI iç temsili değişmez.

| Sembol | Önerilen kod adı | Ekran | Domain içi / dönüşüm sınırı |
|---|---|---|---|
| A | protected_area_m2 | m² | m² |
| q | application_density_lpm_m2 | L/(min·m²) | aynı |
| t | application_duration_min | min | min; saniye kabul edilirse /60 |
| Cfoam | foam_fraction | % | boyutsuz 0–1; parse sonrası yüzde /100 |
| Vfoam | foam_volume_l | L, m³ | L; m³= L/1000 |
| Vsolution | solution_volume_l | L, m³ | L, türetilmiş destek |
| Qsolution | solution_flow_lpm | L/min, m³/h | L/min; ×0.06 |
| Qfoam | foam_flow_lpm | L/min, m³/h | L/min; ×0.06 |
| Qwater | water_flow_lpm | L/min, m³/h | L/min; ×0.06 |
| fwater | water_fraction | % veya boyutsuz açık etiket | Boyutsuz; 1−Cfoam yalnızca onaylı modelde |
| CHW | hazen_williams_c | boyutsuz | boyutsuz; Darcy k değildir |
| Di | inside_diameter_mm | mm adayı | Boru adaptöründe mm; HW paketine dönüşüm onay bekler |
| L | pipe_length_m | m adayı | m adayı; HW kaynak onayı bekler |
| Δp_HW / hf_HW | loss_value + loss_unit | henüz belirlenmedi | Basınçsa Pa, yükse m; birim onayı olmadan biri seçilmez |
| Knozzle | nozzle_k | kaynağın belirlediği birim | Formüle bağlı, henüz belirlenmedi |
| Pnozzle | working_pressure_bar | bar | Onaydan sonra Pa sınırı: ×100000; basınç referansı ayrı |
| Qnozzle | nozzle_flow_lpm | L/min | Onaydan sonra L/min; m³/s= /60000 |

`C` tek başına kullanılmaz: Cfoam ile CHW ayrıdır. Boru korozyon `c`si veya
lokal kayıp K ile nozul Knozzle karışmaz. HW basıncına Pnozzle adı verilmez.
Yüzde editörü `3,00 %` gösterir, normalize değer .03 olur. Aynı editörde .03
yazmak .03%=.0003 demektir; 3/.03 otomatik tahmini yapılmaz. Import alanı
birimini açıkça taşımalı ve dönüştürülmüş önizleme göstermelidir.
TR virgül mevcut parser/formatter ile, JSON ham sayılar nokta ile tutulur.
14,94 / 483,06 sunumdur; ham değer hesap ortasında yuvarlanmaz.
Ekipman seçimi ayrı kayıt ve gerekçe gerektirir. Global precision değiştirilmez.

## 13. Kaynak, varsayılan ve Library tasarımı

Workbook q/t/c, 0.97, HW C ve 15 değerleri otomatik üretim önerileri değildir.
Yeni projede alan/q/t/c/CHW açık kullanıcı girişi olursa USER_PROJECT_ASSUMPTION,
SourceType.USER_INPUT + VerificationStatus.USER_SUPPLIED ve OverridePolicy.USER_INPUT
kullanılır; recommended_value yoktur. Onaylanmış bir öneri ileride SUGGESTED
olabilir; used_value değişirse override_reason zorunludur. Kaynağın otoritesi
user override ile yükselmez. Doğrulanmış sabit dönüşümler kullanıcı seçimi değildir.

| Aday varsayılan | Köken / kaynak durumu | Önerilen / kullanılan | Override |
|---|---|---|---|
| q5,t30,Cfoam.03 | Workbook / WORKBOOK_REFERENCE_ONLY | Yeni projede recommended yok; used açık kullanıcı seçimi | USER_INPUT, varsayılan gibi sessiz doldurma yok |
| fwater.97 | E30 / WORKBOOK_REFERENCE_ONLY | Bağımsız faktör olarak as-found; türev yorumu SOURCE_REQUIRED | Onaylı türev modelde doğrudan override yok; Cfoam düzenlenir |
| CHW100/120/140/150 | Tablo / WORKBOOK_REFERENCE_ONLY | Seçim kaynağı ve servis onaylanınca öneri olabilir | Onaylı SUGGESTED ise gerekçeli |
| H12=15 | Elle girilmiş yaklaşık / SOURCE_REQUIRED | Hesap14.94; seçilen15 bağımsız kullanıcı tercihi | Seçim gerekçesi zorunlu |
| Nozul K / HW birim paketi | Kaynak yok / NOT_CONFIGURED | recommended ve used yok | Kaynak engelini override çözmez |

Analiz sınıfları mevcut VerificationStatus enum'u değildir. Workbook kanıtı
SourceType.ENGINEERING_REFERENCE, verification USER_SUPPLIED/UNVERIFIED,
document+sheet+cell+hash ile temsil edilebilir; SOURCE_REQUIRED tanısı ayrı
domain bulgu olarak saklanır. Enum'a yanlışlıkla yeni string sokulmaz.
SOURCE_VERIFIED ancak kaynak denetimiyle VERIFIED'a eşlenir.

| Gelecek dataset | Öncelik | İçerik ve karar |
|---|---|---|
| Yangın / Hazen-Williams C | OPTIONAL; değerlerin yetkisi SOURCE_REQUIRED | V1 açık manuel C kullanabilir; factory katalog zorunlu değil |
| Yangın / Nozul Katsayıları | SOURCE_REQUIRED | Nozul formül/birim/ürün onayı olmadan eklenmez |
| Yangın / Köpük Uygulama Verileri | OPTIONAL; öneriler SOURCE_REQUIRED | V1 manuel proje kriteriyle çalışabilir; q/t/c seed edilmez |

Bu fazda REQUIRED_FOR_V1 olan yeni Library dataset yoktur; gerekli olan
kullanıcı/proje girdisi ve kaynak izidir. Katalog otomatik seçim özellikleri
istenirse ayrıca onaylı kaynak gerekir.
Gelecek CHW kayıt taslağı: id, code, original_description, normalized_description,
material_id (opsiyonel), C, condition, service, wet/dry applicability, fluid_scope,
source_id/SourceReference (organization/document/revision/table), verification,
notes, ownership/is_factory/is_active, record_revision. C dimensionless.
Mevcut sahiplik/deactivate ve repository katmanı kullanılır; DB yapısı bu fazda yok.

## 14. Validation ve warning matrisi

Tüm sayılar finite gerçek sayı olmalı; bool, NaN, infinity, eksik giriş reddedilir.
Sınırlar matematiksel/geçerli aktif tasarım politikasıdır; mevzuat limiti değildir.

| Girdi | Matematik / aktif tasarım doğrulaması | Sıfır ve kaynak bağımlı sınır |
|---|---|---|
| A,q,t | Negatif ERROR; aktif koruma tasarımında >0 | Sıfır aritmetik olarak mümkün; aktif hesap için sonuç üretme. Üst limit/q/t min kaynağa bağlı |
| Cfoam | 0≤c≤1, dışı ERROR | Uçlar matematiksel olarak geçerli; gerçek köpük ürünü uygunluğu SOURCE_REQUIRED, regülasyon aralığı uydurma |
| fwater | Bağımsız faktörde 0–1 | 1−c modeli ancak açık onayla; iki fraksiyon çelişkisi ERROR |
| CHW | >0; eksik ERROR | 100/150 alt/üst limit değildir; servis/yaş uygunluğu kaynak gerekir |
| Di | >0 | OD−2wall tutarlılığı mevcut geometri sözleşmesi; HW iç çap tanımı source blocker |
| QHW | Aktif akışta >0 önerisi | Q=0 cebirsel sıfır verebilir; yöntemin geçerlilik alanı kaynak onayını bekler |
| L | Aktif düz hat hesabında >0 önerisi | L=0 cebirsel sıfır; V1 aktif hat için reddet; negatif ERROR |
| Pnozzle | >0 | 0 literal ifadede bölme hatası; hesap zaten source blocked |
| Knozzle | Sayısal model/birim belirlenmedi | Onaylı pasif nozul modelinde pozitif gereği teyit edilir; keyfi üst limit yok |
| Seçilen pompa kapasitesi | Finite, pozitif; hesap sonucundan ayrı | Kullanıcı daha düşük seçerse sayısal fark görünür; mevzuat marjı iddiası yok |

| Durum | Gelecek tepki |
|---|---|
| Eksik/negatif/sonlu olmayan girdi, sıfır payda | ERROR; ilgili hesap engellenir |
| HW birim/katsayı tanımsız | SOURCE_REQUIRED; sayısal üretim çıktısı engellenir |
| Nozul belirsiz | FORMULA_BLOCKED_SOURCE_REQUIRED; hesap düğmesi devre dışı |
| q/t/c kullanıcının kaynaklandırılmamış kriteri | USER_PROJECT_ASSUMPTION görünür; compliance PASS verilmez |
| fwater yorumu onaysız | SOURCE_REQUIRED; birleşik modelde su çıktısı engellenir |
| PipeSelection eski/kayıp/farklı bağlam | STALE/SOURCE_MISSING/DIFFERENT; update/keep current açık işlemi |
| H12≈15 dayanağı yok | ENGINEERING_DECISION_REQUIRED; otomatik ekipman seçme |
| Düz hat dışı kayıp/pompa yükü isteniyor | OUT_OF_SCOPE açıklaması; sıfır gibi toplama yok |

Kaynak eksikliği sayısal WARNING/PASS ile geçiştirilmez. Mevcut CheckStatus'da
SOURCE_REQUIRED yok; sebep anahtarıyla NOT_CONFIGURED/domain issue olarak
taşınması veya dar ek enum ihtiyacı sonraki fazda kararlaştırılır.

## 15. FormulaStep, snapshot, History ve PDF kontratı

### FormulaStep

Builder, saf hesap sonucunu anlatır; yeniden hesaplamaz. Her adım stable step_id,
TR/EN title_key, denklem, ham substitution, result_value/unit/symbol, sıralama,
FormulaVariable kaynakları, used_values, seçim nedeni ve source/check içerir.
Sınıflandırma ENGINEERING_CALCULATION; TL_RULE_CALCULATION değildir.

| Hesap | Önerilen adımlar |
|---|---|
| Köpük miktarı | solution_flow=Aq → concentrate_flow=Qsolution*c → concentrate_volume=Qfoam*t → volume_m3 dönüşümü |
| Köpük pompa | solution_flow → kullanılan fraksiyonun izahı → concentrate_flow → m³/h dönüşümü |
| Deniz suyu pompa | solution_flow → onaylı water_fraction veya açık bağımsız factor → water_flow → m³/h |
| HW | Doğrulanmış input normalization → katsayı/birim kaynak paketi → per-length loss → total loss |
| Nozul | FORMULA_BLOCKED_SOURCE_REQUIRED; başarılı equation/result adımı yok |

Girdi fraksiyon açıklaması sırf görünüm için sahte hesap sonucuna dönüştürülmez;
değişken/used_values olarak yer alabilir. Final sonucu tekrar eden gereksiz adım yok.
Gelecek audited PNG adayları köpük çarpımı, debiler ve onaylı HW bağıntısıdır.
Şimdi PNG eklenmez; mevcut PNG→MathText→native fallback ve lazy render korunur.
Nozul PNG'si kaynak çözülmeden hazırlanmaz.

### CalculationSnapshot

Mevcut schema=1 kabı korunmaya adaydır; uyumluluk testleri geçmeden otomatik
destek varmış sayılmaz. Aday ModuleCode'lar: fire_foam_system, fire_hazen_williams,
ileride fire_nozzle. Foam stage/subtype quantity/concentrate_pump/seawater_pump
olarak seçilebilir; tek birleşik tasarım kaydı tüm üç sonucu tutar, seçili çıktı
sunum metadata'sıdır. Ayrı kayıt istenirse aynı design_case_id/design_revision
ile açık alt tür kaydı alınır, otomatik üç history satırı üretilmez.

Önerilen evidence facts: calculation_type/subtype, raw_inputs (birimleriyle),
normalized_inputs, outputs, unit_metadata, formula_version/method_id,
source/provenance per input, recommended/used/override_reason, issue/status,
warnings, design_case_id/revision, fluid_roles ve mixture_basis, uygulanan
PipeSelection snapshot/selection_id/source_revision/link state.
Mevcut context, steps, summary, snapshot_id, UTC created_at, project_id,
model_version ve schema_version alanları kullanılır. Workbook referansında
sheet/cell/hash tutulur. UI renkleri fiziksel veriye dönüştürülmez.
Unit/source engelli hesap başarılı snapshot üretemez; proje taslağı ayrı state'tir.
Eski evidence'e alan ekleyerek geçmiş kayıtlar değiştirilmez. Enum, builder
dispatch, serialization allowlist, History etiketleri ve PDF adaptörü gelecekte
birlikte ele alınmalıdır; tek UI tab eklemesi yeterli değildir.

### History / PDF

History etiketi adayları: Yangın — Köpük Miktarı / Köpük Tulumbası / Deniz Suyu
Tulumbası / Hazen-Williams / Nozul. Birleşik kaydın başlığı Yangın — Köpük Sistemi,
alt tür ve özet çıktılar detayda. Fire coral kimliği tüm alt türlerde aynı;
verification ayrı durum metnidir. Filtre ve primary-result map açıkça genişler.
Seçim yalnızca donmuş evidence okur, güncel Library/formül tekrar uygulanmaz.
Formula View yalnızca kullanıcı isteğiyle mevcut historical yolundan açılır.

PDF: mevcut snapshot-only export ve A4 motoru. Header D243 Engineering Report;
Yangın Söndürme/sistem-devre/akışkan rolleri, hesap türü, girdi/birim,
denklem/yerine koyma, ham hesap sonucu ve sunum değeri, seçilen kapasiteyi
ayrı göstermek, kaynak/doğrulama/gerekçe, unresolved bulgular, snapshot UUID,
UTC tarih/model sürümü. Mevcut adaptörde Fire labels/whitelist eklenmelidir.
Canlı widget/Library sorgusu veya yeniden hesaplama yok. Nozul/source blocked
durumu başarılı mühendislik raporu olarak export edilmez. Bu fazda PDF değişmez.

## 16. Persistence ve açık veri bağları

Tek mevcut project state içinde versioned `fire_fighting` namespace önerilir:
active_submodule, design_cases, ham giriş/unit/source seçimleri, normalized
girdiler, concentration basis, model version, manuel seçilen ekipman,
PipeSelection link kimliği/revision/applied values, last_snapshot_id ve dirty state.
Restore sırasında tüm payload önce doğrulanır, sonra UI'ya uygulanır. Eksik Fire
namespace eski projede boş taslak demektir; eski sayfalar varsayılanlarını korur.
Bir sonuç kalıcı iz olarak gerekirse immutable snapshot'tadır; kaydedilmiş UI
sonucu yeniden hesaplanmış kabul edilmez. Ayrı DB/parallel persistence yok.
Mevcut main_window export yalnızca sayfa anahtarlarını topluyor: Fire namespace
eski sürümle save edilirse korunacağı varsayılmaz. Gelecek fazda bilinmeyen
namespace korunması/unsupported-version politikası ve round-trip testleri gerekir.

| Bağ | Kontrat |
|---|---|
| Ortak köpük girdisi → üç sonuç | Aynı vaka/revision'a bağlı; explicit Calculate tüm desteklenen çıktıları atomik üretir. Girdi değişince eski sonuç stale, yeniden hesaplama sessiz değil |
| Ayrı taslaklar arasında köpük girdisi | Opt-in manual/linked, source_case_id/revision, applied values, applied_at ve source state |
| PipeSelection → HW | Mevcut PipeInputState yaklaşımı, birim adaptörü; CHW ayrı kaynaklı. Link otomatik q/t/c taşımıyor |
| Nozul → gelecek hidrolik denge | Şimdi OUT_OF_SCOPE; gelecekte frozen verified result UUID/revision/unit, asla metin formülünden canlı aktarım yok |

Kaynak revision değişince STALE; tüketici used values değişmez. Update açıkça yeni
değerleri uygular, bağımlı sonucu geçersiz kılar; Keep current eski uygulanan
değerleri ve source/observed revision'ı saklar. Manual moda geçiş açık olur.
Kaynak kaybolunca SOURCE_MISSING, current değeri sıfırlanmaz. SystemContext
değişimi hesapları sessizce taşımamalı; proje/context uyuşmazlığı görünür olmalıdır.

## 17. V1 kapsamı, açık konular ve faz planı

**ARCHITECTURAL RECOMMENDATION:** V1 hedefi tek Köpük Sistemi workspace,
üç ilişkili çıktı ve kaynakları çözülmüş düz hat HW. Nozul kapalı kalır.
Köpük su fraksiyonu yorumu ve HW birim/uygulanabilirlik paketi çözülmezse
ilgili çıktı V1'den çıkarılır/NOT_CONFIGURED olur; takvim için kaynak uydurulmaz.
Yeni boru boyutlandırma kuralı, ağ dengeleme, fitting, pompa head/güç/verim,
NPSH, simultane alan seçimi, mevzuat uygunluk kararı bu V1'in dışında.

| Açık konu | Durum | Gereken karar / kanıt |
|---|---|---|
| FIRE-NOZZLE-FORMULA-001 | SOURCE_REQUIRED | Üs/bağıntı, K birimi, basınç temeli, ürün ve test örneği |
| FIRE-HW-UNITS-001 | SOURCE_REQUIRED | Q/d/L/çıktı ve katsayı paketi, iç çap, akışkan/rejim kapsamı |
| FIRE-FOAM-WATER-001 | SOURCE_REQUIRED | E29 etiket çelişkisi, .97'nin 1−c olması, hacimsel karışım temeli |
| FIRE-FOAM-CRITERIA-001 | SOURCE_REQUIRED | q5/t30/c.03 seçiminin proje/ürün/standart dayanağı |
| FIRE-PUMP-SELECTION-001 | SOURCE_REQUIRED | 14.94→15 manuel yaklaşımının ekipman/rounding/marj anlamı |
| FIRE-HW-C-SOURCE-001 | SOURCE_REQUIRED | Tablo kuruluş/belge/sürüm, wet/dry/fluid/condition kapsamı |

Bu kaynakların TL/SOLAS/FSS/NFPA/IMO/LR olduğu ileri sürülmez. Kullanıcı kriteri
olarak kullanım ile standart uygunluğu ayrı onaylardır. Kritik source blocker,
gerekçe yazarak veya verification etiketini değiştirerek çözülmüş sayılamaz.

| Faz | Çıktı / geçiş kapısı |
|---|---|
| FIRE 0 | Bu analiz + açık kaynakların çözümü ve kullanıcı scope onayı; hiçbir production default yok |
| FIRE 1 | Kullanıcı onayı sonrası saf domain/input/output taslakları, unit boundary, provenance/status ve sürüm kontratı; belirsiz HW/nozul hesabı yok |
| FIRE 2 | Onaylı köpük hesapları, ortak vaka, kaynak ve workbook regresyonları; .97 yorumu onaysızsa su çıktısı gated |
| FIRE 3 | Yalnızca HW kaynak/birim paketi onaylanınca bağımsız düz hat calculator/service |
| FIRE 4 | Aile navigasyonu ve sayfalar; eski dört sayfa/state/scroll davranışı korunur |
| FIRE 5 | FormulaStep builder ve mevcut Formula View entegrasyonu; audit edilmemiş PNG yok |
| FIRE 6 | Additive ModuleCode/serializer/builder, append-only snapshot, History ve snapshot-only PDF uyumluluğu |
| FIRE 7 | Gerekliyse kaynaklandırılmış Library dataset; manuel V1 için zorunlu katalog yok |
| FIRE 8 | Nozul yalnızca FIRE-NOZZLE-FORMULA-001 kaynak ve birim çözümünden sonra |
| FIRE 9 | Mühendislik regresyonu, legacy/persistence round-trip, Windows manuel ve performans kabulü |

Faz 4–6 boyunca yeni sayfa başarılı kaydı olmayan PDF/History yolu sunmamalı;
entegrasyon tamamlanmadan kullanıcı sürümüne çıkarılmamalıdır.
**Tam sonraki adım: FIRE PHASE 0 kaynak/yorum kararlarının alınması.** Kullanıcı
ayrıca onaylarsa FIRE PHASE 1 yalnızca domain/units kontratıyla başlayabilir;
bu belge bunu otomatik başlatmaz.

## 18. Gelecek test ve kabul sözleşmesi

- Saf birim testleri: köpük çarpımları, süre değişiminin debiyi değiştirmemesi,
  onaylı water modelinde Qfoam+Qwater=Qsolution; vaka kimlikleri birbirine karışmaz.
- Dönüşümler: 3%↔.03, L↔m³, L/min↔m³/h↔m³/s, mm↔m, bar↔Pa;
  TR virgül parse ve raw precision korunur, premature rounding yok.
- Workbook fixtures: §8 altı miktar ve pompa çarpımları; HW sayısal fixture ancak
  anlam/birim teyidiyle production testi olur. Şimdiki sayısal uyum source onayı değildir.
- Domain: finite, bool/None/NaN, negatif ve sıfır, fraksiyon uçları, eksik kaynak;
  kaynak bağımlı min/max uydurulmaz. Nozul ve unit-blocked HW başarı üretemez.
- FormulaStep: stable order, substitution, kullanılan/önerilen ayrımı,
  kaynak/override gerekçesi, doğru birim ve classification; renderer hesap yapmaz.
- Snapshot: yeni enum ve allowlist/dispatch, detached JSON, frozen context/fluid
  roles, timestamp, source hash, input/output/unit/formula version, eski kayıt decode.
- History/PDF: Fire filtre/etiket/özet, immutability, legacy incomplete,
  güncel Library değişse de eski rapor aynı; A4 taşma/Türkçe karakter ve uzun source.
- Library: ownership, active/revision, source ve servis uygulanabilirliği;
  yetkisiz factory edit ve eksik kaynaklı VERIFIED reddi, seed olmadan açılış.
- Project: yeni/eski dosya load/save round-trip, eksik namespace, desteklenmeyen
  sürüm, proje izolasyonu; eski dört sayfa ve kayıtlı boru linkleri korunur.
- Link: manual/linked, stale, update, keep current, missing source ve farklı context;
  tümünde applied/observed revision ve sayısal sonuçların izlenebilirliği.
- UI: sistem ailesi geçişi, mevcut Boru/Transfer/Basma/Emme erişimi, scroll/focus,
  TR/EN, küçük pencere/Windows DPI, nozul blocked açıklaması ve source görünürlüğü.
- Performans: Fire'a girmeden yeni calculator/assets/history yüklenmemesi,
  Formula View seçili adım lazy render, büyük History ve mevcut startup ölçümleri.
- Her faz mevcut tam regresyonu geçer. Bu belge için yeni production test eklenmedi.

## 19. Bu fazın doğrulaması

Baseline **1552 passed, 0 failed**. Final tam regresyon: **1552 passed, 0 failed**,
63.58 s; uyarı yok. Commit kimliği teslim raporunda bildirilir; commit kendi
SHA'sını içeren belgeyle döngüsel olarak güncellenmez.
Belgenin dışında tracked dosya değişmemesi, referans hash'inin aynı kalması ve
git index'in Excel dosyasını içermemesi teslim öncesi kontrol edilir.
Production hesap davranışı değişikliği yoktur. Uygulamalı Fire hesap veya görsel
kabul yapılmadı; bu faz yalnızca teknik analizdir.
