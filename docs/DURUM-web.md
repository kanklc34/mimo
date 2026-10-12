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

## Arayüz güncellemesi · 12 Ekim 2026

- Harita karşılaştırması ana çalışma alanına, 01 talimat ve 02 onay/kısıt adımları sağ yan panele taşındı. Masaüstü yerleşimi 1366×768 ve 1920×1080 görünüm yüksekliklerine göre sıkılaştırıldı; rota ve doğrulama ayrıntıları kendi alanlarında taşma yönetimi kullanır.
- Başlıkta mevcut Mimo Kurye PNG logosu kullanılır. Uzak font/CDN kaldırıldı; sistem fontları, okunabilir 16 px gövde metni, belirgin önceki/yeni kilometre değerleri ve doğrulama/ihlal renkleri uygulandı.
- HTML işaretlemesi ve CSS güncellendi. `web/app.js`, API ve mevcut JS ID/sınıf/data bağları değiştirilmedi.
- Son kontrol: `node --check web/app.js` başarılı; `tests/test_api.py`, `tests/test_api_flow.py`, `tests/test_api_gemini.py` **11 geçti**; `git diff --check` temiz.
- Harita balonu boş metinde gizlenir; dolu metin tek satırda daha okunur boyutta gösterilir.
- Harita Mimo işaretçisi 44 px durum PNG'si kullanır; yükleme hatasında emoji yedeğine döner.
- Önceki rota ilk yüklemede baseline planla çizilir; eski rota çizgileri artık kurye renklerini korur.
- Harita koordinatları iki görünümde ortak ölçek ve 6% kenar payıyla çizilir; Mimo balonu harita içinde tek satır kalır. Değişen duraklar iki haritada aynı belirgin stille, listede okunur durak adları ve kurye renk noktalarıyla gösterilir; saat kaymaları tek satırda açılır.
- Onay kartı kısıtları 08:00 vardiya başlangıcına göre saatlendirilmiş satırlar halinde gösterir. Ham JSON varsayılan kapalıdır ve “JSON'u düzenle” ile açılır; mevcut düzeltme/onay akışı korunur.
- `POST /reset`, kısıtsız seed=42 başlangıç planını yeniden üretip önceki plan olarak saklar; loga `sıfırlandı` olayı yazar ve başlangıç kilometresini döner.
- Rota karşılaştırmasının üstündeki “Başa dön” düğmesi iki haritayı baseline'a alır, kilometreyi gösterir, durak değişim sayısını sıfırlar ve Mimo'yu depoya döndürür.
- Başa dönme talimatı/kısıt girişlerini temizler, onay durumunu beklemeye alır ve zaman çizgisini 08:00'a getirir; aynı kısıt tekrar onaylandığında baseline'a göre aynı fark oluşur.
- Kurye değişiklikleri önceki rota zamanı ve etkin kısıtlarla gerekçelendirilir; eşleşen neden yoksa genel yeniden dağıtım açıklaması gösterilir. Karşılaştırma altında validator kontrolleri ve API kaynaklı ihlal sayısı kanıt şeridinde listelenir.
