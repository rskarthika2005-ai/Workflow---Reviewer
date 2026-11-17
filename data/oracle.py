CATEGORIES = [None, "billing", "other"]
URGENT_VALUES = [True, False, None]


def correct_route(ticket, threshold=30):
    if ticket["category"] is None:
        return "manual_review"
    if ticket["urgent"] is True:
        return "priority_queue"
    if ticket["waiting"] is not None and ticket["waiting"] >= threshold:
        return "escalation"
    return "normal_queue"


def ticket_grid(threshold):
    tickets = []
    for category in CATEGORIES:
        for urgent in URGENT_VALUES:
            for waiting in [0, threshold - 1, threshold, threshold + 1, None]:
                tickets.append({"category": category, "urgent": urgent, "waiting": waiting})
    return tickets


def code_differences(code, threshold):
    scope = {}
    exec(code, scope)
    route = scope["route"]
    different = []
    for ticket in ticket_grid(threshold):
        got = route(ticket["category"], ticket["urgent"], ticket["waiting"])
        if got != correct_route(ticket, threshold):
            different.append(ticket)
    return different