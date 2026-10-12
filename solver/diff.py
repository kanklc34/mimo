from __future__ import annotations

from models import Plan


def diff_plans(eski: Plan, yeni: Plan) -> list[dict]:
    """Return changed stops and the courier/time/unserved changes for each stop."""
    def locations(plan: Plan):
        result = {}
        for courier_id, visits in plan.routes.items():
            for visit in visits:
                result[visit.stop_id] = (courier_id, visit.arrival_min)
        return result

    old, new = locations(eski), locations(yeni)
    changes = []
    for stop_id in sorted(set(old) | set(new) | set(eski.unserved_stops) | set(yeni.unserved_stops)):
        fields = []
        old_loc, new_loc = old.get(stop_id), new.get(stop_id)
        record = {"stop_id": stop_id, "changes": fields}
        if old_loc and new_loc:
            if old_loc[0] != new_loc[0]:
                fields.append("courier_changed")
                record.update(old_courier_id=old_loc[0], new_courier_id=new_loc[0])
            if old_loc[1] != new_loc[1]:
                fields.append("arrival_changed")
                record.update(old_arrival_min=old_loc[1], new_arrival_min=new_loc[1])
        elif new_loc:
            fields.append("newly_served")
            record.update(new_courier_id=new_loc[0], new_arrival_min=new_loc[1])
        elif stop_id in yeni.unserved_stops and stop_id not in eski.unserved_stops:
            fields.append("newly_unserved")
        elif stop_id in eski.unserved_stops and stop_id in old:
            fields.append("served_to_unserved")
        elif stop_id in old:
            fields.append("removed")
        if fields:
            changes.append(record)
    return changes
