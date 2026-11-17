import re

COMPARE_SIGNS = [">=", ">", "<=", "<"]

TIME_UNITS = {
    "second": 1 / 60, "seconds": 1 / 60,
    "minute": 1, "minutes": 1, "min": 1, "mins": 1,
    "hour": 60, "hours": 60,
    "day": 1440, "days": 1440,
}

WORD_TO_SIGN = {
    "at least": ">=",
    "more than": ">",
    "at most": "<=",
    "less than": "<",
}


def to_minutes(value, unit):
    if unit not in TIME_UNITS:
        raise ValueError("unknown time unit: " + str(unit))
    return value * TIME_UNITS[unit]


def validate_condition(cond):
    errors = []
    if not isinstance(cond, dict):
        return ["condition must be a dict"]

    op = cond.get("op")

    if op in ("and", "or"):
        items = cond.get("items")
        if not isinstance(items, list) or len(items) == 0:
            errors.append(op + " needs a non-empty items list")
        else:
            for item in items:
                errors.extend(validate_condition(item))

    elif op == "compare":
        if "field" not in cond:
            errors.append("compare needs a field")
        if cond.get("cmp") not in COMPARE_SIGNS:
            errors.append("compare sign must be one of " + str(COMPARE_SIGNS))
        if not isinstance(cond.get("value"), (int, float)):
            errors.append("compare value must be a number")
        if "unit" in cond and cond["unit"] not in TIME_UNITS:
            errors.append("unknown unit: " + str(cond["unit"]))

    elif op == "equals":
        if "field" not in cond or "value" not in cond:
            errors.append("equals needs field and value")

    elif op == "missing":
        if "field" not in cond:
            errors.append("missing needs a field")

    else:
        errors.append("unknown op: " + str(op))

    return errors


def normalize_condition(cond):
    new = dict(cond)
    if cond["op"] in ("and", "or"):
        new["items"] = [normalize_condition(i) for i in cond["items"]]
    elif cond["op"] == "compare" and "unit" in cond:
        new["value"] = to_minutes(cond["value"], cond["unit"])
        new["unit"] = "minutes"
    return new


def parse_single(text):
    text = text.strip().lower().rstrip(".")

    m = re.match(r"^(\w+) is missing$", text)
    if m:
        return {"op": "missing", "field": m.group(1)}

   
    m = re.match(r"^(\w+)\s*(>=|>|<=|<)\s*(\d+(?:\.\d+)?)\s*(\w+)?$", text)
    if m:
        return make_compare(m.group(1), m.group(2), m.group(3), m.group(4))


    m = re.match(
        r"^(\w+) (?:time )?(?:is )?(at least|more than|at most|less than) "
        r"(\d+(?:\.\d+)?) (\w+)$", text)
    if m:
        return make_compare(m.group(1), WORD_TO_SIGN[m.group(2)], m.group(3), m.group(4))

   
    m = re.match(r"^ticket is (\w+)$", text)
    if m:
        return {"op": "equals", "field": m.group(1), "value": True}

    
    m = re.match(r"^(\w+) is (\w+)$", text)
    if m:
        return {"op": "equals", "field": m.group(1), "value": m.group(2)}

    return None  


def make_compare(field, sign, number, unit):
    value = float(number)
    if value == int(value):
        value = int(value)

    cond = {"op": "compare", "field": field, "cmp": sign, "value": value}
    if unit is not None:
        if unit not in TIME_UNITS:
            return None  
        cond["value"] = to_minutes(value, unit)
        cond["unit"] = "minutes"
    return cond


def parse_text(text):
    or_parts = re.split(r"\s+or\s+", text.strip().lower())
    or_items = []

    for part in or_parts:
        and_parts = re.split(r"\s+and\s+", part)
        and_items = []
        for piece in and_parts:
            cond = parse_single(piece)
            if cond is None:
                return None
            and_items.append(cond)
        if len(and_items) == 1:
            or_items.append(and_items[0])
        else:
            or_items.append({"op": "and", "items": and_items})

    if len(or_items) == 1:
        return or_items[0]
    return {"op": "or", "items": or_items}