# Implementation Plan: Gate-Artifact Merge Driver Unit Gate

**Branch**: `fix/gate-artifact-merge-driver-unit-gate` | **Date**: 2026-08-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/gate-artifact-merge-driver-unit-gate-01KZPG7V/spec.md`

## Summary

Restore the driver-level unit gate `tests/merge/test_gate_artifact_merge_drivers_2804.py` (deleted by
`b04da00e1`) as a narrow, fast, in-memory overlay that pins the #2804 invariant against the **#3076
row-union authority model**. The gate calls the pure reconcilers
`reconcile_acceptance_matrix_documents` and `reconcile_issue_matrix_documents`
(`src/specify_cli/cli/commands/merge_driver.py`) directly — no git repo, no `spec-kitty
merge-driver-*` subprocess, no `pip install -e .`. It closes the driver-level ownership gap the
existing coverage leaves: the integration marker
(`tests/merge/test_issue_2804_merge_resets_gate_artifacts.py`) is a ~160 s subprocess test, and the
row-aware sibling (`tests/specify_cli/cli/commands/test_row_aware_merge_driver.py`) exercises the
general row-union contract but never the #2804-specific scaffold-vs-filled + accepted-evidence framing.
Full pre-spec research: [research.md](./research.md) (and scoping brief in scratchpad
`3232-scoping-brief.md`).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest (unit); the shipped reconcilers under `specify_cli.cli.commands.merge_driver` and constants from `specify_cli.acceptance.matrix`
**Storage**: N/A (in-memory JSON dicts as fixtures)
**Testing**: `tests/merge/test_gate_artifact_merge_drivers_2804.py` (new/restored), `pytest.mark.unit` only; runnable via `python -m pytest tests/merge/test_gate_artifact_merge_drivers_2804.py -q`
**Target Platform**: CI unit lane (`fast-tests-merge` via the `merge` dorny group) + local
**Project Type**: single (test-only; no product code change)
**Performance Goals**: whole file < 5 s (NFR-003); no I/O, no subprocess
**Constraints**: pure in-memory (NFR-001); every invariant paired with a negative control (NFR-002); do not touch the integration marker (C-001); admit `pending`, do not fix #3231 (C-002); overlay not duplicate, cross-reference the sibling (C-003)
**Scale/Scope**: ~6 unit tests in one file; no source, no arch-guard, no fixture-corpus changes

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **ATDD-first / test-remediation discipline**: PASS — this mission *is* test restoration; it re-pins a
  real behavioral invariant (no-reset-to-scaffold + evidence survival) that lost its driver-level owner.
  It is red-provable: mutating the reconciler to take-theirs, or the fixture to all-scaffold, reds the gate.
- **Canonical sources / no hand-rolled equivalents**: PASS — the gate calls the *shipped* reconcilers
  directly; it does not re-implement or copy merge logic. Fixtures use the real `SCAFFOLD_TODO_MARKER`
  and `VERDICT_PASS_PENDING_CONSOLIDATION` constants from `specify_cli.acceptance.matrix`.
- **Refactor-stable / behavioral invariants, not code shape**: PASS — the assertions pin observable
  merge behavior (document contents, verdict domain), not the reconciler's internal structure.
- **No false-green / no vacuous test**: PASS — NFR-002 mandates a negative control per invariant plus a
  two-way fixture self-control on the evidence handle, so no assertion can pass silently
  unsatisfiable or vacuous.
- **Scope discipline**: PASS — one test file; the integration marker and the #3231 product defect are
  explicitly out of scope (C-001, C-002).

No charter violations. No Complexity Tracking entries required.

## Project Structure

### Documentation (this mission)

```
kitty-specs/gate-artifact-merge-driver-unit-gate-01KZPG7V/
├── plan.md
├── spec.md
├── research.md          # Phase 0 — reconciler surface + assertion design (from the scoping brief)
├── quickstart.md        # Phase 1 — how to run + falsify the gate
└── tasks.md             # Phase 2 (/spec-kitty.tasks)
```

(No `data-model.md` / `contracts/` — this mission introduces no new entities or API surfaces; it tests
existing pure functions.)

### Source (repository root)

```
tests/merge/
└── test_gate_artifact_merge_drivers_2804.py   # RESTORED — ~6 unit tests over the row-union reconcilers
```

**Structure Decision**: Single project, test-only. No product code, no arch-guard co-evolution (the
reconcilers are already imported by the sibling → not dead; `tests/merge/` has no file-count ratchet).

## Implementation Concern Map

> Concerns are not work packages. `/spec-kitty.tasks` maps these to WPs. This mission is narrow enough
> that a single WP is expected. Authoritative research: [research.md](./research.md).
>
> **⚠️ Post-plan squad remediation is AUTHORITATIVE — see
> [post-plan-squad-findings.md](./post-plan-squad-findings.md).** Two lenses exercised the real
> reconcilers and found A3 as first drafted was a FALSE RED (`fail`, not admissible). The corrected A3
> fixture (equal `pass_fail`, divergent non-None evidence → `pending`), the corrected A3 control
> (take-theirs → handle disappears), the disjoint A4 fixture, and the A1/A5 caveats below are binding.

### IC-01 — The #2804 invariant assertions (acceptance + issue matrix)

- **Purpose**: pin, at reconciler-unit level, that a filled/accepted criterion is never reset to
  `SCAFFOLD_TODO_MARKER`, the accepted evidence handle survives (incl. inside a conflict marker), and
  the merged verdict stays admissible.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004, FR-005.
- **Affected surfaces**: NEW `tests/merge/test_gate_artifact_merge_drivers_2804.py`. Imports
  `reconcile_acceptance_matrix_documents` / `reconcile_issue_matrix_documents` from
  `specify_cli.cli.commands.merge_driver`; `SCAFFOLD_TODO_MARKER` + `VERDICT_PASS_PENDING_CONSOLIDATION`
  from `specify_cli.acceptance.matrix`. Module const `ACCEPTED_EVIDENCE_HANDLE = "d5b8324f9"` (cross-refs
  the integration marker's handle); `ADMISSIBLE_MERGED_VERDICTS = {"pass", "pending", pass_pending_consolidation}`.
- **Assertions (CORRECTED per post-plan squad; each with a negative control — see IC-02)**:
  - A1 base-present clobber, fill on `ours` (theirs==base scaffold): merged=filled, handle present,
    marker absent in that criterion, verdict `pass`. **Caveat:** the filled `ours` fixture must carry
    `SCAFFOLD_TODO_MARKER` in NO field (description AND notes both real) — the scaffold writes it into both.
  - A2 reverse ordering, fill authored in `theirs` (ours==base): fill + handle survive, verdict `pass`.
  - A3 no-base add/add, **equal `pass_fail` (both `pending`), divergent evidence** (ours=handle,
    theirs=`"TODO: evidence"` — non-None, ≠ handle): no raise; handle in `json.dumps(merged)`; a conflict
    marker (`<<<<<<< ours`) is present in the merged AC-001 evidence field; verdict `pending`
    (∈ ADMISSIBLE, ≠ `fail`). **NOTE:** divergent `pass_fail` (pass-vs-pending) would conflict that field
    and recompute to `fail` — do NOT use that fixture; keep `pass_fail` equal (F1).
  - A4 admissible-verdict domain, **disjoint add/add** (base `{}`, ours=filled AC-001, theirs=scaffold
    AC-002): both rows present, handle survives, verdict `pending` (∈ ADMISSIBLE, ≠ `fail`).
  - A5 issue-matrix terminal survival (base row `unknown`, one side terminal+evidence_ref, theirs==base):
    merged row verdict ≠ `unknown`, evidence ref survives. **Note:** the issue reconciler does NO verdict
    recompute — pure field-union; add an inline comment. Schema `{"rows": {ref: {...}}}`.
- **Sequencing/depends-on**: none.
- **Risks**: (F1) A3 with divergent `pass_fail` reds correct code (`fail`) — use equal `pass_fail` +
  divergent non-None evidence. Asserting `SCAFFOLD_TODO_MARKER` *absence* is correct ONLY for A1 (the
  clean theirs==base case); A3's conflict marker legitimately contains scaffold text, so A3 asserts handle
  *survival*, not marker absence.

### IC-02 — Anti-vacuity: negative controls + fixture self-control (NFR-002)

- **Purpose**: guarantee each invariant is falsifiable and no fixture makes an assertion vacuous.
- **Relevant requirements**: NFR-002; SC-002.
- **Affected surfaces**: same test file.
- **Details**:
  - A6 two-way fixture self-control: `ACCEPTED_EVIDENCE_HANDLE in json.dumps(FILLED)` and
    `not in json.dumps(PLACEHOLDER)`, for both the acceptance and issue fixtures.
  - Per-assertion negative controls: A1/A2 → take-theirs/take-ours (or all-scaffold) mutation makes the
    scaffold win → handle absent + marker present → red. **A3 control (CORRECTED, F2/F3): take-theirs
    (drop `ours`) → the accepted evidence handle disappears from `json.dumps(merged)` → red** (NOT the old
    "verdict ≠ fail" framing, which collides with A4). A4's non-vacuity control = a genuinely invalid
    `pass_fail` recomputes to `fail` (proving the domain assertion bites). A5 → take-theirs (==base) drops
    the terminal verdict + evidence_ref.
- **Sequencing/depends-on**: co-located with IC-01.
- **Risks**: none beyond keeping controls tight; `pending` MUST stay admissible (C-002) — a control that
  demanded `pass` would encode the #3231 product fix and is forbidden.

### IC-03 — Overlay hygiene (C-003)

- **Purpose**: keep the gate a #2804-specific overlay, not a duplicate of the general row-union sibling.
- **Affected surfaces**: module docstring cross-references
  `tests/specify_cli/cli/commands/test_row_aware_merge_driver.py` and states the #2804 framing (scaffold
  marker + accepted evidence handle) that the sibling does not cover, so a future reader does not cull it.
- **Risks**: over-broadening into general row-union assertions the sibling already owns — keep to ~6 tests.

### IC-04 — Doctrine Sonar-HIGH + minor remediation (folded, WP02–WP04)

- **Purpose** (operator decision): opportunistically clear the doctrine module's Sonar backlog in this PR
  since the #2804 gate is a single small WP. 48 findings, all code smells: 37 `S1192` dup-literals, 8
  `S3776` complexity (7 tractable + `extractor.py:545`/183 DEFERRED), 3 minors (`S6353`/`S7632`/`S117`).
- **Relevant requirements**: FR-006, FR-007, FR-008; NFR-004 (behavior-preserving), NFR-005 (no
  suppressions); C-004 (scoped to `src/doctrine/`; `extractor.py:545` out).
- **WP split (by file, disjoint owners → 4 parallel lanes)**:
  - **WP02** — `hand_authored_overlay.py` S1192 sweep (36): hoist repeated literals to named constants.
  - **WP03** — the 7 tractable S3776 functions + `extractor.py`'s 1 S1192: extract tested helpers toward
    ≤15, behavior-preserving; owns `tests/doctrine/**` for the helper tests. Heaviest WP
    (`versioning.py:316`/65 is the hardest; partial-reduction-with-documented-residual allowed, never suppressed).
  - **WP04** — the 3 minors (`org_pack_config.py`, `artifact_kinds.py`, `glossary_hook.py`).
- **Sequencing/depends-on**: independent of WP01 and of each other (disjoint files).
- **Risks**: behavior drift in the S3776 refactors (mitigate: read+run existing tests before/after);
  `extractor.py` bundled wholly in WP03 to avoid S1192/S3776 owner overlap; the deferral of
  `extractor.py:545` (183→15 is a mission-sized restructure) is explicit.
