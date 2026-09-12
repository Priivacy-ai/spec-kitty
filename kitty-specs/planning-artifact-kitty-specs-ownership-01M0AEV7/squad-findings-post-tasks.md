# Post-tasks adversarial squad — convergent findings

Point-cut: post-tasks (anti-laziness / decomposition-realism / implementer-feasibility). Three
profile-loaded, read-only lenses. **Verdict: WP01 is ready to implement**, decomposition sound
(one `code_change` WP is correct — ATDD forbids severing the red-first test), every named seam
verified against source. The lenses found cheap, required tightenings, all folded into WP01.

## reviewer-renata (anti-laziness)
- **R1 [HIGH, required]** — T001 could pass green-both-times if inference resolves to `docs/`-only
  ownership (never trips the kitty-specs ban); exit-0 + planning-lane placement don't rule it out.
  **Folded**: T001 now asserts the finalized `owned_files` contains a `kitty-specs/` entry.
- **R2 [MEDIUM, required]** — SC-004/FR-006 mandate the paired accept/reject on one flipped fixture;
  it was "if useful". **Folded**: T003 promotes it to required.
- **R3 [MEDIUM]** — DoD overstated decision-table coverage (6 of 9 rows); row 4 (kitty-specs +
  `scripts/` → REJECT) untested. **Folded**: T003 adds the `scripts/` case; DoD corrected.
- **R4 [MEDIUM]** — FR-005 (out-of-planning WARNING preserved) had no assertion. **Folded**: T003 adds
  a direct `validate_execution_mode_consistency` unit test.
- **R5 [LOW]** — name the T004 read-back API. **Folded**: T004 names both seams (written frontmatter /
  `state.would_modify`).

## planner-priti (decomposition/scope/tracker)
- **P1 [PASS]** — one `code_change` WP is the right call (ATDD); 8 subtasks earned (one per
  decision-table row/guardrail); `dependencies: []` correct; #3214/#3432 cleanly scoped out with a
  regression tripwire (T001's planning-lane assertion).
- **P2 [MEDIUM]** — the A-4 follow-up was a soft "PR body and/or issue" (could land untracked).
  **Folded**: T008 hardens it to a REQUIRED tech-debt issue at merge, referenced in the PR body.
- **P3 [LOW]** — `mission_finalize.py` ownership is borderline padding but justified by the
  confirm-hedge; prompt-size estimate drift. **Folded**: estimate reconciled; ownership kept.

## python-pedro (implementer feasibility) — implementable, with-caveats
- **Verified empirically**: `_PLANNING_PREFIXES`/`ExecutionMode` import from `ownership.validation`
  with no cycle; `WPMetadata.execution_mode` is `str|None` (so `.value` compare is correct, `None →
  "None"` fail-closed); inference→ban ordering holds (no `mission_finalize.py` change); durability
  kinds (`analysis-report.md`→ANALYSIS_REPORT managed, `disposition-matrix.md`→None durable);
  complexity ~5 (helper optional). No blockers.
- **PQ5 [caveat, blessed]** — confinement must normalize each `owned_files` entry with
  `_normalize_owned_file_path` before the prefix check (the ban predicate matches on normalized
  paths; a raw `startswith` would false-reject a `./kitty-specs/…`-spelled planning WP). **Folded**:
  T002 blesses normalize-before-check; T003 adds the `./`-spelled fixture.
- **Concrete recipes folded**: T001 surface+create_intent with a non-managed filename + overridden
  `authoritative_surface`; T004 inference via field-absent (not `owned_files: []`) + zero code tokens;
  T007 quotes the real durability authorities.

Adversarial-evidence contract: no contested finding dropped. All findings were refinements; none
blocked. WP01 DoD is now non-gameable on every requirement.
