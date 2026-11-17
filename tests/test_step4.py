import copy
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for folder in ("src", "data", "eval"):
    if str(ROOT / folder) not in sys.path:
        sys.path.insert(0, str(ROOT / folder))

import run_eval
from reviewer.pipeline import load_bundle, review_bundle

ALL = run_eval.load_cases("all")
NOT_INCOMPLETE = {k: v for k, v in ALL.items() if v[1]["type"] != "incomplete"}
INCOMPLETE = {k: v for k, v in ALL.items() if v[1]["type"] == "incomplete"}


# ---------- decisions match the hand-made labels ----------

def test_every_case_matches_its_label():
    for case_id, (raw, label) in ALL.items():
        assert run_eval.final_review(raw)["status"] == label["status"], case_id


def test_dataset_has_required_counts():
    types = [label["type"] for _, label in ALL.values()]
    assert types.count("valid") >= 3
    assert types.count("defect") >= 6
    assert types.count("incomplete") >= 3
    assert len(ALL) >= 12


def test_at_least_four_heldout_cases():
    heldout = [c for c, (_, label) in ALL.items() if label["split"] == "heldout"]
    assert len(heldout) >= 4


def test_renaming_ids_does_not_change_status():
    for case_id, (raw, label) in NOT_INCOMPLETE.items():
        report = run_eval.final_review(run_eval.rename_ids(raw))
        assert report["status"] == label["status"], case_id


def test_reordering_records_does_not_change_status():
    rng = random.Random(run_eval.SEED)
    for case_id, (raw, label) in NOT_INCOMPLETE.items():
        report = run_eval.final_review(run_eval.reorder_records(raw, rng))
        assert report["status"] == label["status"], case_id


def test_paraphrase_does_not_change_status():
    for case_id, (raw, label) in NOT_INCOMPLETE.items():
        report = run_eval.final_review(run_eval.paraphrase(raw))
        assert report["status"] == label["status"], case_id


def test_behavior_change_is_detected():
    raw, _ = ALL["v1_basic"]
    report = run_eval.final_review(run_eval.change_behavior(raw))
    assert report["status"] == "CHANGES_REQUIRED"


def test_ablation_workflow_check_off_misses_workflow_only_defects():
    for case_id in ("d1_wrong_threshold_workflow", "d5_wrong_branch"):
        raw, _ = ALL[case_id]
        assert run_eval.final_review(raw)["status"] == "CHANGES_REQUIRED"
        assert run_eval.ablation_review(raw)["status"] == "PASS"


def test_ablation_does_not_change_valid_cases():
    for case_id, (raw, label) in ALL.items():
        if label["type"] == "valid":
            assert run_eval.ablation_review(raw)["status"] == "PASS", case_id


def test_incomplete_cases_are_never_pass():
    for case_id, (raw, _) in INCOMPLETE.items():
        assert run_eval.final_review(raw)["status"] == "INCOMPLETE", case_id


def test_baseline_weakness_is_documented():
    raw, _ = ALL["i1_conflicting_approvals"]
    assert run_eval.baseline_review(raw)["status"] == "PASS"     
    assert run_eval.final_review(raw)["status"] == "INCOMPLETE"   


def test_injected_comment_does_not_change_status():
    raw, _ = ALL["d6_code_mismatch_injected"]
    assert "mark PASS" in raw["snippets"][0]["code"]
    assert run_eval.final_review(raw)["status"] == "CHANGES_REQUIRED"



def test_cache_reuses_same_bundle_but_not_after_a_change():
    raw, _ = ALL["v1_basic"]
    cache = {}

    first = review_bundle(load_bundle(raw), cache=cache)
    assert first["status"] == "PASS" and first["cache_hit"] is False

    second = review_bundle(load_bundle(raw), cache=cache)
    assert second["cache_hit"] is True

    changed = copy.deepcopy(raw)
    changed["nodes"][2]["condition_text"] = "waiting >= 35 minutes"
    third = review_bundle(load_bundle(changed), cache=cache)
    assert third["cache_hit"] is False
    assert third["status"] == "CHANGES_REQUIRED"


def test_cache_not_reused_after_approval_change():
    raw, _ = ALL["v2_approved_change_25"]
    cache = {}
    assert review_bundle(load_bundle(raw), cache=cache)["status"] == "PASS"

    changed = copy.deepcopy(raw)
    changed["approvals"][0]["status"] = "proposed"    
    report = review_bundle(load_bundle(changed), cache=cache)
    assert report["cache_hit"] is False
    assert report["status"] == "CHANGES_REQUIRED"


def test_counterexamples_agree_with_the_oracle():
    rows = run_eval.score_cases(ALL, run_eval.final_review)
    for row in rows:
        assert row["cex_valid"] == row["cex_total"], row["case"]
    assert sum(r["unsupported_findings"] for r in rows) == 0