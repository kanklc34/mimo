from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from constraints import ConstraintSet
from models import Scenario


SYSTEM_INSTRUCTION = """Türkçe kurye talimatlarını yalnızca aşağıdaki ConstraintSet JSON şemasına çevir.
Zamanları vardiya başlangıcından itibaren dakika tamsayısı olarak yaz. 'İlk iki saatte' gibi
göreli süreleri vardiya başlangıcından itibaren dakikaya dönüştür (iki saat = 120 dakika).
Kurye ve etiket adlarını yalnızca verilen senaryo listesinden seç. Anlamı kesin çıkaramıyorsan
constraints boş bırak ve anlaşılmadığını belirt. Başka alan veya açıklama üretme."""


class GeminiTranslator:
    def __init__(self, cache_dir: str | Path = "cache"):
        self.cache_dir = Path(cache_dir)

    @staticmethod
    def _dotenv() -> dict[str, str]:
        env_path = Path(".env")
        values: dict[str, str] = {}
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip("\"'")
        return values

    def _cache_path(self, sentence: str) -> Path:
        digest = hashlib.sha256(sentence.strip().encode("utf-8")).hexdigest()
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
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=json.dumps({"scenario": scenario_context, "text": sentence}, ensure_ascii=False),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0,
                response_mime_type="application/json",
                response_schema={
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
                                            "tag": {"type": "STRING"},
                                            "within_minutes_from_start": {"type": "INTEGER"},
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
                },
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
        constraints = ConstraintSet.model_validate(raw.get("constraints", {}), context={"scenario": scenario})
        understood_text = raw.get("understood_text")
        if not isinstance(understood_text, str) or not understood_text.strip():
            raise ValueError("Gemini yanıtında anlaşılır özet yok.")
        return {"constraints": constraints.model_dump(mode="json"), "understood_text": understood_text}
