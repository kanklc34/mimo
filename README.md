# Mimo Kurye

**Mimo Kurye**, devre dışı kalan bir kurye için dağıtımcının Türkçe talimatını gözden geçirilebilir planlama kurallarına çevirir, onaydan sonra günlük rotayı mümkün olduğunca az değiştirerek yeniden hesaplar ve sonucu bağımsız bir doğrulayıcıyla kontrol eder.

## Demo kapsamı

- Sabit tohumla üretilmiş İstanbul senaryosu: **50 sentetik durak, 4 kurye**.
- Dağıtımcı talimatı Türkçe yazar; sistem anladığı kısıtları gösterir, kullanıcı onaylar veya düzenler.
- OR-Tools yeni planı hesaplar ve önceki atamaları mümkün olduğunca korumaya çalışır.
- Ayrı doğrulayıcı durak kapsamı, vardiya, zaman penceresi, kapasite ve depo dönüşü gibi kuralları kontrol eder.
- Haritada eski ve yeni plan, kurye renkleri, etkilenen duraklar ve plan farkı incelenebilir.

Bu prototip **sentetik ve statiktir**. Gerçek zamanlı konum, gerçek yol ağı veya trafik, teslim edilmiş durakları sabitleme ve paket devri içermez. Mesafeler kuş uçuşudur; süreler sabit hız varsayımına dayanır. Sonuçları gerçek saha performansı olarak yorumlamayın.

## Akış

1. **Talimat:** Dağıtımcı doğal Türkçe ile bir kuryenin devre dışı kalacağını veya başka bir kuralı yazar.
2. **Onay:** Gemini talimatı kısıt şemasına çevirir. Kullanıcı anlaşılan kuralı kontrol eder ve onaylar; JSON düzenlemesi gerekmez.
3. **Yeniden planlama:** OR-Tools mevcut plana yakın yeni bir rota hesaplar; önceki planla farklar haritada gösterilir.
4. **Bağımsız doğrulama:** Validator rotayı kural ihlallerine karşı kontrol eder ve doğrulama özeti arayüze döner.

Gemini yalnızca talimatı yorumlar. Rota planlamasını OR-Tools yapar; planın kurallara uygunluğunu ayrı validator kontrol eder. Validator, kullanıcının Türkçe talimatının anlamını doğru yorumlandığını tek başına kanıtlamaz; bu nedenle onay adımı akışın parçasıdır.

## Yerel çalıştırma (Windows)

Proje kökünde PowerShell açın. `mimo` Conda ortamı önceden kuruluysa:

```powershell
conda activate mimo
python -m uvicorn api.main:app --reload
```

Tarayıcıdan [http://127.0.0.1:8000](http://127.0.0.1:8000) adresini açın. Windows bağlantı noktası hatası verirse alternatif port kullanın:

```powershell
python -m uvicorn api.main:app --reload --port 8001
```

Bu durumda [http://127.0.0.1:8001](http://127.0.0.1:8001) adresini açın. Uygulamanın API uçları `/health`, `/scenario`, `/interpret`, `/plan`, `/reset` ve `/log` şeklindedir.

### Gemini yapılandırması

Kök dizindeki örnek ayarı kopyalayın ve `.env` dosyasına kendi Gemini API anahtarınızı ekleyin:

```powershell
Copy-Item .env.example .env
```

`.env` gizli bilgi içerir; Git'e eklemeyin. Canlı ortamda `GEMINI_API_KEY`, `GEMINI_MODEL` ve gerekirse `GEMINI_DEMO_MODE` değerlerini hosting sağlayıcısının gizli ortam değişkenleri olarak tanımlayın. `GEMINI_DEMO_MODE=1`, yalnızca yerel cache'te kayıtlı cümleleri çalıştırır; cache Git deposuna dahil değildir.

## Vercel

Vercel'in Python runtime'ı FastAPI uygulamalarını destekler ve `api/main.py` içindeki `app` nesnesini tanıyabilir. Deploy ayarlarında `GEMINI_API_KEY` değerini gizli ortam değişkeni olarak ekleyin; anahtarı kaynak koda veya GitHub'a koymayın. Deploy sonrasında önce `/health` ve ana sayfayı, ardından talimat → onay → plan → doğrulama akışını kontrol edin.

## Testler

Proje ortamında:

```powershell
python -m pytest -q
```

Testler modelleri ve kısıtları, çözücü ve doğrulayıcıyı, API akışını ve arayüzün temel davranışlarını kapsar.

## Teknoloji

- **Arayüz:** HTML, CSS ve JavaScript; FastAPI tarafından sunulur.
- **API:** FastAPI ve Pydantic.
- **Talimat yorumlama:** Gemini (`google-genai`).
- **Rota planlama:** OR-Tools; mevcut plana yakınlığı gözeten maliyetlerle.
- **Doğrulama:** Solver'dan bağımsız validator modülü.
