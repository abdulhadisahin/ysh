# D243 V2 — FIRE PHASE 1 — Domain Models, Units & Provenance Contracts

Tarih: 2026-10-21. Branch: `d243-v2-handoff`.
Başlangıç commit: `b2d083add49fe4a10ed27ed010de247be0a294c8`.
Baseline: **1552 passed, 0 failed**, 62.76 s. Baseline'da sandbox pytest-cache
yazma uyarısı vardı. Kullanılan tek Python `.venv314\Scripts\python.exe`, 3.14.8.

Yetkili kapsam belgeleri: [teknik analiz](fire_fighting_module_analysis.md) ve
[Phase 0 kaynak kararları](fire_fighting_source_decisions.md). Bu faz kaynak
kararlarını yeniden yorumlamaz; talimatın açıkça izin verdiği saf hesapları ekler.

## Dosya ve entegrasyon sınırı

Yeni namespace `YSH/engineering/fire/`:

| Dosya | Sorumluluk |
|---|---|
| __init__.py | Hafif paket tanımı; otomatik startup kaydı yok |
| enums.py | FireCalculationType, FireSourceStatus, FoamMixtureBasis, HWApplicability, FireRuleId ve immutable SYMBOLS |
| models.py | Frozen/slots/keyword-only input, result ve NozzleRequest |
| calculators.py | İki saf hesap fonksiyonu ve deterministik nozul engeli |
| provenance.py | Mevcut EngineeringValue'yu parametreye bağlayan küçük tipli kayıt ve tutarlılık kontrolü |
| units.py | Eksik Fire birim sınırları; mevcut pressure converter delegasyonu |
| validation.py | Mevcut ValidationError/ValidationIssue ile alan bazlı sayı doğrulama |
| pipe_adapter.py | Mevcut PipeInputState/PipeSelectionSnapshot uygulanmış değer adaptörü |

FireCalculationType değerleri `fire_foam_system`, `fire_hazen_williams`,
`fire_nozzle`. Mevcut ModuleCode sayfa/snapshot sınırında kullanıldığı için bu
fazda genişletilmedi. Ayrı domain kimlikleri sonraki entegrasyonun açık eşleştirme
noktasıdır; mevcut MODULES dört modül kalır. Snapshot serializer/allowlist,
History, PDF ve UI bu tipleri henüz tüketmez.

Mevcut production dosyası değiştirilmez. DB/migration/repository/seed, Library,
sekme/menu/button, FormulaStep/Formula View/PNG, History/PDF ve
CalculationSnapshot değişikliği yoktur. Ek bir servis/persistence sistemi kurulmadı.

## Köpük sözleşmesi

`FoamSystemInput` zorunlu alanları:
`protected_area_m2`, `application_density_lpm_m2`, `application_duration_min`,
`foam_fraction`, `mixture_basis`.
`mixture_basis` açık typed
`FoamMixtureBasis.CONCENTRATE_VOLUME_PER_SOLUTION_VOLUME` olmalıdır.
Mass fraction veya expanded foam hacmi bu sözleşme değildir.
q=5/t=30/c=.03 defaultu yoktur. `provenance` immutable tuple, `context`
mevcut frozen SystemContext'tir; boş metadata kaynak onayı yaratmaz.

`calculate_foam_system(input)` yalnız şu ilişkileri uygular:

```
Qsolution = A * q
Qfoam = c * Qsolution
Qwater = (1 - c) * Qsolution
Vfoam = Qfoam * t
```

`FoamSystemResult`: input'un aynısını ve `solution_flow_lpm`,
`foam_concentrate_flow_lpm`, `water_flow_lpm`, `foam_concentrate_volume_l`
alanlarını tutar. `FIRE_FOAM_VOLUMETRIC_1` formula_version ve dört FireRuleId
kimliği class metadata'sıdır. Hesap source/verification bilgisini değiştirmez.
Matematiksel başarı mevzuat/ürün uygunluğu veya pompa ekipman seçimi değildir.
Selected pump=15 gibi ayrı bir seçim sonucu üretilmez; margin/rounding yok.

## HW sözleşmesi ve uygulanabilirlik

`HazenWilliamsInput` zorunlu alanları: `flow_lpm`, `inside_diameter_mm`,
`pipe_length_m`, `hazen_williams_c`, `applicability`.
Opsiyonel evidence `provenance`, mevcut `SystemContext`, uygulanmış
`PipeInputState`'tir. Scope için sessiz WATER_ONLY defaultu yoktur.

`calculate_hazen_williams(input)` yalnız `HWApplicability.WATER_ONLY` kabul eder:

```
r = 605000 * Q**1.85 / (CHW**1.85 * Di**4.87)
delta_p = r * L
```

Katsayı/üsler calculators.py içinde tek isimli tanımdadır. Kaynak Phase0 S03:
JCI/SKUM ZF Inductor FDS-2017084-04, s.2; başka SI katsayısı türetilmedi,
1.852 varyantına geçilmedi. Formula version `FIRE_HW_SKUM_605000_1_85_4_87_1`.
`HazenWilliamsResult`: input, `pressure_loss_per_m_bar`,
`total_pressure_loss_bar`; `FIRE.HW.EQUATION` kimliğiyle.
Çıktı bar/m ve bar BASINÇ kaybıdır; m yük/head değildir.

`SEAWATER_SOURCE_REQUIRED` ve `OTHER_FLUID_SOURCE_REQUIRED` girdileri saklanabilir
ama execution `FireCalculationBlocked.status=SOURCE_REQUIRED` ile durur.
`NOT_CONFIGURED` için aynı hata türü NOT_CONFIGURED döner. Issue kimliği
`FIRE-HW-UNITS-001`. L=0 da scope engelini aşamaz.
WATER_ONLY bir kaynak/uygulanabilirlik beyanıdır, fiziksel uygunluk testi değildir;
çağıran katman fluid kimliğini, sıcaklık/rejimi ve kapsamı doğru kaynakla seçmelidir.
Bu paket akışkan DB'sini çözmez ve kaynak onayı üretmez.
Fuel/oil, seawater, konsantre/karışım ve marine compliance etkinleştirilmedi.
Darcy çekirdeği ve roughness_mm anlamı değişmedi; CHW için k alias/dönüşümü yok.

## Validation ve birimler

| Girdi | Koşul |
|---|---|
| Köpük A/q/t | Sonlu gerçek sayı ve >0 |
| Aktif köpük c | **0<c<1** |
| HW Q/Di/CHW | Sonlu gerçek sayı ve >0 |
| HW L | **L≥0** |
| Tüm inputlar | Bool, text, None, NaN, infinity reddedilir |
| Hesap çıktısı | Sonlu; geçerli pozitif girdide underflow/overflow başarı sayılmaz |

Aktif köpükte strict fraksiyon, HW'de sıfır uzunluk bu fazın kullanıcı talimatıdır;
önceki belgede önerilen endpoint/aktif hat politikalarına göre önceliklidir.
Sıfır uzunlukta total=0, per-m kayıp hesaplanabilir kalır. CHW için regülasyon
min/max limiti yoktur. ValidationError.issue alanı code/field_key taşır;
UI metni/i18n veya yeni ekran eklenmez. Kaynak/applicability engeli ayrıca
FireCalculationBlocked status/issue_id ile yakalanabilir.

| Helper | Açık sınır |
|---|---|
| percent_to_fraction / fraction_to_percent | /100, ×100; dönüştürücü0–1 uçlarını kabul eder, aktif model daha dardır |
| lpm_to_m3h / m3h_to_lpm | ×60/1000, ×1000/60 |
| litres_to_m3 / m3_to_litres | /1000, ×1000 |
| bar_to_pa / pa_to_bar | Mevcut engineering.units.convert_pressure delegasyonu |

Eski shared unit helper değiştirilmedi. L/min shared helper'da olmadığı için
eksik sınır Fire paketinde isimli helper'dır. Signed birim dönüşümü fiziksel
girdi validation'ından ayrıdır; domain modeli pozitifliği denetler.
Domain sayı alır; Türkçe virgül parse/format UI fazına aittir. `3` yüzde→`.03`,
`.03` yüzde→`.0003`; tahmin/heuristic yok. Ara/final sonuçlarda round yok.

Semboller: A,q,t,Cfoam,Qsolution,Qfoam,Qwater,Vfoam,CHW,Di,L,rHW,ΔpHW;
Knozzle yalnız future metadata için ayrıldı. Cfoam/CHW karıştırılmaz.

## Provenance ve boru adaptörü

`ParameterProvenance(field_name, engineering_value, source_status)` yalnız
binding/classification ekler. source, used_value, recommended_value,
override_policy/reason ikinci kez tanımlanmaz; mevcut EngineeringValue içindedir.
Kaynak sınıfları Phase0'ın on değerini korur; boolean'a indirgenmez.
SourceStatus ile SourceReference.verification_status ayrı boyutlardır; çağıranın
verdiği classification kabul edilir, sistem hiçbirini aritmetikten türetmez veya
otomatik yükseltmez. Böylece UNVERIFIED bir referans hesap sonunda da UNVERIFIED'dır.
Yeni bir kaynak denetimi/sınıflandırma motoru eklenmedi.

Model construction sırasında metadata.used_value sayısal inputa, metadata.unit
canonical birime eşit olmalıdır. Tekrarlı/unknown alan ve çelişkili değer/birim
ValidationError verir. Units: m², L/(min·m²), min, fraksiyon/CHW için `1`,
Q için L/min, Di için mm, L için m. Kaynaklı veri kanıtı opsiyoneldir; eksik tuple
bilginin olmadığını gösterir, fabricated USER_INPUT/VERIFIED eklenmez.
Recommended/used farkında reason gereksinimini mevcut EngineeringValue uygular.
Result tam input'u tuttuğu için metadata/gerekçe kaybolmaz.

`hazen_williams_from_pipe(...)` mevcut PipeInputState.used_values.hydraulic_values()
üzerinden gerçek uygulanmış Di/Q alır. Q m³/h→L/min dönüştürülür; OD−2t yeniden
hesaplanmaz, teorik çap kullanılmaz. Input içinde aynı frozen PipeInputState
tutulur: mode, status, applied source UUID/revision/time, observed revision,
pipe identity, standard ve dimension source izleri korunur. Model çelişkili
pipe evidence ile manuel Q/Di değiştirilmesini reddeder.
CHW ve scope ayrı zorunlu girdidir; malzemeden/defaulttan türetilmez.
Adapter canlı kaynağa bakmaz, link/update/keep-current yapmaz. Bu kararlar
mevcut PipeInputState sözleşmesindedir. Stale/keep-current girdiyi tüketmek
mevcut applied değerleri kullanır; sessiz upstream update yoktur.

## Nozul engeli

`NozzleRequest` opsiyonel device_id, source-bearing nozzle_k ve pressure_bar
taslak alanlarını taşır. Class metadata: fire_nozzle, SOURCE_REQUIRED,
FIRE-NOZZLE-FORMULA-001, FIRE.NOZZLE.K_FACTOR_RELATION.
`calculate_nozzle` **daima FireCalculationBlocked** yükseltir. K ve basınç tam
doldurulsa da sonuç yoktur. Q=K√p veya legacy P^-2 için aktif equation bulunmaz.
NozzleResult/sahte0/başarılı snapshot yoktur.

## Test matrisi ve performans

`YSH/tests/test_fire_phase1_domain.py`: **110 passed**, 0.67 s.

- Altı workbook köpük hacmi;210m² örneğinde1050/31.5/1018.5 L/min ve945L.
- 1660m² örneğinde8300/249/8051 L/min;14.94/483.06m³/h; gizli15 yok.
- Süre yalnız hacmi değiştirir; c=.06 ile su fraksiyonu yeniden türetilir.
- HW C120/C140:2.3717829024660286 /1.7832957445009588bar,
  relative tolerance1e-13; kaynak örneği ve L0 testi.
- Geçersiz/sonlu olmayan girdiler, typed basis/scope, immutable input/result,
  metadata mismatch/duplicate, override reason ve tüm source status'ları.
- Deniz suyu/diğer sıvı/no-config engelleri, supplied K dahil nozul engeli.
- Manual/linked actual geometry; stale/keep-current/update, identity/revision izi.
- Birim round-trip, fraksiyon uçları, overflow; fresh-process import kontrolü.

Hesaplarda full float precision kullanılır; örneğin1003.5 için son bit farkı
test toleransıyla değerlendirilir, üretim sonucuna round eklenmez.
20,000 çağrı ölçümünde köpük yaklaşık **4.99 µs/çağrı**, HW **3.40 µs/çağrı**;
tek yerel fresh import ölçümü85.70ms. Ölçümler platforma bağlı tanısaldır,
CI için zaman limiti yazılmadı. Fresh process'te Tk, Matplotlib, DB/repository,
UI veya network-client importu bulunmadı. Mevcut startup paketi import etmez.

Full regresyon: **1662 passed, 0 failed**, **61.81 s**, uyarı yok.
Mevcut Boru/Transfer/Basma/Emme
testleri aynı tam suite içinde çalışır; mevcut kodu değiştirmeyen git kapsamı
ayrıca kontrol edilir. Referans Excel SHA-256:
`bd9aa871454c184afdb45e14bd0c008818d49701d5cc92e1de7ca89126159474`.
Dosya **approved untracked reference input**, stage/commit edilmez.

## Kalan engeller ve sonraki faz

q5/t30 ve seçilmiş ürün oranının mühendislik dayanağı, marine seawater HW,
C kataloglarının exact normative edition/condition kapsamı, nozzle device/K
eşlemesi ve güncel normatif kaynak erişimi Phase0 backlog'undadır.
Mevcut matematik domain kontratı bu engelleri çözülmüş göstermez.

Sonraki öneri: **FIRE PHASE 2 — Foam Workflow / Application Contracts**;
hazır saf hesabı tekrar yazmadan kaynak/girdi/vaka koordinasyonunu ele almak.
Phase2 bu görevde başlatılmaz. Genel sonuç: **PHASE1_PASS_WITH_BLOCKERS**.
