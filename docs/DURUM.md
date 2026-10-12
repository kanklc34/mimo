# Mimo Kurye backend durum raporu

## Tamamlananlar

- FastAPI uygulama iskeleti ve `/health` endpoint'i.
- Pydantic modelleri: `Courier`, `Stop`, `Depot`, `Plan` ve `Violation`.
- `courier_unavailable_after`, `tag_deadline` ve `max_stops` için ayrıştırmalı JSON şeması. Senaryoda bulunmayan kurye ve etiket referansları reddedilir; plandaki bilinmeyen durak ve kurye kimlikleri doğrulayıcıda ihlal olur.
- Sabit seed ile 50 duraklı, 4 kuryeli sentetik İstanbul senaryosu; durakların 4'ü `soğuk_zincir` etiketlidir.
- Haversine mesafesi, 30 km/saat ortalama hız ve her seyahat ayağını yukarı yuvarlayarak tam dakika hesaplama.
- Solver'dan bağımsız doğrulayıcı: ziyaret sayısı, kapasite, vardiya, zaman pencereleri, seyahat ve servis süresi, ayrıca üç kısıt tipi.
- Kullanılmayan duraklar `Plan.unserved_stops` içinde raporlanır; tek başına ihlal değildir.
- Durakları sırayla kuryelere dağıtan naif baseline. Mesafeye her turun depodan çıkışı ve depoya dönüşü dahildir.

## Test ve mutation sonuçları

- Komut: `C:\Users\KAAN\miniconda3\envs\mimo\python.exe -m pytest -q`
- Sonuç: **33 geçti**.
- Mutation ölçümü: **20/20 yakalandı, 0 yanlış alarm**.
- Seed 42 baseline: **275.68 km**, **0 ihlal**, **0 atlanan durak**.

## Public fonksiyon imzaları

```python
validate(
    plan: Plan,
    scenario: Scenario,
    constraints: ConstraintSet | list | None = None,
) -> list[Violation]

generate_scenario(seed: int = 42) -> Scenario

naive_plan(scenario: Scenario) -> Plan
```

Mesafe raporu için ayrıca `plan_distance_km(plan: Plan, scenario: Scenario) -> float` kullanılabilir.

## Açık sorunlar

- Gerçek yol ağı ve trafik yok; Haversine düz çizgi ve sabit hız varsayımıdır.
- OR-Tools rota çözücüsü henüz eklenmedi; `solver.naive_plan` yalnızca başlangıç baseline'ıdır.
- FastAPI şu an yalnızca health endpoint'i sunuyor; planlama uçları ve Gemini entegrasyonu kapsam dışı.
- Dönüş ayağının mesafesi baseline metriğine katılır, fakat planın vardiya doğrulamasında dönüş zamanı henüz modellenmez.
