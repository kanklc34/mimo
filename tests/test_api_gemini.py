import hashlib
import json
import sys
from types import ModuleType, SimpleNamespace
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from api.gemini import GeminiTranslator
from generator import generate_scenario


def test_demo_mode_reads_sentence_cache_without_calling_client(monkeypatch):
    with TemporaryDirectory(dir=Path(__file__).parent) as temp_dir:
        cache = Path(temp_dir) / "cache"
        cache.mkdir()
        sentence = "Kurye 1 en fazla 7 durak alsın"
        digest = hashlib.sha256(sentence.encode("utf-8")).hexdigest()
        (cache / f"{digest}.json").write_text(
            json.dumps({
                "constraints": {"constraints": [{"type": "max_stops", "courier_id": "courier-1", "n": 7}]},
                "understood_text": "Kurye 1 en fazla 7 durak alacak.",
            }, ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.setenv("GEMINI_DEMO_MODE", "1")

        translator = GeminiTranslator(cache_dir=cache)
        result = translator.interpret(sentence, generate_scenario())

        assert result["constraints"]["constraints"][0]["courier_id"] == "courier-1"


def test_demo_mode_cache_miss_returns_understood_error(monkeypatch):
    with TemporaryDirectory(dir=Path(__file__).parent) as temp_dir:
        monkeypatch.setenv("GEMINI_DEMO_MODE", "1")
        translator = GeminiTranslator(cache_dir=temp_dir)

        with pytest.raises(ValueError, match="cache"):
            translator.interpret("kayıtsız cümle", generate_scenario())


def test_live_translation_uses_mocked_sdk_and_caches_response(monkeypatch):
    with TemporaryDirectory(dir=Path(__file__).parent) as temp_dir:
        captured = {}
        response_text = json.dumps({
            "constraints": {"constraints": [{"type": "tag_deadline", "tag": "soğuk_zincir", "within_minutes_from_start": 120}]},
            "understood_text": "Soğuk zincir duraklarını ilk 120 dakikada teslim et.",
        }, ensure_ascii=False)

        class FakeModels:
            def generate_content(self, **kwargs):
                captured["request"] = kwargs
                return SimpleNamespace(text=response_text)

        class FakeClient:
            def __init__(self, *, api_key):
                captured["api_key"] = api_key
                self.models = FakeModels()

        google_module = ModuleType("google")
        genai_module = ModuleType("google.genai")
        types_module = ModuleType("google.genai.types")
        genai_module.Client = FakeClient
        types_module.GenerateContentConfig = lambda **kwargs: SimpleNamespace(**kwargs)
        google_module.genai = genai_module
        monkeypatch.setitem(sys.modules, "google", google_module)
        monkeypatch.setitem(sys.modules, "google.genai", genai_module)
        monkeypatch.setitem(sys.modules, "google.genai.types", types_module)
        monkeypatch.setattr(GeminiTranslator, "_dotenv", staticmethod(lambda: {"GEMINI_API_KEY": "secret-test-key", "GEMINI_MODEL": "gemini-test"}))
        monkeypatch.delenv("GEMINI_DEMO_MODE", raising=False)

        translator = GeminiTranslator(cache_dir=temp_dir)
        result = translator.interpret("Soğuk zincir ilk iki saatte teslim edilsin", generate_scenario())

        config = captured["request"]["config"]
        assert result["constraints"]["constraints"][0]["within_minutes_from_start"] == 120
        assert captured["api_key"] == "secret-test-key"
        assert captured["request"]["model"] == "gemini-test"
        assert config.temperature == 0
        assert config.response_mime_type == "application/json"
        assert "120 dakika" in config.system_instruction
        assert len(list(Path(temp_dir).glob("*.json"))) == 1

