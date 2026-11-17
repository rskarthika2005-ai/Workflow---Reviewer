from reviewer.schemas import Requirement, SpecRule, WorkflowNode, Snippet
from reviewer.conditions import parse_text
from reviewer.resolver import parse_requirements
from reviewer.checks import run_checks

GOOD_CODE = '''
def route(category, urgent, waiting):
    if category is None:
        return "manual_review"
    if urgent is True:
        return "priority_queue"
    if waiting is not None and waiting >= 30:
        return "escalation"
    return "normal_queue"
'''


def make_requirements():
    reqs = [
        Requirement("R1", "category is missing", "manual_review", 1, location="req#R1"),
        Requirement("R2", "ticket is urgent", "priority_queue", 2, location="req#R2"),
        Requirement("R3", "waiting >= 30 minutes", "escalation", 3, location="req#R3"),
    ]
    return parse_requirements(reqs)


def make_spec(r3_text="waiting >= 30 minutes", orders=(1, 2, 3)):
    return [
        SpecRule("S1", "R1", parse_text("category is missing"), "manual_review", orders[0], location="spec#S1"),
        SpecRule("S2", "R2", parse_text("ticket is urgent"), "priority_queue", orders[1], location="spec#S2"),
        SpecRule("S3", "R3", parse_text(r3_text), "escalation", orders[2], location="spec#S3"),
    ]


def make_nodes(false_of_n3="normal_queue"):
    return [
        WorkflowNode("n1", parse_text("category is missing"), "manual_review", "n2", location="wf#n1"),
        WorkflowNode("n2", parse_text("ticket is urgent"), "priority_queue", "n3", location="wf#n2"),
        WorkflowNode("n3", parse_text("waiting >= 30 minutes"), "escalation", false_of_n3, location="wf#n3"),
    ]


def make_snippets(code=GOOD_CODE):
    return [Snippet("c1", "n1", code, location="code#route")]


def run(spec=None, nodes=None, snippets=None):
    return run_checks(make_requirements(),
                      spec or make_spec(),
                      nodes or make_nodes(),
                      snippets or make_snippets(),
                      "n1")


def test_all_correct_gives_no_findings():
    report = run()
    assert report["findings"] == []
    assert report["tickets_checked"] > 0


def test_wrong_threshold_gives_counterexample():
    report = run(spec=make_spec(r3_text="waiting >= 25 minutes"))
    finding = report["findings"][0]
    assert finding["artifact"] == "spec"
    assert 25 <= finding["counterexample"]["waiting"] < 30
    assert finding["expected_route"] == "normal_queue"
    assert finding["actual_route"] == "escalation"


def test_wrong_precedence_gives_counterexample():
    # R3 checked before R2
    report = run(spec=make_spec(orders=(1, 3, 2)))
    finding = report["findings"][0]
    assert finding["counterexample"]["urgent"] is True
    assert finding["counterexample"]["waiting"] >= 30
    assert finding["expected_route"] == "priority_queue"
    assert finding["actual_route"] == "escalation"


def test_missing_branch_is_found():
    report = run(nodes=make_nodes(false_of_n3=""))
    finding = report["findings"][0]
    assert finding["kind"] == "missing_branch"
    assert finding["artifact"] == "workflow"


def test_code_mismatch_is_found():
    bad = GOOD_CODE.replace("waiting >= 30", "waiting > 30")
    report = run(snippets=make_snippets(bad))
    finding = report["findings"][0]
    assert finding["artifact"] == "code:c1"
    assert finding["counterexample"]["waiting"] == 30


def test_equivalent_code_is_valid():
    other = GOOD_CODE.replace("waiting is not None and waiting >= 30",
                              "not (waiting < 30) and waiting >= 30")
    report = run(snippets=make_snippets(other))
    assert report["findings"] == []


def test_unsupported_code_is_not_executed():
    evil = "import os\ndef route(category, urgent, waiting):\n    return 'normal_queue'\n"
    report = run(snippets=make_snippets(evil))
    code_result = report["check_results"][-1]
    assert code_result["status"] == "failed"


def test_omitted_requirement_is_found():
    spec = make_spec()[:2]             
    report = run(spec=spec)
    kinds = [f["kind"] for f in report["findings"]]
    assert "omitted_requirement" in kinds