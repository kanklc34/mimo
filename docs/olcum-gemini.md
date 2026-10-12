# Gemini talimat değerlendirmesi

Model kimliği: `gemini-3.1-flash-lite`
Doğru vaka oranı: **18/30 (60.0%)**
Plan başına çağrı hedefi: **1** · Bu çalıştırmada yapılan API çağrı denemesi: **17** · Değerlendirme cache eşleşmesi: **13**

Çağrı sayısı vaka başına kaydedilir; 429 yeniden denemeleri ayrı çağrı denemesi olarak sayılır. Cache'ten okunan yanıt raporunda ilk üretim çağrı sayısı korunur.

## Kısıt tipine göre

| Kısıt tipi | Tam eşleşen / beklenen kısıt |
|---|---:|
| `courier_unavailable_after` | 3/12 |
| `tag_deadline` | 8/12 |
| `max_stops` | 13/13 |

## Hata türleri

| Hata türü | Adet |
|---|---:|
| wrong type | 0 |
| wrong value | 13 |
| missing constraint | 0 |
| extra constraint | 0 |
| schema error | 0 |

## Hatalı vakalar ve Gemini yanıtı

### unavailable-02 · wrong value

Cümle: Saat 11:00'den sonra Kurye 2'ye iş verme.
Beklenen: `[{"type": "courier_unavailable_after", "courier_id": "courier-2", "time_min": 180}]`
Hata: wrong value (beklenen: {'type': 'courier_unavailable_after', 'courier_id': 'courier-2', 'time_min': 180}; alınan: {'type': 'courier_unavailable_after', 'courier_id': 'courier-2', 'time_min': 660})

<details><summary>Gemini yanıtı</summary><pre>
{
  &quot;constraints&quot;: {
    &quot;constraints&quot;: [
      {
        &quot;type&quot;: &quot;courier_unavailable_after&quot;,
        &quot;courier_id&quot;: &quot;courier-2&quot;,
        &quot;time_min&quot;: 660
      }
    ]
  },
  &quot;understood_text&quot;: &quot;Saat 11:00&#x27;den sonra Kurye 2&#x27;ye iş verme.&quot;
}
</pre></details>

### unavailable-03 · wrong value

Cümle: Kurye 3, 14'ten sonra yok.
Beklenen: `[{"type": "courier_unavailable_after", "courier_id": "courier-3", "time_min": 360}]`
Hata: wrong value (beklenen: {'type': 'courier_unavailable_after', 'courier_id': 'courier-3', 'time_min': 360}; alınan: {'type': 'courier_unavailable_after', 'courier_id': 'courier-3', 'time_min': 840})

<details><summary>Gemini yanıtı</summary><pre>
{
  &quot;constraints&quot;: {
    &quot;constraints&quot;: [
      {
        &quot;type&quot;: &quot;courier_unavailable_after&quot;,
        &quot;courier_id&quot;: &quot;courier-3&quot;,
        &quot;time_min&quot;: 840
      }
    ]
  },
  &quot;understood_text&quot;: &quot;Kurye 3, 14&#x27;ten sonra yok.&quot;
}
</pre></details>

### unavailable-04 · wrong value

Cümle: Kurye 4'ü saat 09.45'ten sonra kullanma.
Beklenen: `[{"type": "courier_unavailable_after", "courier_id": "courier-4", "time_min": 105}]`
Hata: wrong value (beklenen: {'type': 'courier_unavailable_after', 'courier_id': 'courier-4', 'time_min': 105}; alınan: {'type': 'courier_unavailable_after', 'courier_id': 'courier-4', 'time_min': 45})

<details><summary>Gemini yanıtı</summary><pre>
{
  &quot;constraints&quot;: {
    &quot;constraints&quot;: [
      {
        &quot;type&quot;: &quot;courier_unavailable_after&quot;,
        &quot;courier_id&quot;: &quot;courier-4&quot;,
        &quot;time_min&quot;: 45
      }
    ]
  },
  &quot;understood_text&quot;: &quot;Kurye 4&#x27;ü saat 09.45&#x27;ten sonra kullanma.&quot;
}
</pre></details>

### unavailable-06 · wrong value

Cümle: İki numaralı kurye 12:30'dan sonra görev almasın.
Beklenen: `[{"type": "courier_unavailable_after", "courier_id": "courier-2", "time_min": 270}]`
Hata: wrong value (beklenen: {'type': 'courier_unavailable_after', 'courier_id': 'courier-2', 'time_min': 270}; alınan: {'type': 'courier_unavailable_after', 'courier_id': 'courier-2', 'time_min': 390})

<details><summary>Gemini yanıtı</summary><pre>
{
  &quot;constraints&quot;: {
    &quot;constraints&quot;: [
      {
        &quot;type&quot;: &quot;courier_unavailable_after&quot;,
        &quot;courier_id&quot;: &quot;courier-2&quot;,
        &quot;time_min&quot;: 390
      }
    ]
  },
  &quot;understood_text&quot;: &quot;İki numaralı kurye 12:30&#x27;dan sonra görev almasın.&quot;
}
</pre></details>

### tag-deadline-05 · wrong value

Cümle: En geç 11.00'de soğuk zincir paketleri teslim edilmiş olsun.
Beklenen: `[{"type": "tag_deadline", "tag": "soğuk_zincir", "within_minutes_from_start": 180}]`
Hata: wrong value (beklenen: {'type': 'tag_deadline', 'tag': 'soğuk_zincir', 'within_minutes_from_start': 180}; alınan: {'type': 'tag_deadline', 'tag': 'soğuk_zincir', 'within_minutes_from_start': 660})

<details><summary>Gemini yanıtı</summary><pre>
{
  &quot;constraints&quot;: {
    &quot;constraints&quot;: [
      {
        &quot;type&quot;: &quot;tag_deadline&quot;,
        &quot;tag&quot;: &quot;soğuk_zincir&quot;,
        &quot;within_minutes_from_start&quot;: 660
      }
    ]
  },
  &quot;understood_text&quot;: &quot;En geç 11.00&#x27;de soğuk zincir paketleri teslim edilmiş olsun.&quot;
}
</pre></details>

### tag-deadline-06 · wrong value

Cümle: Soğuk zincir grubuna 14:00'a kadar zaman tanı.
Beklenen: `[{"type": "tag_deadline", "tag": "soğuk_zincir", "within_minutes_from_start": 360}]`
Hata: wrong value (beklenen: {'type': 'tag_deadline', 'tag': 'soğuk_zincir', 'within_minutes_from_start': 360}; alınan: {'type': 'tag_deadline', 'tag': 'soğuk_zincir', 'within_minutes_from_start': 480})

<details><summary>Gemini yanıtı</summary><pre>
{
  &quot;constraints&quot;: {
    &quot;constraints&quot;: [
      {
        &quot;type&quot;: &quot;tag_deadline&quot;,
        &quot;tag&quot;: &quot;soğuk_zincir&quot;,
        &quot;within_minutes_from_start&quot;: 480
      }
    ]
  },
  &quot;understood_text&quot;: &quot;Soğuk zincir grubuna 14:00&#x27;a kadar zaman tanı.&quot;
}
</pre></details>

### combined-02 · wrong value

Cümle: 11:00'den sonra Kurye 2 yok; soğuk zincir ilk iki saatte bitsin.
Beklenen: `[{"type": "courier_unavailable_after", "courier_id": "courier-2", "time_min": 180}, {"type": "tag_deadline", "tag": "soğuk_zincir", "within_minutes_from_start": 120}]`
Hata: wrong value (beklenen: {'type': 'courier_unavailable_after', 'courier_id': 'courier-2', 'time_min': 180}; alınan: {'type': 'courier_unavailable_after', 'courier_id': 'courier-2', 'time_min': 660})

<details><summary>Gemini yanıtı</summary><pre>
{
  &quot;constraints&quot;: {
    &quot;constraints&quot;: [
      {
        &quot;type&quot;: &quot;courier_unavailable_after&quot;,
        &quot;courier_id&quot;: &quot;courier-2&quot;,
        &quot;time_min&quot;: 660
      },
      {
        &quot;type&quot;: &quot;tag_deadline&quot;,
        &quot;tag&quot;: &quot;soğuk_zincir&quot;,
        &quot;within_minutes_from_start&quot;: 120
      }
    ]
  },
  &quot;understood_text&quot;: &quot;11:00&#x27;den sonra Kurye 2 yok; soğuk zincir ilk iki saatte bitsin.&quot;
}
</pre></details>

### combined-04 · wrong value

Cümle: Kurye 1, 14:00'ten sonra çalışmasın; en fazla 5 durak alsın ve soğuk zincir ilk 120 dakikada teslim edilsin.
Beklenen: `[{"type": "courier_unavailable_after", "courier_id": "courier-1", "time_min": 360}, {"type": "max_stops", "courier_id": "courier-1", "n": 5}, {"type": "tag_deadline", "tag": "soğuk_zincir", "within_minutes_from_start": 120}]`
Hata: wrong value (beklenen: {'type': 'courier_unavailable_after', 'courier_id': 'courier-1', 'time_min': 360}; alınan: {'type': 'courier_unavailable_after', 'courier_id': 'courier-1', 'time_min': 480})

<details><summary>Gemini yanıtı</summary><pre>
{
  &quot;constraints&quot;: {
    &quot;constraints&quot;: [
      {
        &quot;type&quot;: &quot;courier_unavailable_after&quot;,
        &quot;courier_id&quot;: &quot;courier-1&quot;,
        &quot;time_min&quot;: 480
      },
      {
        &quot;type&quot;: &quot;max_stops&quot;,
        &quot;courier_id&quot;: &quot;courier-1&quot;,
        &quot;n&quot;: 5
      },
      {
        &quot;type&quot;: &quot;tag_deadline&quot;,
        &quot;tag&quot;: &quot;soğuk_zincir&quot;,
        &quot;within_minutes_from_start&quot;: 120
      }
    ]
  },
  &quot;understood_text&quot;: &quot;Kurye 1 saat 14:00&#x27;ten sonra (vardiya başlangıcı 06:00 varsayılarak 480. dakika) çalışmayacak, en fazla 5 durak alacak ve soğuk zincir etiketli siparişler ilk 120 dakika içinde teslim edilecek.&quot;
}
</pre></details>

### combined-05 · wrong value

Cümle: Kurye 4 12:00'den sonra yok, dokuz durağı geçmesin, soğuk zincir ilk üç saatte teslim edilsin.
Beklenen: `[{"type": "courier_unavailable_after", "courier_id": "courier-4", "time_min": 240}, {"type": "max_stops", "courier_id": "courier-4", "n": 9}, {"type": "tag_deadline", "tag": "soğuk_zincir", "within_minutes_from_start": 180}]`
Hata: wrong value (beklenen: {'type': 'courier_unavailable_after', 'courier_id': 'courier-4', 'time_min': 240}; alınan: {'type': 'courier_unavailable_after', 'courier_id': 'courier-4', 'time_min': 360})

<details><summary>Gemini yanıtı</summary><pre>
{
  &quot;constraints&quot;: {
    &quot;constraints&quot;: [
      {
        &quot;type&quot;: &quot;courier_unavailable_after&quot;,
        &quot;courier_id&quot;: &quot;courier-4&quot;,
        &quot;time_min&quot;: 360
      },
      {
        &quot;type&quot;: &quot;max_stops&quot;,
        &quot;courier_id&quot;: &quot;courier-4&quot;,
        &quot;n&quot;: 9
      },
      {
        &quot;type&quot;: &quot;tag_deadline&quot;,
        &quot;tag&quot;: &quot;soğuk_zincir&quot;,
        &quot;within_minutes_from_start&quot;: 180
      }
    ]
  },
  &quot;understood_text&quot;: &quot;Kurye 4 vardiya başlangıcından 360 dakika sonra (12:00) paydos edecek, en fazla 9 durak yapabilecek ve soğuk zincir etiketli gönderiler ilk 180 dakika içinde teslim edilecek.&quot;
}
</pre></details>

### combined-06 · wrong value

Cümle: Kurye 2'ye en çok 7 durak ver ve 13:15'ten sonra görev verme.
Beklenen: `[{"type": "max_stops", "courier_id": "courier-2", "n": 7}, {"type": "courier_unavailable_after", "courier_id": "courier-2", "time_min": 315}]`
Hata: wrong value (beklenen: {'type': 'courier_unavailable_after', 'courier_id': 'courier-2', 'time_min': 315}; alınan: {'type': 'courier_unavailable_after', 'courier_id': 'courier-2', 'time_min': 795})

<details><summary>Gemini yanıtı</summary><pre>
{
  &quot;constraints&quot;: {
    &quot;constraints&quot;: [
      {
        &quot;type&quot;: &quot;max_stops&quot;,
        &quot;courier_id&quot;: &quot;courier-2&quot;,
        &quot;n&quot;: 7
      },
      {
        &quot;type&quot;: &quot;courier_unavailable_after&quot;,
        &quot;courier_id&quot;: &quot;courier-2&quot;,
        &quot;time_min&quot;: 795
      }
    ]
  },
  &quot;understood_text&quot;: &quot;Kurye 2&#x27;ye en çok 7 durak ver ve 13:15&#x27;ten sonra görev verme.&quot;
}
</pre></details>

### combined-07 · wrong value

Cümle: Soğuk zincirleri 11'e kadar teslim et, Kurye 3'e dört duraktan fazla yükleme.
Beklenen: `[{"type": "tag_deadline", "tag": "soğuk_zincir", "within_minutes_from_start": 180}, {"type": "max_stops", "courier_id": "courier-3", "n": 4}]`
Hata: wrong value (beklenen: {'type': 'tag_deadline', 'tag': 'soğuk_zincir', 'within_minutes_from_start': 180}; alınan: {'type': 'tag_deadline', 'tag': 'soğuk_zincir', 'within_minutes_from_start': 660})

<details><summary>Gemini yanıtı</summary><pre>
{
  &quot;constraints&quot;: {
    &quot;constraints&quot;: [
      {
        &quot;type&quot;: &quot;tag_deadline&quot;,
        &quot;tag&quot;: &quot;soğuk_zincir&quot;,
        &quot;within_minutes_from_start&quot;: 660
      },
      {
        &quot;type&quot;: &quot;max_stops&quot;,
        &quot;courier_id&quot;: &quot;courier-3&quot;,
        &quot;n&quot;: 4
      }
    ]
  },
  &quot;understood_text&quot;: &quot;Soğuk zincirleri 660. dakikaya kadar teslim et, Kurye 3&#x27;e dört duraktan fazla yükleme.&quot;
}
</pre></details>

### combined-08 · wrong value, wrong value

Cümle: Kurye 1 için en fazla 10 teslimat olsun, Kurye 2 09:30'dan sonra yok, soğuk zincir 10:00'a kadar tamamlansın.
Beklenen: `[{"type": "max_stops", "courier_id": "courier-1", "n": 10}, {"type": "courier_unavailable_after", "courier_id": "courier-2", "time_min": 90}, {"type": "tag_deadline", "tag": "soğuk_zincir", "within_minutes_from_start": 120}]`
Hata: wrong value (beklenen: {'type': 'courier_unavailable_after', 'courier_id': 'courier-2', 'time_min': 90}; alınan: {'type': 'courier_unavailable_after', 'courier_id': 'courier-2', 'time_min': 330}); wrong value (beklenen: {'type': 'tag_deadline', 'tag': 'soğuk_zincir', 'within_minutes_from_start': 120}; alınan: {'type': 'tag_deadline', 'tag': 'soğuk_zincir', 'within_minutes_from_start': 360})

<details><summary>Gemini yanıtı</summary><pre>
{
  &quot;constraints&quot;: {
    &quot;constraints&quot;: [
      {
        &quot;type&quot;: &quot;max_stops&quot;,
        &quot;courier_id&quot;: &quot;courier-1&quot;,
        &quot;n&quot;: 10
      },
      {
        &quot;type&quot;: &quot;courier_unavailable_after&quot;,
        &quot;courier_id&quot;: &quot;courier-2&quot;,
        &quot;time_min&quot;: 330
      },
      {
        &quot;type&quot;: &quot;tag_deadline&quot;,
        &quot;tag&quot;: &quot;soğuk_zincir&quot;,
        &quot;within_minutes_from_start&quot;: 360
      }
    ]
  },
  &quot;understood_text&quot;: &quot;Kurye 1 için en fazla 10 teslimat, Kurye 2 için 09:30 (330. dakika) sonrası kısıtlaması ve soğuk zincir için 10:00 (360. dakika) teslimat süresi tanımlandı.&quot;
}
</pre></details>

## Plan başına Gemini çağrı sayısı

| Vaka | Çağrı denemesi | Bu çalıştırmada | Cache kullanıldı |
|---|---:|---:|---|
| `unavailable-01` | 1 | 0 | Evet |
| `unavailable-02` | 1 | 0 | Evet |
| `unavailable-03` | 1 | 0 | Evet |
| `unavailable-04` | 1 | 0 | Evet |
| `unavailable-05` | 1 | 0 | Evet |
| `unavailable-06` | 1 | 0 | Evet |
| `tag-deadline-01` | 1 | 0 | Evet |
| `tag-deadline-02` | 1 | 0 | Evet |
| `tag-deadline-03` | 1 | 0 | Evet |
| `tag-deadline-04` | 1 | 0 | Evet |
| `tag-deadline-05` | 1 | 0 | Evet |
| `tag-deadline-06` | 1 | 0 | Evet |
| `max-stops-01` | 1 | 0 | Evet |
| `max-stops-02` | 1 | 1 | Hayır |
| `max-stops-03` | 1 | 1 | Hayır |
| `max-stops-04` | 1 | 1 | Hayır |
| `max-stops-05` | 1 | 1 | Hayır |
| `max-stops-06` | 1 | 1 | Hayır |
| `combined-01` | 1 | 1 | Hayır |
| `combined-02` | 1 | 1 | Hayır |
| `combined-03` | 1 | 1 | Hayır |
| `combined-04` | 1 | 1 | Hayır |
| `combined-05` | 1 | 1 | Hayır |
| `combined-06` | 1 | 1 | Hayır |
| `combined-07` | 1 | 1 | Hayır |
| `combined-08` | 1 | 1 | Hayır |
| `ambiguous-01` | 1 | 1 | Hayır |
| `ambiguous-02` | 1 | 1 | Hayır |
| `ambiguous-03` | 1 | 1 | Hayır |
| `ambiguous-04` | 1 | 1 | Hayır |
