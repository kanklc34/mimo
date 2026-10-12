from __future__ import annotations

from collections import Counter

from models import Plan, Violation


def summarize(violations: list[Violation], plan: Plan) -> dict:
    """Summarize validation violations and stops explicitly left unserved."""
    counts = Counter(violation.type for violation in violations)
    return {
        "ihlal_sayisi": len(violations),
        "ihlaller_tipe_gore": dict(counts),
        "atlanan_duraklar": list(plan.unserved_stops),
    }
