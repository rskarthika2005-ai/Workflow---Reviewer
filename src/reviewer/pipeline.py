import copy
import dataclasses
import hashlib
import json

from reviewer.schemas import Requirement, SpecRule, WorkflowNode, Snippet, Approval
from reviewer.conditions import parse_text
from reviewer.resolver import parse_requirements, apply_approvals
from reviewer.checks import run_checks
from reviewer.model import call_model

DEFAULT_CONFIG = {
    "max_retries": 2,
    "max_code_chars": 5000,
    "max_rules": 50,
}


def load_bundle(raw):
    requirements = [Requirement(**r) for r in raw["requirements"]]

    spec_rules = []
    for item in raw["spec_rules"]:
        item = dict(item)
        text = item.pop("condition_text", None)
        if text is not None:
            item["condition"] = parse_text(text)
        spec_rules.append(SpecRule(**item))

    nodes = []
    for item in raw["nodes"]:
        item = dict(item)
        text = item.pop("condition_text", None)
        if text is not None:
            item["condition"] = parse_text(text)
        nodes.append(WorkflowNode(**item))

    return {
        "requirements": requirements,
        "spec_rules": spec_rules,
        "nodes": nodes,
        "snippets": [Snippet(**s) for s in raw["snippets"]],
        "approvals": [Approval(**a) for a in raw["approvals"]],
        "start_node": raw["start_node"],
    }


def make_cache_key(bundle, config, client):
    parts = {
        "requirements": [dataclasses.asdict(x) for x in bundle["requirements"]],
        "spec_rules": [dataclasses.asdict(x) for x in bundle["spec_rules"]],
        "nodes": [dataclasses.asdict(x) for x in bundle["nodes"]],
        "snippets": [dataclasses.asdict(x) for x in bundle["snippets"]],
        "approvals": [dataclasses.asdict(x) for x in bundle["approvals"]],
        "start_node": bundle["start_node"],
        "config": config,
        "client": getattr(client, "name", None),
    }
    text = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(text.encode()).hexdigest()


def check_input_size(bundle, config):
    problems = []
    rule_count = len(bundle["requirements"]) + len(bundle["spec_rules"]) + len(bundle["nodes"])
    if rule_count > config["max_rules"]:
        problems.append("input too large: " + str(rule_count) + " rules, limit "
                        + str(config["max_rules"]))
    for snippet in bundle["snippets"]:
        if len(snippet.code) > config["max_code_chars"]:
            problems.append("input too large: snippet " + snippet.snippet_id)
    return problems


def compute_status(findings, check_results, unreviewed):
    for finding in findings:
        if finding["severity"] == "blocker":
            return "CHANGES_REQUIRED"
    if unreviewed:
        return "INCOMPLETE"
    for check in check_results:
        if check["status"] == "failed":
            return "INCOMPLETE"
    return "PASS"


def collect_unreviewed(effective, conflicts, bundle):
    unreviewed = []
    for req in effective:
        if not req.supported:
            unreviewed.append("requirement " + req.req_id + " has unsupported text")
    for conflict in conflicts:
        unreviewed.append("approval conflict on " + conflict["req_id"]
                          + "." + conflict["field"])
    for rule in bundle["spec_rules"]:
        if rule.condition is None:
            unreviewed.append("spec rule " + rule.rule_id + " has unsupported condition")
    for node in bundle["nodes"]:
        if node.condition is None:
            unreviewed.append("workflow node " + node.node_id + " has unsupported condition")
    return unreviewed


def known_locations_of(bundle):
    locations = set()
    for group in ("requirements", "spec_rules", "nodes", "snippets", "approvals"):
        for item in bundle[group]:
            locations.add(item.location)
    return locations


def find_rule_ref(finding, requirements):
    for req in requirements:
        if req.location == finding.get("expected_location"):
            return req.req_id
    for route_key in ("expected_route", "actual_route"):
        for req in requirements:
            if req.route == finding.get(route_key):
                return req.req_id
    return None


def make_summary(status, findings, unreviewed):
    blockers = len([f for f in findings if f["severity"] == "blocker"])
    return (status + ": " + str(blockers) + " blocker(s), "
            + str(len(unreviewed)) + " item(s) not fully reviewed.")


def review_bundle(bundle, client=None, config=None, cache=None):
    settings = dict(DEFAULT_CONFIG)
    if config:
        settings.update(config)

    key = make_cache_key(bundle, settings, client)
    if cache is not None and key in cache:
        report = copy.deepcopy(cache[key])
        report["cache_hit"] = True
        return report

    problems = check_input_size(bundle, settings)
    if problems:
        report = {
            "status": "INCOMPLETE",
            "summary": make_summary("INCOMPLETE", [], problems),
            "findings": [],
            "coverage": [],
            "checks": [],
            "unreviewed": problems,
            "model": {"status": "not_run"},
            "cache_key": key,
            "cache_hit": False,
        }
        if cache is not None:
            cache[key] = copy.deepcopy(report)
        return report


    requirements = parse_requirements(copy.deepcopy(bundle["requirements"]))
    resolved = apply_approvals(requirements, bundle["approvals"])
    effective = resolved["effective"]

  
    result = run_checks(effective, bundle["spec_rules"], bundle["nodes"],
                        bundle["snippets"], bundle["start_node"])
    findings = result["findings"]
    check_results = list(result["check_results"])

   
    for finding in findings:
        if "rule_ref" not in finding:
            finding["rule_ref"] = find_rule_ref(finding, effective)

    unreviewed = collect_unreviewed(effective, resolved["conflicts"], bundle)

    
    model_info = {"status": "not_run"}
    if client is not None:
        rule_ids = set(req.req_id for req in effective)
        model_info = call_model(client, findings, rule_ids,
                                known_locations_of(bundle), settings["max_retries"])
        check_results.append({"name": "model", "status": model_info["status"],
                              "reason": model_info["error"]})
        if model_info["status"] == "ok":
            for note in model_info["notes"]:
                for finding in findings:
                    if finding.get("rule_ref") == note["rule_ref"]:
                        finding.setdefault("model_notes", []).append(note["text"])

    status = compute_status(findings, check_results, unreviewed)

    report = {
        "status": status,
        "summary": make_summary(status, findings, unreviewed),
        "findings": findings,
        "coverage": resolved["coverage"],
        "checks": check_results,
        "unreviewed": unreviewed,
        "approvals": {"applied": resolved["applied"],
                      "ignored": resolved["ignored"],
                      "conflicts": resolved["conflicts"]},
        "model": model_info,
        "cache_key": key,
        "cache_hit": False,
    }

    if cache is not None and model_info["status"] != "failed":
        cache[key] = copy.deepcopy(report)
    return report