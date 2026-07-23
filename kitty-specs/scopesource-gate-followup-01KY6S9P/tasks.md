# Work Packages: ScopeSource gate follow-up — cleanup & correctness

**Mission**: `scopesource-gate-followup-01KY6S9P` · **Branch**: `fix/scopesource-gate-followup`
**Base**: merged main `eb06ca176` (#2874 coord-commit-integrity + #2820 dossier-parity landed) · **Closes**: #2873
**Design authorities**: [spec.md](./spec.md) (14 FR / 7 NFR / 6 C) · [plan.md](./plan.md) (15 ICs, IC-00..IC-14) · [research.md](./research.md) (D-1..D-6) · [data-model.md](./data-model.md) (file:line register) · [contracts/](./contracts/) · reviews: [post-spec](./reviews/post-spec-squad.md) · [fold/boyscout](./reviews/fold-boyscout-squad.md) · [post-plan](./reviews/post-plan-squad.md).

## Overview

Five work packages close the four #2873 follow-ups. The mission is **inherently serial** — it edits a
tightly-coupled 4-file cluster (`scope_source.py`, `baseline.py`, `pre_review_gate.py`,
`tasks_move_task.py`), so the decomposition is **file-partitioned** (each hot file owned by exactly one
WP, no overlapping `owned_files`) and **dependency-sequenced**. The single load-bearing safety net
(behavior-preservation goldens) lands FIRST; the ~450-LoC dead-census deletion is gated behind it.

```
WP01 (safety net) ──▶ WP02 (scope_source hub) ──▶ WP03 (baseline lifecycle+identity) ──▶ WP04 (prg deletion + SOURCE_MISMATCH) ──▶ WP05 (test migration + inventory)
```

There is little genuine parallelism here and the decomposition does not manufacture any: WP03 needs
WP02's factory+identity helper, WP04 needs WP02's predicates + WP03's identity field, WP05 needs WP04's
signature change. This is honest — the shared-file coupling is the reason.

**MVP / first-landable slice**: WP01 → WP02 → WP03 → WP04 closes the P1 correctness bug (US1 / SC-001 /
SC-004) and retires the dead duplicate. WP05 (test migration + committed inventory) is the coverage-parity
close-out that keeps NFR-004 green.

## Non-negotiables carried from the three squads (every WP honors these)

- **IC-00 lands FIRST** (WP01), BEFORE any deletion, via the **canonical** harness
  `tests/review/fixtures/parity/{_capture.py, ...}` + `tests/review/test_transition_gate_parity.py`
  **re-pinned to `eb06ca176`** (the harness currently pins the half-A base `e4ef6e850` — WP01 re-pins
  `_require_base_commit` and regenerates). `HEAD==base` assert + machine-emitted `base_commit`; the
  NFR-006 override golden MUST drive a **non-empty** scope. No improvised snapshot, no hand-typed SHA.
- **FR-014** (operator decision): `resolve_scope_source` SELECTS `DeclaredCommandScopeSource` when
  `review.test_command` is present/non-pytest, else `GateCoverageScopeSource` — makes SC-001 real, keeps
  `_capture_baseline_via_config` alive. Fix the stale `scope_source.py:51-55` comment + `review-gates.md:174`.
- **FR-008 B1 red-first carrier** = a **direct** `capture_baseline(DeclaredCommandScopeSource, worktree-
  relative --junitxml)` unit test, RED on base before the relocate fix (workflow path is dormant on base).
- **FR-004**: MIGRATE the 8 verdict-diff tests to `scope_source=` injection; MIGRATE FORWARD the
  mutation-bite (live-CI-topology) assertions of `test_pre_review_scope_singlesource.py` — it is NOT a
  duplicate. Committed coverage-parity inventory reviewed at gate.
- **FR-011**: `GateOutcome.SOURCE_MISMATCH` is WARN_PROCEED by allowlist — **assert**, do NOT edit the
  filters; add the console-ladder branch + defensive `else`. Compat golden **157→156**.
- **NFR-005** dual-root (`main_repo_root` vs `gate_repo_root`) `test_command()` equality + structural
  same-`scope_source_identity`-symbol assertion; `source_identity` excludes the command by design.
- **Keep-live set (C-002)**: `_CompositeRoute`, `evaluate_with_scope`, `run_scoped_tests_at_head`,
  `ScopeResult`, `_mt_pre_review_gate_with_override_scope`, `_mt_empty_scope_verdict`,
  `_pre_review_gate_filter_groups`/`_pre_review_gate_composite_routing`.
- **#2825 baseline-red-gotcha**: before attributing any `test_no_dead_symbols` / `test_golden_count_ban`
  failure to this diff, confirm it is pre-existing red on `eb06ca176` (`PYTHONPATH=<worktree>/src` vs
  `upstream/main`). Do NOT green-wash a category-1 pre-existing red.
- **Env**: prefix every `spec-kitty`/`pytest` with `PYTHONPATH=$(pwd)/src`.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Re-pin `_capture.py` `_require_base_commit` to `eb06ca176`; extend for override-tier capture | WP01 | |
| T002 | Capture NFR-001 registry-path golden (HEAD==base, machine-emit `base_commit`) | WP01 | |
| T003 | Capture NFR-006 override-tier golden driving a **non-empty** derived scope | WP01 | |
| T004 | Wire `test_transition_gate_parity.py` replay for both golden sets | WP01 | |
| T005 | IC-01 sole-live-caller characterization test (green-on-base) | WP01 | [P] |
| T006 | Hoist `resolve_scope_source` factory into `scope_source.py` (params, no cycle) | WP02 | |
| T007 | Add `scope_source_identity(scope_source, raw)` single-source helper | WP02 | [P] |
| T008 | Two independent predicates + distinct `ClassVar` marker (FR-005) | WP02 | [P] |
| T009 | `ScopeBreakdownMixin`; `GateCoverageScopeSource` inherits `file_to_scope` (FR-006) | WP02 | |
| T010 | Config-driven selection in `resolve_scope_source` (FR-014) + stale comment/doc fix | WP02 | |
| T011 | Migrate intent-encoding test onto the two predicates (FR-007) | WP02 | |
| T012 | NFR-005 dual-root equivalence + structural same-helper assertion | WP02 | |
| T013 | `source_identity` field on `BaselineTestResult` + `to_dict`/`from_dict` (FR-009) | WP03 | |
| T014 | Parse-before-teardown lifecycle fix + record identity (FR-008 / B1) | WP03 | |
| T015 | Inject shared factory into implement-time capture (FR-008) | WP03 | |
| T016 | B1 red-first **direct** capture unit test (worktree-relative `--junitxml`) | WP03 | |
| T017 | Anti-narrowing guard test (FR-012 / C-005) | WP03 | [P] |
| T018 | `baseline.py` boyscout: drop `timezone` import + tighten `ruff.toml` (FR-013) | WP03 | [P] |
| T019 | Delete dead census tier (12 symbols + branch + params) (FR-001) | WP04 | |
| T020 | Delete `_mt_pre_review_gate_verdict` + re-export + compat golden 157→156 (FR-002, C-004) | WP04 | |
| T021 | Swap `isinstance`→predicates at `pre_review_gate.py:881,:1013` (FR-005) | WP04 | |
| T022 | `GateOutcome.SOURCE_MISMATCH` + `_evaluate_via_scope_source` construction (FR-009, FR-011) | WP04 | |
| T023 | Console-ladder branch + defensive `else` + `verdict_aggregation` fail-open assert (FR-011) | WP04 | |
| T024 | Rewire head-path factory (FR-014) + dual-impl/dual-parse-mode parity + SC-004 demo (FR-010) | WP04 | |
| T025 | Docstring/CHANGELOG scrub + replay NFR-001/006 goldens green (FR-013) | WP04 | |
| T026 | Retire census-only tests (FR-004a) | WP05 | |
| T027 | Migrate the 8 verdict-diff tests to `scope_source=` injection (FR-004c) | WP05 | |
| T028 | Migrate FORWARD the mutation-bite live-topology assertions (FR-004, M-mut) | WP05 | [P] |
| T029 | Reconcile `test_pre_review_gate_integration.py` (kept-seam path) | WP05 | [P] |
| T030 | Committed coverage-parity inventory (FR-004d) | WP05 | |

> **Parallel note**: `[P]` marks subtasks with no *intra-WP* ordering dependency. The WPs themselves are a
> strict chain (see DAG above) — do not attempt to run WPs concurrently; the allocator will lane them
> serially.

---

## WP01 — Safety net: behavior-preservation goldens + sole-caller audit

**Goal**: Capture the NFR-001 (registry hook) and NFR-006 (override tier, non-empty scope) verdict
goldens via the **canonical** parity harness re-pinned to `eb06ca176`, and characterize (green-on-base)
that the census branch is the sole live `scope_source=None` caller — the falsifiable precondition for
"no coverage lost". **Nothing is deleted until this WP is green and committed.**
**Priority**: P1 (blocks everything) · **Dependencies**: none · **Prompt**: [`tasks/WP01-safety-net-goldens-audit.md`](./tasks/WP01-safety-net-goldens-audit.md) · **~260 lines**

- [ ] T001 Re-pin `_capture.py` `_require_base_commit` to `eb06ca176`; extend for override-tier capture (WP01)
- [ ] T002 Capture NFR-001 registry-path golden (HEAD==base, machine-emit `base_commit`) (WP01)
- [ ] T003 Capture NFR-006 override-tier golden driving a **non-empty** derived scope (WP01)
- [ ] T004 Wire `test_transition_gate_parity.py` replay for both golden sets (WP01)
- [ ] T005 IC-01 sole-live-caller characterization test (green-on-base) (WP01)

**Independent test**: `pytest tests/review/test_transition_gate_parity.py tests/review/test_pre_review_gate_sole_caller_audit.py` green on `eb06ca176`; the override golden drives a non-empty scope (proven by `run_scoped_tests_at_head` executing).
**Risks**: capturing after the deletion (circular oracle) — the `HEAD==base` assert forbids it; a vacuous override golden (empty scope) — T003 must drive a non-empty scope.

## WP02 — scope_source.py hub: factory, selection, predicates, mixin, identity helper

**Goal**: Land every additive change to `scope_source.py` that downstream WPs consume: the hoisted
`resolve_scope_source` factory (FR-003) with config-driven selection (FR-014), the single-source
`scope_source_identity` helper (FR-009 producer / NFR-005), the two independent predicates (FR-005), and
the `ScopeBreakdownMixin` projection (FR-006) — all behavior-preserving for the two shipped sources.
**Priority**: P1 · **Dependencies**: WP01 · **Prompt**: [`tasks/WP02-scope-source-hub.md`](./tasks/WP02-scope-source-hub.md) · **~420 lines**

- [ ] T006 Hoist `resolve_scope_source` factory into `scope_source.py` (params, no cycle) (WP02)
- [ ] T007 Add `scope_source_identity(scope_source, raw)` single-source helper (WP02)
- [ ] T008 Two independent predicates + distinct `ClassVar` marker (FR-005) (WP02)
- [ ] T009 `ScopeBreakdownMixin`; `GateCoverageScopeSource` inherits `file_to_scope` (FR-006) (WP02)
- [ ] T010 Config-driven selection in `resolve_scope_source` (FR-014) + stale comment/doc fix (WP02)
- [ ] T011 Migrate intent-encoding test onto the two predicates (FR-007) (WP02)
- [ ] T012 NFR-005 dual-root equivalence + structural same-helper assertion (WP02)

**Independent test**: `pytest tests/review/test_scope_source.py`; both predicates asserted independently (synthetic source satisfies one without the other); selection routes non-pytest `review.test_command` → `DeclaredCommandScopeSource`, spec-kitty (no `review.test_command`) → `GateCoverageScopeSource`; NFR-001 golden still green.
**Risks**: the carla-2 trap (both predicates reading the same signal) — the `ClassVar` marker keeps them independent; a wrong selection policy silently re-routes every consumer — test both branches.

## WP03 — baseline lifecycle + source identity (the B1 fix)

**Goal**: Close the parse-after-teardown asymmetry (FR-008 / B1) — parse/relocate the baseline artifact
BEFORE worktree teardown, inject the shared factory into implement-time capture, record `source_identity`
via the single-source helper, guard the broad-baseline invariant (FR-012), and fold the `baseline.py`
boyscout (FR-013).
**Priority**: P1 · **Dependencies**: WP01, WP02 · **Prompt**: [`tasks/WP03-baseline-lifecycle-identity.md`](./tasks/WP03-baseline-lifecycle-identity.md) · **~380 lines**

- [ ] T013 `source_identity` field on `BaselineTestResult` + `to_dict`/`from_dict` (FR-009) (WP03)
- [ ] T014 Parse-before-teardown lifecycle fix + record identity (FR-008 / B1) (WP03)
- [ ] T015 Inject shared factory into implement-time capture (FR-008) (WP03)
- [ ] T016 B1 red-first **direct** capture unit test (worktree-relative `--junitxml`) (WP03)
- [ ] T017 Anti-narrowing guard test (FR-012 / C-005) (WP03)
- [ ] T018 `baseline.py` boyscout: drop `timezone` import + tighten `ruff.toml` (FR-013) (WP03)

**Independent test**: `pytest tests/review/test_baseline_lifecycle.py tests/review/test_baseline_anti_narrowing.py`; the B1 direct test is red before T014 and green after; `from_dict` on a field-less artifact yields `"unknown"` (no `KeyError`).
**Risks**: the B1 bug itself (worktree-relative artifact deleted on teardown); firing `source_identity` on the override tier (WP04 guards that it only fires in the injected head path).

## WP04 — pre_review_gate deletion + SOURCE_MISMATCH + parity

**Goal**: The correctness+cleanup hub on `pre_review_gate.py` + the compat cluster. Delete the dead
census tier + verdict helper atomically (FR-001/FR-002/C-004, golden 157→156), swap the welded
`isinstance` for the two predicates (FR-005), add the warn-shaped `GateOutcome.SOURCE_MISMATCH` with the
console ladder + fail-open assertion (FR-009/FR-011), and prove baseline↔head parity across both sources
× both parse modes (FR-010 / SC-001 / SC-004).
**Priority**: P1 · **Dependencies**: WP01, WP02, WP03 · **Prompt**: [`tasks/WP04-prg-deletion-source-mismatch.md`](./tasks/WP04-prg-deletion-source-mismatch.md) · **~500 lines**

- [ ] T019 Delete dead census tier (12 symbols + branch + params) (FR-001) (WP04)
- [ ] T020 Delete `_mt_pre_review_gate_verdict` + re-export + compat golden 157→156 (FR-002, C-004) (WP04)
- [ ] T021 Swap `isinstance`→predicates at `pre_review_gate.py:881,:1013` (FR-005) (WP04)
- [ ] T022 `GateOutcome.SOURCE_MISMATCH` + `_evaluate_via_scope_source` construction (FR-009, FR-011) (WP04)
- [ ] T023 Console-ladder branch + defensive `else` + `verdict_aggregation` fail-open assert (FR-011) (WP04)
- [ ] T024 Rewire head-path factory (FR-014) + dual-impl/dual-parse-mode parity + SC-004 demo (FR-010) (WP04)
- [ ] T025 Docstring/CHANGELOG scrub + replay NFR-001/006 goldens green (FR-013) (WP04)

**Independent test**: NFR-001/006 goldens replay byte-identical; `SYMBOL_TO_MODULE == 156`; a source/parse-mode mismatch yields `SOURCE_MISMATCH` (warn, not block, not `NO_COVERAGE`); the four-combination parity test green; C-002 keep-live set survives.
**Risks**: an accidental import break if the compat edit is not atomic (C-004); editing the allowlist filters instead of asserting them (FR-011); missing the console fall-through.

## WP05 — Test migration + coverage-parity inventory

**Goal**: Discharge FR-004 exhaustively — retire the census-only tests, migrate the 8 verdict-diff tests
to `scope_source=` injection, migrate FORWARD the mutation-bite live-CI-topology assertions (NOT a
duplicate), and commit the coverage-parity inventory reviewed at gate. Keeps NFR-004 green with zero
live-path coverage lost.
**Priority**: P2 · **Dependencies**: WP04 · **Prompt**: [`tasks/WP05-test-migration-inventory.md`](./tasks/WP05-test-migration-inventory.md) · **~320 lines**

- [ ] T026 Retire census-only tests (FR-004a) (WP05)
- [ ] T027 Migrate the 8 verdict-diff tests to `scope_source=` injection (FR-004c) (WP05)
- [ ] T028 Migrate FORWARD the mutation-bite live-topology assertions (FR-004, M-mut) (WP05)
- [ ] T029 Reconcile `test_pre_review_gate_integration.py` (kept-seam path) (WP05)
- [ ] T030 Committed coverage-parity inventory (FR-004d) (WP05)

**Independent test**: `pytest tests/review/ tests/architectural/test_pre_review_scope_singlesource.py` (migrated) green; `coverage-parity-inventory.md` maps every retired test → a named surviving id or explicit "not carried forward because X"; `test_no_dead_symbols` / `test_golden_count_ban` green (after confirming pre-existing reds per #2825).
**Risks**: losing the unique verdict-diff coverage (NO_COVERAGE warn, terminal-interruption, sentinel/None-baseline, NEW_FAILURES) if the 8 are retired instead of migrated — they MUST be migrated; retiring the mutation-bite instead of migrating it forward.

---

## Requirement coverage (no orphans)

FR-001→WP04 · FR-002→WP01(audit)+WP04(delete) · FR-003→WP02 · FR-004→WP05 · FR-005→WP02(defs)+WP04(call-sites) · FR-006→WP02 · FR-007→WP02 · FR-008→WP03 · FR-009→WP03(field)+WP04(assert) · FR-010→WP04 · FR-011→WP04 · FR-012→WP03 · FR-013→WP02+WP03+WP04 · FR-014→WP02(factory+selection)+WP04(head-path rewire).
NFR-001→WP01(capture)+WP04(replay) · NFR-002→WP02/03/04 · NFR-003→all · NFR-004→WP04+WP05 · NFR-005→WP02(defines)+WP03/WP04(consume) · NFR-006→WP01+WP04 · NFR-007→WP01.
C-001→(scope guard, all) · C-002→WP04(keep-live golden) · C-003→this DAG · C-004→WP04 · C-005→WP03 · C-006→every WP's red-first test.

## Sizing

5 WPs, 30 subtasks, ~260–500 lines each. ✓ All WPs ≤7 subtasks / ≤~500 lines (within the ideal-to-max band). No WP exceeds 10 subtasks or 700 lines.

## Next

Post-task adversarial squad ✓ (3 lenses — renata anti-laziness / priti decomposition / paula boyscout —
all GO-WITH-FIXES; findings folded: WP01 dual-SHA re-pin, WP02 T007 source-owned `parse_mode`, WP04 T024
head-path rewire, WP04 read-site precision).

**HELD — do NOT start `/spec-kitty.implement` yet.** Two binding holds:
1. **PR #2835 must land first** (operator directive — avoid post-mission rebase conflicts; both this
   mission and the sibling `lifecycle-gate-execution-context-01KY72GQ` rebase onto it).
2. **Gate-layer collision with the sibling mission.** `lifecycle-gate-execution-context-01KY72GQ` (clone
   `coord-trust-2841`, branch `remediation/coord-lifecycle-gates`, same base `eb06ca176`) edits the same
   **Gate layer** files this mission owns: `review/pre_review_gate.py` + `cli/commands/agent/tasks_move_task.py`
   (WP04), and reads `review/gate_registry.py` (WP01 audit). Different changes (its execution-context seam
   / exemption-retirement vs our census-deletion + SOURCE_MISMATCH) → textual conflicts likely at
   rebase/merge. **Sequence the two missions (operator decides landing order); the second rebases onto the
   first.** We touch NONE of the highest-risk overlaps (`merge/*`, `coordination/transaction.py`).

When both holds clear: `/spec-kitty.analyze` (optional) → `/spec-kitty.implement` (WP01→…→WP05, serial
chain; implementers=sonnet, reviewers=opus).
