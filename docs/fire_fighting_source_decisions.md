# D243 V2 — FIRE PHASE 0 — Source Resolution & Engineering Decisions

Doğrulama tarihi: **2026-10-21**. Bu faz dokümantasyon/kaynak kararıdır;
Fire Phase 1'i veya production uygulamasını başlatmaz.

## 1. Başlangıç ve karar özeti

Branch `d243-v2-handoff`, başlangıç commit
`9d1448702708f3aefeaa4a2173a1b4280f881db7`.
Yalnızca `.venv314\Scripts\python.exe` kullanıldı: Python 3.14.8.
Baseline **1552 passed, 0 failed**, 62.73 s; sandbox pytest cache yazma
uyarısı vardı. Beklenmeyen başka çalışma ağacı değişikliği yoktu.

`docs/references/Yangın Söndürme.xlsx` **approved untracked reference input**,
salt okunur, stage/commit dışında. Başlangıç SHA-256:
`bd9aa871454c184afdb45e14bd0c008818d49701d5cc92e1de7ca89126159474`.
Önceki [tam analiz](fire_fighting_module_analysis.md) bütünüyle okundu;
workbook envanteri yeniden kurulmadı, önceki hücre bulguları korundu.

| Hesap | Production-readiness gate | Tam kapsam |
|---|---|---|
| FOAM | **READY** | Açık proje girdileriyle, hacimsel çözeltinin debi/hacim talebi hesabı; mevzuat kriteri otomatik seçilmez |
| HAZEN–WILLIAMS | **READY** | Yayımlanmış pratik birim biçiminde, su için düz dolu basınçlı hat sürtünme basınç kaybı; uygulanabilirlik kaydı zorunlu |
| NOZZLE | **BLOCKED** | Workbook cihazı/K anlamı ve formül değişikliği kararı eksik; kaynaklanan cihaz bağıntısı ayrı tutulur |

HW gate'i deniz suyuna, köpük konsantresine/karışımına, fuel/oil'e veya tüm
sıcaklık/rejimlere onay değildir. **Seawater HW applicability: SOURCE_REQUIRED**.
Tümleşik marine yangın tasarımı/compliance gate'i READY değildir.
READY, tanımlı sınırlı hesabın sonraki fazlara alınabileceği anlamındadır;
yazılımın mevcut sürümünde kullanılabilir olduğu anlamına gelmez.

## 2. Kaynak envanteri ve erişim sınırları

Her S kimliğinin erişim/doğrulama tarihi 2026-10-21'dir. Yayın tarihi bilinmeyen
web sayfalarına tarih uydurulmadı. Teknik doküman revizyonu ile crawler tarihi
birbirine karıştırılmadı. Tam standart kopyalanmadı; kısa formül ve paraphrase kullanıldı.

| ID | Kuruluş / belge / sürüm | Yer ve erişim | Kanıt türü / sınırlama |
|---|---|---|---|
| S01 | IMO, MSC.98(73), FSS Code'u kabul eden karar, 2000-12-05; başlangıç yürürlüğü 2002-07-01 | [Resmî karar PDF](https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MSCResolutions/MSC.98%2873%29.pdf), ch.6,7,8,14 | Erişildi; tarihsel as-adopted metin, güncel konsolide sürüm değildir |
| S02 | IMO, current publications list; FSS Code **2026**, IC155E | [Güncel yayın listesi](https://www.imo.org/en/publications/pages/currentpublications.aspx), FSS satırı | Liste erişildi; 2026 konsolide normatif tam metin bu araştırmada edinilemedi: SOURCE_IDENTIFIED_BUT_NOT_ACCESSIBLE |
| S03 | Johnson Controls / SKUM, **ZF Inductor**, Form **FDS-2017084-04**, ©2024; ayrı gün/ay verilmemiş | [Üretici PDF](https://docs.johnsoncontrols.com/specialhazards/api/khub/documents/dEMK03nJ_8bSJITUY0xc0Q/content), s.2 Calculations / Example calculations | Erişildi; yayımlanmış HW pratik birim biçimi; üretici uygulama bağlamı genel marine kural değildir |
| S04 | US EPA, Rossman ve diğerleri, **EPANET 2.2 User Manual**, EPA/600/R-20/133, **2020** | [Resmî metin](https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=P10113EM.txt), §3.1 Pipes, Tables 3.1–3.2, basılı s.17–18 | Erişildi; yöntem kapsamı/üs konvansiyonu için, marine mevzuat yerine geçmez |
| S05 | Viking, **3% XMAX High Expansion Foam Concentrate**, page **F_081620**; web revizyon tarihi belirtilmemiş | [Ürün sayfası](https://www.vikinggroupinc.com/products/foam-products/high-ex-fff/xmax), description | Erişildi; ürün özelinde çözelti hacmine göre %3, fresh/brackish/seawater açıklaması |
| S06 | Dafo Fomtec AB, **LS xMax**, Revised **2025-04-22** | [Üretici PDF](https://www.fomtec.com/wp-content/uploads/2022/04/Fomtec%E2%94%AC%C2%AE-LS-xMax.pdf), s.1 revision, s.2 proportioning/application | Erişildi; URL'deki 2022 tarihi belge revizyonu değildir; üretici oranı ve uygulama ayrımı |
| S07 | NAFFCO, **Aqueous Film Forming Foam (AFFF) Concentrate**, FILMPLUS ürün tablosu; tarih/revizyon yok | [Üretici sayfası](https://www.naffco.com/en/aqueous-film-forming-foam-afff), Specifications / Use Concentration | Erişildi; ürünlere göre 1%,3%,6% örnekleri; D243 için ürün önerisi veya güncel kullanım onayı değil |
| S08 | Viking, **Model E Spray Nozzles VK810–VK817**, Form **F_062104**, **20.06.15 Rev.20.1** | [Üretici PDF](https://www.vikinggroupinc.com/sites/default/files/migrated/062104.pdf), teknik s.1, s.4, **s.10 Figure 7** | Erişildi; bu alınan sürümün güncel ürün seçimi için en son sürüm olduğu doğrulanmadı; denklem/birim kanıtı |
| S09 | NFPA, **NFPA 13 Second Draft Technical Committee FINAL Ballot Results (A2024)**, memorandum **2023-12-06** | [Resmî komite PDF](https://docinfofiles.nfpa.org/files/AboutTheCodes/13/13_A2024_AUT_SSD_SD__ballot_final.pdf), SR-1169, Table 28.3.4.8.1, PDF s.5–6; SR-1171 alternatif metinleri ayrıca var | Erişildi; **komite taslağı**, yayımlanmış nihai 2025 standardı değildir |
| S10 | NFPA, **NFPA 13 2025** | [Development sayfası](https://www.nfpa.org/codes-and-standards/nfpa-standard-development-process/13), [LiNK 2025](https://link.nfpa.org/all-publications/13/2025) | Baskı tanımlandı; LiNK yalnızca JavaScript kabuğu döndürdü, tam normatif maddeler erişilemedi: SOURCE_IDENTIFIED_BUT_NOT_ACCESSIBLE |
| S11 | Türk Loydu, güncel kural portalı | [Kural listesi](https://www.turkloydu.org/yayinlar/turk-loydu-kurallari/), [RuleRead](https://tlrule.turkloydu.org/RuleRead.aspx?lang=tr) | Landing/koşullar erişildi; ilgili güncel normatif doküman alınamadı: SOURCE_IDENTIFIED_BUT_NOT_ACCESSIBLE |
| S12 | Türk Loydu, Chapter 107 **Naval Ship Technology — Ship Operation Installations and Auxiliary Systems**, January 2016 | [Resmî eski PDF konumu](https://www.turkloydu.org/pdf-files/turk-loydu-kurallari/cilt-e/chapter-107-naval-ship-technology-ship-operation-installations-and-auxiliary-systems-2016-JAN.pdf), §9 G/I adayları | Aramada bulundu, tam dosya fetch timeout: SOURCE_IDENTIFIED_BUT_NOT_ACCESSIBLE; tarihsel/naval metin güncel TL şartı diye kullanılmadı |
| S13 | IMO, **OSV Chemical Code**, A.1122(30), adopted **2017-12-06** | [Resmî karar PDF](https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/AssemblyDocuments/A.1122%2830%29.pdf), §9.3.6, annex s.36 / PDF s.38 | Erişildi; dar sistem bağlamı karşılaştırması; güncel amendment kapsamı ayrıca kontrol edilmeli |

Ek taramalar: IMO fire protection sayfası eski 2015 FSS yayınını listeliyor;
current-publications listesi S02 tercih edildi. Eski TYCO F960/Q-48 belgesinde
OBSOLETE ibaresi görüldüğünden güncel cihaz seçimi kaynağı yapılmadı; nozul
kanıtı için S08 kullanıldı. Blog, forum, üçüncü taraf standart kopyası ve
atfedilmemiş hesaplayıcılar production kural kaynağı olarak kullanılmadı.
S03 PDF screenshot denemesi ve S09 screenshot erişimi hata verdi; bu kaynaklar
metin katmanından incelendi. Denklemler arama indeksindeki aynı üretici metniyle
eşleştirildi. Görsel kontrol başarıyla yapılmış gibi raporlanmaz.

## 3. Mevzuat ve uygulama ayrımları

S01 tarihsel metninde ch.14 §2.2.1, tanker deck foam için alan/monitor üzerinden
birden çok talebin en büyüğünü kullanır; §2.2.1.2 süreyi inert gas durumuyla
20/30 dakika olarak ayırır. Ch.7 §2.1.1.2'deki 5 L/(min·m²) **water spray**,
ch.8 §2.5.2.3'teki 5 ise **sprinkler** bağlamındadır. Ch.6 high-expansion
machinery-space yaklaşımı hacim/dolum esaslıdır. Bu farklı sistemlerden tek
bir q=5/t=30 köpük profili çıkarılamaz. S01 güncel mevzuat doğrulaması değildir.

S13 §9.3.6, OSV chemical cargo-deck/tank bağlamında 10 L/(min·m²), üstte
cofferdam bulunmasına göre 30/20 dakika örneği verir. Farklı kapsam olduğundan
S01 ile otomatik SOURCE_CONFLICT değildir; ortak defaulta indirgeme yanlıştır.

| Uygulama | İncelenen kaynak rolü | D243 kararı |
|---|---|---|
| Machinery-space sabit high-expansion foam | S01 tarihsel ch.6; S05/S06 ürün bilgisi | Alan×q×t hesabı eksiksiz hacim dolum tasarımı sayılmaz |
| Tanker deck foam | S01 tarihsel ch.14; güncel S02 tam metin yok | q ve t için gemi/inert-gas/alan tanımı gerekir |
| OSV chemical deck/tank | S13 §9.3.6 | Cargo/cofferdam bağlamı olmadan kriter taşınmaz |
| Fire-main / düz su hattı | S03 yöntem, S04 sınırlamalar | Yalnız sürtünme basınç kaybı; komple pompa seçimi değil |
| Seawater hattı HW | Açılan kaynaklar tuzluluk/sıcaklık/rejim için genel marine onay vermiyor | SOURCE_REQUIRED; su yöntemi izni buraya sessiz genişlemez |
| Sprinkler / directional water-spray nozzle | S08 cihaz ailesi; S01 water sistemleri | Cihazın K/basınç kontratı gerekir; tüm nozullara evrensel katsayı yok |
| Helideck / hangar / farklı yakıt sınıfı | S05/S06 ürün uygulaması bir mevzuat kapsamı değildir | Bu araştırmada sayısal kriter kabul edilmedi; SOURCE_REQUIRED |
| Fuel/oil hidrolikleri | Fire HW kapsamı dışında | Mevcut Darcy aynen korunur |

Gerekli gelecek context: ship_type, flag/class, rule_edition/effective_basis,
space_type, protected_area_basis, fire/system_type, fuel/cargo_class,
foam_product, water_type, mixture_basis; gerekiyorsa inert_gas/cofferdam.
Bu context alanları mevcut System Profile/Circuit kimliğinin yanında tutulur;
“Yangın” seçmek tek başına bu değerleri belirlemez.

## 4. Köpük: kaynak kararı ve tanımlı matematik

### q, t ve Cfoam

Workbook q=5 için **köpük çözeltisi uygulama yoğunluğu** yorumu hücrelerle
tutarlıdır, fakat hangi koruma/risk için seçildiği bilinmiyor. Genel normatif
değeri **SOURCE_REQUIRED**; production default yasak. Yeni projede açık q
seçimi **USER_PROJECT_ASSUMPTION** olabilir. A×q, tek tip yoğunluk uygulanmış
alanın çözeltisi debisidir; expanded foam/air dahil hacmi değildir.

t=30 da workbook için **WORKBOOK_REFERENCE_ONLY**, genel dayanağı
**SOURCE_REQUIRED**. Gemi/sistem/risk özelinde süre değişir; proje kriteri
olarak girilebilir. Mevcut 30 dakikayı “IMO/TL minimumu” diye etiketleme yok.

Cfoam ürün ve uygulamadan bağımsız 3% olamaz. S05 oranı açıkça çözelti
hacmine bağlar. S06 hidrokarbon uygulamasında 3%, Class A uygulamasında
0.3–1% belirtir. S07 ürün tablosunda 1%,3%,6% ayrı ürünlere aittir.
Bu değerler yalnızca oranların ürün/servis bağımlı olduğunu kanıtlar;
bir ürünü seçmez veya düzenleyici uygunluğunu onaylamaz.

### Karışım kontratı

Kaynak: S05 description, S06 s.2. **SOURCE_VERIFIED_CONTEXT_DEPENDENT**:
karışım oranı seçilmiş ürünün tarif ettiği konsantre/nihai çözelti hacim oranıdır.
Bu temel altında aşağıdaki cebir **DERIVED_FROM_VERIFIED_RULE** olur:

```
c = Vconcentrate / Vsolution              (dimensionless volume fraction)
Qsolution = A * q
Qfoam = c * Qsolution
Qwater = (1 - c) * Qsolution
Vfoam = Qfoam * t                         (constant flow and constant c)
```

İki sıvının tarif edilen nominal hacimsel proportioning yaklaşımı kullanılır;
kütle fraksiyonu, yoğunluk eşitliği veya hassas termodinamik hacim toplamsallığı
iddiası değildir. Proportioner toleransları, gerçek pompaların sapmaları,
viskozite/ürün/sıcaklık ve ölçülmüş induction rate ayrı ekipman şartlarıdır.
Faz 1 modelinde `mixture_basis=CONCENTRATE_VOLUME_PER_SOLUTION_VOLUME` açık olmalı.
Suyla karışıp hava almadan önceki solution ile expanded foam ayrı kavramlardır.

### 0.97 ve 15 kararları

0.97 yeni modelde, hacimsel c=.03 seçildiyse **DERIVED_FROM_FOAM_FRACTION**
karar etiketi alır; formal kaynak sınıfı **DERIVED_FROM_VERIFIED_RULE**.
Workbook E30'un hardcode ve E29 etiketinin tutarsız olduğu değişmez. Tarihsel
niyet kanıtlanmış değildir; importta otomatik düzeltme yapılmaz. Yeni taslakta
1−c açıkça gösterilir ve kullanıcı eski bağımsız factor'den geçişi görür.
`FIRE-FOAM-WATER-001` matematiksel model için RESOLVED; legacy hücre niyeti
WORKBOOK_REFERENCE_ONLY olarak kalır.

14.94→15 için bu workbook'a bağlanabilen bir seçim/yuvarlama kaynağı bulunmadı.
Karar etiketi **DISPLAY_OR_MANUAL_SELECTION_ONLY**, tarihsel kaynak sınıfı
**WORKBOOK_REFERENCE_ONLY**. Hesap 14.94 kalır; selected_capacity ayrı açık
kullanıcı tercihi olarak **USER_PROJECT_ASSUMPTION** taşır. Gizli yukarı yuvarlama,
design/redundancy margin yok. S03'ün yaşlanma için C önerisi bir pompa debisi
yuvarlama kuralı değildir. `FIRE-PUMP-SELECTION-001` tarihsel gerekçe için
SOURCE_REQUIRED; gizli marj uygulanmaması yönündeki yazılım kararı kesindir.

## 5. Hazen–Williams kaynak biçimi ve sınırlı kabul

S03 s.2 yayımlanmış equation/unit paketi:

```
r_bar_per_m = 6.05e5 * Q_lpm**1.85 / (CHW**1.85 * Di_mm**4.87)
delta_p_bar = r_bar_per_m * length_m
```

**SOURCE_VERIFIED_CONTEXT_DEPENDENT**. Q hacimsel debi, Di iç çap,
CHW boyutsuz ampirik katsayıdır. Çıktı **sürtünme BASINÇ kaybı**, m yük değildir.
Katsayı 605000 bu pratik birimlere aittir; boyutsuz evrensel SI katsayısı değil.
Workbook denklem ailesi ve üsleri aynıdır; Ptotal bar, P per-length bar/m olarak
eşleştirilebilir. Bu eşleştirme workbook'un kaynak tarihi iddiası değildir.

S03 kendi inductor tasarım bağlamında C≤100 tavsiyesi verir. Bu tavsiye D243
genel defaultu değildir; workbook C120/140'ı aynı ekipmana otomatik onaylamaz.
S04, HW'nin su dışı sıvılar için kullanılmaması ve başlangıçtaki turbulent-flow
esasını belirtir. Viskozite/sıcaklık etkisi formülde açık parametre değildir.
Bu araştırma evrensel sıcaklık/çap/hız alt-üst sınırı doğrulamadı; sayısal limit
uydurulmaz. Seawater veya concentrate/solution için uygulama yetkisi ayrıca gerekir.

**Üs kararı:** seçilen yayımlanmış pratik biçim **1.85 / 4.87** olarak sürümlenir.
S04 Table 3.1 farklı unit/formulation bağlamında debi üssü **1.852** kullanır.
Bu iki konvansiyon rastgele karıştırılmaz; S03 katsayısına yalnızca 1.852 yazmak
onaylı yeni formül değildir. Yeni SI katsayısı türetilmedi. Darcy değişmedi.
`FIRE-HW-UNITS-001`: equation/unit alt sorunu RESOLVED; marine seawater
uygulanabilirliği ayrı **SOURCE_REQUIRED** alt sorusu olarak sürer.

## 6. Dokuz C satırının kaynak karşılaştırması

Referans S09, SR-1169 Table 28.3.4.8.1, PDF s.5–6. Aşağıdaki “eşleşme”
resmî komite dokümanında görülmeyi belirtir; **nihai yayımlanmış normatif
NFPA 13 2025 doğrulaması değildir**. Bu nedenle source-match durumu ve
production sınıfı ayrı sütunlardadır.

| Workbook etiketi / C | Kaynakta değer | Koşul / eşleşme | İstenen satır durumu | Production sınıfı |
|---|---|---|---|---|
| Unlinen cast or ductile iron /100 | 100 | Unlined karşılığı, özgün typo korunur | SOURCE_VERIFIED (doküman eşleşmesi) | SOURCE_IDENTIFIED_BUT_NOT_ACCESSIBLE (nihai normatif kabul) |
| Black Steel dry incl. preaction /100 | 100 | Geleneksel dry; özel atmosfer satırları ayrıdır | CONTEXT_DEPENDENT | SOURCE_REQUIRED |
| Black Steel wet incl. deluge /120 | 120 | Wet/deluge | SOURCE_VERIFIED (doküman eşleşmesi) | SOURCE_IDENTIFIED_BUT_NOT_ACCESSIBLE |
| Galvanized (all) /120 | Dry100; wet120 | “all” genellemesi uyuşmuyor | SOURCE_CONFLICT | SOURCE_CONFLICT |
| Plastic (listed) all /150 | 150 | Listed kapsamı | SOURCE_VERIFIED (doküman eşleşmesi) | SOURCE_IDENTIFIED_BUT_NOT_ACCESSIBLE |
| Cement-lined cast or ductile iron /140 | 140 | Lining koşulu | SOURCE_VERIFIED (doküman eşleşmesi) | SOURCE_IDENTIFIED_BUT_NOT_ACCESSIBLE |
| copper tube or stainless steel /150 | 150 | Kaynak ayrıca brass içeriyor | SOURCE_VERIFIED (doküman eşleşmesi) | SOURCE_IDENTIFIED_BUT_NOT_ACCESSIBLE |
| Asbestos Cement /140 | 140 | Malzemenin güncel kullanımına izin anlamına gelmez | SOURCE_VERIFIED (doküman eşleşmesi) | SOURCE_IDENTIFIED_BUT_NOT_ACCESSIBLE |
| Concrete /140 | 140 | Aynı değer | SOURCE_VERIFIED (doküman eşleşmesi) | SOURCE_IDENTIFIED_BUT_NOT_ACCESSIBLE |

**8/9 satırın değer/koşul eşleşmesi bulundu; 1 genelleme çatışıyor. Güncel nihai
standarda dayalı production-default olarak doğrulanan satır sayısı 0/9.**
Tablodaki dar SOURCE_VERIFIED sözü bu sayıyı değiştirmez.
`FIRE-HW-C-SOURCE-001` nihai edition/applicability için SOURCE_REQUIRED.

C anahtarı yalnız malzeme olamaz: condition, lining, age/inspection basis,
wet/dry/preaction/deluge, iç atmosfer, su/servis, kaynak ve edition gerekir.
S09 komite metni özel nitrogen/vacuum koşullarını ayırır; bunlar yeni default
olarak alınmadı. S04 yeni boru katsayısı ve yaş etkisini ayırır. S03'ün daha
muhafazakâr cihaz tavsiyesi de farklı kapsamdır. Doğru context seçilmeden tek
“en iyi C” kararı verilmez. **CHW ≠ Darcy roughness k**; alanlar arası aktarım yok.

## 7. Nozul kararı / FIRE-NOZZLE-FORMULA-001

Workbook A25: `Q = Kx(P^-2)`. S08 Figure 7'de yayımlanan ilişki:

```
Q_lpm = K_metric * sqrt(p_bar)
K_metric unit = (L/min)/sqrt(bar)
```

S08 teknik s.1/10, Model E su püskürtme nozulları için katsayıyı orifice/cihaz
özelliği ve basıncı nozul girişindeki akış halindeki residual pressure olarak
tanımlar. Atmosfere boşalan cihazda bu gauge basıncıdır; mutlak basınç doğrudan
kullanılmaz. Kapalı/back-pressure uygulamasında uygun Δp ve cihaz ilişkisi
ayrıca doğrulanır. Pump discharge pressure doğrudan nozul basıncı değildir.
K birim taşır; gpm/√psi ile L/min/√bar aynı sayısal K değildir.

Kaynak ilişkisi **SOURCE_VERIFIED_CONTEXT_DEPENDENT**, workbook ile karşılaştırma
etiketi **WORKBOOK_TRANSCRIPTION_ERROR_LIKELY**. Literal −2 üssü debiyi basınçla
azaltır; kaynak +1/2 artırır. İki ifade eşdeğer değildir. Bu bulgu workbook
yazarının yazım niyetinin kesin kanıtı değildir; eski hücre değiştirilmez.

Issue **SOURCE_REQUIRED** olarak kalır: workbook cihazı/K tanımı bilinmiyor,
source expression'ın o hesaba uygulanması ve model değişikliği açık karar ister.
Kaynaklı fiziksel ilişki çözülmüştür, legacy mapping çözülmemiştir.
**NO_NUMERIC_FIXTURE**: workbook'ta nozul girdi/çıktısı yok.
Arbitrary K ile workbook doğrulama testi üretilmedi. Eski sürüm teknik doküman
ürünün güncel kabulünün kanıtı olmadığı için otomatik cihaz defaultu da yoktur.

Gelecek Knozzle: üretici+model+orifice+K unit+fluid+pressure reference+range+
revision/source/verification. K üretici verisi seçimi veya aynı metadatayla
kullanıcı girişi olabilir; keyfi generic Library katsayısı olmaz. Override,
cihaz kimliği değiştiğinde yeni record/selection gerektirir; gerekçesiz
manufacturer value değiştirme veya verification yükseltme olmaz.

## 8. Master rule-decision table

S kimlikleri §2'de organization/document/edition/URL/erişim tarihini tam olarak
tanımlar. Formal classification yalnızca bu fazın izin verdiği sözlüktendir.
Karar etiketleri (0.97, approximate15, transcription) ayrı açıklamadır.
“Production-ready” aşağıdaki dar kapsamı belirtir; bu faz uygulama yapmaz.

| Rule ID | Engineering item | Workbook | Proposed production rule | Source org | Document | Edition/revision | Section/table | Verification status | Applicability | Override allowed? | Production-ready? | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FIRE.FOAM.APPLICATION_RATE | q | 5 | Açık q; evrensel default yok | IMO / proje | S01,S02; proje kriteri | As-adopted2000 / current2026 erişilemedi | ch.7/8/14 karşılaştırması | USER_PROJECT_ASSUMPTION | Seçilmiş alan/koruma/risk | Gerekçeli proje girdisi | YES input; NO default | Workbook'un foam q dayanağı SOURCE_REQUIRED |
| FIRE.FOAM.DURATION | t | 30min | Açık süre, otomatik30 yok | IMO / proje | S01,S13 | 2000 /2017 tarihsel kapsam | ch.14 §2.2.1.2 /§9.3.6 | USER_PROJECT_ASSUMPTION | Belirtilmiş sistem/gemi | Evet, kaynakla | YES input; NO default | Mevzuat kontrolü ayrı |
| FIRE.FOAM.CONCENTRATION | c | .03 | Ürünün solution-volume fraksiyonu | Viking/Fomtec | S05,S06 | F_081620 /2025-04-22 | description /s.2 | SOURCE_VERIFIED_CONTEXT_DEPENDENT | Kaynaklanan ürün/risk; generic3 değil | Ürün değişiminde yeniden seçim | YES definition; NO global value | Ürün seçilmemişse NOT_CONFIGURED |
| FIRE.FOAM.SOLUTION_FLOW | Qsolution | Çarpımlarda örtülü | Aq | Tanımlı yoğunluk / kaynaklı mix | S05,S06 + cebir | Yukarıdaki | §4 | DERIVED_FROM_VERIFIED_RULE | Uniform solution application | Türevi override etme; girdiyi değiştir | YES | Çok mahal/simultane seçim yok |
| FIRE.FOAM.CONCENTRATE_FLOW | Qfoam | Aqc | cQsolution | Viking/Fomtec | S05,S06 | Yukarıdaki | description /s.2 | DERIVED_FROM_VERIFIED_RULE | Nominal volumetric mixture | Hayır | YES | Gerçek proportioner sapması ayrı |
| FIRE.FOAM.WATER_FLOW | Qwater | Aq×.97 | (1−c)Qsolution | Viking/Fomtec | S05,S06 | Yukarıdaki | Aynı | DERIVED_FROM_VERIFIED_RULE | İki sıvılı nominal hacimsel karışım | Hayır | YES | Legacy hardcode değişmez |
| FIRE.FOAM.CONCENTRATE_VOLUME | Vfoam | Aqtc | Qfoam×t | Mix + zaman integrali | S05,S06 + cebir | Yukarıdaki | §4 | DERIVED_FROM_VERIFIED_RULE | Sabit debi/oran/süre | Hayır | YES | Storage reserve/margin dahil değil |
| FIRE.PUMP.CAPACITY_SELECTION | selected flow | 14.94→15 | Ham hesap + ayrı seçilen değer | Kullanıcı workbook/proje | Workbook H12 | Sürüm yok | A12/G12/H12 | USER_PROJECT_ASSUMPTION | Yalnız açık ekipman seçimi | Gerekçe ile | YES separation; NO auto15 | Display/manual selection only |
| FIRE.HW.EQUATION | Düz hat pressure loss | 605000,1.85,4.87 | S03 biçimi sabit sürüm | JCI/SKUM | S03 | FDS-2017084-04 ©2024 | s.2 | SOURCE_VERIFIED_CONTEXT_DEPENDENT | Su, dolu hat, turbulent yöntem esası | Katsayı/üs override yok | YES limited water | Seawater scope ayrı blocked |
| FIRE.HW.C_VALUE | CHW | 9 satır | Kaynaklı bağlam seçimi/manual used C | NFPA / kullanıcı | S09,S10 | A2024 draft /2025 tam metin yok | Table28.3.4.8.1 draft | SOURCE_REQUIRED | Malzeme+koşul+servis+edition | Öneri varsa gerekçeli | YES sourced input; NO seeded defaults | Galvanized all çatışması |
| FIRE.HW.SEAWATER_APPLICABILITY | Marine kapsam | Belirtilmemiş | İlgili sınıf/üretici kabulü bekle | TL/IMO/uygulama kaynağı | S02,S11 | Exact source eksik | NOT_CONFIGURED location | SOURCE_REQUIRED | Tuzluluk/sıcaklık/rejim/boru | Hayır; gerekçe source yerine geçmez | NO | Generic water gate burayı açmaz |
| FIRE.NOZZLE.K_FACTOR_RELATION | Q(K,P) | K×P^-2 | Seçilmiş uygun cihazda K√p | Viking | S08 | F_062104 Rev20.1 | s.10 Figure7 | SOURCE_VERIFIED_CONTEXT_DEPENDENT | Model E/source-compatible nozzle | Formül override yok | NO workbook mapping | Issue SOURCE_REQUIRED |
| FIRE.NOZZLE.K_VALUE | K | Veri yok | Model/orifice/source/unit ile | Üretici | S08 örnek kaynak | Seçilen cihaz revizyonu gerekli | Teknik s.1/4 | NOT_CONFIGURED | Belirli cihaz/akışkan/aralık | Yeniden seçim veya gerekçeli kullanıcı kaynağı | NO current input | Arbitrary K yok |
| FIRE.UNITS.CONVERSIONS | Birim sınırı | ×.06 | Explicit L/min↔m³/h, L↔m³,bar↔Pa | Birim tanımları | §9 contract | D243.Fire.Units.v1 önerisi | §9 | DERIVED_FROM_VERIFIED_RULE | Aynı fiziksel quantity | Hayır | YES | Empirik katsayı yeniden türetilmez |
| FIRE.HYDRAULICS.LOCAL_LOSSES | Fittings | Yok | V1 dışı | — | — | — | — | OUT_OF_SCOPE | Düz hat çıktısına gizli ekleme yok | — | NO | “Toplam sistem kaybı” denmez |
| FIRE.PUMP.COMPLETE_SIZING | Head/selection | Debi var, head yok | V1 dışı | — | — | — | — | OUT_OF_SCOPE | Tam pompa tasarımı yok | — | NO | Gerekli Debi terminolojisi |

## 9. Final proposed units contract

Foam domain'de açık pratik birimler korunur: L/min, L, min, m², boyutsuz
fraksiyon. Gerekçe: kaynakların oran ve application-density sözleşmesiyle
doğrudan izlenebilirlik; gizli SI katsayısı yaratmadan workbook karşılaştırması.
HW equation boundary S03 birim paketidir. Mevcut D243 Darcy iç temsili değişmez.

| Quantity / field | UI | Canonical domain | Equation boundary / conversion |
|---|---|---|---|
| A / protected_area_m2 | m² | m² | Aynı; alan tanımı context'te |
| q / application_density_lpm_m2 | L/(min·m²) | Aynı | m² ile çarpım L/min |
| t / application_duration_min | min | min | Saniye input varsa /60; sabit akış hacmi Q×t |
| Cfoam / foam_fraction | % | 0–1, volume/solution-volume | UI /100; .03↔3%, auto-detect yok |
| water_fraction | % veya açık boyutsuz | 1−c | Seçili mix basis'te türetilir |
| Qsolution/Qfoam/Qwater | L/min ve m³/h | L/min | m³/h=×.06; m³/s=/60000; m³/h→L/min=×1000/60 |
| Vfoam/Vsolution | L ve m³ | L | m³=/1000; Vsolution destek sonucu |
| selected_capacity | m³/h | m³/h | Hesap debisinden ayrı; ham precision korunur |
| CHW / hazen_williams_c | boyutsuz | boyutsuz | Pozitif; material.roughness_mm ile bağlantısız |
| Di / inside_diameter_mm | mm | mm | S03 mm; OD/et geometri adaptörü mevcut sözleşmede |
| L / pipe_length_m | m | m | V1 physical straight length; equivalent fitting length dahil değil |
| HW flow | L/min veya m³/h | L/min | Source equation yalnız L/min ile |
| r_HW | bar/m | bar/m | S03 published coefficient basis |
| Δp_HW | bar, isteğe bağlı kPa | bar | Pa=×100000; kPa=×100; m head ile eşitlenmez |
| Pnozzle (conditional) | bar | bar residual/Δp tanımıyla | Kaynağa uygun gauge inlet vs outlet farkı; absolute yasak |
| Knozzle (conditional) | (L/min)/√bar | Aynı | K birimi inputun parçası; psi/kPa K otomatik eşitlenmez |
| Qnozzle (conditional) | L/min | L/min | K√p yalnız onaylı cihaz modelinde; şu an gate BLOCKED |

Basınç→yük dönüşümü V1'e dahil değil. Gelecekte Δp/(ρg) için kaynaklı yoğunluk,
g ve akışkan koşulu gerekir. Sıcaklık/viskozite doğrulaması ayar olarak varsa
ayrı unit metadata taşır; mevcut HW equation bunları kullanmış gibi görünemez.
TR ekranda 14,94/483,06; JSON sayılar ve bağımsız hesap ham hassasiyetle.
Tüm aktif inputlar finite; A/q/t/Di/CHW/L için geçerli pozitif tasarım girdileri,
fraksiyon matematik sınırı0–1; ürün uygunluğu ayrıca doğrulanır. Kaynak bağımlı
min/max veya nozzle pressure-range uydurulmaz.

### Parametre ve override kararı

| Parametre | Girdi politikası | Kaynak/override davranışı |
|---|---|---|
| A | USER_INPUT_REQUIRED | Proje/mahal alan tanımı; kullanılan değer ve revision |
| q | USER_INPUT_REQUIRED | Default yok; proje kriteri+source basis; doğrulanmış öneriden sapmada reason |
| t | USER_INPUT_REQUIRED | q'dan bağımsız provenance; otomatik30 yok |
| Cfoam | USER_INPUT_REQUIRED | Ürün verisi veya açık kaynaklı proje seçimi; Library varsa seçim olabilir, zorunlu katalog yok |
| Qsolution/Qfoam/Qwater/Vfoam | CONTEXT_DERIVED | Aynı vaka girdilerinden; ayrı sonuç override yok |
| CHW | USER_INPUT_REQUIRED | Manuel kaynaklı C veya ileride Library; evrensel default yok |
| Knozzle | SOURCE_BLOCKED | Önce cihaz/uygulanabilirlik kararı; sonra unit/source'lu Library veya manual input |
| HW coefficient/exponents | DEFAULT_ALLOWED | Yalnız seçilmiş source equation version içinde kilitli yöntem tanımı; proje varsayılanı değil |
| selected_capacity | USER_INPUT_REQUIRED | Opsiyonel alan seçilecekse açık kullanıcı girdisi; recommended/used ayrımı |

USER_INPUT politikası recommended_value yaratmaz. Onaylı katalog önerisi varsa
EngineeringValue.SUGGESTED, recommended_value, used_value, SourceReference,
override_reason birlikte saklanır. Kritik formül/birim/applicability engeli
override gerekçesiyle kaldırılmaz. q/t/c tek opaque profile içine gömülmez.

## 10. Workbook–source bağımsız sayısal karşılaştırma

Yalnız onaylı Python ile Decimal precision=40 kullanıldı. Tam ara hassasiyet
korundu; aşağıdaki uzun değerler rapor için kısaltılmıştır.
Fark=source biçimi yeniden üretim−kayıtlı Excel değeri.

| Vaka | Workbook | Kaynaklı/derive model sonucu | Fark / yorum |
|---|---|---|---|
| A210,q5,t30,c.03 | 945 L | 945 L | 0; kriter seçimi onaylanmış değildir |
| A230/223/96/190/358, diğerleri aynı | 1035/1003.5/432/855/1611 L | Aynı | Her biri0; önceki fixture'lar korunur |
| A1660,q5,c.03 köpük | 249 L/min;14.94m³/h | 249;14.94 | 0; no hidden margin |
| Aynı vaka su, c.03 | 8051 L/min;483.06m³/h | (1−.03)×8300=8051;483.06 | 0; yeni model derived, eski E30 hardcode |
| H12 yaklaşık | 15m³/h | Hesap14.94 | −.06; selection ayrı |
| HW C120,Q2000 L/min,Di105mm,L150m | .01581188602;2.371782902 | **.015811886016440190658816 bar/m**; **2.371782902466028598822398 bar** | Per−3.55980934e−12; total+4.66028599e−10; kayıtlı son basamak farkı |
| HW C140, aynı Q/Di/L | .0118886383;1.783295745 | **.011888638296673058912446 bar/m**; **1.783295744500958836866903 bar** | Per−3.32694109e−12; total−4.99041163e−10 |
| S03 bağımsız yayımlanmış örnek: Q600,Di55.501,C100,L30 | Workbook fixture değil | .053283194221809519212710 bar/m;1.598495826654285576381295 bar | Üretici .053 ve1.6 sunumuyla uyumlu; yuvarlamayı ara hesaba taşıma |
| Workbook nozul | Sayısal örnek yok | NO_NUMERIC_FIXTURE | −2 ve+1/2 için sahte fixture üretilmedi |

HW sayısal uyum bu kez yayımlanmış birim paketiyle birlikte gösterilmiştir;
C seçiminin/deniz suyu uygulanabilirliğinin onayı yine ayrı konudur.
Nozul için S08'in nominal discharge curves'ü cihaz kanıtıdır, workbook fixture'ı değildir.

## 11. Readiness kapıları, source conflicts ve kalan işler

FOAM READY koşulları: q/t açık proje kriteri, alanın tanımı, c'nin hacimsel
solution basis'i ve kaynak/ürün seçimi kaydedilir. Girdiler eksikse NOT_CONFIGURED.
Regülasyon doğrulaması veya approved concentrate selection iddiası yapılmaz.
Eksik evrensel default hesap motoru modelini engellemez.

HW READY koşulları: yalnız yukarıdaki yayımlanmış su/düz-hat biçimi,
CHW/Di/Q/L açık, source version sabit, yöntem uygunluğu context'te açıkça kabul
edilmiş. Seawater/karışım/viskozite-sıcaklık kapsamı belirsizse ilgili çalışma
BLOCKED, source gerekçesi görünür. Source kabul kaydı gerçek kanıtın yerine
geçmez. Sistem uygunluğu yalnız kullanıcı checkbox'ıyla doğrulanmış sayılmaz.
Basınç kaybı ≠ pompa head; lokal kayıpları sıfır kabul edip total system üretme yok.

NOZZLE BLOCKED: denklem ailesi kaynaklandı ama workbook cihaz eşlemesi ve
K kontratı yok. Phase 1 yalnız typed placeholder/configuration contract yapabilir;
literal−2 veya varsayılan K üretim hesabı yok.

| Açık konu | Durum | Sonraki kanıt/karar |
|---|---|---|
| FIRE-FOAM-CRITERIA-001 | SOURCE_REQUIRED | Workbook'un risk/gemi/mahal sistemi ve q5/t30 gerekçesi; güncel geçerli standard/proje kriteri |
| FIRE-FOAM-WATER-001 legacy niyet | WORKBOOK_REFERENCE_ONLY | Tarihsel yazar onayı yok; yeni volumetric model çözülmüş durumda |
| FIRE-HW-UNITS-001 marine alt kapsamı | SOURCE_REQUIRED | Seawater/salinity/temperature/regime için ilgili tasarım kaynağı/class kabulü |
| FIRE-HW-C-SOURCE-001 | SOURCE_REQUIRED | Seçilen yürürlükteki NFPA/TL/marine source exact text ve uygulanabilirliği |
| Galvanized(all)120 | SOURCE_CONFLICT | Dry/wet/koruma koşulu ayrılmadan default kullanma |
| FIRE-NOZZLE-FORMULA-001 | SOURCE_REQUIRED | Cihaz/ürün ve K tanımı; kaynaklı+1/2 modele geçiş kararı |
| FIRE-PUMP-SELECTION-001 geçmiş15 gerekçesi | SOURCE_REQUIRED | Workbook yazarı/proje ekipman seçimi; üretim core14.94 kalır |
| Güncel TL / FSS2026 / NFPA13-2025 tam normatif metin | SOURCE_IDENTIFIED_BUT_NOT_ACCESSIBLE | İlgili izinli tam metin ve edition/effective-context doğrulaması |

S03'ün C≤100 tavsiyesi ile S09'un malzeme tablosunu aynı koşul için rakip
otorite gibi seçmek yanlış olur. İlkinde cihaz/yaşlanma/AHJ, ikincisinde sprinkler
tasarım koşulu vardır. Context bilinmiyorsa SOURCE_CONFLICT olarak tutulur;
kapsam ayrıldığında farklı ruleset olarak saklanır. q/t'nin farklı sistemlerde
farklı olması kendi başına çelişki değildir. Workbook'a bağlanamayan kaynaklar
workbook tarihsel kökeni gibi sunulmadı.

## 12. Mimari/Library etkisi ve Phase 1 kararı

Önceki Fire workspace → Foam/HW/Nozzle düzeni geçerli. Foam alt modeli solution
volume fraction ile kesinleşir. HW sonucu adı `pressure_loss_bar`, destek
`pressure_gradient_bar_per_m` olabilir; `hf_HW_m` kullanılmaz. Nozul future
contract'ta device_relation_id/formula_version ve pressure_reference zorunlu.
Nozzle stage blocked kalır; üçlü görünüm üç production-ready calculator demek değildir.

Library adayları (bu fazda kayıt yok):

| Dataset | Gerekli alanlar | Ownership / verification / override | V1 gereği |
|---|---|---|---|
| Foam application criteria | q ve t için bağımsız value/unit/source/edition; ship/space/system/risk/area basis | Onaylı factory record kilitli; user/project record ayrı; recommended/used/reason | Opsiyonel; açık manuel kriter yeterli |
| Foam concentrate products | manufacturer/model, ratio+volume basis, fuel/water/device scope, source revision, approval reference | Ürün verisi source-specific; arbitrary override yeni source selection olur | Katalog opsiyonel, oran provenance zorunlu |
| HW C | material/lining/condition/wet-dry/atmosphere/service/age basis, C, source+edition | User/reference/factory sahipliği ayrı; koşulsuz material→C yok; gerekçeli suggestion | Opsiyonel; kaynaklı manual C mümkün |
| Nozzle device coefficients | maker/model/orifice/K+unit, relation version, fluid, residual/Δp basis, pressure range, revision | Cihaz verisiyle traceable; unrelated K override yok | Nozul sonraya kaldığı için V1'de gerekmez |

VerificationStatus ile bu belgenin source sınıfları aynı enum değildir.
Kaynak nesnesi kuruluş/belge/bölüm/revizyon/verification_date taşır; source
blocker ayrı domain finding'dir. Kaynak metadata'sı olmayan girdiye VERIFIED
etiketi atanmaz. Library, DB veya snapshot şeması şimdi değişmez.

System Profile olarak Yangın Söndürme mevcut System/Circuit yapısına temizce
eklenebilir. Tek-fluid SystemContext nedeniyle base_water/concentrate/solution
rolleri workspace metadata'sında ayrı tutulmalıdır. Ruleset/applicability ve
mixture basis kavramsal eklemedir; yeni paralel persistence sistemi gerekmez.
Darcy k ve CHW arasında cross-population yapılmaz. Mevcut dört modül korunur.

**Fire V1 önerisi:** Foam required flow/volume + **sınırlı su HW straight-pipe
pressure-loss**. Marine seawater HW ve workbook nozzle dışarıda/blocked.
Kullanıcıya “Köpük Konsantresi Gerekli Debisi”, “Deniz Suyu Bileşeni Gerekli Debisi”,
“Köpük Konsantresi Gerekli Hacmi” denmeli; “Tam Yangın Pompası Boyutlandırması”
denmemeli. Deniz suyu bileşeni debi hesabının READY olması, deniz suyu HW
uygulanabilirliğinin READY olduğu anlamına gelmez.

**FIRE PHASE 1 ENTRY: YES**, yalnız kullanıcı ayrıca başlatırsa. Scope:
immutable domain models, units, per-value provenance, context/applicability,
blocked/no-config states, explicit link/version contracts. q5/t30/c3/CHW/K
hidden defaults, yeni UI, DB/seed, kaynak engelli calculator yok.
Tam sonraki faz adı: **FIRE PHASE 1 — Domain Models, Units & Provenance Contracts**.
Kaynak gereken marine/nozzle konuları paralel dokümantasyon backlog'unda kalır;
Phase 1 bunların anlamını tahmin etmek zorunda değildir.

## 13. Faz doğrulaması

Production davranışı değişmedi. Yalnız bu belge ve önceki analize tarihli Phase0
eki değişir. Yeni test/helper production dosyası eklenmez. Final tam test sonucu,
referans hash kontrolü, commit SHA ve ending status teslim raporunda bildirilir.
Final regresyon: **1552 passed, 0 failed**, **62.14 s**, uyarı yok.
Workbook SHA-256 değişmedi, önceki analiz metni birebir korundu ve git staged
kapsamı yalnızca iki Markdown belgesi olarak doğrulandı.
Genel sonuç: **SOURCE_RESOLUTION_PASS_WITH_BLOCKERS**. Phase 1 otomatik başlamaz.
