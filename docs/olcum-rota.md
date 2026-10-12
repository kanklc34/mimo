# Demo rota ölçümü

Komut: `C:\Users\KAAN\miniconda3\envs\mimo\python.exe scripts/demo_scenario.py`

Senaryo `generate_scenario(seed=42)` ile üretildi (50 durak, 4 kurye). Önce kısıtsız OR-Tools planı oluşturuldu; ikinci çözüm bu planı başlangıç ataması olarak aldı. Kısıtlar: Kurye 1 servis bitişi en geç 180. dakika, Kurye 1 en fazla 24 durak, soğuk zincir en geç 120. dakika.

## Gerçek çalıştırma çıktısı

```text
Yeni talimat: Kurye 1 180. dakikadan sonra yok; Kurye 1 en fazla 24 durak; soğuk zincir ilk 120 dakikada teslim.
Gerçekten değişen durak: 6
Yalnızca saat kaydı değişen durak: 9
Gerçek değişiklik kimlikleri: stop-09, stop-19, stop-21, stop-25, stop-41, stop-43
{"status": "ortools", "solve_time_s": 0.3259, "validator_violations": 0}
```

Değişim türü sayıları: 6 kurye değişikliği ve 9 yalnızca saat kaydı değişikliği. Atlanan durak olmadı; validator **0 ihlal** verdi. Çözücü süresi makineye ve çalıştırmaya göre değişebilir.

Bu sonuç seed 42 sentetik senaryosuna aittir. Mesafe/süre hesabı kuş uçuşu Haversine ve sabit 30 km/saat varsayımıdır; gerçek yol ağı ve trafik ölçümü değildir.
