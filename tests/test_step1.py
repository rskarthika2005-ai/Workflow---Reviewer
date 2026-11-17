from reviewer.schemas import Requirement, Approval
from reviewer.conditions import parse_text, validate_condition
from reviewer.resolver import parse_requirements, apply_approvals


def make_requirements():
    reqs = [
        Requirement("R1", "category is missing", "manual_review", 1, location="req#R1"),
        Requirement("R2", "ticket is urgent", "priority_queue", 2, location="req#R2"),
        Requirement("R3", "waiting >= 30 minutes", "escalation", 3, location="req#R3"),
    ]
    return parse_requirements(reqs)


def get_threshold(result, req_id):
    for req in result["effective"]:
        if req.req_id == req_id:
            return req.condition["value"]


def test_parser_builds_valid_conditions():
    cond = parse_text("waiting at least 1 hours")
    assert cond["value"] == 60          
    assert validate_condition(cond) == []


def test_unsupported_text_stays_visible():
    reqs = [Requirement("R9", "customer feels sad", "normal_queue", 9)]
    parse_requirements(reqs)
    result = apply_approvals(reqs, [])
    assert result["coverage"][0]["status"] == "unsupported"


def test_approved_change_is_applied():
    ap = Approval("A1", "R3", "waiting", 25, status="approved")
    result = apply_approvals(make_requirements(), [ap])
    assert get_threshold(result, "R3") == 25


def test_unapproved_and_rejected_are_ignored():
    aps = [Approval("A1", "R3", "waiting", 25, status="proposed"),
           Approval("A2", "R3", "waiting", 20, status="rejected")]
    result = apply_approvals(make_requirements(), aps)
    assert get_threshold(result, "R3") == 30
    assert len(result["ignored"]) == 2


def test_conflicting_approvals_are_flagged():
    aps = [Approval("A1", "R3", "waiting", 25, status="approved"), Approval("A2", "R3", "waiting", 20, status="approved")]
    result = apply_approvals(make_requirements(), aps)
    assert len(result["conflicts"]) == 1
    assert get_threshold(result, "R3") == 30   


def test_later_change_order_wins():
    aps = [Approval("A1", "R3", "waiting", 25, status="approved", change_order=1), Approval("A2", "R3", "waiting", 20, status="approved", change_order=2)]
    result = apply_approvals(make_requirements(), aps)
    assert get_threshold(result, "R3") == 20
    assert result["conflicts"] == []


def test_wrong_revision_is_ignored():
    ap = Approval("A1", "R3", "waiting", 25, status="approved", applies_to_version="v0")
    result = apply_approvals(make_requirements(), [ap])
    assert get_threshold(result, "R3") == 30