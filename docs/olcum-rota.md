# Rota karşılaştırması

Koşu komutu: `C:\Users\KAAN\miniconda3\envs\mimo\python.exe scripts/compare_routes.py`  
Senaryo: `generate_scenario(seed=42)` (50 durak, 4 kurye). Mesafe kuş uçuşu Haversine; generator'ın 30 km/saat ve her seyahat ayağını yukarı yuvarlayan hesabı kullanılır. Çözücü zaman sınırı 10 saniyedir. Naif ve kümelenmiş plan süreleri plan üretim çağrısının ölçümüdür; OR-Tools süresi `SolveResult.solve_time_s` değeridir. Validator süresi ölçüme dahil değildir.

| Kısıt | Plan | Mesafe (km) | Validator ihlali | Atlanan | Plan/çözüm süresi (s) |
|---|---|---:|---:|---:|---:|
| Kısıtsız | Naif | 275.68 | 0 | 0 | 0.0009 |
| Kısıtsız | Kümelenmiş naif | 86.34 | 0 | 0 | 0.0016 |
| Kısıtsız | OR-Tools | 63.89 | 0 | 0 | 0.3948 |
| Kurye 1, 14:00 sonrası yok (başlangıçtan 360 dk) | Naif | 275.68 | 0 | 0 | 0.0002 |
| Kurye 1, 14:00 sonrası yok (başlangıçtan 360 dk) | Kümelenmiş naif | 86.34 | 0 | 0 | 0.0015 |
| Kurye 1, 14:00 sonrası yok (başlangıçtan 360 dk) | OR-Tools | 63.89 | 0 | 0 | 0.3505 |
| Soğuk zincir ilk 120 dk içinde | Naif | 275.68 | 2 | 0 | 0.0001 |
| Soğuk zincir ilk 120 dk içinde | Kümelenmiş naif | 86.34 | 0 | 0 | 0.0015 |
| Soğuk zincir ilk 120 dk içinde | OR-Tools | 69.06 | 0 | 0 | 0.2557 |

Demo komutu: `C:\Users\KAAN\miniconda3\envs\mimo\python.exe scripts/demo_scenario.py`. Sabit `seed=42` senaryosunda başlangıç planı kısıtsız OR-Tools çözümüdür. Yeni kısıtlar: **Kurye 1** servis bitişi en geç 180. dakika, **Kurye 2** en fazla 8 durak, soğuk zincir en geç 120. dakika. Gerçek koşuda **49 durak değişti**, atlanan durak çıkmadı. Değişmeyen durak `stop-16` idi. 49 değişiklik beşin altında olmadığı için parametre ayarı tetiklenmedi.

Bu değerler tek sentetik seed ve tek çalıştırmanın çıktılarıdır; gerçek yol ağı/trafik ölçümü değildir. Kurye 1 için 360 dakika kısıtı seed 42'de ölçülen rotayı değiştirmedi. Kümelenmiş baseline coğrafi açıyı dört bölgeye ayırır; kapasite aşımında durağı sıradaki kuryeye taşır ve her kurye içinde en yakın komşu sırasını kurar.
