# Mimo Kurye birleşik durum

## Uygulama kapsamı

- FastAPI uygulaması `GET /health`, `GET /scenario`, `POST /interpret`, `POST /plan` ve `GET /log` uçlarını sunar. Web istemcisi `web/` altındadır.
- `Courier`, `Stop`, `Depot`, `Plan` ve `Violation` Pydantic modelleri; ayrıştırmalı kısıt şeması ve sabit seed'li sentetik İstanbul senaryosu mevcuttur.
- `POST /plan`, varsayılan `OrtoolsPlanner` ile OR-Tools `solve()` fonksiyonunu çağırır. Atlanan durak nedenleri `SolveResult.unserved_reasons` alanından döner. Planlar validator ile bağımsız doğrulanır.
- Gün içi yeniden planlamada önceki plan çözücüye başlangıç ataması olarak verilir; aynı kuryede kalma ve önceki rota bağlantılarını koruma için küçük maliyetler uygulanır. `solve(..., previous_plan=None)` varsayılan kullanımı korur.
- Plan farkları durak bazında `kurye_degisti`, `sira_degisti`, `sadece_saat_kaydi` veya `yeni_atlandi` türünü içerir. Sıra değişikliği, aynı kuryede kalan durakların göreli rotası değiştiğinde raporlanır; sadece saat farkları ayrı sayılır ve arayüzde soluk gösterilir.
- OR-Tools çalışma zamanı çözüm üretemezse uygulanabilirlik denetimli en yakın komşu ve 2-opt yedeği vardır. Durak atlama nedenleri açıklayıcı sınıflandırmadır; infeasibility kanıtı değildir.
- Zamanlar vardiya başlangıcından itibaren tam dakika; mesafe Haversine, seyahat hızı sabit 30 km/saat ve her ayak dakika üstüne yuvarlanır.
- Solver ve validator birbirini import etmez. Solver bağımsızdır; validator yalnızca modelleri ve kısıtları kullanır.

## Çalıştırma

Proje kökünden API'yi başlat:

```powershell
C:\Users\KAAN\miniconda3\envs\mimo\python.exe -m uvicorn api.main:app --reload
```

Demo ölçümünü üret:

```powershell
C:\Users\KAAN\miniconda3\envs\mimo\python.exe scripts/demo_scenario.py
```

Testleri çalıştır:

```powershell
C:\Users\KAAN\miniconda3\envs\mimo\python.exe -m pytest -q
```

## Son doğrulama

Yukarıdaki tam test komutu: **61 geçti**, OR-Tools SWIG kaynaklı 3 deprecation uyarısı.

`seed=42` demo koşusu: Kurye 1 için 180. dakika sınırı, Kurye 1 için en fazla 24 durak, soğuk zincir için 120 dakika. **6 gerçek değişiklik**, **9 yalnızca saat kaydı değişikliği**, **0 atlanan durak**, **0 doğrulayıcı ihlali**. Gerçek konsol çıktısı [olcum-rota.md](olcum-rota.md) dosyasındadır.

## Sınırlar

- Rota hesabı gerçek yol ağı ve trafiği kullanmaz; kuş uçuşu mesafe ve sabit hız varsayımıdır.
- Gemini entegrasyonu yapılandırılmış Türkçe talimat yorumlama içindir; gerçek servis anahtarı sunucu ortamında tutulmalıdır.
- Sentetik tek seed ölçümü gerçek saha performansını temsil etmez.
