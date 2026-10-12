from __future__ import annotations

from models import Plan


def diff_plans(eski: Plan, yeni: Plan) -> list[dict]:
    """Return changed stops and the courier/time/unserved changes for each stop."""
    def locations(plan: Plan):
        result = {}
        for courier_id, visits in plan.routes.items():
            for index, visit in enumerate(visits):
                result[visit.stop_id] = (courier_id, index, visit.arrival_min)
        return result

    old, new = locations(eski), locations(yeni)
    old_common_order = {}
    new_common_order = {}
    shared_by_courier = {
        courier_id: {
            stop_id for stop_id, loc in old.items()
            if loc[0] == courier_id and stop_id in new and new[stop_id][0] == courier_id
        }
        for courier_id in set(eski.routes) | set(yeni.routes)
    }
    for courier_id, shared in shared_by_courier.items():
        old_common_order.update({stop_id: rank for rank, stop_id in enumerate(
            visit.stop_id for visit in eski.routes.get(courier_id, []) if visit.stop_id in shared
        )})
        new_common_order.update({stop_id: rank for rank, stop_id in enumerate(
            visit.stop_id for visit in yeni.routes.get(courier_id, []) if visit.stop_id in shared
        )})
    changes = []
    for stop_id in sorted(set(old) | set(new) | set(eski.unserved_stops) | set(yeni.unserved_stops)):
        fields = []
        old_loc, new_loc = old.get(stop_id), new.get(stop_id)
        record = {"stop_id": stop_id, "changes": fields}
        if old_loc and new_loc:
            if old_loc[0] != new_loc[0]:
                fields.append("courier_changed")
                record.update(old_courier_id=old_loc[0], new_courier_id=new_loc[0])
                record["type"] = "kurye_degisti"
            elif old_common_order.get(stop_id) != new_common_order.get(stop_id):
                fields.append("order_changed")
                record["type"] = "sira_degisti"
            if old_loc[2] != new_loc[2]:
                fields.append("arrival_changed")
                record.update(old_arrival_min=old_loc[2], new_arrival_min=new_loc[2])
                record.setdefault("type", "sadece_saat_kaydi")
        elif new_loc:
            fields.append("newly_served")
            record["type"] = "sira_degisti"
            record.update(new_courier_id=new_loc[0], new_arrival_min=new_loc[2])
        elif stop_id in yeni.unserved_stops and stop_id not in eski.unserved_stops:
            fields.append("newly_unserved")
            record["type"] = "yeni_atlandi"
        elif stop_id in eski.unserved_stops and stop_id in old:
            fields.append("served_to_unserved")
            record["type"] = "yeni_atlandi"
        elif stop_id in old:
            fields.append("removed")
            record["type"] = "yeni_atlandi"
        if fields:
            changes.append(record)
    return changes
