# Mimo Kurye web/API durumu

## Başlatma

Proje kökünde sanal ortamı/bağımlılıkları etkinleştirdikten sonra:

```powershell
uvicorn api.main:app --reload
```

Uygulama `http://127.0.0.1:8000` adresinde açılır. Gemini entegrasyonu için `.env.example` dosyasını `.env` adıyla kopyalayıp `GEMINI_API_KEY` ve `GEMINI_MODEL` değerlerini girin. `google-genai` bağımlılığını `api/requirements.txt` üzerinden kurun. API anahtarı yalnızca sunucuda okunur.

Kayıtlı çeviri demosu için `.env` içinde `GEMINI_DEMO_MODE=1` kullanılır. Cümle yanıtları `cache/` altına SHA-256 cümle anahtarıyla yazılır; demo modunda yeni Gemini çağrısı yapılmaz ve bulunmayan kayıt hata verir.

## Uygulanan kapsam

- `GET /scenario`: seed 42 sentetik İstanbul senaryosu.
- `POST /interpret`: Türkçe talimatı Gemini structured output ile kısıt JSON'una çevirir ve kurye/etiket referanslarını doğrular.
- `POST /plan`: şimdilik `MockPlanner` üzerinden `naive_plan` çalıştırır; bağımsız doğrulama, rota özeti, önceki plana göre değişen duraklar ve atlanan durak nedenlerini döndürür.
- `GET /log`: adımları UTC zaman damgasıyla sunar; arayüz Mimo görsel durumunu bu kayıttan türetir.
- Framework kullanmayan web arayüzü: talimat, düzenlenebilir kısıt JSON'u ve yan yana SVG rotaları.

Plan doğrulama ihlal içeriyorsa `summary.valid` false olur. Rota görselleştirmesi harita altlığı olmayan SVG'dir; yol ve trafik verisi içermez. `web/assets/` altında Mimo PNG'leri bulunmadığından arayüz emoji yedeğini kullanır.

## Test

```powershell
C:\Users\KAAN\miniconda3\envs\mimo\python.exe -m pytest tests/test_api.py tests/test_api_flow.py tests/test_api_gemini.py -q
```

Gemini çağrıları testlerde sahte SDK ile taklit edilir; gerçek servis çağrısı yapılmaz.
