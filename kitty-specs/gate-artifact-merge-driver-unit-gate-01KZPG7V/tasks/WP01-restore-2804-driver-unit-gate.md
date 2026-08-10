---
work_package_id: WP01
title: 'Restore the #2804 driver-level unit gate (row-union)'
dependencies: []
requirement_refs:
- C-001
- C-002
- C-003
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- NFR-001
- NFR-002
- NFR-003
planning_base_branch: fix/gate-artifact-merge-driver-unit-gate
merge_target_branch: fix/gate-artifact-merge-driver-unit-gate
branch_strategy: Planning artifacts for this mission were generated on fix/gate-artifact-merge-driver-unit-gate. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/gate-artifact-merge-driver-unit-gate unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-gate-artifact-merge-driver-unit-gate-01KZPG7V
base_commit: ec37ad919f2cd336fd1532990e1f876425f5170c
created_at: '2026-08-10T19:31:33.381418+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
history:
- event: created
  at: '2026-08-10T19:04:04Z'
  actor: architect-alphonso
agent_profile: python-pedro
authoritative_surface: tests/merge/
create_intent:
- tests/merge/test_gate_artifact_merge_drivers_2804.py
execution_mode: code_change
owned_files:
- tests/merge/test_gate_artifact_merge_drivers_2804.py
role: implementer
tags: []
tracker_refs:
- '#3232'
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load your assigned agent profile:

```
/ad-hoc-profile-load python-pedro
```

This profile governs your implementation style, boundaries, and quality standards for this work package.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

Recreate `tests/merge/test_gate_artifact_merge_drivers_2804.py` (deleted by `b04da00e1`) as a fast,
in-memory **unit** overlay that pins the #2804 invariant against the **#3076 row-union authority
model**. Call the pure reconcilers directly — no git repo, no `spec-kitty merge-driver-*` subprocess,
no `pip install -e .`.

**Done when**:
- SC-001: the file exists with ~6 unit tests, all green, `pytestmark = [pytest.mark.unit]` only.
- SC-002: each invariant has a negative control that reds when the invariant is removed.
- SC-003: closes the #2804 driver-level ownership gap (a reconciler regression that resets filled→scaffold
  or drops the evidence handle reds this gate, in-process, < 5 s).
- SC-004: `pending` stays admissible (the gate does not force `pass` → #3231 not silently fixed).

## Context & Constraints

- **AUTHORITATIVE**: [post-plan-squad-findings.md](../post-plan-squad-findings.md). Two lenses exercised
  the real reconcilers; the corrected A3 fixture/control, disjoint A4 fixture, and A1/A5 caveats below are
  binding. Read it before writing a line.
- **Surfaces under test** (`src/specify_cli/cli/commands/merge_driver.py`):
  - `reconcile_acceptance_matrix_documents(base, ours, theirs) -> dict` (`:608`) — row-unions `criteria`
    (by `criterion_id`) + `negative_invariants` (by `invariant_id`), then **recomputes** `overall_verdict`
    via `AcceptanceMatrix.from_dict(...).to_dict()`.
  - `reconcile_issue_matrix_documents(base, ours, theirs) -> dict` (`:536`) — issue-matrix JSON
    `{"rows": {ref: {...}}}`; **no** verdict recompute (pure field-union).
  - `_merge_field(base, ours, theirs)` returns `ours` when `theirs == base`; emits a git-style conflict
    marker string (`<<<<<<< ours … ======= … >>>>>>> theirs`) when both diverge from base.
- **Constants** from `specify_cli.acceptance.matrix`: `SCAFFOLD_TODO_MARKER`,
  `VERDICT_PASS_PENDING_CONSOLIDATION`. Verdict domain = `{pass, fail, pending, pass_pending_consolidation}`;
  a conflicted (marker-string) `pass_fail` is not a valid verdict → recomputes to `fail` (`matrix.py:255`).
- **C-001**: do NOT touch `tests/merge/test_issue_2804_merge_resets_gate_artifacts.py` (the integration marker).
- **C-002 / #3231**: the gate MUST admit `pending`. Never assert `overall_verdict == "pass"` on an
  admitted-scaffold-row input — that would encode the out-of-scope #3231 product fix.
- **C-003**: keep it a #2804 overlay (~6 tests). The module docstring MUST cross-reference
  `tests/specify_cli/cli/commands/test_row_aware_merge_driver.py` and state the #2804-specific framing
  (scaffold marker + accepted evidence handle) it adds beyond the sibling's general row-union coverage,
  so a future reader does not cull it as a duplicate.

### ⚠️ Required fixture shapes (post-tasks squad landmine)

**Every acceptance criterion dict MUST carry `proof_type`** (e.g. `"automated_test"`) in addition to
`criterion_id` and `description` — all three are no-default constructor args on `AcceptanceCriterion`;
the reconciler ends in `AcceptanceMatrix.from_dict(...)`, so a criterion missing `proof_type` raises
`AcceptanceMatrixParseError` and every A1–A4 test errors at the reconciler call. Minimal correct shapes
(the input docs need NOT carry `mission_slug` — the reconciler synthesizes identity; `base={}` is safe):

```python
# acceptance-matrix input doc (one side)
{
    "criteria": [
        {
            "criterion_id": "AC-001",
            "description": "AC-001 verified end to end",   # marker-free on the FILLED side
            "proof_type": "automated_test",                # REQUIRED — omitting it raises AcceptanceMatrixParseError
            "pass_fail": "pass",                           # or "pending"
            "evidence": ACCEPTED_EVIDENCE_HANDLE,          # scaffold side: None (A1/A2) or "TODO: evidence" (A3)
            "notes": "real note",                          # scaffold side: SCAFFOLD_TODO_MARKER
        }
    ]
}

# issue-matrix input doc
{"rows": {"#3232": {"verdict": "verified", "evidence_ref": ACCEPTED_EVIDENCE_HANDLE}}}
# base side: {"rows": {"#3232": {"verdict": "unknown"}}}
```

The reconcilers are positional `(base_doc, ours_doc, theirs_doc)`. `from_dict` does NOT require a
non-empty `criteria`; the issue reconciler does NOT require `schema_version` on input (it injects it).

## Subtasks & Detailed Guidance

### Subtask T001 — Module scaffold + fixtures + fixture self-control (FR-001, NFR-001, NFR-002, C-003, A6)

- Create the file with `pytestmark = [pytest.mark.unit]` (ONLY — never `git_repo`/`non_sandbox`/`integration`).
- Module docstring: state the #2804 invariant and cross-reference the sibling (C-003).
- Imports: the two reconcilers from `specify_cli.cli.commands.merge_driver`; `SCAFFOLD_TODO_MARKER` +
  `VERDICT_PASS_PENDING_CONSOLIDATION` from `specify_cli.acceptance.matrix`.
- Module constants: `ACCEPTED_EVIDENCE_HANDLE = "d5b8324f9"` (cross-refs the integration marker's handle);
  `ADMISSIBLE_MERGED_VERDICTS = {"pass", "pending", VERDICT_PASS_PENDING_CONSOLIDATION}`.
- Fixtures (in-memory dicts): a FILLED and a PLACEHOLDER acceptance-matrix doc and issue-matrix doc.
  The scaffold/placeholder writes `SCAFFOLD_TODO_MARKER` into BOTH `description` and `notes`; the filled
  criterion carries the handle in `evidence` and real (marker-free) `description`/`notes`.
- **A6 two-way fixture self-control**: assert `ACCEPTED_EVIDENCE_HANDLE in json.dumps(FILLED)` and
  `ACCEPTED_EVIDENCE_HANDLE not in json.dumps(PLACEHOLDER)` for both the acceptance and issue fixtures —
  proves no fixture makes a survival assertion vacuous.

### Subtask T002 — A1 + A2: clean-merge survival (FR-002)

- **A1** (fill on `ours`, `theirs == base` scaffold): assert the merged AC-001 is the filled criterion,
  `ACCEPTED_EVIDENCE_HANDLE in json.dumps(merged)`, `SCAFFOLD_TODO_MARKER` NOT in the merged AC-001, and
  `overall_verdict == "pass"`. **Caveat**: the filled `ours` fixture must carry the marker in NO field.
- **A2** (fill authored in `theirs`, `ours == base`): symmetric — fill + handle survive, marker absent,
  verdict `pass`.
- **Controls**: a take-theirs (A1) / take-ours (A2) or all-scaffold variant makes the scaffold win →
  handle absent + marker present → the assertion reds. Encode at least one as an explicit test that would
  fail if the reconciler took the wrong side.

### Subtask T003 — A3: evidence survives inside a conflict marker (FR-003)

- **⚠️ Use the corrected fixture (F1)**: base = `{}`; `ours` and `theirs` BOTH `pass_fail="pending"`
  (EQUAL — divergent pass/pending would conflict `pass_fail` and recompute to `fail`); `ours.evidence =
  ACCEPTED_EVIDENCE_HANDLE`; `theirs.evidence = "TODO: evidence"` (non-None, ≠ handle, so the evidence
  field genuinely forms a conflict marker); `theirs` description/notes = `SCAFFOLD_TODO_MARKER`.
- Assert: does NOT raise; `ACCEPTED_EVIDENCE_HANDLE in json.dumps(merged)`; a conflict marker
  (`"<<<<<<< ours"`) is present in the merged AC-001 evidence; `overall_verdict == "pending"`
  (∈ `ADMISSIBLE_MERGED_VERDICTS`, ≠ `fail`). Do NOT assert `SCAFFOLD_TODO_MARKER` absence here (the marker
  legitimately contains scaffold text).
- **Control (F2)**: mutate to take-theirs (drop `ours`) → the handle disappears from `json.dumps(merged)`
  → red. (Not a "verdict ≠ fail" control — that collides with A4.)

### Subtask T004 — A4: admissible-verdict domain, disjoint add/add (FR-004)

- Fixture: base = `{}`; `ours` = filled AC-001 (handle, `pass_fail="pass"`); `theirs` = scaffold AC-002
  (`pass_fail="pending"`). Assert both criteria present, `ACCEPTED_EVIDENCE_HANDLE in json.dumps(merged)`,
  `overall_verdict == "pending"` (∈ `ADMISSIBLE_MERGED_VERDICTS`, ≠ `fail`). This admits `pending`
  deliberately (C-002).
- **Non-vacuity control**: a criterion with an invalid `pass_fail` (e.g. `"definitely-not-valid"`)
  recomputes to `overall_verdict == "fail"` → proves the domain assertion bites.

### Subtask T005 — A5: issue-matrix terminal survival (FR-005)

- Fixture: base row `{"#3232": {"verdict": "unknown"}}` (issue-matrix `{"rows": {...}}` shape); one side
  terminal (`{"verdict": "verified", "evidence_ref": ACCEPTED_EVIDENCE_HANDLE}`); the other == base.
  Assert the merged row `verdict != "unknown"` and the `evidence_ref` handle survives.
- **Inline note**: the issue-matrix reconciler does NO verdict recompute (no `AcceptanceMatrix`) — survival
  is pure field-union (`_merge_field` returns `ours` when `theirs == base`).
- **Control**: take-theirs (== base) drops the terminal verdict + evidence_ref.

## Test Strategy

- Run: `PWHEADLESS=1 python -m pytest tests/merge/test_gate_artifact_merge_drivers_2804.py -p no:cacheprovider -q` — all green, < 5 s.
- Sanity: confirm each control genuinely reds by temporarily inverting the relevant reconciler branch (revert after).
- `ruff check` + `mypy` on the new file — zero issues.
- Do NOT run the whole `tests/merge/` or `tests/architectural/` dirs; this one file is the surface.

## Risks & Mitigations

- **A3 false-red (F1)**: equal `pass_fail` + divergent non-None evidence; assert `pending`, not `fail`.
- **Marker-absence misapplied**: only A1 asserts `SCAFFOLD_TODO_MARKER` absence.
- **#3231 leak (C-002)**: never demand `pass` on an admitted-scaffold input.
- **Duplication (C-003)**: keep to ~6 tests + the sibling cross-ref; don't re-assert general row-union.

## Review Guidance

- Confirm `pytest.mark.unit` only; no git/subprocess/reinstall; < 5 s.
- Confirm A3 uses equal `pass_fail` + divergent evidence and asserts `pending` (not `fail`) + conflict marker.
- Confirm every invariant has a genuinely-falsifying control (take-theirs → handle disappears; invalid pass_fail → fail).
- Confirm `pending` admitted (C-002) and the docstring cross-references the sibling (C-003).
- Confirm the integration marker file is untouched (C-001).

## Activity Log

- 2026-08-10T19:04:04Z – system – lane=planned – Prompt created.
