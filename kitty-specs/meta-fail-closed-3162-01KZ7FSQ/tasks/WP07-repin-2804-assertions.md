---
work_package_id: WP07
title: "Re-pin both of #2804's red assertions and close the tracker honestly"
dependencies:
- WP01
requirement_refs:
- FR-009
- FR-010
- FR-011
- C-006
- C-008
- C-009
planning_base_branch: feat/meta-fail-closed-3162
merge_target_branch: feat/meta-fail-closed-3162
branch_strategy: Planning artifacts for this mission were generated on feat/meta-fail-closed-3162. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/meta-fail-closed-3162 unless the human explicitly redirects the landing branch.
subtasks:
- T041
- T042
- T043
- T044
- T045
- T046
history: []
agent_profile: python-pedro
authoritative_surface: tests/regression/
create_intent: []
execution_mode: code_change
owned_files:
- tests/regression/test_issue_2804_merge_resets_gate_artifacts.py
role: implementer
tags: []
tracker_refs: []
---

# WP07 — Re-pin both of #2804's red assertions and close the tracker honestly

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work
package's `task_type` and `authoritative_surface`.

---

## Objective

`#2804`'s regression marker is **honestly red on `main` today**, and it is an **inverted red**: the
assertions are wrong, not the product. Re-pin **both** of them to what the current merge design actually
guarantees, file the product defect they pointed at, and supersede the tracker item — **without** fixing the
product defect (`C-006`) and **without** weakening the row-union design that the sibling tests pin. Four
commits, one file, two tracker filings.

## Where this WP runs, how to start it, and where its evidence lands

**This WP runs from the repository root.** Everything below that reads a count, imports `specify_cli`, or
shells out to `spec-kitty` assumes the tree `.venv` was installed from.

**Start command:**

```bash
spec-kitty implement WP07
```

`spec-kitty agent action implement WP07 --agent <name>` does **not** prepare a workspace — its `--help` reads
*"Display work package prompt with implementation instructions."* `CLAUDE.md` § Execution Workspace Strategy
is explicit: *"`spec-kitty implement WP##` is the only supported way to prepare a workspace."*

**`PYTHONPATH` on anything that could run outside the root.** This WP creates a pristine `git worktree` at
`98198e980` (T041) and diffs against `96494e5ec` (T045). Every `python -c` and every `pytest` run in a tree
other than the repository root must carry `PYTHONPATH=<workspace>/src`, naming the tree being measured. The
hazard is a *silently wrong* answer, not an error:
`.venv/lib/python3.11/site-packages/_editable_impl_spec_kitty_cli.pth` pins `specify_cli` / `runtime` imports
to the **main** tree's `src/`, while `SRC_ROOT` in the gate
(`tests/architectural/test_inline_meta_read_gate.py:61`) and `_SRC_ROOT` in the ledger test
(`tests/specify_cli/test_meta_fail_closed_full_census_contract.py:54`) are derived from **the test file's own
location**. In a worktree without `PYTHONPATH` the AST census reads the *edited* `src/` while every
behavioural assertion imports the *unedited* one — a structural assertion goes green while its behavioural
twin stays red, with no diagnosable cause. It matters concretely here: T041's pristine-base reproduction is
worthless if it imported this branch's `src/`.

**Committed evidence destination.** `spec-kitty agent tasks mark-status` exposes only `--status`,
`--mission`, `--auto-commit` and `--json`; its payload is `WPInnerStateDelta.subtasks: Mapping[str, Status]`
(`src/specify_cli/status/models.py:481`) — a bare `{T0xx: Status}`. **The record carries no evidence field.**
This WP's committed evidence destination is
`kitty-specs/meta-fail-closed-3162-01KZ7FSQ/evidence/WP07-evidence.md`, written as a declared **out-of-map**
planning write with a one-line rationale (the tasks-packages contract permits it; `kitty-specs/` paths cannot
appear in `owned_files` by construction — `mission_parsing.py:153-157`, `:207-215`). Every quotation the
subtasks demand — both reds, the banner, the pristine `1 failed`, the four reconciler lines, the two
`git diff --stat` empties, the perishability statement, the two `gh issue view` outputs — goes **into that
file**. Scratch redirect targets are working files whose contents are quoted into it; nothing load-bearing is
left in `/tmp`.

## Context

### The marker carries TWO red assertions, not one

`tests/regression/test_issue_2804_merge_resets_gate_artifacts.py::test_merge_resets_filled_gate_artifacts_to_placeholder`
asserts **twice** under one `# --- CONTRACT (RED on base) ---` banner (`:476-493`):

```python
assert post_matrix.get("overall_verdict") == "pass", ...          # :482
assert SCAFFOLD_TODO_MARKER not in json.dumps(post_matrix), (     # :489
    "#2804: ... discarding the real accepted evidence.")
```

Line numbers verified by opening the file: the banner's first line is **`:476`**, assertion 1 is **`:482`**,
assertion 2 is **`:489`**. (An earlier draft said `:477` and `:488`. `:442` is a *different*
`SCAFFOLD_TODO_MARKER not in json.dumps(...)` assertion — the **pre**-merge precondition on `pre_matrix` — so
grepping for the marker and taking the first hit picks the wrong assertion.)

Earlier scoping said "the assertion", singular, and was short by one. `analysis-report.md` **BLOCKER-3** and
**BLOCKER-4** are why this work package exists in this shape. The second assertion is also false after the
merge, by a **different mechanism**: the row-union admits the scaffold row, whose `description` and `notes`
**are** the marker (fixture rows `:172-185`, `PLACEHOLDER_ACCEPTANCE_MATRIX`). Measured through the
reconciler, control first:

```
CONTROL filled fixture contains marker?  False
merged criterion_ids: ['AC-001', 'FR-001', 'FR-003']
overall_verdict: pending
POST contains SCAFFOLD_TODO_MARKER?      True
```

**So widening only the verdict assertion cannot make the marker pass.** The FILLED fixture contains no
marker; the merged document does — the marker arrives *with the union*, by design.

### Re-pin assertion 2, do not delete it

Its content **is** the real `#2804` contract, and under the row-union authority model shipped as
`` `#3076` ``'s FR-008 it is unsatisfiable *by design*, not merely stale. Deleting it discards the only
remaining executable statement of that contract. Re-pin it to **evidence survival**: the accepted evidence
handle must appear somewhere in `json.dumps(post_matrix)` — including inside a structured conflict —
negatively controlled against a **take-theirs** fixture where it is absent. Measured:

```
accepted evidence survives in merged doc: True
take-theirs control (placeholder alone):  False
```

The handle is already in the fixture: `FILLED_ACCEPTANCE_MATRIX`'s `FR-001` evidence reads
`"WP01 (commit d5b8324f9): ..."` (`:114-121`), and `d5b8324f9` appears nowhere in
`PLACEHOLDER_ACCEPTANCE_MATRIX` — the acceptance-matrix twin of the handle the issue-matrix sibling already
uses (`"verified-already-fixed"`).

### Two different siblings — do not conflate them

| Sibling | Where | Role |
|---|---|---|
| **In-file issue-matrix sibling** | same file, `:496-517` (same test function) | Carries the **form to mirror**: the comment "*both are satisfied whether the merge cleanly resolves to the real verdict or surfaces it inside a structured conflict marker*", plus `merged_row["verdict"] != "unknown"` and `"verified-already-fixed" in json.dumps(merged_row)` |
| **Cross-file row-aware sibling** | `tests/specify_cli/cli/commands/test_row_aware_merge_driver.py:427-448`, `test_merge_driver_acceptance_matrix_writes_result_to_ours` | **READ-ONLY, must stay byte-identical (`SC-008`)**. It pins `merged["overall_verdict"] == "pending"` for exactly this union shape — which is *why* the widened predicate must admit `pending` |

The two must stop contradicting each other **without weakening the new design**: the cross-file sibling is
correct and stays untouched; the marker moves.

### `SC-010` — the non-vacuity trap

`overall_verdict` is a computed property (`src/specify_cli/acceptance/matrix.py:248-271`) with domain
{`pass`, `pending`, `fail`, `pass_pending_consolidation`}. The row-aware sibling pins `pending`, so the
widened predicate **must admit `pending`** — and that is the trap:
**`pending` IS the `#2804` defect's own signature.** A companion test that merely fails on
`"fail"` proves nothing — `verdict in {"pass", "pending"}` passes with the regression fully present. Record
`"fail"` as a reachable disallowed value (one-criterion fixture, `matrix.py:259`,
`if any(v == "fail" for v in criterion_results)`) but state **explicitly that it is insufficient on its
own**. The companion must fail against **the defect's own fixture** — the take-theirs / scaffold-clobber
shape where the criteria are reset to the placeholder and the accepted evidence handle is absent. Assertion
2's evidence-survival pin is what carries the falsifiability.

**`Q10` is settled: keep the marker.** Do not delete it.

### The product defect is filed, not fixed (`C-006`, `C-009`); `SC-008` is restated

`src/specify_cli/acceptance/gates_core.py:525` is `verdict = acc_matrix.overall_verdict`; `:528` turns
`pending` into a blocking activity issue. One admitted scaffold row therefore poisons the whole aggregate.
The scaffold-row suppression rule is **rejected for this mission** — the driver has zero scaffold awareness
today and the rule would amend the row-union authority model. Widening the pin **without filing** this would
make a red go away without addressing what it pointed at, which is the whole failure mode this work package
guards against.

`SC-008`'s original phrasing — "both assertions pass on current `main`" — is **unrunnable**: the widened
marker lives on the branch. Restated: **passes on branch head with `src/` unchanged from the measurement
baseline** (`96494e5ec`), proved by `git diff --stat 96494e5ec -- src/` printing nothing.

### The evidence is perishable — that is why this work package does not end the mission

It may **start** anytime (`dependencies: []`), but the marker runs the mission's own degrade sites for real.
It imports `_run_lane_based_merge`; `src/specify_cli/merge/executor.py:116` imports
`resolve_placement_only`, which reaches `_assemble_core_fragments` → `_resolve_mission_id`
(`mission_runtime/resolution.py:1107`, census row 3) and `_resolve_coordination_branch` (`:852`, row 2) —
**two of WP04's four degrade sites**. It also shells out to `merge_driver.py` **as a subprocess**
(`src/specify_cli/lanes/merge.py:84` registers `spec-kitty merge-driver-meta %O %A %B` for
`kitty-specs/**/meta.json`), which **WP05 may edit** and which is **invisible until `pip install -e .`** —
the documented stale-install false-red class.

So a green capture here is **not** evidence that it still passes after WP04 and WP05 land. Re-capture belongs
to **WP08**, on the integrated tree, after the reinstall. Say so in your evidence, and say why.

### The inverted-red protocol (mandatory)

An inverted red is the one class where "make it green" is indistinguishable from green-washing (charter
Standing Order 9). A single line saying "pre-existing, not caused by a new test" licenses exactly the
pass-while-broken outcome. All four are required: (1) quote the failing selection **before** the change, on a
pristine base; (2) name **every** failing assertion — a one-assertion account is what made `SC-008` look
reachable by widening the verdict alone; (3) cite the **separately-filed product defect** (`SC-009` row 2),
plus #3138 for the red itself; (4) show the companion falsifiability test failing on the **defect fixture**,
not on an unrelated disallowed value.

### Run discipline

The marker performs a **real squash merge in a fixture repo** and is slow (~97s). Run it **by node id**,
**redirect** (never pipe — a piped exit status is not trustworthy), quote the `N passed` / `N failed` line
with the selected count, use **`-ra`, never `-rf`**, count `^ERROR tests/` not `^ERROR `. `ruff check`
only — **never `ruff format`**; this repo is not `ruff format`-clean.

**Cone**: `tests/regression` (owned) plus `tests/merge` **read-only for context**.
`tests/specify_cli/cli/commands/test_row_aware_merge_driver.py` may be **run** to prove it is still green —
it lives inside `tests/specify_cli` and is **not** the barred top-level `tests/cli` (`plan.md` Technical
Context corrects the census on exactly this point). **Never sweep `tests/sync` or `tests/cli`**: sibling
mission 3167 may hold those windows (`C-007`), and the handshake belongs to WP08.

---

### Subtask T041 — Quote both reds, reproduce on a pristine base, measure the reconciler control-first

**Purpose**: satisfy inverted-red protocol steps (1) and (2) before a single character changes, and prove by
measurement that widening the verdict assertion alone cannot make `SC-008` pass.

**Steps**

1. Quote **both** assertions verbatim from the current file, with `file:line` and the enclosing symbol
   (`C-003`): `:482` (`overall_verdict == "pass"`) and `:489`
   (`assert SCAFFOLD_TODO_MARKER not in json.dumps(post_matrix)`), both under the single
   `# --- CONTRACT (RED on base) ---` banner whose first line is `:476`. **Open the file and confirm both
   numbers before quoting them**; `:442` is a different marker assertion (the pre-merge precondition on
   `pre_matrix`) and is not one of the two. Quote the banner too — one banner, two assertions,
   is the fact the earlier scoping missed.
2. Reproduce the red on a **pristine** base: `git worktree add <scratch>/repro-3162-main 98198e980`
   (`upstream/main`). Run the **same selection** by node id, redirected, **from inside that worktree and with
   `PYTHONPATH` pointing at its own `src/`** — otherwise `.venv`'s editable `.pth` imports this branch's
   `src/` and the "pristine" red is not pristine:
   ```bash
   cd <scratch>/repro-3162-main
   PYTHONPATH=<scratch>/repro-3162-main/src \
     <repo-root>/.venv/bin/python -m pytest -ra \
     tests/regression/test_issue_2804_merge_resets_gate_artifacts.py::test_merge_resets_filled_gate_artifacts_to_placeholder \
     > <scratch>/pre.txt 2>&1; echo "exit=$?"
   ```
   Quote the `PYTHONPATH` you used alongside the result. Quote: `rootdir:` line, `1 failed in <N>s`
   (reference: `1 failed in 96.97s`),
   `grep -c '^ERROR tests/' <scratch>/pre.txt` → **0**, and the assertion line `E assert 'pending' == 'pass'`.
   A killed run is neither a pass nor a fail — rerun it.
3. **"Known class tracked elsewhere" is not a pre-existing classification** — only this same-selection
   reproduction on a pristine base is one. Say so, and print the live **routed** count PRE using WP01's
   recorded measurement command verbatim (**0-net** work package; expect **129**, unchanged at T045).
4. Capture the reconciler measurement pair as a scratch probe, **control first**, importing
   `reconcile_acceptance_matrix_documents` and feeding it the module's own fixtures
   (`FILLED_ACCEPTANCE_MATRIX` as *ours*, `PLACEHOLDER_ACCEPTANCE_MATRIX` as *theirs*): the control
   `CONTROL filled fixture contains marker? False` (proving the marker is not already in the input), then
   `merged criterion_ids: ['AC-001', 'FR-001', 'FR-003']`, `overall_verdict: pending`, and
   `POST contains SCAFFOLD_TODO_MARKER? True`.
5. State the conclusion in one line: **widening only the verdict assertion cannot make `SC-008` pass**,
   because the union admits the scaffold row whose `description`/`notes` *are* the marker.

**Files**: none changed. Scratch worktree and probe outside the repo tree.

**Validation**: both assertions and the banner quoted with `file:line`; pristine-base `1 failed` quoted with
`^ERROR tests/` → 0 and `E assert 'pending' == 'pass'`; the four measurement lines quoted **with the control
first**; routed PRE printed with its input count.

---

### Subtask T042 — COMMIT 1: widen assertion 1, matched to the in-file sibling's form

**Purpose**: pin assertion 1 to the design's admissible verdicts, in the *same words* the issue-matrix
sibling in this very file already carries — so the file stops holding two answers to one question.

**Steps**

1. Widen `:482` so it is satisfied **whether the merge cleanly resolves *or* surfaces a structured
   conflict**. Mirror the in-file sibling's clause at `:496-506` verbatim in spirit: the scaffold's
   placeholder verdict must never win **outright**. The predicate must **admit `pending`** — the cross-file
   sibling `test_merge_driver_acceptance_matrix_writes_result_to_ours` pins exactly that for this union
   shape, and contradicting it would weaken the row-union design rather than fix the marker.
2. Keep the failure message naming #2804 and printing the actual verdict. Do not soften it into a narration.
3. In the assertion's own comment (and the module docstring, T043) record two facts a future reader will
   otherwise re-derive wrongly: `"fail"` **is** a concrete disallowed verdict, reachable from a one-criterion
   fixture (`src/specify_cli/acceptance/matrix.py:259`), so the widened predicate is falsifiable — **and
   `"fail"` alone is insufficient evidence**, because `pending` is the defect's own signature and must be
   *admitted*, so `verdict in {"pass", "pending"}` would pass with the regression fully present. Assertion 2
   (T043) is what carries the falsifiability.
4. Do **not** touch assertion 2 in this commit, and do **not** touch the issue-matrix assertions at
   `:507-517` — they are already widened and already green.
5. Commit and **quote the SHA**. Run the node id, redirected. It will still be **red on assertion 2** — that
   is expected and must be **quoted as the intermediate state**, naming the still-failing assertion. Do not
   present this commit as green.

**Files**: `tests/regression/test_issue_2804_merge_resets_gate_artifacts.py`.

**Validation**: SHA quoted; the widened assertion quoted pre and post; the intermediate red quoted with the
still-failing assertion named (`SCAFFOLD_TODO_MARKER not in ...`); `pending` demonstrably admitted;
`ruff check` clean on the file.

---

### Subtask T043 — COMMIT 2: re-pin assertion 2 to evidence survival, with its take-theirs control

**Purpose**: keep the real `#2804` contract executable. Assertion 2 is **re-pinned, not deleted**.

**Steps**

1. Introduce a module constant for the accepted evidence handle, derived from the fixture rather than
   hand-typed twice — e.g. `ACCEPTED_EVIDENCE_HANDLE = "d5b8324f9"`, the commit handle already carried by
   `FILLED_ACCEPTANCE_MATRIX`'s `FR-001` evidence (`:114-121`).
2. Add a **two-way fixture self-control** so the handle can never go silently vacuous: assert it **is** in
   `json.dumps(FILLED_ACCEPTANCE_MATRIX)` and **is not** in `json.dumps(PLACEHOLDER_ACCEPTANCE_MATRIX)`. A
   handle absent from the filled side makes the new pin unsatisfiable; a handle present on the placeholder
   side makes it vacuous. Neither is catchable by the merged-document assertion alone.
3. Replace `:489` with the evidence-survival pin: `ACCEPTED_EVIDENCE_HANDLE in json.dumps(post_matrix)`,
   with a message that says the accepted evidence was discarded **without leaving any trace of it, not even
   inside a structured conflict marker** — the same shape as the in-file issue-matrix sibling's
   `"verified-already-fixed" in json.dumps(merged_row)` at `:512-516` (the `assert` is on **`:512`**; an
   earlier draft said `:513`).
4. **Extract the re-pinned pair into one shared helper** — e.g. `_assert_2804_acceptance_contract(doc)` —
   and call it from the marker. T044's companion **must call the same helper**, so it exercises the real
   predicate rather than a paraphrase of it. A copy-pasted predicate in the companion is a rejection.
5. Amend the module docstring: what the two assertions pin **now** (assertion 1: the verdict is one of the
   design's admissible values, never the placeholder winning outright; assertion 2: **evidence survival**),
   why the shape changed (row-union authority model, `` `#3076` `` FR-008), that `Q10` is settled **keep the
   marker**, and that the product defect is **filed, not fixed here** (`C-006`) — with the `SC-009` row 2
   issue number once T046 has it. Remove the now-false "intentionally FAILING until the product defect is
   fixed" framing; the honest replacement is that the pin changed shape and the defect is tracked separately.
6. Commit and **quote the SHA**. Run the node id redirected; quote the `N passed` line with the selected
   count. Both re-pinned assertions must now pass.

**Files**: `tests/regression/test_issue_2804_merge_resets_gate_artifacts.py`.

**Validation**: SHA quoted; assertion 2 quoted pre and post; the two-way fixture control quoted; the shared
helper exists and the marker calls it; measured `accepted evidence survives in merged doc: True` and
`take-theirs control (placeholder alone): False`; docstring diff quoted; `N passed` with selected count.

---

### Subtask T044 — COMMIT 3: the companion test, fed the defect's own fixture

**Purpose**: `SC-010`. Prove the re-pinned pair is falsifiable **by the defect it exists to catch**, not by
an unrelated disallowed value — the criterion previously passed while the defect was fully present.

**Steps**

1. Add `test_widened_2804_assertion_rejects_wrong_verdict` to the same file. Build **the defect's own
   fixture**: the take-theirs / scaffold-clobber document — criteria reset to the placeholder
   (`PLACEHOLDER_ACCEPTANCE_MATRIX` alone), so `overall_verdict` is `pending` **and** the accepted evidence
   handle is **absent**. This is exactly the shape the pre-fix merge produced.
2. Assert the **shared helper from T043 raises** on it: `with pytest.raises(AssertionError):
   _assert_2804_acceptance_contract(take_theirs_doc)`. The **pair** must fail, and the failure must be
   attributable to the evidence-survival clause — assert on the raised message so a future edit that moves
   the failure to some other clause is visible.
3. Add the `"fail"` case as a **secondary, explicitly labelled-insufficient** witness: a one-criterion
   fixture with `pass_fail: "fail"` yields `overall_verdict == "fail"` (`matrix.py:259`), which assertion 1
   rejects. Label it in the test's docstring: *this alone is not `SC-010` evidence*, because it is a value
   unrelated to the defect.
4. Add the **positive twin**: the same helper must **pass** on the filled/merged document. A negative with
   no positive twin is the vacuous gate `architectural-gate-non-vacuity` forbids (charter Standing Order 5).
   Write the anti-vacuity argument into the docstring in one paragraph: `pending` is the defect's own
   signature and is *admitted* by the widened predicate, therefore `verdict in {"pass", "pending"}` plus a
   `fail` fixture is **not** falsifiability; assertion 2's evidence-survival pin is what carries it.
5. The companion must be **fast** — it exercises the reconciler / helper directly and must **not** run the
   squash-merge harness. Quote its own runtime. Commit, **quote the SHA**, and run marker + companion
   together by node id, redirected, `-ra`.

**Files**: `tests/regression/test_issue_2804_merge_resets_gate_artifacts.py`.

**Validation**: SHA quoted; the companion's failing case is the **defect's own fixture**, quoted; the raised
`AssertionError` message quoted and attributed to the evidence-survival clause; positive twin present and
passing; `"fail"` witness present and labelled insufficient; both nodes green in one redirected run with the
selected count quoted.

---

### Subtask T045 — `SC-008`'s two byte-identity proofs, and the perishability statement (parallel)

**Purpose**: prove the marker was made honest **without** weakening the design or moving `src/`, and record
in writing that this capture is lane-local.

**Steps**

1. `git diff --stat upstream/main -- tests/specify_cli/cli/commands/test_row_aware_merge_driver.py` must
   print **nothing**. Quote the empty output *and* the command. That file is **read-only** for this work
   package and must stay **byte-identical** (`SC-008`, US4 scenario 2). Then **run** it and quote its
   `N passed` with the selected count — "unchanged" alone does not establish "green". Reminder: it lives
   inside `tests/specify_cli`, **not** the barred top-level `tests/cli`.
2. `git diff --stat 96494e5ec -- src/` must print **nothing**. Quote it. This is what makes the restated
   `SC-008` runnable: *branch head with `src/` unchanged from the measurement baseline*. State explicitly
   that the original phrasing ("passes on current `main`") is **unrunnable**, because the widened marker
   lives on the branch.
3. Print the live **routed** count POST and compare with T041's PRE — both **129**, delta **0**. This work
   package touches no `src/` file; a non-zero delta means something was edited that should not have been.
4. Write the **perishability statement** into the evidence, in full: this capture is **lane-local**, because
   (i) the marker's live path crosses WP04's degrade sites — `merge/executor.py:116` →
   `resolve_placement_only` → `_assemble_core_fragments` → `_resolve_mission_id` (`resolution.py:1107`) and
   `_resolve_coordination_branch` (`:852`) — and (ii) it runs `spec-kitty merge-driver-meta` as a
   **subprocess** (`lanes/merge.py:84`), which WP05 may edit and which is invisible until
   `pip install -e .`. **WP08 re-captures `SC-008` and `SC-010` on the integrated tree after the reinstall.**
   A capture taken before that reinstall is a stale-install false red or false green — both worthless.
   Redirect every run; quote node counts; `-ra` never `-rf`.

**Files**: none changed.

**Validation**: both `git diff --stat` commands quoted printing nothing; the sibling's `N passed` quoted;
routed PRE == POST == 129 with delta 0; the perishability statement present naming WP04, WP05 and WP08 and
the `pip install -e .` requirement; the `SC-008` restatement written out.

---

### Subtask T046 — COMMIT 4: the two tracker filings (`SC-009` rows 1 and 2)

**Purpose**: `C-009` — file, do not absorb. Both filings are this work package's, and neither is optional.

**Steps**

1. **`SC-009` row 2 — the product defect** (`FR-011`, `C-006`). File *pending-poisons-the-aggregate*: one
   admitted scaffold row makes `overall_verdict` `pending` (`src/specify_cli/acceptance/matrix.py:263`,
   `any(v == "pending")` dominates), and `src/specify_cli/acceptance/gates_core.py:525`
   (`verdict = acc_matrix.overall_verdict`) feeds that straight into the gate, where `:528` turns it into a
   blocking activity issue. Cite `gates_core.py:525` as the evidence line. Name the **scaffold-row
   suppression rule** as the *candidate* fix and state that it is **rejected for this mission** — the
   reconciler has zero scaffold awareness today, so the rule would amend the row-union authority model
   shipped as `` `#3076` ``'s FR-008. **Do not fix it** (`C-006`). Say in the issue that this filing is the
   reason the marker's pin could be widened at all.
2. **`SC-009` row 1 — the superseding issue for #2804** (`FR-010`, `Q9`). Record what is pinned **now**
   (assertion 1: admissible verdicts, matched to the in-file issue-matrix sibling's already-widened form;
   assertion 2: evidence survival, take-theirs negatively controlled), **why the shape changed** (row-union
   authority model), and that **`b04da00e1` deleted `tests/merge/test_gate_artifact_merge_drivers_2804.py`
   (−249 lines)** — the unit gate that held this invariant, whose absence **no requirement currently owns**.
   **Cite it; do not restore it.** Verified: `git show --stat b04da00e1` lists
   `.../merge/test_gate_artifact_merge_drivers_2804.py | 249 --------` inside a 130-file commit.
3. **Supersede, do not reopen** (`Q9`): point #2804 at the new issue with a comment, and link back. Verify
   **each** filing with `gh issue view <n> --json number,title,body`, quote the output, and record the
   **real numbers** in `SC-009` rows 1 and 2 — `[to record]` left in place is an unmet criterion.
4. Charter obligations: assign both tickets to the HiC (Tracker Ticket Assignment Rule); give each addressed
   issue its issue-matrix row + claim + tracker comment naming the mission (Standing Order 8); note that
   T041's pristine-base reproduction discharges the Pre-existing Failure Reporting Rule for this red, tracked
   as #3138. Append to the three mission tracer files (Standing Order 3) — in particular the inverted-red
   finding: a marker can be honestly red *and* wrong.
5. Commit the docstring's issue-number backfill from T043 step 5 and **quote the SHA**.

**Files**: `tests/regression/test_issue_2804_merge_resets_gate_artifacts.py` (issue numbers into the
docstring); tracker; mission tracer files.

**Validation**: two `gh issue view <n> --json number,title,body` outputs quoted; `SC-009` rows 1 and 2 carry
real numbers; #2804 carries the superseding comment; `b04da00e1`'s −249 line cited with `git show --stat`;
`C-006` restated as **not fixed here**; SHA quoted.

---

## Definition of Done

- [ ] **Both** red assertions quoted verbatim pre-change with `file:line` and the shared
      `# --- CONTRACT (RED on base) ---` banner. A one-assertion account is a rejection.
- [ ] Pristine-base reproduction on `upstream/main` `98198e980`, same node id, `1 failed` quoted,
      `grep -c '^ERROR tests/'` → **0**, `E assert 'pending' == 'pass'` quoted.
- [ ] Reconciler measurement pair quoted **control first**: filled-contains-marker `False`; merged
      `criterion_ids`; `overall_verdict: pending`; post-contains-marker `True`.
- [ ] Assertion 1 widened, matched to the in-file issue-matrix sibling's "cleanly resolves *or* surfaces a
      structured conflict" clause, and **admits `pending`**.
- [ ] Assertion 2 **re-pinned, not deleted**, to evidence survival; measured `True` in the merged document
      and `False` on the take-theirs control; two-way fixture self-control asserted.
- [ ] One **shared predicate helper** used by both the marker and the companion — not a copy.
- [ ] `test_widened_2804_assertion_rejects_wrong_verdict` fails on **the defect's own fixture** (take-theirs
      / scaffold-clobber, accepted handle absent), with the raised message quoted; positive twin present;
      `"fail"` recorded as a reachable disallowed value **and labelled insufficient on its own**.
- [ ] `git diff --stat upstream/main -- tests/specify_cli/cli/commands/test_row_aware_merge_driver.py`
      prints **nothing**, quoted; that sibling **also run and green**, `N passed` quoted.
- [ ] `git diff --stat 96494e5ec -- src/` prints **nothing**, quoted; `SC-008`'s unrunnable phrasing restated
      in writing. Routed count printed pre and post, **both 129**, delta **0** (0-net: test + tracker only).
- [ ] Four commits present and unsquashed, in order: widen / re-pin / companion / filings. T042's commit is
      quoted as an **intermediate red**, never as green.
- [ ] `SC-009` rows 1 and 2 filed with **real numbers**, each verified by
      `gh issue view <n> --json number,title,body` and quoted; the product defect **filed and not fixed**
      (`C-006`) with `gates_core.py:525` cited; #2804 superseded, not reopened; `b04da00e1`'s −249 deletion
      cited, not restored.
- [ ] The **perishability statement** is written: WP04's degrade sites and WP05's subprocess make this
      capture lane-local; **WP08 re-captures after `pip install -e .`**.
- [ ] `C-008` exception declared out loud: this requirement's red is an **inverted red** — pre-existing and
      wrong — so the work makes it green, and all four protocol steps are discharged.
- [ ] Only `tests/regression/test_issue_2804_merge_resets_gate_artifacts.py` changed
      (`git diff --name-only` quoted): no `src/`, no routing ledger, no sibling merge-driver test. Cone was
      `tests/regression` + `tests/merge` read-only + the row-aware sibling under `tests/specify_cli` —
      **no `tests/sync`, no `tests/cli`**.
- [ ] Every run **redirected** (never piped), by node id, `-ra` never `-rf`, `N passed`/`N failed` and the
      selected count quoted. `ruff check` clean; **`ruff format` never run**. Every citation carries
      **`file:line` and symbol** (`C-003`); foreign issue IDs backticked, this mission's own bare.
- [ ] Every command run in the pristine `98198e980` worktree carries `PYTHONPATH=<worktree>/src`, and the
      evidence names which tree each result came from. A pristine-base red taken without it proves nothing
      about the pristine base.
- [ ] All of it is written into the committed
      `kitty-specs/meta-fail-closed-3162-01KZ7FSQ/evidence/WP07-evidence.md`, not left in a `mark-status`
      record (which carries only `{T0xx: Status}`) or in `/tmp`.

**Subtask marking** — run per subtask as it completes. This records **status only**: `mark-status` exposes
`--status`, `--mission`, `--auto-commit`, `--json` and nothing else, and its payload is a bare
`{T0xx: Status}` (`src/specify_cli/status/models.py:481`). It is **not** an evidence channel. Every
quotation this WP owes lives in the committed
`kitty-specs/meta-fail-closed-3162-01KZ7FSQ/evidence/WP07-evidence.md`.

```bash
spec-kitty agent tasks mark-status <Txxx> --status done --mission meta-fail-closed-3162-01KZ7FSQ
```

## Risks

1. **Widening only the verdict assertion.** The most likely wrong move, and it *looks* complete: the marker
   still fails on assertion 2, by a different mechanism (measured at T041). An implementer who stops after
   T042 will report `SC-008` met while the node is red.
2. **Deleting assertion 2 instead of re-pinning it.** Also makes the marker green, and destroys the only
   remaining executable statement of the real `#2804` contract. `Q10` is **settled: keep the marker.**
3. **A vacuous companion test.** `verdict in {"pass", "pending"}` plus a `fail` fixture satisfies the letter
   of "fails on some disallowed verdict" while the regression is **fully present** — `pending` is the
   defect's signature and must be admitted. This is exactly how `SC-010` passed before
   (`analysis-report.md` BLOCKER-4). The companion's fixture must be the defect's own shape.
4. **A paraphrased predicate in the companion.** If the companion re-implements the assertions instead of
   calling the shared helper, it proves a copy falsifiable and the marker nothing at all.
5. **Green-washing the inverted red.** "Pre-existing, not caused by a new test" is one line that licenses the
   pass-while-broken outcome. Charter Standing Order 9 forbids it; step (3) of the protocol — the
   separately-filed product defect — is the one most likely to be skipped.
6. **Editing the sibling merge-driver test to resolve the contradiction.** It is byte-identical read-only
   (`SC-008`) and it is the **correct** side: it pins `pending` for the union shape. Changing it weakens the
   row-union design instead of fixing the marker.
7. **Treating this lane's green as the mission's evidence.** Do **not** re-capture WP08's integration
   evidence here, and do **not** claim `SC-008`/`SC-010` are settled for the mission.
8. **Absorbing the product defect.** Fixing the scaffold-row suppression rule here would make the marker
   pass *and* amend `` `#3076` ``'s FR-008 authority model in a work package that owns one test file.
   Rejected (`C-006`); file it (`C-009`).
9. **Tooling shortcuts.** A piped exit status on a ~97s real-git run is not trustworthy and a killed run is
   neither a pass nor a fail; `ruff format` would produce an unreviewable diff across a 517-line test file.

## Reviewer Guidance

Check these in order; the first four are where this work package fails if it fails.

1. **Are both assertions named, and did the change touch both?** Find assertion 1 (verdict) and assertion 2
   (evidence survival) in the diff. If only the verdict moved, the node is still red and the work package is
   not done regardless of what the summary says. If assertion 2 was **deleted**, reject — `Q10` is settled.
2. **Is the companion fed the defect's own fixture?** Read the fixture, not the test name. It must be the
   take-theirs / scaffold-clobber document with the criteria reset to the placeholder and the accepted
   evidence handle **absent**. A companion whose only failing case is a `"fail"` verdict is the documented
   `SC-010` cheat and must be rejected. Confirm the `"fail"` witness is present **and labelled
   insufficient**, and that a positive twin exists.
3. **Does the companion call the same predicate the marker calls?** Find the shared helper and both call
   sites. A copy-pasted predicate is a rejection.
4. **Is the product defect filed, with `gates_core.py:525` cited?** `gh issue view <n>` quoted, real number
   in `SC-009` row 2. Widening the pin without this filing is the exact failure mode this work package
   guards against. Then confirm no `src/` file moved: `git diff --name-only 96494e5ec -- src/` empty.
5. **Byte-identity of the sibling.** `git diff --stat upstream/main --
   tests/specify_cli/cli/commands/test_row_aware_merge_driver.py` printing nothing, quoted — **and** the
   sibling actually run and green. Unchanged-but-unrun does not satisfy US4 scenario 2.
6. **The four commits, in order, unsquashed.** T042's commit must be presented as an **intermediate red**
   with the still-failing assertion named. A lane that squashes to one green commit has destroyed the
   inverted-red protocol's step (1)–(2) evidence.
7. **The perishability statement is present and specific.** It must name WP04's two degrade sites reached
   through `merge/executor.py:116`, WP05's subprocess at `lanes/merge.py:84`, `pip install -e .`, and WP08
   as the owner of the re-capture. A generic "evidence may age" sentence does not satisfy this.
8. **The superseding issue cites `b04da00e1`'s −249-line deletion** of
   `tests/merge/test_gate_artifact_merge_drivers_2804.py` and does **not** restore it, and #2804 is
   **superseded, not reopened** (`Q9`).
9. **Cone.** No `tests/sync`, no `tests/cli` in any quoted selection. A refusal to run
   `tests/specify_cli/cli/commands/test_row_aware_merge_driver.py` on the belief that it is `tests/cli` is a
   correctable misreading, not a cone violation.

### Things in the upstream planning artifacts to be aware of

- **Do not accept a narration that `SC-008` "could not be run".** `spec.md:397-405` already carries the
  runnable restatement — *branch head with `src/` unchanged from the measurement baseline*.
- **`analysis-report.md` predates the IC renumbering.** `plan.md`'s numbering (`### IC-07`) is authoritative
  for this work package; `analysis-report.md` is authoritative for **why** BLOCKER-3 and BLOCKER-4 changed
  its shape.
- **`plan.md` records branch `HEAD` as `1e5bc865b`**; the branch has advanced since with
  planning-artifact-only commits. The load-bearing invariant is the one to check:
  `git diff --name-only 96494e5ec HEAD | grep -v '^kitty-'` → **0** files.
- **The `SC-009` register lists 8 rows; this work package owns exactly 2** (rows 1 and 2). Do not file rows
  3–8 here — they belong to the work packages that touch their surfaces, and row 4 must be filed *before*
  its code is edited, which is not this lane.
