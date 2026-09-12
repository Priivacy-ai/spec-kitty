# Tracer: Post-Plan Squad Findings (2026-08-10)

Authoritative plan-remediation record. Two profile-loaded lenses (architect-alphonso — technical
achievability by exercising the real reconcilers; reviewer-renata — test-honesty/anti-vacuity/scope)
converged. `/spec-kitty.tasks` and the implementer MUST honor these. They fold into plan.md IC-01/IC-02.

## BLOCKER — F1: A3 as originally planned is a FALSE RED on correct code

Original plan A3: no base, `ours` = filled (`pass_fail="pass"`, evidence=handle), `theirs` = scaffold
(`pass_fail="pending"`), assert `overall_verdict ∈ admissible (never fail)`. **Verified live: real output
is `overall_verdict == "fail"`.** Mechanism: divergent `pass_fail` (add/add, base absent) →
`_merge_field` emits a git-conflict-marker STRING for `pass_fail` (`merge_driver.py:378-384`) →
`AcceptanceMatrix.overall_verdict` sees a value not in `CRITERION_VERDICTS` (`matrix.py:255`) →
recomputes `fail`. So the "admissible/never-fail" assertion reds correct code — the exact anti-pattern
this gate exists to prevent.

**Corrected A3 (equal `pass_fail`, divergent evidence — the FR-003 "survives inside a conflict marker"
witness):**
- Fixture: base = `{}`; `ours` = `{criterion_id:"AC-001", pass_fail:"pending", evidence:"d5b8324f9",
  description:<real>, notes:<real>}`; `theirs` = `{criterion_id:"AC-001", pass_fail:"pending",
  evidence:"TODO: evidence", description:SCAFFOLD_TODO_MARKER, notes:SCAFFOLD_TODO_MARKER}`.
  **`pass_fail` MUST be equal on both sides** (both `pending`) → merges cleanly, verdict stays
  admissible; **`theirs.evidence` MUST be non-None and ≠ the handle** (else with base absent
  `theirs==base` on evidence and it merges to `ours` with NO conflict marker — the "inside a conflict
  marker" clause would be silently un-exercised).
- Assert: does NOT raise; `"d5b8324f9" in json.dumps(merged)` (handle survives); a conflict marker
  (`"<<<<<<< ours"`) is present in the merged AC-001 evidence field; `merged["overall_verdict"] ==
  "pending"` (∈ ADMISSIBLE, ≠ fail). Verified live: `verdict = pending, handle in dumps = True, evidence
  merged = "<<<<<<< ours\n\"d5b8324f9\"\n=======\n\"TODO\"\n>>>>>>> theirs"`.

## BLOCKER — F2/F3: A3's negative control was misframed + self-contradictory

Original IC-02 A3 control ("verdict ≠ fail AND raw scaffold verdict did not win outright") is not a
control for handle-survival and collides with A4's correct "invalid `pass_fail` → fail" control.
**Corrected A3 control:** mutate the reconciler to take-theirs (drop `ours`) → the accepted evidence
handle disappears from `json.dumps(merged)` → red. (Standard: a control whose only failing case is the
target defect's own signature.)

## MAJOR — A4: use the disjoint add/add fixture

`overall_verdict` admissible (`pending`, ≠ fail) with a scaffold row ADMITTED ALONGSIDE a filled row.
Best witness = genuine disjoint union: base = `{}`, `ours` = filled AC-001 (handle, `pass_fail="pass"`),
`theirs` = scaffold AC-002 (`pass_fail="pending"`). Verified live: `verdict = pending`, both rows
present, handle survives. Non-vacuity control (verified): a criterion with an invalid `pass_fail`
(`"definitely-not-valid"`) recomputes to `overall_verdict == "fail"` → the domain assertion bites.
This deliberately admits `pending` (the #3231 product behavior) and MUST NOT force `pass` (C-002).

## MINOR — fixture caveats (record for /tasks)

- **A1**: the filled `ours` criterion must carry `SCAFFOLD_TODO_MARKER` in **no** field (description AND
  notes both real) — the scaffold author writes the marker into BOTH `description` and `notes`
  (`matrix.py:531,534`); otherwise the "marker absent in criterion" assertion reds. Verified A1 holds:
  `verdict=pass, handle present, marker absent` (theirs==base → `_merge_field` returns ours cleanly).
- **A2**: symmetric to A1 (fill authored in `theirs`, `ours`==base). Holds.
- **A5**: the issue-matrix reconciler does **NO** verdict recomputation (no `AcceptanceMatrix`) — it
  row-unions field-by-field; `evidence_ref`/`verdict` survive via `_merge_field` returning `ours` when
  `theirs==base`. Add an inline comment so a future reader doesn't expect acceptance-style recompute.
  Schema shape: `{"rows": {ref: {...}}}` in, `{"schema_version": ..., "rows": {...}}` out. Verified A5
  holds: merged row `verdict != "unknown"`, `evidence_ref` survives.

## OPTIONAL (do NOT require — respects the ~6-test C-003 bound)

- **negative_invariants survival**: an NI row reset from `confirmed_absent`→`pending` is the same
  regression class, but the reconciler path is identical (`_reconcile_keyed_rows`) for `criteria` and
  `negative_invariants`, and the sibling already covers NI keying — low marginal value. Belt-and-suspenders
  only; adding it risks padding past ~6 tests.

## SOUND (confirmed, no action)

- Ownership gap real: `test_row_aware_merge_driver.py` (37 tests) owns the GENERAL row-union contract;
  ZERO hits for `SCAFFOLD`/`d5b8324f9` — the #2804 scaffold-marker + accepted-evidence framing is
  unowned. Not a duplicate (C-003). ~6 tests is the right bound; keep the docstring cross-ref.
- Target name `tests/merge/test_gate_artifact_merge_drivers_2804.py` free to reclaim (deleted by
  `b04da00e1`, absent today). The deleted file's fill-score functions are gone from `src/` → verbatim
  restore impossible; row-union re-framing is correct.
- C-002 / #3231 respected: no assertion demands `pass` on an admitted-scaffold input; `pending` stays
  admissible. No brownfield fold (integration marker C-001 out; #3231 separate).

## Verdict
Design legitimate; A1/A2/A4/A5 achievable as specified (with the caveats above). **A3 must be reframed
(equal `pass_fail`, divergent non-None evidence; assert `pending`) and its control restated (take-theirs
→ handle disappears) BEFORE /tasks**, or the gate reds on its own first run. Spec FR-003 / scenario-3
text ("survives inside a conflict marker", "verdict admissible/never fail") is CORRECT and unchanged —
the defect was the plan's fixture-level construction, now fixed in IC-01.
