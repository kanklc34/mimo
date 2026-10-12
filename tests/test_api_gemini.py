import json
import sys
from types import ModuleType, SimpleNamespace
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from api import gemini
from api.gemini import GeminiTranslator
from generator import generate_scenario


@pytest.mark.parametrize(("clock", "expected"), [
    ("11:00", 180),
    ("14:00", 360),
    ("09:45", 105),
    ("12:30", 270),
])
def test_wall_clock_conversion_uses_0800_shift_start(clock, expected):
    assert gemini.clock_to_minutes_from_shift_start(clock, shift_start_min=0) == expected


def test_process_environment_overrides_dotenv_gemini_configuration(monkeypatch):
    with TemporaryDirectory(dir=Path(__file__).parent) as temp_dir:
        (Path(temp_dir) / ".env").write_text(
            "GEMINI_API_KEY=file-key\nGEMINI_MODEL=file-model\n", encoding="utf-8"
        )
        with monkeypatch.context() as patch:
            patch.chdir(temp_dir)
            patch.setenv("GEMINI_API_KEY", "host-key")
            patch.setenv("GEMINI_MODEL", "host-model")

            config = GeminiTranslator._dotenv()

            assert config["GEMINI_API_KEY"] == "host-key"
            assert config["GEMINI_MODEL"] == "host-model"


def test_relative_minutes_are_preserved_during_time_normalization():
    raw = {"constraints": {"constraints": [
        {"type": "tag_deadline", "tag": "soğuk_zincir", "within_minutes_from_start": 120},
    ]}, "understood_text": "Göreli süre."}

    normalized = GeminiTranslator._normalize_clock_constraints(raw, generate_scenario())

    assert normalized["constraints"]["constraints"][0]["within_minutes_from_start"] == 120


def test_clock_fields_are_converted_and_removed_before_constraint_validation():
    raw = {"constraints": {"constraints": [
        {"type": "courier_unavailable_after", "courier_id": "courier-1", "time_hhmm": "11:00"},
        {"type": "tag_deadline", "tag": "soğuk_zincir", "deadline_hhmm": "14:00"},
    ]}, "understood_text": "Saatli kısıtlar."}

    normalized = GeminiTranslator._normalize_clock_constraints(raw, generate_scenario())

    assert normalized["constraints"]["constraints"] == [
        {"type": "courier_unavailable_after", "courier_id": "courier-1", "time_min": 180},
        {"type": "tag_deadline", "tag": "soğuk_zincir", "within_minutes_from_start": 360},
    ]


def test_demo_mode_reads_sentence_cache_without_calling_client(monkeypatch):
    with TemporaryDirectory(dir=Path(__file__).parent) as temp_dir:
        cache = Path(temp_dir) / "cache"
        cache.mkdir()
        sentence = "Kurye 1 en fazla 7 durak alsın"
        translator = GeminiTranslator(cache_dir=cache)
        digest = translator._cache_path(sentence).stem
        (cache / f"{digest}.json").write_text(
            json.dumps({
                "constraints": {"constraints": [{"type": "max_stops", "courier_id": "courier-1", "n": 7}]},
                "understood_text": "Kurye 1 en fazla 7 durak alacak.",
            }, ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.setenv("GEMINI_DEMO_MODE", "1")

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
        assert "08:00" in config.system_instruction
        assert "HH:MM" in config.system_instruction
        schema_item = config.response_schema["properties"]["constraints"]["properties"]["constraints"]["items"]
        assert "time_hhmm" in schema_item["properties"]
        assert "deadline_hhmm" in schema_item["properties"]
        assert len(list(Path(temp_dir).glob("*.json"))) == 1


def test_live_translation_reuses_open_client_for_consecutive_calls(monkeypatch):
    with TemporaryDirectory(dir=Path(__file__).parent) as temp_dir:
        client_state = {"closed": False, "created": 0}
        response_text = json.dumps({
            "constraints": {"constraints": []},
            "understood_text": "Kısıt bulunamadı.",
        }, ensure_ascii=False)

        class FakeModels:
            def __init__(self, state):
                self.state = state

            def generate_content(self, **_kwargs):
                if self.state["closed"]:
                    raise RuntimeError("Cannot send a request, as the client has been closed.")
                return SimpleNamespace(text=response_text)

        class FakeClient:
            def __init__(self, *, api_key):
                self.api_key = api_key
                client_state["created"] += 1
                self.models = FakeModels(client_state)

            def __del__(self):
                client_state["closed"] = True

        google_module = ModuleType("google")
        genai_module = ModuleType("google.genai")
        types_module = ModuleType("google.genai.types")
        genai_module.Client = FakeClient
        types_module.GenerateContentConfig = lambda **kwargs: SimpleNamespace(**kwargs)
        google_module.genai = genai_module
        monkeypatch.setitem(sys.modules, "google", google_module)
        monkeypatch.setitem(sys.modules, "google.genai", genai_module)
        monkeypatch.setitem(sys.modules, "google.genai.types", types_module)
        monkeypatch.setattr(GeminiTranslator, "_dotenv", staticmethod(lambda: {
            "GEMINI_API_KEY": "secret-test-key",
            "GEMINI_MODEL": "gemini-test",
        }))
        monkeypatch.delenv("GEMINI_DEMO_MODE", raising=False)

        translator = GeminiTranslator(cache_dir=temp_dir)
        first = translator.interpret("ilk cümle", generate_scenario())
        second = translator.interpret("ikinci cümle", generate_scenario())

        assert first["understood_text"] == "Kısıt bulunamadı."
        assert second["understood_text"] == "Kısıt bulunamadı."
        assert client_state["created"] == 1
        assert client_state["closed"] is False

