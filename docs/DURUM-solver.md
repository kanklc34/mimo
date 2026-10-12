# Solver durum raporu

## Public imzalar

```python
solve(scenario, constraints, time_limit_s=10) -> SolveResult
diff_plans(eski: Plan, yeni: Plan) -> list[dict]
```

`SolveResult` alanları: `plan: Plan`, `unserved_reasons: dict[str, str]`, `solve_time_s: float`, `status: str`. Plan modeli değiştirilmedi. `diff_plans` değişen durak başına `stop_id` ve `changes` (`courier_changed`, `arrival_changed`, `newly_unserved`, vb.) alanları döndürür.

OR-Tools VRP kapasiteyi, varış pencerelerini, servis sürelerini, vardiya bitişini dönüş ayağı dahil ve maksimum durak sayısını modeller. `courier_unavailable_after` ilgili kuryeye atanmış durak için servis bitişini sınırlar; dönüş ayağına uygulanmaz. Etiket son tarihi vardiya başlangıcından itibaren verilen dakika sınırıdır. Her durak için sonlu atlama cezası vardır; atlanan duraklar `plan.unserved_stops` ve nedenleri `unserved_reasons` içinde raporlanır. Zaman boyutunda seyahat süresi `Scenario.travel_time_min` üzerinden alınır; böylece generator ve doğrulayıcıyla aynı fonksiyon/yuvarlama kullanılır.

OR-Tools yüklenemez veya çalışma zamanı çözüm üretemezse en yakın komşu atama ve uygulanabilirlik koruyan 2-opt yedeği devreye girer. Sonuç durumunda kullanılan yol belirtilir.

## Test sonucu

Komut: `C:\Users\KAAN\miniconda3\envs\mimo\python.exe -m pytest -q`  
Sonuç: **45 geçti**, 3 OR-Tools SWIG deprecation uyarısı. Testler solver planını doğrulayıcıdan geçiriyor; üç kısıt tipini, atlanan durak ve sebebini, plan diff'ini, aynı girdide deterministik planı ve kısıtın diğer kuryeye taşmamasını kapsıyor.

## Ölçüm

`seed=42` ile kısıtsız, Ali için 360. dakika sınırı ve soğuk zincir için 120. dakika son tarihi karşılaştırıldı. Gerçek koşu tablosu ve kapsam notu [olcum-rota.md](olcum-rota.md) içinde. OR-Tools sırasıyla 63.89 km, 63.89 km ve 69.06 km; her üçünde 0 doğrulayıcı ihlali ve 0 atlanan durak verdi. Naif planın soğuk zincir senaryosunda 2 ihlali vardı.

## Açık sorunlar ve sınırlamalar

- Mesafe/süre modeli kuş uçuşu ve sabit 30 km/saat varsayımıdır; yol ağı ve trafik hesaba katılmaz.
- Atlanan durak nedeni, çözüm sonrasında mevcut kısıtlara göre açıklayıcı bir sınıflandırmadır; OR-Tools infeasibility kanıtı değildir. Genel neden metni bazı durumlarda kesin sebebi ayırt etmez.
- Kıyas tek seed/tek koşudur. `courier_unavailable_after` kısıtı seed 42'de baseline rotasını değiştirmedi.
- OR-Tools proje bağımlılık listesine eklenmedi; bu çalışma ortamında kurulu. Eksik/çalışmayan OR-Tools için fallback var.
- Solver ve validator birbirini import etmez; solver validator'ı kullanmaz. Testler bağımsız doğrulama yapar.
