# Tasks: Gate-Artifact Merge Driver Unit Gate

**Mission**: `gate-artifact-merge-driver-unit-gate-01KZPG7V` | **Branch**: `fix/gate-artifact-merge-driver-unit-gate`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Authoritative squad remediation**: [post-plan-squad-findings.md](./post-plan-squad-findings.md) — the
corrected A3/A4 fixtures and controls are binding.

One work package: restore the #2804 driver-level unit gate as a fast in-memory overlay over the
row-union reconcilers. No product code, no arch-guard co-evolution.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Module scaffold: imports, `ACCEPTED_EVIDENCE_HANDLE`/`ADMISSIBLE_MERGED_VERDICTS`, FILLED/PLACEHOLDER fixtures, docstring cross-ref to the sibling (C-003), + A6 two-way fixture self-control | WP01 | |
| T002 | A1 + A2 — clean-merge survival (filled not reset to scaffold, marker absent, verdict `pass`) + take-theirs/all-scaffold controls | WP01 | |
| T003 | A3 — evidence survives inside a conflict marker (equal `pass_fail`, divergent non-None evidence → verdict `pending`) + take-theirs→handle-disappears control | WP01 | |
| T004 | A4 — admissible-verdict domain, disjoint add/add (`pending`, both rows, handle survives) + invalid-`pass_fail`→`fail` non-vacuity control | WP01 | |
| T005 | A5 — issue-matrix terminal-verdict + evidence_ref survival + take-theirs control + inline "no verdict recompute" note | WP01 | |
| T006 | Hoist S1192 repeated literals → named constants in `hand_authored_overlay.py` (36) | WP02 | [P] |
| T007 | Verify WP02 behavior-preserving (tests green, ruff/mypy, Sonar S1192→0) | WP02 | |
| T008 | Extract tested helpers for the 7 tractable S3776 doctrine functions (≤15 target) | WP03 | [P] |
| T009 | Hoist `extractor.py`'s single S1192 dup-literal → constant | WP03 | |
| T010 | (reserved — minors are WP04) | WP03 | |
| T011 | Focused helper tests + verify `tests/doctrine/` green | WP03 | |
| T012 | S6353 concise regex `[A-Za-z0-9_]`→`\w` (`org_pack_config.py:71`) | WP04 | [P] |
| T013 | S7632 fix/remove malformed suppression comment (`artifact_kinds.py:118`) | WP04 | |
| T014 | S117 rename local var (`glossary_hook.py:134`) | WP04 | |

Record completion with `spec-kitty agent tasks mark-status <Txxx> --status done`.
`[P]` marks parallel-safe work across WPs; the four WPs touch disjoint files (lanes).

---

## WP01 — Restore the #2804 driver-level unit gate (row-union)

**Prompt**: [tasks/WP01-restore-2804-driver-unit-gate.md](./tasks/WP01-restore-2804-driver-unit-gate.md)
**Priority**: P1 | **Dependencies**: none | **Requirements**: FR-001, FR-002, FR-003, FR-004, FR-005,
NFR-001, NFR-002, NFR-003, C-001, C-002, C-003 | **Estimated prompt size**: ~260 lines

**Goal**: Recreate `tests/merge/test_gate_artifact_merge_drivers_2804.py` with ~6 unit tests that call
the pure reconcilers `reconcile_acceptance_matrix_documents` / `reconcile_issue_matrix_documents`
directly (in-memory, no git/subprocess), pinning the #2804 invariant against the row-union model: a
filled/accepted criterion is never reset to `SCAFFOLD_TODO_MARKER`, the accepted evidence handle
survives (including inside a structured conflict marker), and the merged `overall_verdict` stays in
`{pass, pending, pass_pending_consolidation}` (never `fail`). Each invariant has a genuinely-falsifying
negative control (NFR-002).

**Independent test**: `python -m pytest tests/merge/test_gate_artifact_merge_drivers_2804.py -q` → all
green, `pytest.mark.unit` only, < 5 s.

**Included subtasks**: T001, T002, T003, T004, T005

**Implementation sketch**:
1. Scaffold module + fixtures + fixture self-control (T001).
2. Clean-merge survival A1/A2 (T002); conflict-marker survival A3 (T003); verdict domain A4 (T004);
   issue-matrix survival A5 (T005) — each with its control.

**Risks**: the A3 false-red trap (use equal `pass_fail` + divergent non-None evidence — see the tracer);
asserting marker-absence on A3 (wrong — only A1); demanding `pass` on an admitted-scaffold row (would
encode #3231, forbidden); over-broadening into the sibling's general row-union contract (C-003).

---

## WP02 — Clear S1192 dup-literals in doctrine overlay

**Prompt**: [tasks/WP02-doctrine-overlay-dup-literals.md](./tasks/WP02-doctrine-overlay-dup-literals.md)
**Priority**: P2 | **Dependencies**: none | **Requirements**: FR-006, NFR-004, NFR-005, C-004
**Goal**: Hoist the 36 `S1192` repeated literals in `src/doctrine/drg/migration/hand_authored_overlay.py`
to named module constants (behavior-preserving, no suppressions). **Included**: T006, T007.

## WP03 — Reduce tractable S3776 complexity in doctrine

**Prompt**: [tasks/WP03-doctrine-complexity-reduction.md](./tasks/WP03-doctrine-complexity-reduction.md)
**Priority**: P2 | **Dependencies**: none | **Requirements**: FR-006, FR-007, NFR-004, NFR-005, C-004
**Goal**: Extract tested helpers to bring the 7 tractable `S3776` doctrine functions toward ≤15
(behavior-preserving), + hoist `extractor.py`'s S1192. `extractor.py:545` (183) DEFERRED.
**Included**: T008, T009, T010, T011. (Heaviest WP — `versioning.py:316` at complexity 65 is the hardest.)

## WP04 — Resolve remaining doctrine minor smells

**Prompt**: [tasks/WP04-doctrine-minor-smells.md](./tasks/WP04-doctrine-minor-smells.md)
**Priority**: P3 | **Dependencies**: none | **Requirements**: FR-008, NFR-004, NFR-005, C-004
**Goal**: Fix the 3 minors (`S6353` regex, `S7632` suppression syntax, `S117` naming).
**Included**: T012, T013, T014.

---

## MVP scope

WP01 (#2804 unit gate) is the correctness core. WP02–WP04 are opportunistic doctrine Sonar cleanup folded
into the same PR; all four WPs touch disjoint files and can proceed in parallel lanes.
