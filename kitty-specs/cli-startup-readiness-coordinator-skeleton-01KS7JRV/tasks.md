# Tasks: CLI Startup Readiness Coordinator Skeleton

**Mission**: `cli-startup-readiness-coordinator-skeleton-01KS7JRV`
**Mission ID**: `01KS7JRVSFFBWPD2XZ7B8162E6`
**Branch**: `kitty/mission-cli-startup-readiness-coordinator-skeleton-01KS7JRV` → `main`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Total WPs**: 3 | **Total subtasks**: 17

---

## Work Package Overview

| WP | Title | Dependencies | FRs covered | Subtasks | agent_profile |
|---|---|---|---|---|---|
| WP01 | Coordinator package + callback hook | — | FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010 | T001–T010 | python-pedro |
| WP02 | Suppression matrix + caching tests | WP01 | FR-009, FR-011, FR-012, NFR-002, NFR-004 | T011–T013 | python-pedro |
| WP03 | Nag passthrough test + final verification | WP02 | FR-006, FR-012, NFR-001, NFR-004, NFR-005 | T014–T017 | python-pedro |

All WPs run sequentially on a single lane (`lane-a`). There is no useful parallelism because WP02 tests the surface WP01 lands, and WP03 verifies the cross-cutting invariants over the surface WP02 covers.

WP01 is intentionally a single WP rather than a scaffold+wiring split because the file-ownership validator (`finalize-tasks --validate-only`) requires non-overlapping `owned_files`, and a clean split with `coordinator.py` in WP01 (scaffold) + `coordinator.py` in WP02 (body) would overlap.

---

## FR Coverage Matrix

| FR | Statement (summary) | WP(s) |
|---|---|---|
| FR-001 | `src/specify_cli/readiness/` package exports `evaluate_readiness`, `ReadinessResult`, `get_readiness` | WP01 |
| FR-002 | `evaluate_readiness(ctx)` called once from root `callback()` after suppression conditions known | WP01 |
| FR-003 | First gate is `is_saas_sync_enabled()`; no-op when disabled | WP01 |
| FR-004 | `output_policy` field derived from existing suppression signals | WP01 |
| FR-005 | Auth-readiness stub field; `_auth_recovery` imported but not exercised | WP01 |
| FR-006 | Coordinator wraps `_render_nag_if_needed` byte-for-byte | WP01 (impl), WP03 (verification) |
| FR-007 | Result stored on `ctx.obj["readiness"]` | WP01 |
| FR-008 | `get_readiness(ctx)` returns cached or no-op default; never raises, never re-runs | WP01 (impl), WP02 (tests) |
| FR-009 | Double-invocation returns cached result | WP01 (impl), WP02 (tests) |
| FR-010 | Coordinator never raises; exceptions → `_NOOP_DISABLED` | WP01 (impl), WP03 (verification) |
| FR-011 | No Teamspace string in stdout/stderr when hosted mode disabled, across the 7-row suppression matrix | WP02 |
| FR-012 | Tests under `tests/readiness/` cover 7-row matrix and once-per-invocation invariant | WP02, WP03 |
| NFR-001 | Coordinator overhead ≤ 1ms p50 disabled / ≤ 2ms p50 enabled | WP03 (verification by inspection) |
| NFR-002 | No network I/O in startup path | WP03 (verification via inspection / mock) |
| NFR-003 | No new disk reads beyond wrapped nag | WP03 (verification by inspection) |
| NFR-004 | ≥ 90% line coverage on `specify_cli/readiness/` | WP03 |
| NFR-005 | `mypy --strict` passes on new + modified files | WP01, WP03 |

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Create `src/specify_cli/readiness/__init__.py` with public re-exports | WP01 |  |
| T002 | Create `src/specify_cli/readiness/coordinator.py` types (`OutputPolicy`, `AuthStatus`, `ReadinessResult`, `_NOOP_DISABLED`) | WP01 |  |
| T003 | Implement `_derive_output_policy` | WP01 |  |
| T004 | Implement `_read_cached` / `_write_cached` | WP01 |  |
| T005 | Implement `_invoke_nag` (lazy import of `_render_nag_if_needed`) | WP01 |  |
| T006 | Implement `_evaluate_uncached` (disabled + enabled paths) | WP01 |  |
| T007 | Implement public `evaluate_readiness` (cache + try/except) | WP01 |  |
| T008 | Implement public `get_readiness` | WP01 |  |
| T009 | Modify `helpers.py` `callback()` to call `evaluate_readiness(ctx)` in place of inline `_render_nag_if_needed(ctx)` | WP01 |  |
| T010 | Verify mypy --strict, imports resolve, `WS2: auth probe wiring` marker present, existing CI-determinism tests pass smoke | WP01 |  |
| T011 | Create `tests/readiness/__init__.py` package marker | WP02 |  |
| T012 | Write `tests/readiness/test_coordinator_suppression_matrix.py`: 7-row + 1-enabled parameterized matrix asserting `output_policy`, `enabled`, `ran`, and the no-Teamspace-leakage invariant | WP02 |  |
| T013 | Write `tests/readiness/test_coordinator_caching.py`: 5 cases (A–E) covering hosted-on cache, hosted-off cache, `get_readiness` identity, fresh-ctx default, non-dict ctx.obj default | WP02 |  |
| T014 | Write `tests/readiness/test_coordinator_nag_passthrough.py`: 3 cases (A: ALLOW_WITH_NAG renders to stderr; B: `--json` suppresses; C: planner-exception swallowed) | WP03 |  |
| T015 | Run `pytest -q tests/cli_gate/test_ci_determinism.py` and confirm it passes unchanged (formal gate for FR-006) | WP03 |  |
| T016 | Run `mypy --strict src/specify_cli/readiness/ src/specify_cli/cli/helpers.py` and confirm pass (NFR-005) | WP03 |  |
| T017 | Run `pytest -q --cov=src/specify_cli/readiness tests/readiness/` and confirm ≥ 90% line coverage (NFR-004); run `git diff main...HEAD --stat` and confirm the diff is confined to the declared surfaces (AC #9) | WP03 |  |

---

## Work Packages

### WP01 — Coordinator package + callback hook

**Goal**: Land the production code in one coherent change. Create `src/specify_cli/readiness/` with `__init__.py` and `coordinator.py`. Implement all coordinator helpers and the public API. Wire `evaluate_readiness(ctx)` into the root callback in `src/specify_cli/cli/helpers.py` in place of the existing inline `_render_nag_if_needed(ctx)` call.

**Priority**: Critical. This is the seam landing.

**Independent test**: `python -c "from specify_cli.readiness import AuthStatus, OutputPolicy, ReadinessResult, evaluate_readiness, get_readiness; print('OK')"` succeeds; `mypy --strict src/specify_cli/readiness/ src/specify_cli/cli/helpers.py` passes; `pytest -q tests/cli_gate/test_ci_determinism.py` passes (smoke check).

**Estimated prompt size**: ~700 lines (10 subtasks × ~65 lines plus header/context). Within the maximum-size guideline because each subtask has tight, code-snippet-anchored guidance.

**Included subtasks**:
- [x] T001 Create `src/specify_cli/readiness/__init__.py`
- [x] T002 Create `coordinator.py` types
- [x] T003 Implement `_derive_output_policy`
- [x] T004 Implement `_read_cached` / `_write_cached`
- [x] T005 Implement `_invoke_nag` (lazy)
- [x] T006 Implement `_evaluate_uncached` (disabled + enabled paths)
- [x] T007 Implement public `evaluate_readiness`
- [x] T008 Implement public `get_readiness`
- [x] T009 Modify `helpers.py` `callback()` hook
- [x] T010 Verification: mypy, imports, smoke

**Prompt**: [`tasks/WP01-coordinator-package-and-hook.md`](tasks/WP01-coordinator-package-and-hook.md)

---

### WP02 — Suppression matrix + caching tests

**Goal**: Prove the suppression contract (FR-011) and the once-per-invocation caching invariant (FR-009, part of FR-012) under test.

**Priority**: Verification. Locks in the FR-011 / FR-012 / NFR-002 contracts.

**Independent test**: `pytest -q tests/readiness/test_coordinator_suppression_matrix.py tests/readiness/test_coordinator_caching.py` is green.

**Estimated prompt size**: ~320 lines.

**Included subtasks**:
- [ ] T011 Create `tests/readiness/__init__.py`
- [ ] T012 Write the 7-row + 1-enabled suppression-matrix parameterized test
- [ ] T013 Write the 5-case caching test

**Dependencies**: WP01.

**Prompt**: [`tasks/WP02-suppression-matrix-and-caching-tests.md`](tasks/WP02-suppression-matrix-and-caching-tests.md)

---

### WP03 — Nag passthrough test + final verification

**Goal**: Prove nag passthrough is byte-for-byte preserved (FR-006), assert the existing CI-determinism tests still pass (AC #5), confirm coverage and mypy gates, and confirm the diff scope (AC #9).

**Priority**: Acceptance gate.

**Independent test**: `pytest -q tests/readiness/ tests/cli_gate/test_ci_determinism.py` is green; `mypy --strict src/specify_cli/readiness/ src/specify_cli/cli/helpers.py` passes; `pytest --cov=src/specify_cli/readiness tests/readiness/` reports ≥ 90% line coverage; `git diff main...HEAD --stat` matches AC #9.

**Estimated prompt size**: ~300 lines.

**Included subtasks**:
- [ ] T014 Write nag-passthrough tests (3 cases)
- [ ] T015 Verify existing CI-determinism tests pass unchanged
- [ ] T016 Verify mypy --strict passes for both modified module surfaces
- [ ] T017 Verify coverage ≥ 90% and diff scope matches AC #9

**Dependencies**: WP02.

**Prompt**: [`tasks/WP03-nag-passthrough-and-final-verification.md`](tasks/WP03-nag-passthrough-and-final-verification.md)

---

## Parallelization Opportunities

None within this mission. All WPs sequential on `lane-a`.

## MVP Scope

WP01 delivers the seam. WP02 + WP03 lock the contract under test. The mission requires all three.

## Branch Strategy (re-stated)

- Planning base branch: `main`
- Mission branch: `kitty/mission-cli-startup-readiness-coordinator-skeleton-01KS7JRV` (this branch carries the planning artifacts and all WP commits)
- Final merge target for the PR: `main`
- Per-WP lane workspace: `.worktrees/cli-startup-readiness-coordinator-skeleton-01KS7JRV-mid8-lane-a/` (resolved at `spec-kitty implement` time)
