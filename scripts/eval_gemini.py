from __future__ import annotations

import argparse
import atexit
import html
import json
import os
import re
import sys
import time
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "tests" / "data" / "gemini_eval.json"
DEFAULT_CACHE = ROOT / "cache" / "gemini_eval"
DEFAULT_REPORT = ROOT / "docs" / "olcum-gemini.md"
ERROR_TYPES = ("wrong type", "wrong value", "missing constraint", "extra constraint", "schema error")


class RequestRecorder:
    def __init__(self, retry_wait_s: float, max_retries: int):
        self.retry_wait_s = retry_wait_s
        self.max_retries = max_retries
        self.attempts = 0
        self.raw_response: str | None = None
        self.response_received = False

    def reset(self) -> None:
        self.attempts = 0
        self.raw_response = None
        self.response_received = False


def _is_rate_limit(error: Exception) -> bool:
    status = getattr(error, "status_code", None) or getattr(error, "code", None)
    response = getattr(error, "response", None)
    status = status or getattr(response, "status_code", None)
    if str(status) == "429":
        return True
    return bool(re.search(r"\b429\b|RESOURCE_EXHAUSTED|RATE.?LIMIT", str(error), re.IGNORECASE))


def _install_request_recorder(recorder: RequestRecorder) -> None:
    try:
        from google import genai
    except ImportError as exc:
        raise SystemExit("Hata: google-genai paketi kurulu değil.") from exc

    original_client = genai.Client

    class RecordingModels:
        def __init__(self, models):
            self._models = models

        def generate_content(self, **kwargs):
            for retry_index in range(recorder.max_retries + 1):
                recorder.attempts += 1
                try:
                    response = self._models.generate_content(**kwargs)
                    recorder.raw_response = response.text
                    recorder.response_received = True
                    return response
                except Exception as error:
                    if not _is_rate_limit(error) or retry_index >= recorder.max_retries:
                        raise
                    time.sleep(min(30.0, recorder.retry_wait_s * (2**retry_index)))
            raise RuntimeError("Gemini çağrısı yeniden deneme sınırına ulaştı.")

    class RecordingClient:
        def __init__(self, *args, **kwargs):
            delegate = original_client(*args, **kwargs)
            self.models = RecordingModels(delegate.models)

    genai.Client = RecordingClient


def _load_gemini_config() -> tuple[dict[str, str], str]:
    from api.gemini import GeminiTranslator

    config = GeminiTranslator._dotenv()
    api_key = os.environ.get("GEMINI_API_KEY") or config.get("GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL") or config.get("GEMINI_MODEL")
    if not api_key:
        raise SystemExit("Hata: GEMINI_API_KEY bulunamadı. Ortam değişkeninde veya proje kökündeki .env dosyasında tanımlayın.")
    if not model:
        raise SystemExit("Hata: GEMINI_MODEL bulunamadı. Ortam değişkeninde veya proje kökündeki .env dosyasında tanımlayın.")

    config["GEMINI_API_KEY"] = api_key
    config["GEMINI_MODEL"] = model
    config["GEMINI_DEMO_MODE"] = "0"
    # GeminiTranslator normally reads credentials from .env. Merge process
    # environment values in memory so the evaluator also supports env-only setup.
    GeminiTranslator._dotenv = staticmethod(lambda: dict(config))
    os.environ["GEMINI_DEMO_MODE"] = "0"
    return config, model


def _subject(constraint: dict[str, Any]) -> tuple[str, Any] | None:
    if "courier_id" in constraint:
        return "courier_id", constraint["courier_id"]
    if "tag" in constraint:
        return "tag", constraint["tag"]
    return None


def _numeric_fields(constraint: dict[str, Any]) -> tuple[str, ...]:
    return {
        "courier_unavailable_after": ("time_min",),
        "tag_deadline": ("within_minutes_from_start",),
        "max_stops": ("n",),
    }.get(constraint.get("type"), ())


def compare_constraints(expected: list[dict[str, Any]], actual: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], Counter]:
    unmatched = set(range(len(actual)))
    unmatched_expected = set(range(len(expected)))
    issues: list[dict[str, Any]] = []
    exact_by_type: Counter = Counter()

    # Match exact type and identity across the whole sentence before classifying
    # mismatches, so an early wrong courier cannot consume a later exact match.
    for expected_index, expected_constraint in enumerate(expected):
        subject = _subject(expected_constraint)
        same_type = [
            index for index in unmatched
            if actual[index].get("type") == expected_constraint.get("type") and _subject(actual[index]) == subject
        ]
        if same_type:
            index = same_type[0]
            unmatched.remove(index)
            unmatched_expected.remove(expected_index)
            actual_constraint = actual[index]
            wrong_values = [field for field in _numeric_fields(expected_constraint)
                            if actual_constraint.get(field) != expected_constraint.get(field)]
            if wrong_values:
                issues.append({
                    "type": "wrong value",
                    "expected": expected_constraint,
                    "actual": actual_constraint,
                    "fields": wrong_values,
                })
            else:
                exact_by_type[expected_constraint["type"]] += 1

    for expected_index in sorted(unmatched_expected):
        expected_constraint = expected[expected_index]
        subject = _subject(expected_constraint)
        same_subject = [index for index in unmatched if subject is not None and _subject(actual[index]) == subject]
        if same_subject:
            index = same_subject[0]
            unmatched.remove(index)
            issues.append({
                "type": "wrong type",
                "expected": expected_constraint,
                "actual": actual[index],
            })
        else:
            same_type = [index for index in unmatched if actual[index].get("type") == expected_constraint.get("type")]
            if same_type:
                def value_distance(index: int) -> tuple[int, int]:
                    fields = _numeric_fields(expected_constraint)
                    differences = [abs(actual[index].get(field, 0) - expected_constraint.get(field, 0)) for field in fields]
                    identity_field = subject[0] if subject is not None else None
                    identity_mismatch = int(bool(identity_field) and actual[index].get(identity_field) != expected_constraint.get(identity_field))
                    return (sum(value != 0 for value in differences), identity_mismatch + sum(differences))

                index = min(same_type, key=value_distance)
                unmatched.remove(index)
                actual_constraint = actual[index]
                identity_field = subject[0] if subject is not None else None
                wrong_values = ([identity_field] if identity_field and actual_constraint.get(identity_field) != expected_constraint.get(identity_field) else [])
                wrong_values.extend(field for field in _numeric_fields(expected_constraint)
                                    if actual_constraint.get(field) != expected_constraint.get(field))
                issues.append({"type": "wrong value", "expected": expected_constraint,
                               "actual": actual_constraint, "fields": wrong_values})
            else:
                issues.append({"type": "missing constraint", "expected": expected_constraint, "actual": None})

    for index in sorted(unmatched):
        issues.append({"type": "extra constraint", "expected": None, "actual": actual[index]})
    return issues, exact_by_type


def _case_cache_path(cache_root: Path, case_id: str) -> Path:
    safe_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", case_id)
    return cache_root / "cases" / f"{safe_id}.json"


def _read_cache(path: Path, case: dict[str, Any], model: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        cached = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if cached.get("sentence") != case["text"] or cached.get("model_id") != model:
        return None
    return cached


def _write_cache(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _load_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise SystemExit(f"Hata: {path} içinde cases listesi yok veya boş.")
    ids = [case.get("id") for case in cases]
    if len(set(ids)) != len(ids) or any(not case.get("text") or not isinstance(case.get("expected"), list) for case in cases):
        raise SystemExit(f"Hata: {path} içinde yinelenen kimlik ya da eksik text/expected alanı var.")
    category_counts = Counter(case.get("category") for case in cases)
    required_categories = ("courier_unavailable_after", "tag_deadline", "max_stops")
    if any(category_counts[category] < 5 for category in required_categories):
        raise SystemExit("Hata: üç tekil kısıt tipinin her birinde en az beş vaka olmalı.")
    if category_counts["combined"] < 5 or category_counts["ambiguous"] < 3:
        raise SystemExit("Hata: birleşik ve belirsiz vaka sayısı eval seti gereksinimini karşılamıyor.")
    if any(not 2 <= len(case["expected"]) <= 3 for case in cases if case.get("category") == "combined"):
        raise SystemExit("Hata: birleşik vakalarda iki veya üç beklenen kısıt olmalı.")
    if any(case["expected"] for case in cases if case.get("category") == "ambiguous"):
        raise SystemExit("Hata: belirsiz vakaların beklenen kısıt listesi boş olmalı.")
    return cases


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    os.chdir(ROOT)
    _, model = _load_gemini_config()
    cases = _load_cases(args.dataset)
    recorder = RequestRecorder(args.retry_wait, args.max_retries)
    _install_request_recorder(recorder)

    from api.gemini import GeminiTranslator
    from generator import generate_scenario

    args.cache.mkdir(parents=True, exist_ok=True)
    translator_cache = tempfile.TemporaryDirectory(prefix="translator-", dir=args.cache)
    atexit.register(translator_cache.cleanup)
    translator = GeminiTranslator(cache_dir=translator_cache.name)
    scenario = generate_scenario(seed=42)
    evaluations = []
    api_calls_this_run = 0
    cache_hits = 0

    for case in cases:
        cache_path = _case_cache_path(args.cache, case["id"])
        record = _read_cache(cache_path, case, model)
        if record is not None:
            cache_hits += 1
            record["calls_this_run"] = 0
        else:
            recorder.reset()
            try:
                translated = translator.interpret(case["text"], scenario)
                error = None
            except Exception as exc:
                translated = None
                # Store only the exception class. SDK exception text may contain
                # request metadata, and no credential belongs in the eval cache.
                error = type(exc).__name__
            api_calls_this_run += recorder.attempts
            if recorder.attempts and args.request_delay > 0:
                time.sleep(args.request_delay)
            if not recorder.response_received and (error is not None or translated is None):
                raise SystemExit(
                    f"Hata: {case['id']} için Gemini yanıtı alınamadı. Hata türü: {error or 'yanıt yok'}"
                )
            record = {
                "case_id": case["id"],
                "sentence": case["text"],
                "model_id": model,
                "raw_response": recorder.raw_response,
                "response_received": recorder.response_received,
                "translated": translated,
                "error": error,
                "api_call_attempts": recorder.attempts,
                "calls_this_run": recorder.attempts,
            }
            _write_cache(cache_path, record)

        schema_error = bool(record.get("error")) or not isinstance(record.get("translated"), dict)
        if schema_error:
            issues = [{"type": "schema error", "expected": case["expected"], "actual": None}]
            exact_by_type = Counter()
            actual_constraints = None
        else:
            try:
                actual_constraints = record["translated"]["constraints"]["constraints"]
                if not isinstance(actual_constraints, list):
                    raise TypeError("constraints.constraints liste değil")
                issues, exact_by_type = compare_constraints(case["expected"], actual_constraints)
            except (KeyError, TypeError) as exc:
                issues = [{"type": "schema error", "expected": case["expected"], "actual": str(exc)}]
                exact_by_type = Counter()
                actual_constraints = None

        evaluations.append({
            **case,
            "actual_constraints": actual_constraints,
            "issues": issues,
            "correct": not issues,
            "exact_by_type": dict(exact_by_type),
            "raw_response": record.get("raw_response"),
            "error": record.get("error"),
            "api_call_attempts": record.get("api_call_attempts", 0),
            "calls_this_run": record.get("calls_this_run", 0),
        })

    return {
        "model_id": model,
        "evaluations": evaluations,
        "api_calls_this_run": api_calls_this_run,
        "cache_hits": cache_hits,
    }


def _md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_report(result: dict[str, Any]) -> str:
    evaluations = result["evaluations"]
    correct = sum(item["correct"] for item in evaluations)
    total = len(evaluations)
    type_expected: Counter = Counter()
    type_correct: Counter = Counter()
    error_counts: Counter = Counter()
    for item in evaluations:
        for constraint in item["expected"]:
            kind = constraint["type"]
            type_expected[kind] += 1
            type_correct[kind] += item["exact_by_type"].get(kind, 0)
        error_counts.update(issue["type"] for issue in item["issues"])

    lines = [
        "# Gemini talimat değerlendirmesi",
        "",
        f"Model kimliği: `{_md(result['model_id'])}`",
        f"Doğru vaka oranı: **{correct}/{total} ({(correct / total * 100):.1f}%)**",
        f"Plan başına çağrı hedefi: **1** · Bu çalıştırmada yapılan API çağrı denemesi: **{result['api_calls_this_run']}** · Değerlendirme cache eşleşmesi: **{result['cache_hits']}**",
        "",
        "Çağrı sayısı vaka başına kaydedilir; 429 yeniden denemeleri ayrı çağrı denemesi olarak sayılır. Cache'ten okunan yanıt raporunda ilk üretim çağrı sayısı korunur.",
        "",
        "## Kısıt tipine göre",
        "",
        "| Kısıt tipi | Tam eşleşen / beklenen kısıt |",
        "|---|---:|",
    ]
    for kind in ("courier_unavailable_after", "tag_deadline", "max_stops"):
        lines.append(f"| `{kind}` | {type_correct[kind]}/{type_expected[kind]} |")

    lines.extend(["", "## Hata türleri", "", "| Hata türü | Adet |", "|---|---:|"])
    for error_type in ERROR_TYPES:
        lines.append(f"| {error_type} | {error_counts[error_type]} |")

    lines.extend(["", "## Hatalı vakalar ve Gemini yanıtı", ""])
    failures = [item for item in evaluations if item["issues"]]
    if not failures:
        lines.append("Bu çalıştırmada hata bulunmadı.")
    else:
        for item in failures:
            issue_text = "; ".join(
                f"{issue['type']} (beklenen: {issue.get('expected')}; alınan: {issue.get('actual')})"
                for issue in item["issues"]
            )
            raw = item["raw_response"]
            response = html.escape(raw) if raw is not None else "Ham Gemini yanıtı cache kaydında yok."
            lines.extend([
                f"### {item['id']} · {', '.join(issue['type'] for issue in item['issues'])}",
                "",
                f"Cümle: {_md(item['text'])}",
                f"Beklenen: `{_md(json.dumps(item['expected'], ensure_ascii=False))}`",
                f"Hata: {_md(issue_text)}",
                "",
                "<details><summary>Gemini yanıtı</summary><pre>",
                response,
                "</pre></details>",
                "",
            ])

    lines.extend([
        "## Plan başına Gemini çağrı sayısı",
        "",
        "| Vaka | Çağrı denemesi | Bu çalıştırmada | Cache kullanıldı |",
        "|---|---:|---:|---|",
    ])
    for item in evaluations:
        current_calls = item["calls_this_run"]
        cached = "Evet" if current_calls == 0 else "Hayır"
        lines.append(f"| `{item['id']}` | {item['api_call_attempts']} | {current_calls} | {cached} |")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Türkçe kurye talimatlarını Gemini ile değerlendirir.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--request-delay", type=float, default=0.5, help="API çağrıları arasındaki kısa bekleme süresi (saniye).")
    parser.add_argument("--retry-wait", type=float, default=2.0, help="429 yeniden denemelerinin başlangıç beklemesi (saniye).")
    parser.add_argument("--max-retries", type=int, default=4, help="429 için ek deneme sayısı.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.request_delay < 0 or args.retry_wait < 0 or args.max_retries < 0:
        raise SystemExit("Hata: bekleme ve yeniden deneme değerleri negatif olamaz.")
    result = evaluate(args)
    report = render_report(result)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(report)
    print(f"Rapor yazıldı: {args.report}")


if __name__ == "__main__":
    main()
