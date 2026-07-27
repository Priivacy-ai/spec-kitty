# WP15 Review — Cycle 1: REJECT

**Reviewer:** reviewer-renata (claude / opus) · **WP:** WP15 — Retire `RUNTIME_STATE_ALLOWLIST` (IC-07e)
**Commit reviewed:** `2927fb737` · **Verdict:** REJECT (one blocking defect; behaviour otherwise correct)

## Summary

The mechanical retirement is clean and behaviour is fully preserved. The single blocking
issue is a **silent survivor**: the 2 human-authored files kept behind the new
`_is_review_lifecycle_basename` predicate are a surviving filename-based exemption mechanism
with **no registry row**, which is exactly the "silent survivor" the plan (lines 233–235)
forbids and the registry README's own mechanism definition covers.

## What is correct (do NOT redo)

- **C5 per-symbol absence — PASS.** `grep -rn "RUNTIME_STATE_ALLOWLIST\|_runtime_state_exemption\|_is_runtime_state_basename" src/` → EMPTY. Row file `registry/RUNTIME_STATE_ALLOWLIST.md` deleted.
- **Delegation of the 4 COORD basenames — CORRECT & COMPLETE.** Proven empirically: `is_toolchain_generated_churn(<path>, mission_slug=…)` returns `True` for `status.events.jsonl`, `status.json`, `issue-matrix.md`, `acceptance-matrix.json` under the running mission. Routing them onto the owner instead of restating basenames is exactly the thesis.
- **C6 behaviour preservation — PASS.** `tests/specify_cli/bulk_edit/` → 130 passed; the untouched `test_runtime_state_exemption.py` still asserts all 6 basenames exempt. Ratchet suite → 12 passed. `assess_file` / `check_diff_compliance` contracts unchanged.
- **The 2 files are genuinely outside the owner's scope — CORRECT.** Proven empirically: the owner returns `False` for `notes.md` and for `review-cycle-1.md` (both at feature-dir root and under `tasks/<WP>/`, where it classifies as PRIMARY `WORK_PACKAGE_TASK`, not coord residue). They are human-authored review/handoff commentary with no `MissionArtifactKind`; forcing them onto the toolchain-churn owner would pollute its boundary. Keeping them out of the owner is right.
- **Quality — PASS.** ruff clean, mypy clean on `bulk_edit/diff_check.py`; no new suppressions; `_own_bookkeeping_exemption` complexity well under 15.
- **Ratchet-test edit (check #4) — acceptable.** The functional change is the single-line removal `- "RUNTIME_STATE_ALLOWLIST",` from the `required` floor (auto-merges with WP11/WP16 disjoint removals). The added docstring paragraph is additive prose above the literal and non-conflicting. OK per WP10 leeway.

## BLOCKING DEFECT (1) — `_is_review_lifecycle_basename` is a silent survivor; add an explicit justified registry row

**Where:** `src/specify_cli/bulk_edit/diff_check.py` — new `_is_review_lifecycle_basename()` (the `basename == "notes.md" or _glob_match(basename, "review-cycle-*.md")` predicate) and the deletion of the registry row with no replacement.

**Why this blocks:**

1. `_is_review_lifecycle_basename` **is** a filename-based exemption mechanism: it classifies basenames (`notes.md`, `review-cycle-*.md`) to grant a bulk-edit-gate exemption, and (proven above) it is **load-bearing** — those two files are exempted by *nothing else*. It is a genuine must-keep.

2. The plan is explicit (plan.md lines 233–235): *"Nothing is declared a permanent survivor … If implementation finds a genuine must-keep, it becomes an explicit, justified registry row, never a silent survivor."* This is precisely the genuine-must-keep case. WP15 produced a silent survivor.

3. The registry README's **own** mechanism definition covers this shape: *"A mechanism with no literal of its own (a predicate that consults a shared authority, a threaded variable, or a dead field) carries `literals: (none)` and is held present by the `symbol` presence check instead."* A predicate-form filename exemption is a registrable mechanism — the literal-collection AST scan is only one of the two registry arms, the other being symbol presence.

4. The "function-local, not module-level, so the ratchet doesn't track it" rationale in the code comment is an **evasion, not a legitimate distinction.** The R-014 AST scanner is collection-scoped *by construction*; inlining the two patterns into a boolean expression dodges the collection arm but does not make the mechanism cease to exist — it makes it **unenumerated**. The ratchet passing green (12 passed) is the symptom, not exoneration. An auditor querying the registry for "un-owned filename exemptions still in `bulk_edit/`" would see zero rows and MISS this one — the exact scattered-per-gate-knowledge harm SC-004 / NFR-006 exist to prevent.

**Required fix (small, no behaviour change):**

- Add an explicit, justified registry survivor row `registry/_is_review_lifecycle_basename.md` (one mechanism per file, per WP10 layout):
  - `mechanism: _is_review_lifecycle_basename`
  - `module: src/specify_cli/bulk_edit/diff_check.py`
  - `literals: (none)` (the two patterns are inline, not a module-level collection)
  - `symbol: _is_review_lifecycle_basename`
  - `retirement-wp: WP15` / `retirement-ref: IC-07e`
  - a `status` marking it a **justified survivor** (not `expected-present`, which means "still-to-retire") — introduce/extend the status vocabulary if needed
  - **prose** recording WHY it cannot route onto the owner: human-authored review/handoff commentary with no `MissionArtifactKind`; `review-cycle-*.md` under `tasks/` classifies PRIMARY `WORK_PACKAGE_TASK`, so `is_toolchain_generated_churn` returns `False` (behaviour would regress if dropped).
- Keep the row honest against the ratchet: ensure the survivor row does not trip the undercount/overcount arms (symbol `_is_review_lifecycle_basename` is present, so the symbol-presence arm is satisfied); if `test_registry_covers_every_known_mechanism`'s hardcoded floor is meant to name survivors, add `_is_review_lifecycle_basename` to it so the floor stays a truthful census.

This converts the silent function-local survivor into the explicit, justified row the plan and the registry README both require, without changing any runtime behaviour.

## Note on the mission's zero-rows goal

The plan's "registry reaches zero rows (IC-08 / SC-004)" target and "genuine must-keep → justified row" clause coexist: the plan resolves the tension in favour of an explicit row (a non-zero terminal registry with one honest survivor beats a silent survivor). If the mission owners intend a *strict* zero-rows terminal state, that is an escalation for the planner/architect — but it does not license leaving this exemption unenumerated. Fix as above.
