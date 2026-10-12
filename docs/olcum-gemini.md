# Gemini talimat değerlendirmesi

Model kimliği: `gemini-3.1-flash-lite`
Doğru vaka oranı: **28/30 (93.3%)**
Plan başına çağrı hedefi: **1** · Bu çalıştırmada yapılan API çağrı denemesi: **18** · Değerlendirme cache eşleşmesi: **12**

Çağrı sayısı vaka başına kaydedilir; 429 yeniden denemeleri ayrı çağrı denemesi olarak sayılır. Cache'ten okunan yanıt raporunda ilk üretim çağrı sayısı korunur.

## Kısıt tipine göre

| Kısıt tipi | Tam eşleşen / beklenen kısıt |
|---|---:|
| `courier_unavailable_after` | 10/12 |
| `tag_deadline` | 11/12 |
| `max_stops` | 12/13 |

## Hata türleri

| Hata türü | Adet |
|---|---:|
| wrong type | 0 |
| wrong value | 0 |
| missing constraint | 0 |
| extra constraint | 0 |
| schema error | 2 |

## Hatalı vakalar ve Gemini yanıtı

### unavailable-05 · schema error

Cümle: Kurye 1 mesainin ilk üç saati dolunca çıksın.
Beklenen: `[{"type": "courier_unavailable_after", "courier_id": "courier-1", "time_min": 180}]`
Hata: schema error (beklenen: [{'type': 'courier_unavailable_after', 'courier_id': 'courier-1', 'time_min': 180}]; alınan: None)

<details><summary>Gemini yanıtı</summary><pre>
{
  &quot;constraints&quot;: {
    &quot;constraints&quot;: [
      {
        &quot;type&quot;: &quot;courier_unavailable_after&quot;,
        &quot;courier_id&quot;: &quot;courier-1&quot;,
        &quot;within_minutes_from_start&quot;: 180
      }
    ]
  },
  &quot;understood_text&quot;: &quot;Kurye 1 mesainin ilk üç saati dolunca çıksın.&quot;
}
</pre></details>

### combined-05 · schema error

Cümle: Kurye 4 12:00'den sonra yok, dokuz durağı geçmesin, soğuk zincir ilk üç saatte teslim edilsin.
Beklenen: `[{"type": "courier_unavailable_after", "courier_id": "courier-4", "time_min": 240}, {"type": "max_stops", "courier_id": "courier-4", "n": 9}, {"type": "tag_deadline", "tag": "soğuk_zincir", "within_minutes_from_start": 180}]`
Hata: schema error (beklenen: [{'type': 'courier_unavailable_after', 'courier_id': 'courier-4', 'time_min': 240}, {'type': 'max_stops', 'courier_id': 'courier-4', 'n': 9}, {'type': 'tag_deadline', 'tag': 'soğuk_zincir', 'within_minutes_from_start': 180}]; alınan: None)

<details><summary>Gemini yanıtı</summary><pre>
{
  &quot;constraints&quot;: {
    &quot;constraints&quot;: [
      {
        &quot;type&quot;: &quot;courier_unavailable_after&quot;,
        &quot;courier_id&quot;: &quot;courier-4&quot;,
        &quot;time_hhmm&quot;: &quot;12:00&quot;
      },
      {
        &quot;type&quot;: &quot;max_stops&quot;,
        &quot;n&quot;: 9
      },
      {
        &quot;type&quot;: &quot;tag_deadline&quot;,
        &quot;tag&quot;: &quot;soğuk_zincir&quot;,
        &quot;within_minutes_from_start&quot;: 180
      }
    ]
  },
  &quot;understood_text&quot;: &quot;Kurye 4 12:00&#x27;den sonra müsait değil, maksimum 9 durak sınırı var ve soğuk zincir etiketi vardiya başlangıcından itibaren 180 dakika içinde teslim edilmeli.&quot;
}
</pre></details>

## Plan başına Gemini çağrı sayısı

| Vaka | Çağrı denemesi | Bu çalıştırmada | Cache kullanıldı |
|---|---:|---:|---|
| `unavailable-01` | 1 | 1 | Hayır |
| `unavailable-02` | 1 | 0 | Evet |
| `unavailable-03` | 1 | 0 | Evet |
| `unavailable-04` | 1 | 0 | Evet |
| `unavailable-05` | 1 | 1 | Hayır |
| `unavailable-06` | 1 | 0 | Evet |
| `tag-deadline-01` | 1 | 1 | Hayır |
| `tag-deadline-02` | 1 | 1 | Hayır |
| `tag-deadline-03` | 1 | 1 | Hayır |
| `tag-deadline-04` | 1 | 1 | Hayır |
| `tag-deadline-05` | 1 | 0 | Evet |
| `tag-deadline-06` | 1 | 0 | Evet |
| `max-stops-01` | 1 | 1 | Hayır |
| `max-stops-02` | 1 | 1 | Hayır |
| `max-stops-03` | 1 | 1 | Hayır |
| `max-stops-04` | 1 | 1 | Hayır |
| `max-stops-05` | 1 | 1 | Hayır |
| `max-stops-06` | 1 | 1 | Hayır |
| `combined-01` | 1 | 1 | Hayır |
| `combined-02` | 1 | 0 | Evet |
| `combined-03` | 1 | 1 | Hayır |
| `combined-04` | 1 | 0 | Evet |
| `combined-05` | 1 | 0 | Evet |
| `combined-06` | 1 | 0 | Evet |
| `combined-07` | 1 | 0 | Evet |
| `combined-08` | 1 | 0 | Evet |
| `ambiguous-01` | 1 | 1 | Hayır |
| `ambiguous-02` | 1 | 1 | Hayır |
| `ambiguous-03` | 1 | 1 | Hayır |
| `ambiguous-04` | 1 | 1 | Hayır |
