from models import Plan, Violation
from validator.report import summarize


def test_summarize_counts_violations_and_lists_unserved_stops():
    violations = [
        Violation(type="outside_shift", courier_id="c1", description="outside shift"),
        Violation(type="outside_shift", courier_id="c2", description="outside shift"),
        Violation(type="window_violation", stop_id="s1", description="late"),
    ]
    plan = Plan(routes={}, unserved_stops=["s2", "s3"])

    assert summarize(violations, plan) == {
        "ihlal_sayisi": 3,
        "ihlaller_tipe_gore": {"outside_shift": 2, "window_violation": 1},
        "atlanan_duraklar": ["s2", "s3"],
    }
