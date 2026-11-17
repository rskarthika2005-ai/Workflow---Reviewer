import argparse
import copy
import json
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "data"))

import oracle
from reviewer.pipeline import load_bundle, review_bundle
from reviewer.model import FakeClient
from reviewer.resolver import parse_requirements, apply_approvals
from reviewer.checks import run_checks

SEED = 7

def load_cases(split="all"):
    with open(ROOT / "data" / "labels" / "labels.json") as f:
        labels = json.load(f)
    cases = {}
    for case_id in sorted(labels):
        if split != "all" and labels[case_id]["split"] != split:
            continue
        with open(ROOT / "data" / "bundles" / (case_id + ".json")) as f:
            cases[case_id] = (json.load(f), labels[case_id])
    return cases


def final_review(raw):
    client = None
    if "model_mode" in raw:
        client = FakeClient(raw["model_mode"])
    return review_bundle(load_bundle(raw), client=client)


def baseline_review(raw):
    bundle = load_bundle(raw)
    reqs = parse_requirements(copy.deepcopy(bundle["requirements"]))
    effective = apply_approvals(reqs, bundle["approvals"])["effective"]
    result = run_checks(effective, bundle["spec_rules"], bundle["nodes"],
                        bundle["snippets"], bundle["start_node"])
    if result["findings"]:
        status = "CHANGES_REQUIRED"
    else:
        status = "PASS"
    return {"status": status, "findings": result["findings"], "model": {"status": "not_run"}}


def ablation_review(raw):
    raw = copy.deepcopy(raw)
    raw["nodes"] = []
    return final_review(raw)


def score_cases(cases, review_fn):
    rows = []
    for case_id, (raw, label) in cases.items():
        start = time.time()
        report = review_fn(raw)
        seconds = time.time() - start

        findings = report["findings"]
        allowed = set(tuple(x) for x in label["allowed"])
        unsupported = 0
        for f in findings:
            if (f["artifact"], f["kind"]) not in allowed:
                unsupported += 1

        found_primary = False
        primary = label["primary"]
        if primary:
            for f in findings:
                if f["artifact"] == primary["artifact"] and f["kind"] == primary["kind"] \
                        and f["location"] == primary["location"]:
                    found_primary = True

        cex_total = 0
        cex_valid = 0
        if label["true_threshold"] is not None:
            for f in findings:
                if "counterexample" in f:
                    cex_total += 1
                    right = oracle.correct_route(f["counterexample"], label["true_threshold"])
                    if f["expected_route"] == right and f["actual_route"] != right:
                        cex_valid += 1

        model = report.get("model", {})
        attempts = model.get("provenance", {}).get("attempts", 0)

        rows.append({
            "case": case_id, "split": label["split"], "type": label["type"],
            "expected": label["status"], "actual": report["status"],
            "correct": report["status"] == label["status"],
            "found_primary": found_primary,
            "unsupported_findings": unsupported,
            "cex_total": cex_total, "cex_valid": cex_valid,
            "model_calls": attempts,
            "model_retries": max(attempts - 1, 0),
            "seconds": round(seconds, 4),
        })
    return rows


def summarize(rows):
    def count(kind):
        return [r for r in rows if r["type"] == kind]

    valid, defect, incomplete = count("valid"), count("defect"), count("incomplete")
    return {
        "cases": len(rows),
        "exact_match": str(len([r for r in rows if r["correct"]])) + "/" + str(len(rows)),
        "false_pass_on_defects": str(len([r for r in defect if r["actual"] == "PASS"])) + "/" + str(len(defect)),
        "false_pass_on_incomplete": str(len([r for r in incomplete if r["actual"] == "PASS"])) + "/" + str(len(incomplete)),
        "false_block_on_valid": str(len([r for r in valid if r["actual"] == "CHANGES_REQUIRED"])) + "/" + str(len(valid)),
        "abstained_on_valid_or_defect": str(len([r for r in valid + defect if r["actual"] == "INCOMPLETE"])) + "/" + str(len(valid + defect)),
        "incomplete_correct": str(len([r for r in incomplete if r["actual"] == "INCOMPLETE"])) + "/" + str(len(incomplete)),
        "defect_found_with_location": str(len([r for r in defect if r["found_primary"]])) + "/" + str(len(defect)),
        "counterexamples_valid": str(sum(r["cex_valid"] for r in rows)) + "/" + str(sum(r["cex_total"] for r in rows)),
        "unsupported_findings": sum(r["unsupported_findings"] for r in rows),
        "runtime_seconds": round(sum(r["seconds"] for r in rows), 3),
        "model_calls_fake_client": sum(r["model_calls"] for r in rows),
        "model_retries_fake_client": sum(r["model_retries"] for r in rows),
    }


def rename_ids(raw):
    new = copy.deepcopy(raw)
    req_map = {}
    for i, r in enumerate(new["requirements"]):
        req_map[r["req_id"]] = "Q" + str(i + 1)
        r["req_id"] = req_map[r["req_id"]]
    for i, s in enumerate(new["spec_rules"]):
        s["rule_id"] = "T" + str(i + 1)
        s["ref_id"] = req_map.get(s["ref_id"], s["ref_id"])
    node_map = {}
    for i, n in enumerate(new["nodes"]):
        node_map[n["node_id"]] = "m" + str(i + 1)
    for n in new["nodes"]:
        n["node_id"] = node_map[n["node_id"]]
        n["if_true"] = node_map.get(n["if_true"], n["if_true"])
        n["if_false"] = node_map.get(n["if_false"], n["if_false"])
    for a in new["approvals"]:
        a["req_id"] = req_map.get(a["req_id"], a["req_id"])
    new["start_node"] = node_map.get(new["start_node"], new["start_node"])
    return new


def reorder_records(raw, rng):
    new = copy.deepcopy(raw)
    for key in ("requirements", "spec_rules", "nodes", "approvals"):
        rng.shuffle(new[key])
    return new


def paraphrase(raw):
    new = copy.deepcopy(raw)
    for group in ("spec_rules", "nodes"):
        for item in new[group]:
            item["condition_text"] = item["condition_text"].replace("waiting >= ", "waiting at least ")
    return new


def change_behavior(raw):
    new = copy.deepcopy(raw)
    for item in new["spec_rules"]:
        match = re.search(r"waiting >= (\d+) minutes", item["condition_text"])
        if match:
            old = match.group(1)
            item["condition_text"] = item["condition_text"].replace(old, str(int(old) + 1))
    return new


def run_variants(cases):
    rng = random.Random(SEED)
    same_total = same_ok = change_total = change_ok = 0
    details = []

    for case_id, (raw, label) in cases.items():
        if label["type"] == "incomplete":
            continue
        for name, make in (("rename_ids", rename_ids),
                           ("reorder", lambda r: reorder_records(r, rng)),
                           ("paraphrase", paraphrase)):
            report = final_review(make(raw))
            ok = report["status"] == label["status"]
            same_total += 1
            same_ok += ok
            details.append({"case": case_id, "variant": name, "status": report["status"], "ok": ok})

        if label["type"] == "valid" and case_id != "v3_unusual_formulation":
            report = final_review(change_behavior(raw))
            ok = report["status"] == "CHANGES_REQUIRED"
            change_total += 1
            change_ok += ok
            details.append({"case": case_id, "variant": "change_behavior", "status": report["status"], "ok": ok})

    return {
        "behavior_preserving_unchanged": str(same_ok) + "/" + str(same_total),
        "behavior_changing_detected": str(change_ok) + "/" + str(change_total),
        "details": details,
    }


def print_summary(title, summary):
    print("\n" + title)
    for key, value in summary.items():
        print("  " + key + ": " + str(value))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["all", "dev", "heldout"], default="all")
    args = parser.parse_args()

    cases = load_cases(args.split)
    final_rows = score_cases(cases, final_review)
    base_rows = score_cases(cases, baseline_review)
    ablation_rows = score_cases(cases, ablation_review)

    report = {
        "split": args.split,
        "seed": SEED,
        "note": "model results use the fake client only; real model performance: not measured",
        "baseline": summarize(base_rows),
        "final": summarize(final_rows),
        "ablation_workflow_check_off": summarize(ablation_rows),
        "ablation_changed_cases": [
            {"case": a["case"], "final": f["actual"], "ablation": a["actual"]}
            for f, a in zip(final_rows, ablation_rows) if f["actual"] != a["actual"]],
        "variants": run_variants(cases),
        "per_case_final": final_rows,
        "per_case_baseline": base_rows,
    }

    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    with open(out_dir / ("eval_report_" + args.split + ".json"), "w") as f:
        json.dump(report, f, indent=2)

    print_summary("BASELINE (steps 1-2 only)", report["baseline"])
    print_summary("FINAL", report["final"])
    print_summary("ABLATION (workflow check off)", report["ablation_workflow_check_off"])
    print("\nCases changed by the ablation:", report["ablation_changed_cases"])
    print("\nVARIANTS:", report["variants"]["behavior_preserving_unchanged"],
          "unchanged;", report["variants"]["behavior_changing_detected"], "changes detected")
    print("\nCases the final reviewer got wrong:",
          [r["case"] for r in final_rows if not r["correct"]])
    print("Real-model results: not measured (fake client only).")


if __name__ == "__main__":
    main()