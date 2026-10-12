# Solver durum raporu

## Public imzalar

```python
solve(scenario, constraints, time_limit_s=10, previous_plan=None) -> SolveResult
diff_plans(eski: Plan, yeni: Plan) -> list[dict]
clustered_naive_plan(scenario: Scenario) -> Plan
```

`SolveResult` alanları `plan`, `unserved_reasons`, `solve_time_s` ve `status` değerleridir. OR-Tools kapasiteyi, zaman pencerelerini, servis sürelerini, vardiya sonunu, kurye/etiket kısıtlarını ve `max_stops` sınırını modeller. Atlanan duraklar plan üzerinde ve açıklayıcı neden sözlüğünde raporlanır.

`previous_plan` verilirse eski rotalar OR-Tools başlangıç atamasına çevrilir. Amaç maliyetinde önceki kuryeyi ve rota bağlantılarını korumak için küçük sapma maliyetleri bulunur. Parametre verilmediğinde normal başlangıç çözümü kullanılır. Aynı girdi için deterministik plan testi korunur.

`diff_plans` her fark satırında `type` alanını verir: `kurye_degisti`, `sira_degisti`, `sadece_saat_kaydi` veya `yeni_atlandi`. Sıradaki salt indeks kayması sıra değişikliği sayılmaz; aynı kuryede kalan durakların göreli sırası karşılaştırılır.

OR-Tools çözüm üretemezse en yakın komşu ve uygulanabilirlik koruyan 2-opt yedeği kullanılır. `clustered_naive_plan`, depo çevresini kurye sayısı kadar açı dilimine böler.

## Doğrulama ve ölçüm

Test komutu `C:\Users\KAAN\miniconda3\envs\mimo\python.exe -m pytest -q`; son koşuda **61 test geçti**, 3 OR-Tools SWIG deprecation uyarısı.

Demo: Kurye 1 180. dakika sınırı, Kurye 1 en fazla 24 durak, soğuk zincir 120. dakika. Gerçek koşu **6 gerçek değişiklik**, **9 saat kaydı değişikliği** ve **0 validator ihlali** üretti. Ayrıntılı çıktı [olcum-rota.md](olcum-rota.md) dosyasındadır.
