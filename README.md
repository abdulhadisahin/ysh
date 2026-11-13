# D243 V2 Final — Kullanım Kılavuzu

D243, boru ve tulumba boyutlandırma ile yangın sistemi hesaplarını yerel olarak
yürüten Windows masaüstü uygulamasıdır. Çalışma sırasında internet gerektirmez.

**Kabul edilen sürüm:** `D243-V2-FINAL` →
`c9c8dfe8096a128302867d2ece630d9ebb3b5dd7`.
Tam regresyon **2080 passed, 0 failed**; paket durumu **RELEASE_READY**.
[Release özeti ve doğrulama kapsamı](docs/V2_FINAL_RELEASE.md).

## Başlatma ve temel akış

Windows dağıtımı `D243_V2_Windows_x64.zip` içindedir. ZIP'in tamamını çıkarın;
`D243` klasöründeki `D243.exe` dosyasını açın. EXE'yi `_internal` klasöründen
ayırmayın. Kaynaktan çalıştırma komutu ve Python ortamı
[geliştirici handoff'unda](YSH/docs/AI_HANDOVER.md) bulunur.

**Proje → Sistem ailesi → Modül → Girdiler → Hesapla → Sonuç →
Formülü Göster / Geçmiş / PDF**

1. Proje oluşturun veya mevcut projeyi açın. Kalıcı hesap geçmişi için hesapları
   kayıtlı proje açıkken yapın; proje olmadan üretilen geçmiş oturuma aittir.
2. Sol taraftaki tek **Sistem** seçicisinden Yakıt veya Yangın ailesini seçin.
   Projedeki sistem profili, devre ve akışkan bilgisi ayrı mühendislik bağlamıdır;
   aile seçimi katsayı, akışkan özelliği veya standart seçmez.
3. Modülü açın, girdileri alanların birimlerine göre doldurun. Belirsiz alanların
   kısa ipuçlarını kullanın. Ondalık için `12,5` veya `12.5` girilebilir; binlik
   ayırıcı ve karışık nokta/virgül kullanmayın.
4. Modülün ana hesap düğmesini seçin. Boş sonuç alanındaki kısa mesaj, gerekli
   sonraki adımı gösterir. Girdi değişikliği yeni hesap gerektirebilir.
5. Ana sonuç, destekleyici değerler, uyarılar ve kaynak özetini birlikte inceleyin.
   **Kaynak doğrulaması gerekli** gibi durumları gözden kaçırmayın.
6. Sonucu açıklamak, önceki kayıtları incelemek veya uygun kaydı PDF olarak almak
   için ikincil araç grubunu kullanın. Proje değişikliklerinizi kaydedin.

## Hesap modülleri

| Aile | Modül | Kullanım |
| --- | --- | --- |
| Yakıt | Boru Tasarımı | Debi/hız ile çap ve gerçek kütüphane ölçüsü önerisi; ayrı et kalınlığı/bükme aşaması. |
| Yakıt | Yakıt Transfer Tulumbası | Tasarım kapasitesi/süre hesabı veya açıkça ayrılmış ampirik referans-gemi tahmini. Seçilen gerçek pompa kapasitesi isteğe bağlıdır. |
| Yakıt | Tulumba Basma Yük Kaybı | Manuel veya bağlı boru girdileriyle basma hattı kayıpları. |
| Yakıt | Tulumba Emme Yük Kaybı ve ENPY | Önce emme hidrolik kaybı, ardından ENPY. İsteğe bağlı NPSHr yoksa bu karşılaştırma yapılamaz. |
| Yangın | Köpük Sistemi | Alan, uygulama yoğunluğu, süre ve konsantrasyonla çözelti/konsantre/su ihtiyacı. `%3` için **3** girin. |
| Yangın | Hazen-Williams | Açık su servisi ve kabul edilen su kapsamı için sürtünme basınç kaybı. |

Nozzle ve deniz suyu hidrolik yöntem/uygulanabilirlik hesapları
**BLOCKED / SOURCE_REQUIRED** durumundadır. Bunlar tamamlanmış hesap modülleri
değildir; kaynak kararı olmadan etkinleştirilmez.

## Kütüphane ve kaynak durumları

Kütüphane, kaynağı ve uygulanabilirliğiyle birlikte mühendislik kayıtlarını sunar.
Kaydı görmek veya yenilemek değeri kendiliğinden hesaba uygulamaz. Seçili kayıt
özetini, hangi alanı beslediğini, kullanılan değeri ve varsa öneriyi kontrol edin.

| Durum | Anlamı |
| --- | --- |
| Manuel / Manual | Kullanıcının girdiği değer. Öneri yokken manuel değer kullanmak override değildir. |
| Kütüphane / Library | Açıkça seçilmiş kütüphane kaydından gelen öneri/kaynak. |
| Bağlı / Linked | Kimliği ve uygulanmış revizyonu saklanan bir kaynak bağlantısı. |
| Değiştirildi / Override | Gerçek bir öneriden farklı kullanılan değer; gerekiyorsa gerekçe girilir. |
| Güncel değil / Stale | Kaynağın değiştiği veya artık aynı şekilde kullanılamadığı gözlenmiş; uygulanmış değer henüz yenilenmemiştir. |

Bu etiketler kaynak doğrulaması veya standart uygunluğu onayı yerine geçmez.

- **Bağlı Boru → Güncelle:** Yeni uygulanmış gerçek iç çap/debi değerlerini açıkça
  alır; etkilenen hesabı yeniden yapın. **Mevcut Değeri Koru:** Önceki değerleri
  saklar; güncel değil durumu sürer.
- **Fire Kütüphane → Güncelle:** Öneri/kaynak revizyonunu yeniler, kullanılan
  sayısal değeri korur. Kullanılan değer yeni öneriden farklıysa override gerekçesi
  gerekebilir. **Mevcut Değeri Koru:** Uygulanmış eski kaydı ve değerleri korur.

Kaynak veya bağlantı değişimini fark etmek, değerleri sessizce değiştirmez.
Hesaplarda kullanılan kaydı açıkça uygulayın; kütüphanedeki örnekleri otomatik
standart gereği saymayın.

## Sonuç, açıklama, geçmiş ve PDF

Boş sonuç paneli kısa yönlendirme verir. Geçerli hesap sonrasında panel opaklaşır;
ana sonuç öne çıkar, uyarılar ayrı görünür. Kontroller ve metinler opaktır.

**Formülü Göster / Hesabı Açıkla**, geçerli sonuç olduğunda etkinleşir ve o hesabı
anlatır. **Geçmiş**, güncel sonuç olmasa da önceki kayıtları incelemek için
kullanılabilir. Tarihsel kayıtlar salt okunurdur; yeniden hesaplanmaz.

Hesap sayfasındaki **PDF**, geçerli ve güncel sonuçla eşleşen kayıt için kullanılabilir.
Girdiler değiştiğinde eski sonuç güncelmiş gibi dışa aktarılmaz. Eski, eksiksiz bir
kaydın raporunu Geçmiş'ten alın; bu rapor kaydın donmuş değerlerini ve kaynaklarını
kullanır. Yeni Library değerleri eski rapora taşınmaz.

Normal kullanıcı verileri `%LOCALAPPDATA%\YSH\data` altında `projects.db` ve
`libraries.db` dosyalarındadır; kurulum klasörüne yazılmaz.

## Geliştirici belgeleri

- [V2 Final geliştirici handoff'u](YSH/docs/AI_HANDOVER.md)
- [Mimari](ARCHITECTURE.md) · [Geliştirme kuralları](RULES.md)
- [Paketleme](build/README_BUILD.md) · [V2 Final release özeti](docs/V2_FINAL_RELEASE.md)

İç Python paketinin ve veri dizininin `YSH` adı uyumluluk için korunur;
kullanıcıya sunulan ürün adı **D243**'tür.
