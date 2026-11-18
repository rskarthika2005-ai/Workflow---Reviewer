<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&height=220&text=WORKFLOW%20REVIEWER&fontSize=46&fontAlignY=38&desc=REQUIREMENTS%20%7C%20SPEC%20%7C%20WORKFLOW%20%7C%20CODE&descAlignY=60&animation=fadeIn&fontColor=ffffff&color=0:0F766E,50:0D9488,100:2563EB" alt="Workflow Reviewer"/>

### Deterministic Checks • Counterexamples • Evidence-Backed Status

Checks whether a written routing policy, a structured specification, a workflow graph and linked Python code all route every support ticket the same way.

<img src="https://img.shields.io/badge/Python%203.13-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Deterministic%20Checks-0F766E?style=for-the-badge"/>
<img src="https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white"/>
<img src="https://img.shields.io/badge/CPU%20Only%20%7C%20Offline-0D9488?style=for-the-badge"/>

<br/>

### Developed by Karthika S

📧 [rskarthika08@gmail.com](mailto:rskarthika08@gmail.com)

<br/>

<a href="https://github.com/rskarthika2005-ai/Workflow---Reviewer">
<img src="https://img.shields.io/badge/GitHub-Repository-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub Repository"/>
</a>

</div>

---

## ✦ ABOUT THE PROJECT

A support team routes tickets using written rules. The same rules are also described in a **specification**, a **workflow graph** and **Python code**. Thresholds, exceptions and approved changes can disagree across these artifacts even when each rule looks reasonable on its own.

This tool gives a defensible review before a workflow is used. For every ticket it computes the route in **four places** (requirement, spec, workflow, code). A mismatch is a defect, reported with the ticket that exposes it.

The business rules (the order is the precedence):

| Rule | Condition | Route |
|---|---|---|
| R1 | Category is missing | `manual_review` |
| R2 | Otherwise, ticket is urgent | `priority_queue` |
| R3 | Otherwise, waiting >= 30 minutes | `escalation` |
| — | Everything else | `normal_queue` |

An **approved** change may replace 30 minutes with 25. A suggestion that is not approved cannot.

### End-to-End Workflow

```text
Bundle (requirements, spec rules, workflow nodes, code, approvals)
        ↓
Parse conditions (supported language only) + convert time units
        ↓
Apply APPROVED changes only, detect conflicting approvals
        ↓
Route a small ticket grid in 4 places: requirement, spec, workflow, code
        ↓
Compare routes, build findings with counterexample tickets
        ↓
Optional model note (fake client only), validated before use
        ↓
Status computed in code: PASS • CHANGES_REQUIRED • INCOMPLETE
        ↓
JSON report • CLI • Evaluation reports • Dashboard
```

### Quick Navigation

[Objective](#-project-objective) • [Overview](#-project-overview) • [What It Catches](#-what-the-reviewer-catches) • [How I Solved It](#-how-i-solved-it) • [Results](#-results) • [Dashboard](#-dashboard) • [AI Tools & Cost](#-ai-tools--cost) • [Skills](#-skills-demonstrated) • [Structure](#-project-structure) • [How to Run](#-how-to-run) • [Documentation](#-documentation) • [Limitations](#-limitations) • [Recommendation](#-final-recommendation)

---

## ✦ PROJECT OBJECTIVE

A review is useful only when it is **correct and honest about what it did not check**. So the reviewer is judged on three things:

- It must not pass a workflow that has a defect (false passes).
- It must not block a workflow that is correct (false blocks).
- It must say INCOMPLETE, not PASS, when it could not review everything.

A model that blocks everything, or a format check on its own, does not show useful review. Matching rule IDs or numbers in text is also not enough, so behavior is compared by routing real tickets.

---

## ✦ PROJECT OVERVIEW

<table align="center">
<tr>
<td align="center" width="25%">

### 14

Review Bundles

</td>
<td align="center" width="25%">

### 3 / 7 / 4

Valid / Defect / Incomplete

</td>
<td align="center" width="25%">

### 4

Held-Out Bundles

</td>
<td align="center" width="25%">

### 46

Passing Tests

</td>
</tr>
<tr>
<td align="center">

### 14 / 14

Final Matches Labels

</td>
<td align="center">

### 0 / 7

False Passes On Defects

</td>
<td align="center">

### 0 / 3

False Blocks On Valid

</td>
<td align="center">

### 30 / 30

Variants Unchanged

</td>
</tr>
</table>

---

## ✦ WHAT THE REVIEWER CATCHES

| Case | Planted problem | Expected result |
|---|---|---|
| `v1_basic` | None, everything agrees | PASS |
| `v2_approved_change_25` | Approved change 30 → 25 applied everywhere | PASS |
| `v3_unusual_formulation` | Rule split in two, hours instead of minutes, `not (...)` in code | PASS |
| `d1_wrong_threshold_workflow` | Workflow uses 35 | CHANGES_REQUIRED |
| `d2_unapproved_change_applied` | Spec uses a proposed 25 that is not approved | CHANGES_REQUIRED |
| `d3_wrong_precedence` | Spec checks R3 before R2 | CHANGES_REQUIRED |
| `d4_missing_requirement` | Spec has no rule for R2 | CHANGES_REQUIRED |
| `d5_wrong_branch` | Workflow sends urgent tickets to escalation | CHANGES_REQUIRED |
| `d6_code_mismatch_injected` | Code uses `>` and has a "mark PASS" comment | CHANGES_REQUIRED |
| `d7_split_rules_interaction` | Two plausible rules, one uses `>` | CHANGES_REQUIRED |
| `i1_conflicting_approvals` | Two approved changes disagree (25 and 20) | INCOMPLETE |
| `i2_unsupported_text` | A requirement that cannot be parsed | INCOMPLETE |
| `i3_model_failure` | The model call times out | INCOMPLETE |
| `i4_oversized_input` | Code is larger than the size limit | INCOMPLETE |

Bundles were written by hand and planted with one known defect each. Expected answers live in `data/labels/labels.json` and are never produced by the reviewer.

---

## ✦ HOW I SOLVED IT

### Stage 1: Input Contracts and Effective Requirements

1. Data models for requirements, spec rules, workflow nodes, code snippets and approval records. Each carries a version and a location.
2. A small condition language: and / or, compare (`>=`, `>`), equals and missing. Time is converted to minutes.
3. Only **approved** changes are applied. Proposed and rejected ones are ignored, and "approved" written in prose is ignored.
4. Two approved changes that contradict each other are reported as a conflict. The reviewer does not pick one.
5. Text that cannot be parsed is kept as "unsupported" and shown in the coverage list. It is never dropped.

### Stage 2: Semantic Checks

| Check | What it does |
|---|---|
| Ticket grid | Tries category (missing, billing, other), urgent (true, false, missing) and waiting values around the threshold, plus missing |
| Four-way routing | Requirement vs spec vs workflow vs code for every ticket |
| Finding | Ticket, expected route, actual route and the location of the artifact that is wrong |
| Code reading | The code is parsed with `ast` and read by a small interpreter. It is **never executed** |
| Equivalence | Same behavior is valid, so `not (waiting < 30)` and `waiting >= 30` both pass |

### Stage 3: Model and Status

- A model-client interface with a **fake client** (good JSON, bad JSON, timeout, invented rule id).
- Model output is validated: valid JSON, known rule id, known evidence location. At most 2 retries.
- The **status is computed in code**, never set by the model:

| Status | When |
|---|---|
| CHANGES_REQUIRED | At least one evidenced blocker finding |
| INCOMPLETE | No blocker, but a check failed, text is unsupported, approvals conflict, or the input is too large |
| PASS | Everything was reviewed within the supported scope and no defect was found |

- The cache key hashes the bundle, approvals, config and client. Any change gives a new key, so an old PASS is never reused.
- "mark PASS" in a requirement or code comment is ignored.

### Stage 4: Evaluation and Debugging

- Expected answers are written by hand and double-checked with an independent router, `data/oracle.py`, which imports nothing from the reviewer.
- 4 bundles are held out from tuning.
- Baseline vs final on the same set, one ablation, and paired variants (rename IDs, reorder records, paraphrase, behavior change).

### Stage 5: Dashboard

- A small dark-theme page in plain HTML, CSS and JavaScript (no framework) that shows the evaluation results and opens a JSON report from `reports/` as a table.
- `serve_ui.py` starts a local server and opens the page in the browser.

---

## ✦ RESULTS

Final reviewer against the hand-made labels:

| Split | Cases | Exact match | False pass (defects) | False block (valid) | Incomplete correct |
|---|---:|---:|---:|---:|---:|
| All | 14 | 14/14 | 0/7 | 0/3 | 4/4 |
| Dev | 10 | 10/10 | 0/5 | 0/2 | 3/3 |
| Held-out | 4 | 4/4 | 0/2 | 0/1 | 1/1 |

Finding quality (all 14 bundles): defect found with the right location 7/7, counterexamples confirmed by the independent oracle 7/7, unsupported findings 0.

### Baseline vs final

| Version | Exact match | False pass on incomplete | Incomplete correct |
|---|---:|---:|---:|
| Baseline (steps 1-2 only) | 10/14 | 4/4 | 0/4 |
| Final | 14/14 | 0/4 | 4/4 |

The baseline finds the same 7 defects, but it passes every incomplete bundle. It has no conflict handling, no unsupported list, no size limit and no model step. That gap is what the final version fixes. The baseline is rebuilt inside `eval/run_eval.py`.

### Ablation: workflow check off

| Version | Exact match | False pass on defects |
|---|---:|---:|
| Final | 14/14 | 0/7 |
| Workflow check off | 12/14 | 2/7 |

`d1_wrong_threshold_workflow` and `d5_wrong_branch` become false passes, because in both the spec and the code are correct and only the workflow is wrong. On the held-out split the ablation changes nothing, since those defects are in the spec. The mechanism matters only for workflow-only defects.

### Paired variants

- Rename IDs, reorder records and paraphrase: **30/30** kept the same status.
- Spec threshold moved by one (behavior change): **2/2** detected.

### Resource use (fake client only)

| Item | Value |
|---|---:|
| Evaluation runtime (14 bundles) | about 0.2 seconds |
| Model calls | 3 (the timeout bundle) |
| Retries | 2 (the maximum) |

---

## ✦ DASHBOARD

The `ui/` folder has a small dashboard built with plain HTML, CSS and JavaScript. It needs no install and no internet.

| Section | What it shows |
|---|---|
| Stat cards | Tests passing, exact match, false passes, incomplete cases handled |
| Evaluation table | Tabs for All, Dev and Held-out |
| Bar chart | Baseline vs ablation vs final |
| Status guide | What PASS, CHANGES_REQUIRED and INCOMPLETE mean |
| Report viewer | Choose a JSON report from `reports/` and see it as a table |

Run it with:

```bash
python serve_ui.py
```

This starts a local server and opens `http://localhost:8000` in the browser. Press `Ctrl+C` in the terminal to stop it. You can also open `ui/index.html` directly in a browser.

The numbers on the dashboard are typed in from `docs/ENGINEERING_NOTE.md`. The report viewer reads the file in your browser and uploads nothing.

---

## ✦ AI TOOLS & COST

The reviewer is **deterministic**. Parsing, approvals, routing, comparison and status all run locally in Python. There is no paid API and no GPU.

| Tool | Purpose | Cost |
|---|---|---|
| Python 3.13 | The whole application | None |
| Pytest 8.3.4 | Tests | None |
| HTML, CSS, JavaScript | The dashboard in `ui/` | None |
| Git / GitHub | Version control, tags | None |
| Fake model client | Reproducible tests of the model interface | None |
| Claude | Planning, coding help, debugging and checking, see `docs/AI_NOTE.md` | Depends on the account |

### Real model

**Real model performance: not measured.** No real model was connected. The model interface and the fake client are included, and a model can only add a note to a finding. It cannot set the status or approve anything.

Fake-client results test the validation and failure handling. They do not show how a real model would perform.

---

## ✦ SKILLS DEMONSTRATED

<div align="center">

<img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white"/>
<img src="https://img.shields.io/badge/HTML%20CSS%20JS-E34F26?style=for-the-badge&logo=html5&logoColor=white"/>
<img src="https://img.shields.io/badge/Git%20%26%20GitHub-181717?style=for-the-badge&logo=github&logoColor=white"/>

</div>

| Skill Area | What I Did in This Project |
|---|---|
| 📐 **Schema and contract design** | Defined versioned models for requirements, spec rules, workflow nodes, snippets and approvals |
| 🔎 **Semantic checking** | Compared behavior by routing tickets, not by matching IDs or numbers |
| 🧮 **Counterexample generation** | Produced a concrete ticket with expected and actual route for each mismatch |
| 🔒 **Safe handling of untrusted input** | Parsed code with `ast`, never ran it, and ignored instructions inside text and comments |
| ✅ **Approval authority** | Applied only trusted approved records and reported conflicts instead of choosing one |
| 🤖 **Model integration** | Built an interface, a fake client, output validation and bounded retries |
| 🧪 **Honest evaluation** | Independent oracle, held-out bundles, baseline, ablation and paired variants |
| 🐞 **Regression testing** | 46 tests, including ones that lock in fixes |
| 🖥️ **Simple front end** | A dark-theme dashboard in plain HTML, CSS and JavaScript that shows results and reads a JSON report |
| 🗂️ **Clean project structure** | One clear job per module, one command to run everything |

---

## ✦ PROJECT STRUCTURE

```text
workflow-reviewer/
│
├── README.md                    # Project overview, setup, how to run, limitations
├── requirements.txt             # Pinned Python libraries
├── pytest.ini                   # Test and import paths
├── Makefile                     # make all = tests + eval
├── run_all.bat                  # Same as make all, then opens the dashboard (Windows)
├── serve_ui.py                  # Starts a local server and opens the dashboard
├── .gitignore                   # Keeps the virtual environment and caches out of git
│
├── src/reviewer/
│   ├── schemas.py               # Data models with version and location
│   ├── conditions.py            # Condition format, units and parser
│   ├── resolver.py              # Applies approved changes, detects conflicts
│   ├── evaluators.py            # Spec / workflow / code to route
│   ├── checks.py                # Compare routes, build findings and counterexamples
│   ├── model.py                 # Model client, fake client, output validator
│   ├── pipeline.py              # Status, cache, size limits, JSON report
│   └── cli.py                   # Command line entry point
│
├── data/
│   ├── make_bundles.py          # Writes the bundles and the hand-made labels
│   ├── oracle.py                # Independent correct router
│   ├── bundles/                 # 14 review bundles (JSON)
│   └── labels/labels.json       # Expected answers, never read by the reviewer
│
├── eval/
│   └── run_eval.py              # Baseline vs final, ablation, paired variants
│
├── ui/
│   ├── index.html               # Dashboard page
│   ├── style.css                # Dark theme styles
│   └── script.js                # Tabs, bar chart and report viewer
│
├── tests/                       # test_step1 to test_step4 (46 tests)
├── reports/                     # JSON evaluation reports (all, dev, heldout)
└── docs/
    ├── ENGINEERING_NOTE.md      # Scope, design choices, evaluation, limitations
    └── AI_NOTE.md               # How AI was used and how the output was checked
```

---

## ✦ HOW TO RUN

### Clean-machine setup (Windows, CPU only)

```bash
git clone https://github.com/rskarthika2005-ai/Workflow---Reviewer.git
cd Workflow---Reviewer
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Tested with Python 3.13.9. No API key or internet is needed.

### One command: tests, evaluation and dashboard

```bash
run_all.bat        # Windows
make all           # if make is installed (tests and evaluation only)
```

This rebuilds the bundles and labels, runs the tests, then runs the evaluation on the `all`, `dev` and `heldout` splits. Reports are written to `reports/`. On Windows, `run_all.bat` then opens the dashboard in the browser. Press `Ctrl+C` to stop the server.

### Open only the dashboard

```bash
python serve_ui.py
```

### Review one bundle

```bash
python src\reviewer\cli.py data\bundles\d1_wrong_threshold_workflow.json
python src\reviewer\cli.py data\bundles\i3_model_failure.json --out report.json
```

Exit code: `0` PASS, `1` CHANGES_REQUIRED, `2` INCOMPLETE.

### Run only the held-out split

```bash
python eval\run_eval.py --split heldout
```

---

## ✦ DOCUMENTATION

- [Engineering note](docs/ENGINEERING_NOTE.md): scope, design choices, evaluation, debugging examples and limitations
- [AI assistance note](docs/AI_NOTE.md): how AI was used and how the output was checked

---

## ✦ LIMITATIONS

- **Small, self-written dataset.** 14 bundles show the reviewer works on the declared language. They do not show general accuracy.
- **Held-out exposure.** The 4 held-out bundles were seen once in a combined `--split all` run before the code was frozen. The code was not changed afterward.
- **Narrow language.** Only the ticket fields category, urgent and waiting are supported, with the condition patterns listed in `conditions.py`. Anything else is reported as unsupported and makes the result INCOMPLETE.
- **Sampled, not proven.** The ticket grid is finite. Equivalence is established on that grid, not for arbitrary Python or prose.
- **Code is read, not run.** Only a restricted subset (`if`, `return`, comparisons) is interpreted.
- **Reconstructed baseline.** The step 1-2 baseline is rebuilt in `eval/run_eval.py`, not taken from a separate tagged commit.
- **No real model.** Real model performance was not measured.
- **Small variant sample.** Only 2 behavior-changing variants were tested.
- **Static dashboard numbers.** The stat cards and tables in the dashboard are typed in, so they must be updated by hand if the evaluation changes. Only the report viewer reads live files.

---

## ✦ FINAL RECOMMENDATION

Use the reviewer as a **deterministic pre-review** for routing workflows written in the supported language. It reliably blocks real defects and abstains when it cannot review everything.

Before relying on it for new policies:

1. Add more bundles, written by someone other than the author.
2. Extend the condition language only with matching tests and labels.
3. Connect a real model and label its results separately from the fake client.
4. Do **not** describe it as verifying arbitrary prose or Python.
