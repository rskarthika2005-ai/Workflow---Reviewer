import ast

from reviewer.evaluators import (
    CodeError,
    route_from_rules,
    route_from_workflow,
    route_from_code,
)

CATEGORIES = [None, "billing", "other"]
URGENT_VALUES = [True, False, None]


def collect_condition_numbers(cond, numbers):
    if cond is None:
        return
    if cond["op"] in ("and", "or"):
        for item in cond["items"]:
            collect_condition_numbers(item, numbers)
    elif cond["op"] == "compare":
        numbers.add(cond["value"])


def collect_code_numbers(code, numbers):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                numbers.add(node.value)


def make_ticket_set(numbers):
    waiting_values = {0}
    for n in numbers:
        waiting_values.update([n - 1, n, n + 1])
    waiting_list = sorted(waiting_values) + [None]

    tickets = []
    for category in CATEGORIES:
        for urgent in URGENT_VALUES:
            for waiting in waiting_list:
                tickets.append({"category": category,
                                "urgent": urgent,
                                "waiting": waiting})
    return tickets


def find_omitted_requirements(requirements, spec_rules):
    referenced = set(rule.ref_id for rule in spec_rules)
    findings = []
    for req in requirements:
        if req.req_id not in referenced:
            findings.append({
                "severity": "blocker",
                "kind": "omitted_requirement",
                "rule_ref": req.req_id,
                "artifact": "requirements",
                "version": req.version,
                "location": req.location,
                "evidence": "no spec rule refers to " + req.req_id,
                "correction": "add a spec rule for " + req.req_id,
            })
    return findings


def first_version(items):
    if items:
        return items[0].version
    return ""


def compare_artifact(name, version, tickets, expected_fn, actual_fn):
    mismatches = []
    for ticket in tickets:
        expected, expected_where = expected_fn(ticket)
        try:
            actual, actual_where = actual_fn(ticket)
        except CodeError as err:
            result = {"name": name, "status": "failed",
                      "reason": str(err), "tickets_checked": 0}
            return result, []
        if actual != expected:
            mismatches.append({
                "ticket": ticket,
                "expected_route": expected,
                "actual_route": actual,
                "expected_location": expected_where,
                "actual_location": actual_where,
            })

    result = {"name": name,
              "status": "ok" if not mismatches else "mismatch",
              "tickets_checked": len(tickets),
              "mismatch_count": len(mismatches)}
    findings = []
    if mismatches:
        first = mismatches[0]
        if first["actual_route"] == "missing_branch":
            kind = "missing_branch"
        else:
            kind = "route_mismatch"
        findings.append({
            "severity": "blocker",
            "kind": kind,
            "artifact": name,
            "version": version,
            "location": first["actual_location"],
            "counterexample": first["ticket"],
            "expected_route": first["expected_route"],
            "actual_route": first["actual_route"],
            "expected_location": first["expected_location"],
            "mismatch_count": len(mismatches),
            "evidence": name + " routes this ticket to " + str(first["actual_route"])
                        + " but the requirements say " + str(first["expected_route"]),
            "correction": "make " + name + " follow the requirements at "
                          + str(first["expected_location"]),
        })
    return result, findings


def run_checks(requirements, spec_rules, nodes, snippets, start_node):
    usable = [r for r in requirements if r.supported]
    unreviewed = [r.req_id for r in requirements if not r.supported]
    numbers = set()
    for item in list(usable) + list(spec_rules) + list(nodes):
        collect_condition_numbers(item.condition, numbers)
    for snippet in snippets:
        collect_code_numbers(snippet.code, numbers)
    tickets = make_ticket_set(numbers)

    def expected_fn(ticket):
        return route_from_rules(usable, ticket)

    check_results = []
    findings = find_omitted_requirements(usable, spec_rules)

    result, found = compare_artifact(
        "spec", first_version(spec_rules), tickets, expected_fn,
        lambda t: route_from_rules(spec_rules, t))
    check_results.append(result)
    findings += found

    if nodes:
        result, found = compare_artifact(
            "workflow", first_version(nodes), tickets, expected_fn,
            lambda t: route_from_workflow(nodes, t, start_node))
        check_results.append(result)
        findings += found

    for snippet in snippets:
        result, found = compare_artifact(
            "code:" + snippet.snippet_id, snippet.version, tickets, expected_fn,
            lambda t, s=snippet: route_from_code(s.code, t, s.location))
        check_results.append(result)
        findings += found

    return {
        "tickets_checked": len(tickets),
        "check_results": check_results,
        "findings": findings,
        "unreviewed_requirements": unreviewed,
    }