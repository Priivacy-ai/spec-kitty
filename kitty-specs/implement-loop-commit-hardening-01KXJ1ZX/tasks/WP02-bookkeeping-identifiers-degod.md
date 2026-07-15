---
work_package_id: WP02
title: '#2649 — degod _resolve_bookkeeping_transaction_identifiers (C-006 symbol)'
dependencies:
- WP01
requirement_refs:
- C-006
- C-008
- FR-003
- NFR-001
- NFR-002
- NFR-004
tracker_refs:
- '2649'
planning_base_branch: mission/2533-pr-bound-coord-claim-precondition
merge_target_branch: mission/2533-pr-bound-coord-claim-precondition
branch_strategy: Planning artifacts for this mission were generated on mission/2533-pr-bound-coord-claim-precondition. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/2533-pr-bound-coord-claim-precondition unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2614085"
shell_pid_created_at: "1784120783.06"
history:
- at: '2026-07-15T07:36:38Z'
  actor: claude
  note: Carved from IC-02 so the C-006 5-tuple contract lands at Lane-A unit 2; WP07 depends_on this WP.
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- tests/specify_cli/cli/commands/test_implement_bookkeeping_identifiers.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/implement.py
- tests/specify_cli/cli/commands/test_implement.py
- tests/specify_cli/cli/commands/test_implement_bookkeeping_identifiers.py
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

Reduce the Sonar S3776 cognitive complexity of
`_resolve_bookkeeping_transaction_identifiers` (`implement.py:353-423`, ≈16) by extracting
module-private helpers — **without changing its public signature or its 5-tuple return
shape**. This function is imported and called cross-lane by `tasks_move_task.py:1382/1392`
(C-006); its contract is frozen here so the Lane B degod (WP07) can rely on it.

## Context — READ BEFORE CODING

- **Brownfield / characterization-first (DM-D, NFR-002):** pin the implicit invariants in
  tests BEFORE extracting. This function has value-level fallbacks that are easy to reorder
  by accident.
- **C-006 cross-lane coupling:** `tasks_move_task.py` imports
  `_resolve_bookkeeping_transaction_identifiers`, `_feature_dir_file_paths`,
  `_planning_artifact_source_dir` from `implement.py` (import block `:1381-1385`). The
  cross-lane call site at `:1392` takes only element `[0]` (`coord_branch`), but the in-module
  caller unpacks all five `(coord_branch, mission_id, mid8, effective_mission_id,
  effective_mid8)` — so the **5-tuple return shape + arity** MUST be preserved (a reshape
  would break the in-module unpack even though the cross-lane consumer only reads `[0]`).
  **WP07 declares a hard `depends_on: WP02`** so it never integrates against a reshaped contract.
- **C-008 / NFR-004:** all extracted helpers stay module-private (`_`-prefixed); no net-new
  public/exported symbol.
- Gate note: this function already passes `ruff C901` (cyclomatic ≈6); the target is S3776
  (advisory-post-merge). The enforceable local acceptance is the extraction + the
  characterization/contract tests + behavior preservation.

## Subtasks

### T006 — Characterization tests FIRST (pin the invariants)

Create `tests/specify_cli/cli/commands/test_implement_bookkeeping_identifiers.py` pinning
the CURRENT behavior before extraction:
1. **Cascade order** — the primary-dir-first resolution order is preserved.
2. **Ambiguous-handle RAISE** — an ambiguous mission handle raises (does not silently pick).
3. **`legacy-<slug>` fallback** — a missing mission id yields `effective_mission_id =
   f"legacy-{mission_slug}"` (`implement.py:411`).
4. **mid8 precedence** — `meta["mid8"]` > `resolve_mid8(...)` > `None`, then
   `resolve_transaction_mid8(...)` (`implement.py:403-422`).

**Validation**: all four pass against the current, un-refactored function.

### T007 — Consumer-side import-contract test (freeze C-006)

1. In the same test file, add a test that imports the three symbols the way
   `tasks_move_task.py` does and asserts: `_resolve_bookkeeping_transaction_identifiers`
   returns a length-5 tuple and each **positional value** matches a known fixture
   (`result[0] == expected_coord_branch`, `result[3] == effective_mission_id`, …) — a bare
   tuple has no field names, so pin positions against T006's fixtures, not `inspect.signature`.
   Also assert `_feature_dir_file_paths` / `_planning_artifact_source_dir` keep their
   current signatures.
2. This is the hard C-006 gate — it must stay green through the extraction AND through WP07.

**Validation**: the contract test passes; it would fail if the 5-tuple arity/order changed.

### T008 — Extract module-private helpers (behavior-preserving)

1. Decompose the id/mid8 resolution cascade into small `_`-prefixed helpers to lower S3776.
2. Keep the public signature + 5-tuple return byte-for-byte identical.

**Validation**: T006 + T007 stay green; no public symbol added.

### T009 — Gate clean

1. `ruff` + `mypy --strict` zero new issues; existing `implement` suite green.

**Validation**: clean gate; characterization + contract tests green.

## Branch Strategy

Planning branch / final merge target: **mission/2533-pr-bound-coord-claim-precondition**.
Lane A, after WP01. WP07 (Lane B) depends on this WP for the C-006 contract.

## Definition of Done

- `_resolve_bookkeeping_transaction_identifiers` decomposed, S3776 reduced, signature +
  5-tuple preserved (C-006, FR-003).
- Characterization (T006) + consumer contract (T007) tests green and enduring.
- No net-new public symbol (C-008, NFR-004); `ruff` + `mypy --strict` clean (NFR-001).

## Risks & Reviewer Guidance

- Reviewer MUST run the T007 contract test and confirm the 5-tuple arity/order is unchanged
  — this is the load-bearing cross-lane contract WP07 relies on.
- Watch for accidental reordering of the mid8 precedence or the `legacy-<slug>` fallback
  under extraction (T006 guards these).

## Activity Log

- 2026-07-15T12:55:23Z – claude:sonnet:python-pedro:implementer – shell_pid=2573191 – Started implementation via action command
- 2026-07-15T13:05:54Z – claude:sonnet:python-pedro:implementer – shell_pid=2573191 – Ready for review: bookkeeping degod, 5-tuple frozen + consumer contract test
- 2026-07-15T13:06:25Z – claude:opus:reviewer-renata:reviewer – shell_pid=2614085 – Started review via action command
- 2026-07-15T13:09:28Z – user – shell_pid=2614085 – Review passed: C-006 5-tuple preserved (return coord_branch,mission_id,mid8,effective_mission_id,effective_mid8 unchanged; consumer[0] + in-module 5-unpack both satisfied). Behavior-preserving extraction into 4 module-private helpers (_load_primary_anchored_mission_meta/_load_fallback_mission_meta/_extract_mission_identifiers_from_meta/_compute_effective_bookkeeping_ids); ambiguous-handle raise still propagates (canonicalize outside try). T006 characterization (cascade primary-first, ambiguous RAISE, legacy-<slug> fallback, mid8 precedence) + T007 positional contract test both concrete & durable. 29 tests green (incl WP01), ruff + mypy --strict clean. No net-new public symbol (C-008/NFR-004). Scope: implement.py + new test file only.
