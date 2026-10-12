# Solver durum raporu

## Public imzalar

```python
solve(scenario, constraints, time_limit_s=10) -> SolveResult
diff_plans(eski: Plan, yeni: Plan) -> list[dict]
clustered_naive_plan(scenario: Scenario) -> Plan
```

`SolveResult` alanları: `plan: Plan`, `unserved_reasons: dict[str, str]`, `solve_time_s: float`, `status: str`. Plan modeli değiştirilmedi. `diff_plans` değişen durak başına `stop_id` ve `changes` (`courier_changed`, `arrival_changed`, `newly_unserved`, vb.) alanları döndürür.

OR-Tools VRP kapasiteyi, varış pencerelerini, servis sürelerini, vardiya bitişini dönüş ayağı dahil ve maksimum durak sayısını modeller. `courier_unavailable_after` ilgili kuryeye atanmış durak için servis bitişini sınırlar; dönüş ayağına uygulanmaz. Etiket son tarihi vardiya başlangıcından itibaren verilen dakika sınırıdır. Her durak için sonlu atlama cezası vardır; atlanan duraklar `plan.unserved_stops` ve nedenleri `unserved_reasons` içinde raporlanır. Zaman boyutunda seyahat süresi `Scenario.travel_time_min` üzerinden alınır; böylece generator ve doğrulayıcıyla aynı fonksiyon/yuvarlama kullanılır.

OR-Tools yüklenemez veya çalışma zamanı çözüm üretemezse en yakın komşu atama ve uygulanabilirlik koruyan 2-opt yedeği devreye girer. Sonuç durumunda kullanılan yol belirtilir. `clustered_naive_plan` depo çevresini kurye sayısı kadar açı dilimine böler, kapasite aşan durağı sıradaki kuryeye taşır ve her bölge içinde en yakın komşu rotası kurar.

Karşılaştırma betiği kısıtsız, zaman kısıtlı ve etiket son tarihli senaryolarda naif, kümelenmiş naif ve OR-Tools planlarını aynı kısıtlar altında ölçer. Demo betiği sabit seed ile önce kısıtsız OR-Tools başlangıç planı kurar, ardından kısıtlı çözümün farkını ve atlanan durak nedenlerini gösterir. Generator'daki kurye adları `Kurye 1` ve `Kurye 2` olduğundan demo kısıtları bu gerçek kurye kimliklerine uygulanır.

## Test sonucu

Komut: `C:\Users\KAAN\miniconda3\envs\mimo\python.exe -m pytest -q`  
Sonuç: **49 geçti**, 3 OR-Tools SWIG deprecation uyarısı. Testler solver planını doğrulayıcıdan geçiriyor; üç kısıt tipini, atlanan durak ve sebebini, plan diff'ini, aynı girdide deterministik planı, kısıtın diğer kuryeye taşmamasını ve kümelenmiş baseline'ı kapsıyor.

## Ölçüm

`seed=42` ile kısıtsız, **Kurye 1** için 360. dakika sınırı ve soğuk zincir için 120. dakika son tarihi karşılaştırıldı. Gerçek koşu tablosu [olcum-rota.md](olcum-rota.md) içinde. OR-Tools sırasıyla 63.89 km, 63.89 km ve 69.06 km; üçünde de 0 ihlal ve 0 atlanan durak verdi. Kümelenmiş naif baseline üç durumda da 86.34 km ve 0 ihlal verdi; naif planın soğuk zincir senaryosunda 2 ihlali vardı. Demo kısıtları Kurye 1 için 180. dakika, Kurye 2 için en fazla 8 durak ve soğuk zincir için 120. dakikadır; gerçek çalıştırmada 49 durak değişti, atlanan durak olmadı. Değişim sayısı beşten az olmadığı için sınırlar ayarlanmadı.

## Açık sorunlar ve sınırlamalar

- Mesafe/süre modeli kuş uçuşu ve sabit 30 km/saat varsayımıdır; yol ağı ve trafik hesaba katılmaz.
- Atlanan durak nedeni, çözüm sonrasında mevcut kısıtlara göre açıklayıcı bir sınıflandırmadır; OR-Tools infeasibility kanıtı değildir. Genel neden metni bazı durumlarda kesin sebebi ayırt etmez.
- Kıyas tek seed/tek koşudur. `courier_unavailable_after` kısıtı seed 42'de baseline rotasını değiştirmedi.
- OR-Tools proje bağımlılık listesine eklenmedi; bu çalışma ortamında kurulu. Eksik/çalışmayan OR-Tools için fallback var.
- Solver ve validator birbirini import etmez; solver validator'ı kullanmaz. Testler bağımsız doğrulama yapar.
