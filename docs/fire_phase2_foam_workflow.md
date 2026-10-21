# D243 V2 — FIRE PHASE 2 — Foam Workflow / Application Contracts

Tarih: 2026-10-21. Branch: `d243-v2-handoff`.
Başlangıç commit: `e79dc7653f9b5c52f6059d932ede384a47b589fa`.
Baseline: **1662 passed, 0 failed**, 62.22 s; sandbox cache yazma uyarısı vardı.
Yalnız `.venv314\Scripts\python.exe` (Python 3.14.8) kullanıldı.

Bağlayıcı girdiler: [teknik analiz](fire_fighting_module_analysis.md),
[Phase 0 kaynak kararları](fire_fighting_source_decisions.md),
[Phase 1 domain kontratı](fire_phase1_domain_contracts.md).
Kaynak kararları değiştirilmedi. Bu faz sadece **Foam System Demand** workflow'udur.

## Mimari ve API

```
Gelecek UI / çağıran kod
  → services.fire_foam_service.FoamCalculationService.calculate(FoamWorkflowInput)
  → engineering.fire.calculators.calculate_foam_system(FoamSystemInput)
  → engineering.formula.fire_foam.foam_steps(precomputed_result)
  → FoamWorkflowResult + detached primitive payload
```

Yeni dosyalar:

- `YSH/engineering/fire/foam_workflow.py`: frozen input/result/read-model/message tipleri.
- `YSH/services/fire_foam_service.py`: validation koordinasyonu, tek domain çağrısı,
  kaynak mesajları, sonuç özeti ve deterministik payload.
- `YSH/engineering/formula/fire_foam.py`: mevcut FormulaStep ile dört adımlık anlatım.
- `YSH/tests/test_fire_phase2_foam_workflow.py`: workflow/compatibility/regresyon testleri.

Mevcut TR/EN kataloglarına yalnız FormulaStep/girdi/result/source-message anahtarları
eklendi. Sayfa, görünür sekme/menu/button veya startup/service registration yok.
Domain formülleri ve Phase 1 dosyaları değiştirilmedi. Servis A×q, c×Q,
(1−c)×Q veya Q×t hesaplarını tekrarlamaz; domain sonucunu anlatır ve dönüştürür.
Formula builder da girdi/result değerlerini kopyalar, sonuç hesaplamaz.

## Input ve provenance sözleşmesi

`FoamWorkflowInput` alanları:

| Alan | Sözleşme |
|---|---|
| protected_area_m2 | ParameterProvenance, canonical m² |
| application_density_lpm_m2 | ParameterProvenance, canonical L/(min·m²) |
| application_duration_min | ParameterProvenance, canonical min |
| foam_fraction | ParameterProvenance, canonical boyutsuz `1` |
| mixture_basis | Açık FoamMixtureBasis.CONCENTRATE_VOLUME_PER_SOLUTION_VOLUME |
| raw_inputs | Opsiyonel immutable FoamRawInput tuple; ilk girişin sayı+birim gözlemi |
| context | Mevcut immutable SystemContext, verilmezse tanımsız context |
| assumptions | Kullanıcının açık metin varsayımları, immutable tuple |
| case_id / revision | İsteğe bağlı UUID / pozitif int, revision başlangıcı1 |

Draft inputta A/q/t/c/basis eksik kalabilir; `calculate()` bunları `required`
ValidationIssue ile alan bazında reddeder. Sayısal fallback veya öneri yaratılmaz.
q5/t30/c.03 yalnız explicit örnek girdidir. Her inputun used_value, source,
recommended_value, override_policy/reason bilgisi mevcut EngineeringValue'dadır.
ParameterProvenance Phase1 tipidir; ikinci provenance modeli kurulmadı.

Inputun field_name/birim/değer tutarlılığı Phase1 FoamSystemInput ile doğrulanır;
pozitiflik, sonlu sayı ve strict0<c<1 matematik doğrulaması aynen devredilir.
Hata halinde FormulaStep veya kısmi workflow sonucu dönmez.
Öneri yoksa recommended_value=None kalır. SUGGESTED override reason şartını
mevcut EngineeringValue uygular. Hesapta yalnız used_value kullanılır.

Raw gözlemler canonical birimle, foam_fraction için ayrıca `%` ile kabul edilir;
örneğin6% gözlemi .06 normalized değerle eşleşmelidir. Birim/değer çelişkisi,
tekrarlı veya unknown alan reddedilir. UI strings/locale parsing bu fazda yok.
Gözlem verilmezse payload aynı normalized sayıyı `representation=normalized_input`
olarak kaydeder; özgün ekran girdisi uydurmaz. Verilen gözlem `original_input`
etiketi taşır. Raw ve normalized girişler ayrı saklanır.

## FormulaStep üretimi

| Sıra / stable ID | Denklem | Sonuç birimi |
|---|---|---|
| 0 / fire.foam.solution_flow | Qsolution = A × q | L/min |
| 1 / fire.foam.concentrate_flow | Qfoam = Cfoam × Qsolution | L/min |
| 2 / fire.foam.water_flow | Qwater = (1 - Cfoam) × Qsolution | L/min |
| 3 / fire.foam.concentrate_volume | Vfoam = Qfoam × t | L |

ID'ler rastgele kimlik/tarih/çeviri içermez. Her adım formül, input/output
FormulaVariable'ları, ilgili used_values, substitution, ham result, stable
TR/EN title_key ve ENGINEERING_CALCULATION classification içerir.
Örneğin su yerine koyması `(1 - 0.03)` gösterir; opaque .97 sabiti yoktur.
Substitution ham sayı metnidir, domain hesabında round yapılmaz; mevcut renderer
görünür sayıları kendi kabul edilmiş formatter'ıyla sunar.

FormulaStep.sources içindeki CALCULATED referans, Phase0 nominal volumetric
kontratından türetilmiş ilişkinin kural kimliğini belirtir. Input kaynakları
FormulaVariable.source ve used_values.source içinde ayrı kalır. Formül kaynağı
q5/t30/%3 için kaynak veya mevzuat onayı sayılmaz. Kaynak doğrulaması uydurulmaz.
Kaynak sınıfı mevcut FormulaStep şemasında ayrı alan olmadığından global şema
genişletilmedi; source_status tam olarak workflow evidence/messages/payload'da
taşınır. SourceReference.verification_status bağımsız biçimde korunur.
Mevcut schema, asset resolver, MathText/text fallback ve görsel davranış değişmedi.
Yeni PNG yok. Headless `step_sections()` TR ve EN ile uyum testi geçti.

## Calculation validity ve source readiness

Başarılı aritmetikte `calculation_validity=VALID` olur. Bu compliance etiketi değildir.
Workflow status CALCULATED veya CALCULATED_WITH_SOURCE_WARNING'dır.

| Input source_status | Mesaj kategorisi |
|---|---|
| SOURCE_VERIFIED / DERIVED_FROM_VERIFIED_RULE | Ek kaynak mesajı yok |
| SOURCE_VERIFIED_CONTEXT_DEPENDENT | SOURCE_CONTEXT_REQUIRED |
| USER_PROJECT_ASSUMPTION | INFO: açık varsayım kaydı; sayının yanlış olduğu söylenmez |
| WORKBOOK_REFERENCE_ONLY | WARNING: yalnız referans workbook dayanağı |
| SOURCE_REQUIRED/CONFLICT/NOT_CONFIGURED/INACCESSIBLE/OUT_OF_SCOPE | SOURCE_REQUIRED kategorisi; özgün source_status aynen korunur |

Her FoamSourceMessage field_name/source_status/category/message_key taşır.
Mesaj sırası A,q,t,c sırasıdır. INFO dahil kaynak mesajı bulunan sonuç genel
CALCULATED_WITH_SOURCE_WARNING durumunu alır; bu matematiksel hata veya minimum
kriter ihlali değildir. q4.5 veya t17 için değer farklılığı uyarısı üretilmez.

SourceReadiness: mesaj yoksa READY, yalnız context mesajları varsa CONTEXT_REQUIRED,
başka kaynak mesajı varsa REVIEW_REQUIRED. READY, caller'ın verdiği source
sınıflarının özetidir; bağımsız kaynak audit'i veya regulatory compliance değildir.
SystemContext verilmiş olması uygulanabilirliği kendiliğinden onaylamaz.
Tüm source statüleri ve SourceReference verification değerleri hiç yükseltilmeden
payload'a geçer. SOURCE_REQUIRED girdi matematik geçerliyse hesaplamayı engellemez.

## Immutable sonuç, read model ve snapshot hazırlığı

`FoamWorkflowResult`: domain_result, dört formula_steps, warnings, status,
source_readiness, input_provenance, dört sayısal/unit/label_key summary,
primary_result_key ve immutable payload_json taşır.
Summary primary anahtarı **foam_concentrate_volume_l** seçildi. Bu, future History
sunum tercihi için açık anahtardır; akış çıktıları aynı kayıtta destek sonuçlarıdır.
Tek bir çıktının her mühendislik kullanımında baskın olduğu iddia edilmez.

Workflow sürümü **fire.foam.workflow.v1**. Payload version1 ayrı bir yerel
evidence kontratıdır; global CalculationSnapshot.schema_version değildir.
Domain formula_version ve dört FIRE.FOAM rule ID'si ayrıca taşınır.

Payload kapsamı:

- calculation_type, workflow/formula version, payload_version, rule_ids;
- supplied case_id/revision (otomatik UUID veya timestamp yok);
- raw_inputs, normalized_inputs, input_units ve mixture_basis;
- numeric results +units, foam/water m³/h ve concentrate volume m³ dönüşümleri;
- her alanın EngineeringValue/SourceReference/used/recommended/reason/source_status;
- FormulaSteps, source messages, source_readiness, calculation validity/status;
- frozen SystemContext, supplied assumptions, summary ve primary_result_key.

Mevcut `engineering.snapshots.serialization.canonical` yalnız primitive dict ve
zaten desteklenen SourceReference/SystemContext/FormulaStep için yeniden kullanılır.
Fire dataclass'ları global allowlist'e eklenmez. Özel Fire metadata'sı explicit
primitive/asdict sınırından geçer. Date/UUID/enum'lar mevcut helper ile dönüştürülür;
NaN/callback/UI/connection nesneleri kabul edilmez. Global snapshot şeması/decode
semantiği değişmez. JSON'dan mevcut FormulaStep ve SourceReference decode uyumu
test edildi; workflow'un kendisi için yeni persistence loader eklenmedi.

`to_json()` canonical string döndürür. `snapshot_payload` her çağrıda yeni
JSON primitive kopyası döndürür; dışarıda dict değiştirildiğinde frozen sonuç
ve saklanan evidence değişmez. Aynı input/context/revision için bytes aynı;
live Library lookup, current time veya çevresel default yoktur.

## Örnekler ve doğrulama

Tüm sayılar explicit fixture'dır; üretim varsayılanı değildir.

| Girdi | Domain/workflow sonucu |
|---|---|
| A210,q5,t30,c.03 | Qsolution1050, Qfoam31.5, Qwater1018.5 L/min; Vfoam945L=.945m³ |
| A1660,q5,t30,c.03 | Qsolution8300, Qfoam249=14.94m³/h, Qwater8051=483.06m³/h |
| recommended c.03, used.06 | Qfoam63 L/min, Vfoam1890L (A210); eski öneri ve “Project-selected approved concentrate” gerekçesi korunur |
| q4.5 ve SOURCE_REQUIRED | Matematik başarılı; source mesajı ve özgün status korunur |

Odaklı **38 test**: başarı/workbook/değişik kriterler, override/no recommendation,
tüm source status'ları, omitted required fields, Phase1 validation forwarding,
stable order/IDs ve tüm FormulaStep içerikleri, direct-domain eşitliği,
tek domain çağrısı, TR/EN helper rendering, immutable/detached payload,
JSON/source/step decode round-trip, raw-percent tutarlılığı, context/case/revision,
HW/nozzle regresyonu ve runtime file/network I/O engelleme testi.

Fresh process import testi Tk/Matplotlib/DB/repositories/UI/openpyxl/network
client import edilmediğini doğrular. Hesap sırasında file/network girişleri
engellendiğinde de sonuç üretildi. Workbook runtime dependency değildir.
1000 çağrılık yerel tanısal ölçüm: **2355.73 µs/çağrı**, JSON dahil;
payload yaklaşık14KB; tek fresh import214.76ms. CI zaman limiti eklenmedi.
Bu servis mevcut startup tarafından çağrılmadığı için yeni görünür modül yoktur.

Tam suite mevcut Boru/Transfer/Basma/Emme, Phase1 HW/nozul ve shared birim
regresyonlarını içerir. Final regresyon: **1700 passed, 0 failed**, **63.17 s**,
uyarı yok. Odaklı38 Phase2 testi0.87s içinde geçti.
Referans workbook SHA-256 değişmedi:
`bd9aa871454c184afdb45e14bd0c008818d49701d5cc92e1de7ca89126159474`.
Dosya **approved untracked reference input**; stage/commit edilmez.

## Donmuş sınırlar ve sonraki faz

DB/migration/seed/Library, project persistence, CalculationSnapshot, History,
PDF ve Formula View renderer değişmedi. Existing engine ve Phase1 HW/nozul
aynı kaldı. HW workflow veya nozul workflow eklenmedi; seawater HW ve nozul
blokları sürüyor. Ortak cross-module link yaratılmadı.
Mevcut proje tek JSON namespace mimarisi incelendi; gelecekte versioned
fire_fighting/foam_cases namespace bu payload/context ve case revision'ı
taşıyabilir. Şimdi namespace'in proje save/load'una kaydı yapılmadı.

Kalan işler: source/context-dependent q/t/c kriterleri, nozul cihaz/K eşlemesi,
marine seawater HW ve normatif katalog kaynakları; global snapshot/History/PDF
entegrasyonu ve görünür Fire UI sonraki ayrı fazlardır.
Önerilen sonraki faz **FIRE PHASE 3 — Hazen-Williams Workflow**.
Bu görev Phase3'ü başlatmaz. Sonuç: **PHASE2_PASS_WITH_BLOCKERS**.
