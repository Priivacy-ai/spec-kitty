---
work_package_id: WP04
title: '#2650 — characterization gate + read/write primary-ref unification (FR-006 + FR-005 ref half)'
dependencies:
- WP03
requirement_refs:
- C-007
- C-008
- C-009
- FR-005
- FR-006
- NFR-001
- NFR-002
- NFR-003
tracker_refs:
- '2650'
planning_base_branch: mission/2533-pr-bound-coord-claim-precondition
merge_target_branch: mission/2533-pr-bound-coord-claim-precondition
branch_strategy: Planning artifacts for this mission were generated on mission/2533-pr-bound-coord-claim-precondition. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/2533-pr-bound-coord-claim-precondition unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
- T020
- T021
- T022
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2753343"
shell_pid_created_at: "1784123679.2"
history:
- at: '2026-07-15T07:36:38Z'
  actor: claude
  note: Gate (FR-006) and cli-side ref-unification (FR-005 ref half) are one WP so the document-first gate is NOT a separate mid-chain lane (avoids a lane cycle). WP05 (commit_router classifier) depends on this WP.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- tests/specify_cli/coordination/test_partition_authority_characterization.py
- tests/specify_cli/cli/commands/test_precondition_ref_unification.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/implement.py
- src/specify_cli/cli/commands/implement_cores.py
- tests/specify_cli/coordination/test_partition_authority_characterization.py
- tests/specify_cli/cli/commands/test_precondition_ref_unification.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its identity, governance scope, boundaries, and initialization declaration.
You are the **implementer**.

## Objective

Two coupled halves, in document-first order (DM-D):
1. **Characterization gate (FR-006):** pin — in tests — the current behavior of the three
   partition-decision sites, the `kind=None` disagreement set, and the flat/legacy
   `placement_ref=None`-at-seam behavior, BEFORE any consolidation swap.
2. **Read/write primary-ref unification (FR-005, ref half):** derive the read-side
   (`resolve_precondition_ref`, `"HEAD"`) and write-side (`_partition_files_for_commit`,
   `planning_branch`) primary ref from ONE cli-local expression so they agree by
   construction — this is the `implement.py`/`implement_cores.py` half of FR-005.

The characterization gate lives in THIS WP (not a separate lane) so the document-first
contract is established in the same execution surface as the cli-side swap, and WP05's
`commit_router` classifier swap can depend on a single gate.

## Context — READ BEFORE CODING

- The three sites (`../data-model.md` has the table):
  - `implement.py::_partition_files_for_commit` (write) — residue predicate → PRIMARY.
  - `implement_cores.py::resolve_precondition_ref` (read, `"HEAD"`) — residue predicate → PRIMARY.
  - `coordination/commit_router.py::_group_files_by_partition` (write) —
    `kind_for_mission_file(file) or kind` → caller partition (can be COORD). The #2533 hole.
- **Disagreement set** = **every non-coord-residue path bundled under a coord-kind caller →
  must route PRIMARY** (recognized-coord paths already agree; they disagree only on
  `kind=None` — `meta.json`, primary-source, unrecognized — under a coord caller). C-007.
- **C-009:** the ref unification MUST preserve the WP00 anchored-primary-surface resolution
  and the narrow-triple fail-close (WP01). Do NOT reintroduce a silent fallback to the
  default branch (`main`). `kind=None`→PRIMARY resolves to the auto-detected `HEAD`/anchored
  `target_branch`, NEVER the primary/default branch.
- **Boundary:** this WP does NOT touch `commit_router.py` (that is WP05). `mission_runtime/*`
  stays read-only. Extracted helper(s) are module-private (C-008, no net-new public symbol).

## Subtasks

### T015 — Gate: enumerate + pin the three sites' current partition decisions

1. In `tests/specify_cli/coordination/test_partition_authority_characterization.py`, for a
   representative path set (a coord-residue path, a PRIMARY path like `spec.md`, `meta.json`,
   an unrecognized path), assert each of the three sites' current PRIMARY/COORD decision.

**Validation**: each site's current decision is a live snapshot in the suite.

### T016 — Gate: pin the disagreement set → PRIMARY

1. Assert `is_coordination_artifact_residue_path` routes the `kind=None` set to PRIMARY.
2. Document (assert current) that `commit_router`'s `kind_for_mission_file(...) or kind`
   routes those to the caller partition (can be COORD) — the divergence WP05 removes.

**Validation**: disagreement captured as "non-coord path under coord caller → COORD today,
PRIMARY after FR-005".

### T017 — Gate: characterize the flat/legacy None-at-seam behavior (confirm WP01's triple)

1. Assert a real flat/legacy mission's `placement_ref=None` reaches the `755`/`790` SUCCESS
   arms — NOT the narrow triple. Pins that WP01 fail-closes only on the narrow triple, not
   bare `None` (INV-7, #2463 None-overload).

**Validation**: the flat/legacy `None` path is characterized as success.

### T018 — Gate: pin the intended unified contract (cli-side only)

1. Add the intended-contract assertions **this WP owns and turns green** (via T019-T021):
   the read (`resolve_precondition_ref`) and write (`_partition_files_for_commit`) cli-side
   sites route `kind=None`→PRIMARY and agree on the primary ref by construction.
2. Do **NOT** plant `commit_router`-side assertions here as `xfail`-pending-WP05. That is a
   broken cross-lane handoff: WP05 is a different lane and does not own this test file, so it
   cannot flip the markers — and with `xfail_strict` unset they would silently XPASS forever.
   The `commit_router`-side structural contract is owned by **WP05 T024** (authored
   fresh-green in `test_commit_router_partition_authority.py`).

**Validation**: the cli-side intended-contract assertions exist (turn green in T021); no
`xfail`-pending WP05 markers in this file.

### T019 — Ref-unif: extract the shared primary-ref expression

1. Introduce one cli-local `_`-prefixed helper yielding the primary ref, and have BOTH
   `resolve_precondition_ref` (read) and the write-side commit path derive their primary ref
   from it — removing the independent `"HEAD"` literal vs `planning_branch` choice.

**Validation**: `ruff` + `mypy --strict` clean; a single source of the cli-side primary ref.

### T020 — Ref-unif: structural + detached-HEAD regression test

1. In `tests/specify_cli/cli/commands/test_precondition_ref_unification.py`: assert read and
   write derive the primary ref from the one expression (no independent `"HEAD"` literal
   remains in the read path); regression a detached-HEAD / off-target-branch claim no longer
   risks read/write disagreement.

**Validation**: the unification + detached-HEAD tests are green.

### T021 — Ref-unif: turn the gate's cli-side intended-contract assertions green + regressions

1. Turn green the T018 assertions this WP owns (read/write agree by construction on the cli
   side). Re-run #2533 + WP01 narrow-triple + the 3 write-side `None` cases — all green.

**Validation**: cli-side unified contract green; named regressions green.

### T022 — Gate clean

1. `ruff` + `mypy --strict` zero new issues; `implement` suite green.

**Validation**: clean gate.

## Branch Strategy

Planning branch / final merge target: **mission/2533-pr-bound-coord-claim-precondition**.
Lane A tail (implement.py chain), after WP03. Gates WP05 (commit_router classifier swap).

## Definition of Done

- The characterization gate (three sites + disagreement set + flat/legacy None-at-seam) is
  pinned (FR-006, NFR-002, NFR-003).
- Read (`"HEAD"`) and write (`planning_branch`) primary ref derive from one cli-local
  expression (FR-005, ref half); `commit_router` untouched.
- C-009 preserved (no default-branch fallback; narrow-triple fail-close intact); no net-new
  public symbol (C-008); `ruff` + `mypy --strict` clean (NFR-001).
- The intended `kind=None`→PRIMARY contract (C-007) is expressed and **green** for the two
  cli-side sites; the `commit_router`-side contract is owned by WP05 T024 (no cross-lane
  xfail markers here).

## Risks & Reviewer Guidance

- Frame the disagreement set as "non-coord path under a coord caller" (not merely
  `meta.json`) — else a future coord-kind caller re-diverges past the test (squad RISK-4).
- Confirm the ref unification did NOT reintroduce a default-branch (`main`) fallback and the
  WP01 narrow-triple fail-close still fires (C-009).

## Activity Log

- 2026-07-15T13:31:27Z – claude:sonnet:python-pedro:implementer – shell_pid=2685917 – Started implementation via action command
- 2026-07-15T13:53:22Z – claude:sonnet:python-pedro:implementer – shell_pid=2685917 – Ready for review: char gate (non-coord-under-coord-caller set) + cli ref-unification; no cross-lane xfail; C-009 preserved
- 2026-07-15T13:54:41Z – claude:opus:reviewer-renata:reviewer – shell_pid=2753343 – Started review via action command
- 2026-07-15T13:58:03Z – user – shell_pid=2753343 – Review passed: char gate (FR-006) pins all 3 sites + frames disagreement set as non-coord-under-coord-caller (parametrized meta+unrecognized, RISK-4 addressed) + INV-7 flat/legacy None reaches 755 success via real git repo; AST xfail guard proves no cross-lane xfail, cli-side contract asserted GREEN; _primary_ref_for is single ref source for both read (resolve_precondition_ref, _files_changed_vs_precondition_ref) and write (755+790 arms), no independent HEAD literal survives outside helper; C-009 preserved (empty->HEAD not main, detached-HEAD regression proves write targets named branch); commit_router UNTOUCHED; WP01/02/03 surfaces unchanged; C-008 private (not in __all__); 98 tests green, ruff+mypy --strict clean.
