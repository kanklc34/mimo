# Mimo Kurye web/API durumu

## Başlatma

Proje kökünde API'yi başlat:

```powershell
C:\Users\KAAN\miniconda3\envs\mimo\python.exe -m uvicorn api.main:app --reload
```

Uygulama `http://127.0.0.1:8000` adresindedir. OR-Tools proje bağımlılıklarına eklenmiştir. Gemini yorumlaması için `.env.example` dosyasını `.env` olarak kopyalayıp `GEMINI_API_KEY` ve `GEMINI_MODEL` değerlerini girin; API anahtarı sunucuda okunur.

## Uygulanan kapsam

- `GET /scenario`, `POST /interpret`, `POST /plan` ve `GET /log` uçları.
- `POST /plan` varsayılan `OrtoolsPlanner` ile kısıtlı çözücü çalıştırır ve `SolveResult` atlanan durak nedenlerini döndürür. Önceki plan yeniden planlama çözümüne aktarılır.
- Plan bağımsız validator ile kontrol edilir; rota özeti, önceki plan farkları ve atlanan duraklar döner.
- Diff türleri kurye, sıra, yalnızca saat kaydı ve yeni atlanan durak farklarını ayırır. Özet gerçek değişiklik sayısını öne çıkarır; yalnızca saat farkları soluk gösterilir.
- Web istemcisi framework kullanmayan HTML/CSS/JavaScript ve SVG rota gösterimidir. Haversine harita altlığı olmayan düz çizgi tahminidir.
- Haritada hareket eden Mimo, depo konumundan başlar; tur durak ve ihlal verisini `/plan` yanıtından, koordinat/servis/vardiya bilgisini `/scenario` yanıtından alır. Durak seçimi turu keser. Zaman çubuğu durak varışları/servis süreleriyle kurye işaretçilerini yürütür; `/log` Mimo durumunu beslemeye devam eder. Saat kaymaları katlanabilir listede görünür.
- `/plan` yanıtındaki normalize `constraints` alanı, durak seçildiğinde o durağı etkileyen kısıtları göstermek için kullanılır. Tarayıcı kodu `.env` veya API anahtarı okumaz. Hareket `prefers-reduced-motion` tercihini izler; eksik durum PNG'si için emoji yedeği kullanılır.

## Test

```powershell
C:\Users\KAAN\miniconda3\envs\mimo\python.exe -m pytest tests/test_api.py tests/test_api_flow.py tests/test_api_gemini.py -q
```

Tam test paketi son koşuda **61 geçti**, 3 OR-Tools SWIG deprecation uyarısı verdi.
