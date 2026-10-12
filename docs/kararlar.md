# Mimo Kurye: Kesinleşen Kararlar (devam dosyası)

> Yeni sohbete bu dosyayı yapıştır ve "kaldığımız yerden devam edelim" de.
> Tarih: 12 Ekim 2026, OpenAI Codex Hackathonu, DotsHub Beşiktaş, İstanbul.

## 1. Etkinlik bilgisi

- Hacking 09:30'da başladı, **teslim 16:00** (Google Form), etkinlik 18:00'de biter.
- Ön jüri 16:15-17:00: 1 jüriye **2 dk pitch + demo, 1 dk soru-cevap**. Final (ilk 6): 3 dk + 1 dk soru.
- Beş kriter, her biri %20: Problem ve değer / Execution ve kalite / Codex ve araç kullanımı / Potansiyel ve etki / Pitch.
- Krediler: Codex (2.500 kredi, ~$100), fal.ai ($50). Ücretli LLM API yok.
- Çerçeve "sıfırdan, bir günde" diyor. Açık bir "mevcut proje yasak" maddesi görmedim ama Execution "hackathonda ne yapıldı" diye soruyor.
  - **Boş repo bugün açılır, eski kod getirilmez.** Fikir, tasarım bilgisi ve önceden hazır görseller olabilir (sunumda belirt).
  - Sabah organizatöre sor: "Önceden hazırlanmış fikir ve görseller sorun mu?"

## 2. Karar: Mimo Kurye

Tek cümle: **Mimo Kurye, doğal dildeki Türkçe teslimat talimatlarını optimize edilmiş ve kısıtları bağımsız olarak kontrol edilmiş rotalara dönüştürür; planın neden geçerli olduğunu açıklar.**

Ana iddia: AI talimatı **yorumlar**, ama rotanın doğruluğuna tek başına karar vermez.

### Akış
1. Dağıtımcı serbest Türkçe yazar: "Ali 14:00'ten sonra çalışamayacak; soğuk zincir paketleri ilk iki saatte teslim edilsin."
2. **Gemini** bunu JSON kısıta çevirir (plan başına 1 çağrı).
3. Sistem "şunu anladım" diye gösterir, **kullanıcı onaylar ya da düzeltir**.
4. **OR-Tools** rotayı üretir (kendi algoritmalarımızı yazmıyoruz).
5. **Bağımsız doğrulayıcı** (çözücüyü import etmez) kuralları kontrol eder: her durak bir kez, kapasite, vardiya, zaman pencereleri, her kısıt tipi.
6. **Mimo** sonucu ve kanıtı gösterir; hareketleri gerçek işlem günlüğünden gelir. Doğrulama başarısızsa Mimo planı başarılıymış gibi göstermez.

### Demo hikâyesi (60-70 sn)
Başlangıç rotası var, dağıtımcı gün ortasında yeni talimat girer, Mimo Gemini'nin anladığını gösterir, kullanıcı onaylar, yeni rota hesaplanır, değişen duraklar işaretlenir, doğrulama sonucu açıklanır. Mimo'nun varlık sebebi bu.

### Kapsam
- Sentetik veri: İstanbul, ~50 durak, 4 araç, "soğuk_zincir" etiketli birkaç durak.
- Mesafe: haversine (kuş uçuşu), hız varsayımı belgelenir. Gerçek yol/trafik yok, sunumda açıkça söyle.
- Mimo tek karakter. Önceden tanımlı hareketler, serbest dolaşma yok.

## 3. Kesilenler / yapmayacaklarımız

- Clarke-Wright, 2-opt, Or-opt'u sıfırdan yazmak (OR-Tools kullanılacak). **Yedek:** OR-Tools kurulmazsa en yakın komşu + 2-opt, Codex'e ~100 satır.
- Solomon/CVRPLIB benchmark entegrasyonu.
- Gerçek yol ağı, trafik, tam harita.
- Çoklu ajan, kullanıcı hesabı, veritabanı, ayar ekranı.
- Mimo görselleri için 20-30 dk (iki poz; olmazsa SVG + CSS hareketi).
- Kısıt tipleri: yalnızca `courier_unavailable_after`, `tag_deadline`, `max_stops` ile başla.

## 4. Savunmayacağımız iddialar

- "İnsanlar buna daha çok güveniyor" (ölçülmedi). En fazla "her karar kanıtla gösteriliyor".
- "Her sektöre uyarlanır" (yalnızca sonraki adım, mimari slaytı).
- "Daha iyi rota algoritması" ya da "piyasada ilk" (rakip taraması yapılmadı).
- Kuş uçuşu sonucunu gerçek trafikte kazanılan km gibi sunmak.
- Gizlilik: Gemini ücretsiz katmanında gönderilen içerik ürün geliştirmede kullanılabilir (kaynak: ChatGPT'nin aktardığı bilgi, doğrulanmadı). **Sentetik veri kullan.**
- Mimo'nun etkisini ölçtüğümüzü iddia etme (kullanıcı testi yok).

## 5. Ölçümler (üç ayrı, koşudan sonra yazılacak, şimdi uydurma)

1. **Gemini kısıt çevirisi:** ~30 etiketli Türkçe cümlede doğru çevirme oranı (hata türüne göre).
2. **Doğrulayıcı:** bilerek bozulmuş ~20 rotada ihlalleri yakalama oranı ve yanlış alarm.
3. **Rota kalitesi:** aynı kısıtlar altında naif rotaya göre mesafe azalması, ihlal sayısı, çözüm süresi.
4. **LLM kullanımı:** plan başına Gemini çağrısı (hedef: 1).

Not: Doğrulayıcı Gemini'nin cümleyi yanlış anlamasını (ör. "14'ten sonra yok" yerine "14'ten sonra çalışabilir") kendi başına bilemez. Bunu kullanıcı onayı ve etiketli testler ölçer. Pitch'te bu sınırı söyle.

## 6. Zaman planı (~5 saat, 16:00 teslim)

1. 45 dk: veri modeli, sentetik senaryo, kısıt şeması, doğrulayıcı testleri.
2. 60 dk: OR-Tools çözücü, naif baz çizgi, karşılaştırma.
3. 45 dk: Gemini kısıt çevirisi, onay ekranı. Kota biterse kayıtlı akış "demo modu" diye açılır.
4. 90 dk: arayüz, rota karşılaştırması, Mimo'nun günlüğe bağlı hareketleri.
5. Kalan: ölçümler, ekran kaydı yedeği, form, pitch provası.
- Solver ve doğrulayıcı erkenden çalışmıyorsa arayüz kapsamı küçültülür.
- Paylaşım: bir kişi fal.ai ile Mimo görselini paralelde yapar, çekirdek kod beklemez.

## 7. Codex kullanımı (jüri %20)

- Testler önce, sonra kod. Paralel görevler: çözücü + doğrulayıcı, arayüz, benchmark verisi.
- Bitince Codex'e **"bu doğrulayıcıyı nasıl kandırırdın?"** incelemesi yaptır, bulguları testlere çevir.
- Pitch'te iki somut örnek hazırla ("Codex şunu yazdı, şu hatayı buldu"). Commit geçmişi temiz kalsın.

## 8. Gemini notları

- Ücretsiz limit rakamını (günlük istek sayısı) doğrulayamadım. Resmi dokümana göre limitler **proje başına**, model bazlı, günlük kota Pasifik saatiyle gece yarısı sıfırlanıyor, garanti değil. AI Studio'da kendi limitini ekranda gör.
- Tüm kısıtları tek istekte çevir, yanıtları önbelleğe al, en iyi örneklerin cevaplarını demo için kaydet.
- API anahtarı tarayıcıda durmasın: FastAPI backend üzerinden çağır.

## 9. fal.ai

- Görsel/video/ses/3D üretir; **uygulamayı tasarlamaz**. Mimo pozlarını, logoyu, arka planı üretir. Arayüzü Codex kodlar.
- Referans görselle tutarlı poz üretmeyi dene (destekleyen model var mı, doğrulanmadı), arka plan silme, şeffaf PNG.
- Süre sınırı 20-30 dk, yedek tek poz + CSS.

## 10. Jürinin muhtemel soruları

1. **"Neden AI? Neden sadece rota algoritması?"** Dağıtımcılar doğal dilde talimat verir. Gemini bunu yapılandırılmış kısıta çevirir, kullanıcı gözden geçirir; deterministik çözücü rotayı kurar, ayrı bir doğrulayıcı sonucu kontrol eder.
2. **"Gemini'nin doğru anladığını nasıl biliyorsunuz?"** Yorumlanan kısıtı planlamadan önce gösteriyoruz, etiketli Türkçe örneklerde ölçüyoruz. Doğrulayıcı uygulanabilirliği kontrol eder, her anlam hatasını yakalayamaz.
3. **"Mevcut araçlardan farkı ne?"** Daha iyi çözücü iddiamız yok. Odak: Türkçe talimat, düzenlenebilir kısıt, doğrulanmış sonuç ve açıklama tek akışta. Prototip sentetik veriyle çalışıyor; gerçek yol ve trafik sonraki adım.
4. **"Neden Mimo?"** Değer algoritmada ve doğrulamada; Mimo bunu teknik bilgisi olmayan bir dağıtımcının bakışta okuyacağı hale getiren arayüz. Etkisini ölçmedik.
5. **"Kim kullanır?"** Küçük kurye şirketi, e-ticaret satıcısı, mahalle teslimatı (doğrulanmadı). **Bugün bir mentor/jüriye gerçek kullanıcı bilgisini sor.**
6. **"LLM nerede?"** Yalnızca talimat → kısıt çevirisi. Çekirdek kod.

## 11. Pitch iskeleti (2 dk)

1. 0:00-0:20: "AI bir karar verdiğinde kullanıcı neye bakarak onaylayacak?" + problem.
2. 0:20-1:30: Canlı demo (gün ortası talimat, onay, yeni rota, doğrulama).
3. 1:30-2:00: Ölçüm sayıları, Codex katkısı, sonraki adım (gerçek yol ağı, daha fazla kısıt tipi).

## 12. Reddedilen fikirler (tekrar açma)

- **Mimo Check** (AI özetini kaynağa karşı doğrulama): çekirdeği iyi ama ihtiyaç dar ve tekrar kullanım zayıf, Mimo süs kalıyordu. İstenirse yedek.
- **Mimo Okur** (resmi yazı okuma): ihtiyaç iyi ama rakip kontrolü yapılmadı, hukuki hassasiyet.
- **RFP yanıtlama:** kalabalık (Responsive, Sweetspot, SpikeCore vb.) ve büyük kapsam.
- **Görsel çoklu ajan çalışma alanı:** kalabalık (Pixel Agents, Agent Office, pixtuoid, OpenClaw).
- **Ajan makbuzu:** kalabalık (OutcomeLoop, showwork, Kelyra, ARC, Morpheus).
- **Alışkan:** TEKNOFEST projesi, bitmiş kodu var; doğrudan getirilemez, yedek bile olarak zayıf.
- **İade nedeni analizi:** gerçek veri yok, sentetik veriyle döngüsel.

## 13. Aşağıdaki ilk Codex görevi (verilmediyse ver)

```
Python backend'li "mimo-kurye" projesi kur (FastAPI, pytest). Önce testleri yaz, sonra kodu.

1. models: Courier(id, name, capacity, shift_start, shift_end), Stop(id, lat, lon, demand, service_min, window_start, window_end, tags), Depot, Plan(routes: courier_id -> stop id listesi + varış saatleri).
2. constraints: JSON şeması (pydantic). İlk tipler: courier_unavailable_after(courier_id, time), tag_deadline(tag, within_minutes_from_start), max_stops(courier_id, n). Geçersiz kurye/durak referanslarını reddet.
3. generator: seed'li sentetik İstanbul senaryosu (50 durak, 4 kurye, "soğuk_zincir" etiketli birkaç durak). Mesafe: haversine, hız 30 km/h varsayımı belgelenmiş.
4. validator: validate(plan, scenario, constraints) -> ihlal listesi. Çözücüden BAĞIMSIZ olsun (solver modülünü import etme). Kontroller: her durak tam bir kez, kapasite, vardiya, zaman pencereleri, her kısıt tipi.
5. testler: geçerli plan ihlal vermez; bilerek bozulmuş 20 plan (durak eksik/çift, kapasite aşımı, geç varış, yanlış kurye) her biri doğru ihlali bulur. Mutation test sonuçlarını sayarak raporla.
6. baseline: naif plan (duraklar sırayla araçlara dağıtılır), doğrulayıcıdan geçirip toplam mesafeyi yaz.
Henüz Gemini ve arayüz yok. Her adımda testleri çalıştır ve sonucu özetle.
```

## 14. Açık / doğrulanmamış maddeler

- [ ] Organizatör: önceden hazırlanmış fikir ve görseller sorun mu?
- [ ] OR-Tools paketi kuruldu mu, çalışıyor mu?
- [ ] Gemini ücretsiz limit rakamı (AI Studio ekranından).
- [ ] fal.ai kredisi talep edildi mi? Referans görselle tutarlı poz var mı?
- [ ] Gerçek kullanıcı cümlesi (mentor/jüri).
- [ ] Rakip taraması (rota planlama araçları) yapılmadı; pitch'te "ilk" deme.

## 15. Yeni sohbette getirmen gerekenler

- Şu an kaç saat kaldığı ve nereye gelindiği.
- Codex'in ürettiği çıktı ve test sonuçları (özellikle doğrulayıcı ve mutation testleri).
- Takıldığın hata varsa mesajı.
