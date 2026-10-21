# D243 V2 — FIRE PHASE 3 — Hazen-Williams Workflow / FormulaStep Integration

Tarih: 2026-10-21. Branch `d243-v2-handoff`; başlangıç
`41f6face70faeeded8389dac0a5c9481ef550cdb`.
Python yalnız `.venv314/Scripts/python.exe`, 3.14.8.
Baseline **1700 passed, 0 failed**, 63.49 s; sandbox pytest cache yazma uyarısı vardı.

Bağlayıcı kaynaklar: [teknik analiz](fire_fighting_module_analysis.md),
[Phase 0 kaynak kararları](fire_fighting_source_decisions.md),
[Phase 1 domain](fire_phase1_domain_contracts.md),
[Phase 2 Foam](fire_phase2_foam_workflow.md). Kaynak kararları değiştirilmedi.

## Mimari ve API

`services.fire_hazen_williams_service.HazenWilliamsCalculationService.calculate(
HazenWilliamsWorkflowInput)` headless girişidir. Sıra: typed input → servis ve
uygulanabilirlik kapısı → provenance/domain validation → mevcut Phase 1 pipe
adapter (varsa) → tek `calculate_hazen_williams` çağrısı → iki FormulaStep →
immutable result ve canonical payload. Servis ve formula builder hesap yapmaz.
Domain'in 605000 / 1.85 / 4.87 biçimi tek authoritative uygulama olarak kalır.

Yeni dosyalar: `engineering/fire/hazen_williams_workflow.py`,
`engineering/formula/fire_hazen_williams.py`,
`services/fire_hazen_williams_service.py`,
`tests/test_fire_phase3_hazen_williams_workflow.py` ve bu belge.
TR/EN kataloglarına yalnız `fire.hw.*` anahtarları eklendi.

Phase 2'nin immutable numeric observation, summary ve source-message DTO'ları
(`FoamRawInput`, `FoamSummaryValue`, `FoamSourceMessage`) ve source readiness
enum'ları yeniden kullanılır. Bunlar denklem/basis/servis bilgisi içermez;
Foam kontratı veya davranışı bu fazda değiştirilmedi. Ayrı ortak framework yok.

## Input, birimler ve uygulanabilirlik

| Alan | Kontrat |
|---|---|
| flow_lpm | Explicit ParameterProvenance; L/min |
| inside_diameter_mm | Explicit ParameterProvenance; mm; LINKED adapter'dan da alınabilir |
| pipe_length_m | Explicit ParameterProvenance; fiziksel düz uzunluk m |
| hazen_williams_c | Explicit ParameterProvenance; boyutsuz `1` |
| service | HWService.WATER / SEAWATER / FUEL / UNKNOWN |
| applicability | Mevcut HWApplicability; yalnız WATER_ONLY hesaplanabilir |
| pipe_input | Opsiyonel mevcut frozen PipeInputState |
| raw_inputs | Opsiyonel immutable FoamRawInput tuple |
| context / assumptions | SystemContext / immutable text tuple |
| case_id / revision | Opsiyonel UUID / pozitif int |

Draft eksik olabilir, calculate eksik Q/Di/L/C alanını `required` ValidationIssue
ile reddeder. Hidden C, Excel fallback veya malzemeden C tahmini yoktur.
Q/Di/C>0, L≥0 ve finite doğrulaması mevcut domain/EngineeringValue tarafından
uygulanır; yeni regülasyon C sınırı konmadı. L=0 geçerlidir: rHW>0, total=0.

Servis **WATER ve WATER_ONLY birlikte** ister. Diğer tüm kombinasyonlarda,
adapter ve domain çağrısından önce `HWApplicabilityBlocked` yükselir:
`workflow_status=BLOCKED_APPLICABILITY`, `calculation_validity=NOT_CALCULATED`,
`status=SOURCE_REQUIRED`, issue `FIRE-HW-UNITS-001`. Numeric result/steps yoktur.
Fuel Darcy'ye yönlendirilmez. UNKNOWN/NOT_CONFIGURED defaultları başarı vermez.
Service sınıfı çağıranın açık akışkan/servis beyanıdır; SystemContext kimlikleri
saklanır, DB'den akışkan çözümlemesi veya etiketlerden tahmin yapılmaz.
Çağıran katman service ile seçilmiş context'in uyumundan sorumludur.
WATER_ONLY tam dolu su hattındaki sınırlı yöntem kapsamı beyanıdır;
sıcaklık/rejim veya marine compliance doğrulaması değildir.

## Manual / linked PipeSelection

Manual Di ayrı explicit inputtur. PipeInputState yoksa mode MANUAL,
source_selection_id/revision null ve pipe values null olur; sahte kimlik yok.
Mevcut MANUAL PipeInputState de desteklenir; explicit Q/Di evidence eşleşmelidir.

LINKED girdide Phase 1 `hazen_williams_from_pipe` actual applied Di/Q kullanır.
OD−2t veya theoretical diameter hesaplanmaz. Q explicit evidence hâlâ zorunludur
ve adapter'ın m³/h→L/min değeriyle eşleşmelidir. Di evidence verilirse aynı
uygulanmış çapla eşleşir. Di evidence verilmezse captured dimension source ile
LOCKED EngineeringValue oluşturulur; kaynak verification otomatik yükseltilmez,
Fire source_status SOURCE_REQUIRED kalır. Dimension source yoksa yalnız
uygulanmış geometriyi tarif eden doğrulanmamış PIPE_STANDARD referansı tutulur.

Mevcut unit helper 120 m³/h için float `2000.0000000000002` üretir. Bu değer
yuvarlanmaz; linked explicit Q bu helper çıktısı olmalıdır. Manual/link tam
eşitliği aynı normalized Q ve Di ile test edilir. 2000 L/min workbook vakası
ayrıca tam hassasiyetli toleransla test edilir. Eski helper semantiği değişmez.

Source selection/pipe ID, applied revision/time, observed revision, upstream
status, link status, kept_current ve applied PipeValues saklanır. Stale/missing/
different/unavailable supplied state ek `fire.hw.pipe_review` uyarısı üretir.
Servis observe/update/keep_current çağırmaz; frozen applied değerleri kullanır.
Canlı UI/project/latest selection sorgusu yoktur. FormulaVariable linked Q/Di
source_selection_id/revision taşır. CHW bağımsız kaynaklıdır; Darcy k/ε ile
aktarımı veya conversion helper'ı yoktur.

## FormulaStep ve kaynak ayrımı

| Sıra / ID | Denklem | Birim |
|---|---|---|
| 0 / fire.hw.unit_loss | rHW = 605000 × Q^1.85 / (CHW^1.85 × Di^4.87) | bar/m |
| 1 / fire.hw.total_loss | ΔpHW = rHW × L | bar |

TR başlıkları **Birim Uzunluk Başına Basınç Kaybı** ve **Toplam Basınç Kaybı**.
Her adım input/output variables, used EngineeringValues, substitution ve ham
domain result taşır. Basınç kaybı head/yük veya toplam sistem kaybı diye sunulmaz.
Kaynak JCI/SKUM ZF Inductor FDS-2017084-04 ©2024 p.2, Phase0 S03;
rule ID **FIRE.HW.EQUATION**. Formula source step.sources içindedir;
Q/Di/C/L source'ları ayrı variable/used_values/provenance alanlarındadır.
Kaynak verification değeri uydurulmaz. Stable ID'ler UUID/zaman/çeviri içermez.
FormulaStep şeması, Formula View renderer, MathText/text fallback, PNG ve
asset mapping değişmedi. Headless step_sections TR/EN uyumu test edildi.

## Status ve immutable payload

Başarılı matematik `calculation_validity=VALID`; workflow status CALCULATED
veya CALCULATED_WITH_SOURCE_WARNING. Source readiness ayrı READY,
CONTEXT_REQUIRED, REVIEW_REQUIRED değeridir. Phase2 source sınıfı davranışı
korunur: SOURCE_VERIFIED/DERIVED sınıfında mesaj yok, CONTEXT_DEPENDENT context
uyarısı, USER_PROJECT_ASSUMPTION bilgi, WORKBOOK_REFERENCE_ONLY uyarı,
diğer sınıflar SOURCE_REQUIRED kategorisi. Özgün source_status ve bağımsız
SourceReference.verification_status aynen kalır. Valid C + SOURCE_REQUIRED
hesaplanır ve source warning kalır. Regulatory compliance etiketi üretilmez.
Invalid input mevcut ValidationError verir; kısmi başarılı result üretilmez.

HazenWilliamsWorkflowResult frozen/slots: domain_result, iki formula_steps,
warnings/status/readiness, applicability/service, provenance, pipe_mode/state,
summary/primary key ve payload_json. Version **fire.hazen_williams.workflow.v1**.
Primary summary total_pressure_loss_bar; destek rHW,Q,Di,L,CHW.

Payload version1: calculation/workflow/formula version, rule IDs, mode,
raw/normalized inputs+units, context, service/applicability, assumptions,
case/revision, dört inputun EngineeringValue provenance'ı, captured pipe trace
ve applied PipeValues, result+units, FormulaSteps, warnings/readiness/validity,
summary/primary key. Raw observation canonical birimler ve flow için m³/h
kabul eder; çelişki/duplicate/unknown alan reddedilir. Verilmezse özgün UI
girdisi uydurulmaz, representation=normalized_input olur.

Mevcut canonical helper ile primitive dict/asdict ve mevcut desteklenen
FormulaStep/SystemContext/SourceReference serialize edilir. Global allowlist
ve CalculationSnapshot değişmez. Tüm seçim/project nesnesi serialize edilmez.
to_json canonical immutable string; snapshot_payload her erişimde detached
JSON copy döndürür. UUID/date/enum mevcut helper üzerinden çıkar; runtime
handle yok. Aynı supplied input bytes aynıdır; yeni timestamp/UUID üretilmez.
Future History/PDF bu captured evidence'i okuyabilir; bugün entegrasyon yoktur.

## Doğrulama ve donmuş sınırlar

Workbooks yalnız test fixture kaynağıdır; runtime xlsx/openpyxl/path lookup yok.
Q2000,Di105,L150 örnekleri: C120=**2.3717829024660286 bar**,
C140=**1.7832957445009588 bar** beklenen referanslarıyla rel1e-13 uyumlu.
rHW=total/L test edilir; direct domain/workflow equality birebirdir.

55 yeni Phase3 testi +38 mevcut Phase2 testi: **93 passed**, 1.07 s.
Manual/linked actual Di/revision, stale keep-current, source statüleri/override,
missing C, invalid/nonfinite, service gate-before-domain, stable IDs/equations/
units/source separation, raw validation, canonical/detached/decode round-trip,
TR/EN renderer, single engine call, nozzle block ve Foam regresyonu kapsanır.
Fresh import testi UI/Tk/DB/plotting/network client/openpyxl yüklenmediğini;
I/O guard testi runtime file/network erişimi olmadığını doğrular.
1000 yerel çağrı, JSON dahil: **1878.62 µs/çağrı**, payload10574 bytes.
Ölçüm tanısaldır; CI zaman limiti veya startup registration yoktur.

DB/migration/seed/Library, visible Fire UI, global snapshot, History/PDF,
Formula View, mevcut Darcy/Boru/Transfer/Basma/Emme ve Foam kodu değişmedi.
Tam regresyon: **1755 passed, 0 failed**, **63.05 s**, uyarı yok.
1700 mevcut test ve55 yeni test geçti; mevcut modüllerin sayısal regresyonları,
Formula View, History, Library ve PDF testleri aynı tam suite içinde çalıştı.

Referans Excel approved untracked reference input; stage/commit dışındadır.
SHA-256 `bd9aa871454c184afdb45e14bd0c008818d49701d5cc92e1de7ca89126159474`.

## Kalan kaynak engelleri / sonraki faz

Seawater HW SOURCE_REQUIRED; nozul FIRE-NOZZLE-FORMULA-001 blocked kalır.
C exact normative edition/context, galvanized all120 çatışması, güncel TL /
FSS2026 / NFPA13-2025 tam metin erişimi ve q/t/ürün kriterleri çözülmüş sayılmaz.
Önerilen sonraki faz: ayrı onaylı Fire snapshot/History/PDF entegrasyon
kontratları; UI entegrasyonuna geçmeden evidence round-trip sınırlarını belirlemek.
Bu görev Fire UI'ı otomatik başlatmaz. **PHASE3_PASS_WITH_BLOCKERS**.
