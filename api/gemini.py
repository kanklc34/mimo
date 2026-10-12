from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from threading import Lock
from typing import Any

from constraints import ConstraintSet
from models import Scenario


SHIFT_START_CLOCK_MIN = 8 * 60

SYSTEM_INSTRUCTION = """Türkçe kurye talimatlarını yalnızca aşağıdaki JSON şemasına çevir.
Vardiya başlangıcı 08:00'dır. Saat olarak verilen sınırları aritmetik yapmadan, HH:MM
biçiminde `time_hhmm` (kurye müsaitliği) veya `deadline_hhmm` (etiket teslim sınırı)
alanına yaz. Saat ile belirtilmeyen göreli süreleri doğrudan `time_min` veya
`within_minutes_from_start` alanına vardiya başlangıcından itibaren dakika olarak yaz.
Saat sınırını dakika alanlarına yazma ve vardiya başlangıcını tahmin etme. Saat nokta ile
yazılmışsa HH:MM biçimine normalleştir; yalnızca saat belirtilmişse dakikayı 00 kabul et.
Kurye ve etiket adlarını yalnızca verilen senaryo listesinden seç. Anlamı kesin çıkaramıyorsan
constraints boş bırak ve anlaşılmadığını belirt. Başka alan veya açıklama üretme."""

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "constraints": {
            "type": "OBJECT",
            "properties": {
                "constraints": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "type": {"type": "STRING", "enum": [
                                "courier_unavailable_after", "tag_deadline", "max_stops"
                            ]},
                            "courier_id": {"type": "STRING"},
                            "time_min": {"type": "INTEGER"},
                            "time_hhmm": {"type": "STRING"},
                            "tag": {"type": "STRING"},
                            "within_minutes_from_start": {"type": "INTEGER"},
                            "deadline_hhmm": {"type": "STRING"},
                            "n": {"type": "INTEGER"},
                        },
                        "required": ["type"],
                    },
                }
            },
            "required": ["constraints"],
        },
        "understood_text": {"type": "STRING"},
    },
    "required": ["constraints", "understood_text"],
}

PROMPT_SCHEMA_FINGERPRINT = hashlib.sha256(json.dumps({
    "system_instruction": SYSTEM_INSTRUCTION,
    "response_schema": RESPONSE_SCHEMA,
    "clock_normalization": "08:00-wall-clock-v1",
}, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def clock_to_minutes_from_shift_start(clock: str, *, shift_start_min: int = 0) -> int:
    """Convert a wall-clock HH:MM value to minutes since the 08:00 shift start."""
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", clock.strip())
    if not match:
        raise ValueError(f"Saat HH:MM biçiminde olmalı: {clock!r}")
    hours, minutes = map(int, match.groups())
    if hours > 23 or minutes > 59:
        raise ValueError(f"Geçersiz saat: {clock!r}")
    result = hours * 60 + minutes - (SHIFT_START_CLOCK_MIN + shift_start_min)
    if result < 0:
        raise ValueError(f"Saat vardiya başlangıcından önce: {clock!r}")
    return result


class GeminiTranslator:
    def __init__(self, cache_dir: str | Path = "cache"):
        self.cache_dir = Path(cache_dir)
        self._client: Any | None = None
        self._client_lock = Lock()

    @staticmethod
    def _dotenv() -> dict[str, str]:
        env_path = Path(".env")
        values: dict[str, str] = dict(os.environ)
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values.setdefault(key.strip(), value.strip().strip("\"'"))
        return values

    def _cache_path(self, sentence: str) -> Path:
        key = json.dumps({
            "sentence": sentence.strip(),
            "prompt_schema_fingerprint": PROMPT_SCHEMA_FINGERPRINT,
        }, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def interpret(self, sentence: str, scenario: Scenario) -> dict[str, Any]:
        path = self._cache_path(sentence)
        demo_mode = os.getenv("GEMINI_DEMO_MODE", self._dotenv().get("GEMINI_DEMO_MODE", "0")) == "1"
        if demo_mode:
            if not path.exists():
                raise ValueError("Bu cümle için cache kaydı bulunamadı.")
            raw = json.loads(path.read_text(encoding="utf-8"))
            return self._validate(raw, scenario)

        if path.exists():
            return self._validate(json.loads(path.read_text(encoding="utf-8")), scenario)

        env = self._dotenv()
        api_key = env.get("GEMINI_API_KEY")
        model = env.get("GEMINI_MODEL")
        if not api_key or not model:
            raise ValueError("Gemini yapılandırması .env içinde bulunamadı.")
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ValueError("google-genai paketi kurulu değil.") from exc

        scenario_context = {
            "couriers": [{"id": c.id, "name": c.name} for c in scenario.couriers],
            "tags": sorted(scenario.tags),
        }
        # Keep the SDK client owned by this translator. The API's translator
        # lives for the process lifetime, and eval reuses that same instance.
        with self._client_lock:
            if self._client is None:
                self._client = genai.Client(api_key=api_key)
            client = self._client
        response = client.models.generate_content(
            model=model,
            contents=json.dumps({"scenario": scenario_context, "text": sentence}, ensure_ascii=False),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0,
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA,
            ),
        )
        try:
            result = self._validate(json.loads(response.text), scenario)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError("Gemini yanıtı constraints şemasına uymuyor.") from exc
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    @staticmethod
    def _validate(raw: dict[str, Any], scenario: Scenario) -> dict[str, Any]:
        raw = GeminiTranslator._normalize_clock_constraints(raw, scenario)
        constraints = ConstraintSet.model_validate(raw.get("constraints", {}), context={"scenario": scenario})
        understood_text = raw.get("understood_text")
        if not isinstance(understood_text, str) or not understood_text.strip():
            raise ValueError("Gemini yanıtında anlaşılır özet yok.")
        return {"constraints": constraints.model_dump(mode="json"), "understood_text": understood_text}

    @staticmethod
    def _normalize_clock_constraints(raw: dict[str, Any], scenario: Scenario) -> dict[str, Any]:
        normalized = dict(raw)
        constraint_payload = dict(raw.get("constraints", {}))
        constraints = constraint_payload.get("constraints", [])
        normalized_constraints = []
        for source in constraints:
            constraint = dict(source)
            kind = constraint.get("type")
            if kind == "courier_unavailable_after" and "time_hhmm" in constraint:
                courier = scenario.courier_by_id.get(constraint.get("courier_id"))
                if courier is None:
                    raise ValueError("Saat dönüşümü için kurye senaryoda bulunamadı.")
                constraint["time_min"] = clock_to_minutes_from_shift_start(
                    constraint.pop("time_hhmm"), shift_start_min=courier.shift_start,
                )
            elif kind == "tag_deadline" and "deadline_hhmm" in constraint:
                shift_start = min((courier.shift_start for courier in scenario.couriers), default=0)
                constraint["within_minutes_from_start"] = clock_to_minutes_from_shift_start(
                    constraint.pop("deadline_hhmm"), shift_start_min=shift_start,
                )
            normalized_constraints.append(constraint)
        constraint_payload["constraints"] = normalized_constraints
        normalized["constraints"] = constraint_payload
        return normalized
