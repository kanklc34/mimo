# Rota karşılaştırması

Koşu: `C:\Users\KAAN\miniconda3\envs\mimo\python.exe scripts/compare_routes.py`  
Senaryo: `generate_scenario(seed=42)` (50 durak, 4 kurye). Mesafe kuş uçuşu Haversine; seyahat süresi generator'ın 30 km/saat hız ve ayak başına yukarı yuvarlama hesabıdır. Süreler tamsayı dakikadır. Çözücü 10 saniye zaman sınırıyla çalıştırıldı.

| Kısıt | Plan | Mesafe (km) | İhlal | Atlanan | Çözüm süresi (s) | Durum |
|---|---|---:|---:|---:|---:|---|
| Kısıtsız | Naif | 275.68 | 0 | 0 | — | — |
| Kısıtsız | OR-Tools | 63.89 | 0 | 0 | 0.3580 | ortools |
| Ali 14:00 sonrası çalışamaz (başlangıçtan 360 dk) | Naif | 275.68 | 0 | 0 | — | — |
| Ali 14:00 sonrası çalışamaz (başlangıçtan 360 dk) | OR-Tools | 63.89 | 0 | 0 | 0.2731 | ortools |
| Soğuk zincir ilk 120 dk içinde | Naif | 275.68 | 2 | 0 | — | — |
| Soğuk zincir ilk 120 dk içinde | OR-Tools | 69.06 | 0 | 0 | 0.2182 | ortools |

Bu değerler tek sentetik seed ve tek çalıştırmanın çıktısıdır. Gerçek yol ağı/trafik ölçümü değildir. `courier_unavailable_after` örneği seed 42'de rotayı değiştirmedi; bu koşuda mesafenin kısıtsız sonuçla aynı olması beklenen bir çıktıdır.
