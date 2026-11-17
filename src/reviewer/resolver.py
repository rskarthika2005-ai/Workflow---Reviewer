import copy

from reviewer.conditions import parse_text, to_minutes


def parse_requirements(requirements):
    for req in requirements:
        cond = parse_text(req.text)
        req.condition = cond
        req.supported = cond is not None
    return requirements


def build_coverage(requirements):
    coverage = []
    for req in requirements:
        if req.supported:
            status = "supported"
        else:
            status = "unsupported"
        coverage.append({
            "req_id": req.req_id,
            "status": status,
            "version": req.version,
            "location": req.location,
        })
    return coverage


def set_threshold(cond, field, new_value):
    count = 0
    if cond["op"] in ("and", "or"):
        for item in cond["items"]:
            count += set_threshold(item, field, new_value)
    elif cond["op"] == "compare" and cond["field"] == field:
        cond["value"] = new_value
        count = 1
    return count


def check_approval(approval, requirement):
    if requirement is None:
        return False, "unknown requirement"
    if approval.status != "approved":
        return False, "status is " + approval.status
    if approval.applies_to_version != requirement.version:
        return False, "different revision"
    if not requirement.supported:
        return False, "requirement is unsupported"
    return True, ""


def apply_approvals(requirements, approvals):
    by_id = {}
    for req in requirements:
        by_id[req.req_id] = req

    effective = copy.deepcopy(requirements) 
    effective_by_id = {}
    for req in effective:
        effective_by_id[req.req_id] = req

    applied = []
    ignored = []
    conflicts = []

    groups = {}
    for ap in approvals:
        ok, reason = check_approval(ap, by_id.get(ap.req_id))
        if not ok:
            ignored.append({"approval_id": ap.approval_id, "reason": reason})
            continue
        key = (ap.req_id, ap.field)
        groups.setdefault(key, []).append(ap)

   
    for key, group in groups.items():
        latest_order = max(ap.change_order for ap in group)
        latest = [ap for ap in group if ap.change_order == latest_order]


        for ap in group:
            if ap.change_order < latest_order:
                ignored.append({"approval_id": ap.approval_id, "reason": "superseded"})

       
        values = set(to_minutes(ap.new_value, ap.unit) for ap in latest)
        if len(values) > 1:
            conflicts.append({
                "req_id": key[0],
                "field": key[1],
                "approval_ids": [ap.approval_id for ap in latest],
                "values": sorted(values),
            })
            continue

    
        ap = latest[0]
        target = effective_by_id[ap.req_id]
        new_value = to_minutes(ap.new_value, ap.unit)
        changed = set_threshold(target.condition, ap.field, new_value)
        if changed == 0:
            ignored.append({"approval_id": ap.approval_id,
                            "reason": "no matching field in requirement"})
            continue
        applied.append({
            "approval_id": ap.approval_id,
            "req_id": ap.req_id,
            "new_value": new_value,
            "location": ap.location,
        })

    return {
        "effective": effective,
        "applied": applied,
        "ignored": ignored,
        "conflicts": conflicts,
        "coverage": build_coverage(effective),
    }