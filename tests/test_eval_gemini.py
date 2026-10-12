from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

import api.gemini
import api.main
from scripts import eval_gemini


def test_evaluator_uses_api_interpret_translator_for_first_case(monkeypatch):
    first_case = {
        "id": "unavailable-01",
        "text": "Kurye 1 180. dakikadan sonra yok.",
        "expected": [{
            "type": "courier_unavailable_after",
            "courier_id": "courier-1",
            "time_min": 180,
        }],
        "category": "courier_unavailable_after",
    }

    class FakeTranslator:
        def __init__(self):
            self.sentences = []

        def interpret(self, sentence, scenario):
            self.sentences.append(sentence)
            return {
                "constraints": {"constraints": first_case["expected"]},
                "understood_text": "Kurye 1 için 180 dakika sonrası.",
            }

    fake_translator = FakeTranslator()
    monkeypatch.setattr(api.main, "translator", fake_translator)
    monkeypatch.setattr(eval_gemini, "_load_gemini_config", lambda: ({}, "fake-model"))
    monkeypatch.setattr(eval_gemini, "_load_cases", lambda _path: [first_case])
    monkeypatch.setattr(eval_gemini, "_install_request_recorder", lambda _recorder: None)

    def forbidden_constructor(*_args, **_kwargs):
        raise AssertionError("Evaluator must use api.main's /interpret translator instance")

    monkeypatch.setattr(api.gemini, "GeminiTranslator", forbidden_constructor)

    cache_parent = Path("cache")
    cache_parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_parent) as temp_dir:
        result = eval_gemini.evaluate(argparse.Namespace(
            dataset=Path("unused.json"),
            cache=Path(temp_dir) / "eval-cache",
            retry_wait=0,
            max_retries=0,
            request_delay=0,
        ))

    assert fake_translator.sentences == [first_case["text"]]
    assert result["evaluations"][0]["id"] == "unavailable-01"
    assert result["evaluations"][0]["correct"] is True


def test_evaluator_prints_progress_for_each_case(monkeypatch, capsys):
    case = {
        "id": "unavailable-01", "text": "Bir test vakası.", "expected": [],
        "category": "courier_unavailable_after",
    }

    class FakeTranslator:
        def interpret(self, _sentence, _scenario):
            return {"constraints": {"constraints": []}, "understood_text": "Boş."}

    monkeypatch.setattr(api.main, "translator", FakeTranslator())
    monkeypatch.setattr(eval_gemini, "_load_gemini_config", lambda: ({}, "fake-model"))
    monkeypatch.setattr(eval_gemini, "_load_cases", lambda _path: [case])
    monkeypatch.setattr(eval_gemini, "_install_request_recorder", lambda _recorder: None)

    cache_parent = Path("cache")
    cache_parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_parent) as temp_dir:
        eval_gemini.evaluate(argparse.Namespace(
            dataset=Path("unused.json"), cache=Path(temp_dir) / "eval-cache",
            retry_wait=0, max_retries=0, request_delay=0,
        ))

    assert "[1/1] unavailable-01" in capsys.readouterr().out


def test_only_failed_ids_come_from_previous_report():
    ids = eval_gemini._load_previous_failed_ids()

    assert len(ids) == 12
    assert {"unavailable-02", "tag-deadline-06", "combined-08"} <= ids


def test_evaluator_discards_cache_from_old_prompt_or_schema():
    case = {"id": "unavailable-02", "text": "Bir saat sınırı.", "expected": []}
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp_dir:
        cache_file = Path(temp_dir) / "case.json"
        cache_file.write_text(
            '{"sentence":"Bir saat sınırı.","model_id":"model","prompt_schema_fingerprint":"old"}',
            encoding="utf-8",
        )

        assert eval_gemini._read_cache(cache_file, case, "model") is None


def test_evaluator_defaults_to_three_second_request_delay_and_supports_only_failed(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["eval_gemini.py", "--only-failed"])

    args = eval_gemini.parse_args()

    assert args.request_delay == 3.0
    assert args.only_failed is True
