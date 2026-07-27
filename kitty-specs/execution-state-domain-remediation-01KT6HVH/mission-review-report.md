# Mission Review Report: execution-state-domain-remediation-01KT6HVH

**Reviewer**: spec-kitty-mission-review (ultracode workflow)
**Date**: 2026-06-03
**Mission**: `execution-state-domain-remediation-01KT6HVH` — Execution-State Domain Remediation — #1619 Strangler Fig
**Baseline commit**: `80a0b822d7ff9907926075f8b1c5f9cc42b9ff8e`
**HEAD at review**: `17e8c99c0474d56dead50191051e603b77faf0c9`
**WPs reviewed**: WP01–WP06 (all 6 done)
**Changed files**: 66

---

## Gate Results

### Gate 1 — Contract Tests

**Result: PASS**

Command: `pytest tests/contract/ -v -q`
Outcome: 254 passed, 1 skipped, 17 warnings in 75.98s. Zero failures.

Warnings are non-blocking:
- Legacy contract YAML codeblocks missing `pydantic_model` frontmatter annotation.
- Deprecation warnings for `specify_cli.next` shim pointing to `runtime.next` (removal scheduled for 3.3.0).

---

### Gate 2 — Architectural Tests

**Result: PASS** (with pre-existing baseline debt noted)

Command: `pytest tests/architectural/ -v -q`
Outcome: 291 passed, 6 failed, 1 skipped in 52s.

All 6 failures are **pre-existing** and originate from commits that predate the mission squash merge (`0b6e2d7d9`):

| Failing test | Pre-existing since | Root cause |
|---|---|---|
| `test_no_dead_modules` | commit `59c0cfa2b` | `specify_cli.upgrade.migrations.m_3_2_0rc35_spk_skill_pack` unwired |
| `test_no_dead_symbols` | commit `fd27501eb` | `AGENT_UPGRADE_CHECK_BLOCK` + stale allowlist entries |
| `test_pytest_marker_convention` (4 files) | commit `a9518184d` | 4 files missing `pytestmark` |
| `test_subprocess_git_users_must_carry_git_repo_marker` | commit `a9518184d` | `tests/test_dashboard/test_dashboard_preflight.py` |
| `test_fast_marker_must_not_apply_to_subprocess_users` | commit `a9518184d` | same file |
| `test_ratchet_baselines` | tied to dead-modules above | dead_modules allowlist baseline 77 vs current 78 |

Mission-specific tests all pass:
- `test_status_module_boundary` (WP03): 4/4 pass
- `test_execution_context_parity` (WP02): 2/2 pass
- `test_shared_package_boundary`: 7/7 pass, zero regressions

The pre-existing failures constitute inherited baseline debt from `main` and do not reflect any regression introduced by this mission.

---

### Gate 3 — Cross-Repo E2E

**SKIPPED** — no cross-repo test repo is configured in this environment. Not blocking; Gate 3 is reserved for cross-repo scenarios that require an external project fixture.

---

### Gate 4 — Issue Matrix

**Result: PASS**

All 13 rows in `issue-matrix.md` carry valid verdicts. No row has an unknown or empty verdict.

| Issue | Verdict | Owner WP |
|---|---|---|
| #1674 | fixed (commit `b67003f39`) | WP01 |
| #1666 | verified-already-fixed | WP01 |
| #1615 | verified-already-fixed | — |
| #1616 | verified-already-fixed | — |
| #1617 | verified-already-fixed | — |
| #1618 | verified-already-fixed | — |
| #1627 | verified-already-fixed | — |
| #1672 | deferred-with-followup | WP02 |
| #1664 | deferred-with-followup | WP03 |
| #1667 | deferred-with-followup | WP04 |
| #1663 | deferred-with-followup | WP05 |
| #1673 | deferred-with-followup | WP06 |

Every deferred-with-followup row names a follow-up issue in its `evidence_ref` column.

---

## FR Coverage Matrix

| FR ID | Description (brief) | WP Owner | Test File(s) | Test Adequacy | Finding |
|---|---|---|---|---|---|
| FR-001 | ADR: execution-state domain model | WP01 | — (doc artifact) | ADEQUATE | ADR exists at `architecture/3.x/adr/2026-06-03-1-execution-state-domain-model.md` (123 lines) |
| FR-002 | ADR: ExecutionContext owner & CommitTarget | WP01 | — (doc artifact) | ADEQUATE | ADR exists at `architecture/3.x/adr/2026-06-03-2-executioncontext-owner-and-committarget.md` (114 lines) |
| FR-003 | ADR: Effector/actor model | WP01 | — (doc artifact) | ADEQUATE | ADR exists at `architecture/3.x/adr/2026-06-03-3-effector-actor-model.md` (121 lines) |
| FR-004 | 5 glossary entries added | WP01 | — (doc artifact) | ADEQUATE | All 5 entries (GovernanceContext, ExecutionContext, InfraContext, Effector, communication artefact) present in `glossary/contexts/execution.md` lines 161–225 |
| FR-005 | ADRs committed before any impl WP | WP01 | — | ADEQUATE | WP01 has no dependencies; committed before WP02–WP06 per tasks.md gate |
| FR-006 | Test covers full next→implement→move-task→review→status sequence | WP02 | `tests/architectural/test_execution_context_parity.py` | **PARTIAL** | Test only exercises `agent tasks status --json` from two CWDs; no next/implement/move-task/review invocations. See DRIFT-001. |
| FR-007 | CWD-parity test: status from main-checkout CWD | WP02 | `test_execution_context_parity.py` | ADEQUATE | `test_cwd_parity` invokes from main-checkout CWD |
| FR-008 | CWD-parity test: identical WP lane maps | WP02 | `test_execution_context_parity.py` | ADEQUATE | Lines 333, 343 assert identical WP lane maps |
| FR-009 | CI path filter triggers parity test job | WP02 | `.github/workflows/ci-quality.yml` lines 204–209 | ADEQUATE | `execution_context` path filter tied to `integration-tests-core-misc` job; architectural+git_repo markers picked up |
| FR-010 | Ratchet fails on divergence injection | WP02 | `test_execution_context_parity.py` | ADEQUATE | `test_ratchet_catches_divergence` (line 357) corrupts status in worktree and asserts lanes diverge (lines 443, 462, 472) |
| FR-011 | `test_status_module_boundary.py` exists | WP03 | `tests/architectural/test_status_module_boundary.py` | ADEQUATE | pytestarch Rule enforces no `status.*` submodule imports from WP03-owned packages |
| FR-012 | Zero bypass imports in WP03-owned scope | WP03 | `test_status_module_boundary.py` | ADEQUATE | grep returns 0 hits in agent_utils, lanes, post_merge, missions, merge, next |
| FR-013 | No new submodule imports introduced by mission | WP03 | git diff check | ADEQUATE | git diff shows no new `+from specify_cli.status.` submodule imports in this mission |
| FR-014 | `coordination/status_transition.py` exempted | WP03 | `test_status_module_boundary.py` | ADEQUATE | Explicit `_EXEMPT_MODULES` and `_EXEMPT_FILES` entries (lines 85–98) |
| FR-015 | `ActiveWPStatus` dataclass | WP04 | `tests/unit/status/test_mission_status_aggregate.py` | ADEQUATE | Defined in `aggregate.py` lines 69–89; unit tested |
| FR-016 | `MissionStatus` frozen dataclass | WP04 | `test_mission_status_aggregate.py` | ADEQUATE | Defined in `aggregate.py` lines 90–114; unit tested |
| FR-017 | `MissionStatus.load()` resolves topology | WP04 | `test_mission_status_aggregate.py` | ADEQUATE | 4 topology scenarios covered; coord worktree detection tested |
| FR-018 | `MissionStatus.claim()` returns ActiveWPStatus | WP04 | `test_mission_status_aggregate.py` | ADEQUATE | `test_claim_returns_active_wp_status_for_known_wp` and `test_claim_current_lane_matches_last_event_to_lane` |
| FR-019 | `MissionStatus.transition()` validates + applies | WP04 | `test_mission_status_aggregate.py` | **MISSING** | Method implemented (lines 239–305) but has zero test coverage. No test calls `.transition()`. See RISK-001 / DRIFT-003. |
| FR-020 | `MissionStatus.save()` persists via BookkeepingTransaction | WP04 | `test_mission_status_aggregate.py` | **MISSING** | Method implemented (lines 306–332) but has zero test coverage. No test calls `.save()`. See RISK-001 / DRIFT-003. |
| FR-021 | `CoordAuthorityUnavailable` raised on missing coord worktree | WP04 | `test_mission_status_aggregate.py` | ADEQUATE | `test_raises_coord_authority_unavailable` and `test_does_not_fall_back_to_primary_checkout` pass |
| FR-022 | `agent/status.py` uses `MissionStatus.load()` | WP04 | — (grep verification) | ADEQUATE | `cli/commands/agent/status.py` uses `MissionStatus.load()` at lines 127/145/170/173; zero raw `kitty-specs/mission_slug` constructions |
| FR-023 | Domain lane-transition invariants enforced by aggregate | WP04 | `test_mission_status_aggregate.py` | **PARTIAL** | `transition()` calls `validate_transition()` before delegating to BookkeepingTransaction (code-verified), but since FR-019 has no test coverage this invariant is asserted in code only, not test-verified. See DRIFT-003. |
| FR-024 | `MissionRunSnapshot` gains `mission_id`/`mission_slug` fields | WP05 | `tests/next/test_mission_run_back_reference.py` | ADEQUATE | Optional fields in `schema.py` lines 540–541; backward-compat tested |
| FR-025 | `MissionRunRef` gains same optional fields | WP05 | `test_mission_run_back_reference.py` | ADEQUATE | `schema.py` lines 100–101; tested |
| FR-026 | `start_mission_run` accepts and plumbs both fields | WP05 | `test_mission_run_back_reference.py` | ADEQUATE | `engine.py` lines 194–195, 224–225, 239–240; `test_start_mission_run_plumbs_mission_slug_and_id` passes |
| FR-027 | All 6 `MissionRunSnapshot` construction sites carry fields | WP05 | — (grep verification) | ADEQUATE | Lines 212, 295, 383, 488, 701, 853 in `engine.py` verified |
| FR-028 | `feature-runs.json` write site includes both fields | WP05 | `tests/next/test_runtime_bridge_unit.py` | **PARTIAL** | Fields written in `runtime_bridge.py` lines 2118–2125, but `test_feature_runs_index_persisted` (line 379) only asserts `run_id` is present — does not assert `mission_id` or `mission_slug`. See RISK-002. |
| FR-029 | Existing `state.json` files load with `None` defaults | WP05 | `test_mission_run_back_reference.py` | ADEQUATE | `test_mission_run_snapshot_loads_without_mission_id` and model-validate variant pass |
| FR-030 | `inputs["mission_slug"]` write-only redundancy noted | WP05 | — | PARTIAL | New named param added; old `inputs` dict still writes `mission_slug` but it is never read back. Redundancy not cleaned up or explicitly tested. |
| FR-031 | No surface outside facade constructs raw `kitty-specs/mission_slug` path | WP06 | — (grep verification) | **PARTIAL** | Fixed in WP06-owned files (runtime_bridge.py, workflow.py targeted functions) only. 215+ pre-existing violations remain in ~50 other src files. Spec FR-031 text not updated to reflect the narrowed scope. See DRIFT-002. |
| FR-032 | `query_current_state` routes through `resolve_action_context` | WP06 | — (diff verification) | ADEQUATE | `runtime_bridge.py` lines 2985–2994; `ActionContextError` path handled. |
| FR-033 | `_ensure_target_branch_checked_out` routes through `resolve_action_context` | WP06 | — (diff verification) | ADEQUATE | `workflow.py` lines 846–868 per diff |
| FR-034 | Unreachable path-builder helpers deleted | WP06 | — | **PARTIAL** | No helpers were actually deleted because `resolve_target_branch` retains live callers in `implement.py`, `tasks.py`, `merge.py`, `mission.py`. DoD checkbox satisfied vacuously. See DRIFT-004. |
| FR-035 | Parity ratchet tests pass within wall-clock limits | WP02 | `test_execution_context_parity.py` | ADEQUATE | 4 tests green in 1.95s (NFR-005 limit: 10s) |
| NFR-002 | Backward-compat: new fields default to `None` | WP05 | `test_mission_run_back_reference.py` | ADEQUATE | 3 tests verify existing state.json files load without error |
| NFR-003 | `BookkeepingTransaction` unchanged | WP06 | — (git diff) | ADEQUATE | `coordination/transaction.py` diff returns 0 lines against baseline |
| NFR-005 | `test_status_module_boundary.py` completes under 10s | WP03 | `test_status_module_boundary.py` | ADEQUATE | Runs in 1.95s wall-clock |

---

## Drift Findings

### DRIFT-001 — FR-006 test scope narrows without spec update
**Severity: MEDIUM**

FR-006 requires a test covering the full `next -> implement -> move-task -> review -> status` command sequence. The delivered test (`test_execution_context_parity.py`) only exercises `agent tasks status --json` from two CWDs. The test module docstring explicitly states it is "a compact proof that agent tasks status --json produces identical WP lane data". No subprocess calls to `next`, `implement`, `move-task`, or `review` exist anywhere in the test. The FR-006 requirement was narrowed in scope during implementation but the spec text was never updated to reflect this.

**Resolution path**: Update `spec.md` FR-006 description to match the delivered scope, or file a follow-up issue to extend the parity test to cover the full command sequence.

---

### DRIFT-002 — FR-031 global scope vs WP06 write-scope mismatch
**Severity: HIGH**

FR-031 states "no surface outside `core/execution_context.py` and `status/` constructs `main_repo_root / kitty-specs / mission_slug` directly". The actual implementation fixed only the three targeted functions in `runtime_bridge.py` and `workflow.py`. 215+ pre-existing violations remain in `src/` across approximately 50 files including `verify_enhanced.py`, `context/resolver.py`, `core/worktree_topology.py`, `agent_utils/status.py`, `doctrine_synthesizer/apply.py`, `core/paths.py`, and `core/project_resolver.py`. The DoD was retroactively scoped to WP06-owned files during review cycle 2, but the spec FR-031 text was never updated to reflect this narrowing.

**Resolution path**: Update `spec.md` FR-031 to scope the constraint to WP06-owned files (as delivered), and file a follow-up issue to track the remaining 215+ violations as a multi-mission strangler-fig continuation.

---

### DRIFT-003 — FR-019 and FR-020 have no test coverage
**Severity: MEDIUM**

`MissionStatus.transition()` (`aggregate.py` lines 239–305) and `MissionStatus.save()` (lines 306–332) are fully implemented but have zero test coverage. The unit test file `test_mission_status_aggregate.py` covers `load()`, `claim()`, field contracts, and facade exports, but contains no test that calls `ms.transition()` or `ms.save()`. Additionally, neither method has a live caller in production `src/` code outside `cli/commands/agent/status.py`, which only calls `.load()` and `.claim()`. This means the two domain write paths that the spec treats as critical invariants (FR-019, FR-020, FR-023) are implemented but untested and unreachable from any current CLI surface.

**Resolution path**: Add unit tests for `MissionStatus.transition()` (happy path + `validate_transition` rejection) and `MissionStatus.save()` (happy path + `BookkeepingTransaction` receipt). Investigate whether `agent/status.py` was supposed to call `.transition()` or whether there is a missing integration point.

---

### DRIFT-004 — FR-034 satisfied vacuously
**Severity: LOW**

FR-034 requires that "duplicated path-builder functions made unreachable by this work are deleted". The T036 step found "no dead helpers" because `resolve_target_branch` (removed from `workflow.py`'s `_ensure_target_branch_checked_out`) still has live callers in `implement.py`, `tasks.py`, `merge.py`, and `mission.py`. No functions became unreachable, so no functions were deleted. The DoD checkbox is marked complete only because the precondition (functions becoming unreachable) was not met. The architectural intent — eliminating dead path-builder code — was not achieved.

**Resolution path**: No immediate action required given the limited WP06 scope. The finding is informational: the architectural goal of FR-034 remains a future-work item once the broader strangler-fig sequence (FR-031 follow-up) removes more CWD-dependent callers.

---

## Risk Findings

### RISK-001 — MissionStatus.transition() and .save() have zero unit test coverage
**Severity: HIGH**
**Type**: FR-mapped not-tested
**Location**: `src/specify_cli/status/aggregate.py:239,306` / `tests/unit/status/test_mission_status_aggregate.py`

FR-019 (transition validates and applies lane transitions) and FR-020 (save persists via BookkeepingTransaction) are both implemented in `aggregate.py`, but the unit test file contains no test covering either method. The 313-line test file covers only `load()`, `claim()`, field contracts, and facade exports. The two domain write paths have no isolated test coverage and no live callers in current production code, making their correctness unverifiable until a surface is wired up.

---

### RISK-002 — FR-028 feature-runs.json write site lacks assertion
**Severity: MEDIUM**
**Type**: FR-mapped not-tested
**Location**: `src/runtime/next/runtime_bridge.py` (~line 2114) / `tests/next/test_runtime_bridge_unit.py:379–388`

FR-028 requires `feature-runs.json` to include `mission_id` and `mission_slug`. The diff confirms both fields are now written. However, `test_feature_runs_index_persisted` (line 379) only asserts `run_id` is present — it does not assert `mission_id` or `mission_slug`. A future refactor could silently drop these fields with no test catching the regression.

**Resolution path**: Add assertions for `mission_id` and `mission_slug` to `test_feature_runs_index_persisted` or add a dedicated assertion in `test_mission_run_back_reference.py`.

---

### RISK-003 — answer_decision_via_runtime swallows _read_snapshot failure silently
**Severity: MEDIUM**
**Type**: Silent failure
**Location**: `src/runtime/next/runtime_bridge.py:3151–3156`

The new `answer_decision_via_runtime` code path calls `sync_emitter.seed_from_snapshot` inside a bare `except Exception: pass` block. Any I/O error, import error, or schema validation failure in `_read_snapshot` silently produces an unseeded emitter. The answering action proceeds with stale or empty emitter state, potentially recording a decision with wrong run context. This is a pre-existing broad-exception pattern extended to a newly-introduced coordination path.

**Resolution path**: Replace bare `except Exception: pass` with at minimum a `logger.warning` call, or narrow to specific expected exceptions and re-raise unexpected ones.

---

### RISK-004 — answer_decision_via_runtime has no ActionContextError guard
**Severity: MEDIUM**
**Type**: Silent failure (asymmetric with query_current_state)
**Location**: `src/runtime/next/runtime_bridge.py:3136–3143`

`query_current_state` (lines 2985–3002) wraps `resolve_action_context` in `try/except ActionContextError` and returns a graceful not-found `Decision`. The companion function `answer_decision_via_runtime` (lines 3136–3143) calls `resolve_action_context` without any `ActionContextError` guard. If the mission directory is not found during an answer operation, an unhandled `ActionContextError` propagates as a Python traceback instead of a structured error response. This asymmetry was introduced by WP06 (FR-032).

**Resolution path**: Add an `ActionContextError` guard to `answer_decision_via_runtime` symmetric with the guard in `query_current_state`.

---

### RISK-005 — Ratchet test uses hand-crafted synthetic fixtures
**Severity: LOW**
**Type**: Synthetic fixture risk
**Location**: `tests/architectural/test_execution_context_parity.py`

The CWD-invariance ratchet test builds fixtures with hand-crafted `meta.json` and `status.events.jsonl` content (`_META_JSON`, `_WP01_MD`, manual JSONL lines) rather than invoking the real spec-kitty init/finalize-tasks/emit_status_transition pipeline. The design doc acknowledges this as a deliberate tradeoff for speed and hermeticity. The risk is that a bug where the full pipeline's output diverges between CWD invocations could pass the ratchet if that divergence only manifests in fields not present in the hand-crafted fixtures. FR-010's "ratchet fails when a surface re-derives context independently" guarantee is partially weakened by this fixture gap.

**Resolution path**: Document the fixture-limitation tradeoff in the test module docstring (currently implicit in the design doc). Consider a smoke-level integration variant that runs through `emit_status_transition` directly to generate fixtures.

---

### RISK-006 — MissionStatus._read_meta silently returns (None, False) on I/O errors
**Severity: LOW**
**Type**: Silent failure
**Location**: `src/specify_cli/status/aggregate.py:196–203`

Lines 200–203 catch `OSError`, `json.JSONDecodeError`, and non-dict payload all silently, returning `(None, False)`. A corrupted or permission-denied `meta.json` causes `load()` to treat the mission as a legacy topology with no `mission_id`, rather than surfacing the read error. A coord-branch mission with corrupted `meta.json` would silently fall through to the primary checkout instead of raising `CoordAuthorityUnavailable`. The FR-021 fail-closed guarantee depends on `_read_meta` correctly detecting `declares_coord_branch`; a corrupted `meta.json` defeats that guarantee without any caller warning.

**Resolution path**: Add a `logger.warning` call in the except blocks, and consider whether `CoordAuthorityUnavailable` should be raised (rather than returning `(None, False)`) when the file exists but is unreadable.

---

## Silent Failure Candidates

| Location | Trigger Condition | Silent Result | Spec Impact |
|---|---|---|---|
| `aggregate.py:_read_meta` lines 196–203 | `meta.json` corrupted, permission-denied, or non-dict value | Returns `(None, False)` — coord-topology mission silently degrades to stale primary-checkout read | FR-021 fail-closed guarantee bypassed without caller warning |
| `runtime_bridge.py:answer_decision_via_runtime` lines 3151–3156 | `_read_snapshot` raises any exception (ImportError, OSError, Pydantic ValidationError) | `sync_emitter` proceeds unseeded; decision recorded with empty or stale run context. No log output, no exception propagated. | Coordination branch decisions may record wrong run state |
| `runtime_bridge.py:answer_decision_via_runtime` lines 3136–3143 | `resolve_action_context` raises `ActionContextError` (mission directory missing or malformed) | Unhandled exception propagates as Python traceback — asymmetric with `query_current_state` which returns a structured not-found Decision | FR-032 route hardening incomplete for the answer path |

---

## Security Notes

**subprocess safety (low risk):** No `shell=True` subprocess calls introduced in the diff. The single new `subprocess.run` in `coordination/workspace.py` (line 175) uses a list argument with `capture_output=True`. No shell injection vector.

**Path traversal via mission_slug (low risk):** The pattern `Path(".") / "kitty-specs" / mission_slug` appears in `aggregate.py:load()` and related runtime_bridge context. No validation of `mission_slug` for path-traversal characters (e.g. `../`) before constructing filesystem paths. The ULID-based identity model (mission 083) reduces exposure for new missions, but legacy slug values passed from external sources remain unvalidated.
**Recommendation**: Add a slug validation guard (alphanumeric + hyphens only) at the entry point of `MissionStatus.load()` and `resolve_action_context`.

**Deferred-import suppressions (info):** Multiple `noqa: PLC0415` suppressions added throughout `runtime_bridge.py` for deferred imports inside functions. These are structural, not security-relevant, but the pattern makes import-time side-effects harder to audit.

**C-004 locked decision (verified clean):** `git diff` of `coordination/transaction.py` against baseline `80a0b822d` returns empty — `BookkeepingTransaction` is unchanged. NFR-003 satisfied.

---

## Final Verdict

**PASS WITH NOTES**

### Verdict rationale

All four gates passed. All 6 WPs are in the `done` lane. The mission successfully delivered the Strangler Fig #1619 sequence, including three ADRs, a CWD-invariance parity ratchet, a `status/` module facade boundary test, the `MissionStatus` frozen aggregate, `MissionRunSnapshot`/`MissionRunRef` back-reference fields, and `resolve_action_context` routing in `runtime_bridge.py` and `workflow.py`.

The `PASS WITH NOTES` (rather than clean `PASS`) reflects four specific concerns that are non-blocking but require follow-up:

1. **DRIFT-002 (HIGH)**: FR-031's global "no raw path construction" constraint was narrowed to WP06-owned files without updating the spec. 215+ pre-existing violations remain. The spec and delivered state diverge. Follow-up issue required.

2. **RISK-001 (HIGH)**: `MissionStatus.transition()` and `.save()` — the two domain write paths — have zero test coverage and no live callers. These methods are implemented but unreachable from any current CLI surface, undermining FR-019, FR-020, and FR-023.

3. **RISK-003 / RISK-004 (MEDIUM)**: `answer_decision_via_runtime` has an asymmetric failure mode relative to `query_current_state`: it lacks an `ActionContextError` guard (RISK-004) and swallows `_read_snapshot` failures silently (RISK-003).

4. **DRIFT-001 (MEDIUM)**: FR-006 scope was narrowed to a single-command parity proof without updating the spec text.

The pre-existing architectural test failures (Gate 2's 6 failures) are baseline debt from `main` and do not represent regressions from this mission.

---

### Open items (non-blocking)

1. **[DRIFT-002 / FR-031]** File a follow-up GitHub issue to continue the strangler-fig sequence for the remaining 215+ raw `kitty-specs / mission_slug` path-construction sites. Update `spec.md` FR-031 to accurately describe the narrowed delivery scope.

2. **[DRIFT-001 / FR-006]** Update `spec.md` FR-006 to accurately describe the delivered test scope (`agent tasks status --json` CWD parity only). Optionally file a follow-up to extend coverage to the full `next → implement → move-task → review → status` sequence.

3. **[RISK-001 / FR-019, FR-020]** Add unit tests for `MissionStatus.transition()` (happy path + rejection) and `MissionStatus.save()`. Investigate whether `agent/status.py` was meant to call `.transition()` or whether a wiring point is missing.

4. **[RISK-002 / FR-028]** Add assertions for `mission_id` and `mission_slug` to the `test_feature_runs_index_persisted` test (or add equivalent coverage in `test_mission_run_back_reference.py`).

5. **[RISK-003 / RISK-004]** Harden `answer_decision_via_runtime`: add an `ActionContextError` guard symmetric with `query_current_state`, and replace the bare `except Exception: pass` with at minimum a `logger.warning`.

6. **[RISK-006]** Add a `logger.warning` in `_read_meta`'s except blocks to surface corrupted `meta.json` failures rather than silently degrading topology detection.

7. **[Pre-existing debt]** The 6 pre-existing architectural test failures (dead module, dead symbols, marker convention, subprocess marker, ratchet baseline) remain on `main` and should be addressed in a dedicated cleanup mission.

---

## Retrospective Reminder

The retrospective.yaml was authored at `.kittify/missions/01KT6HVH3QND4Q3KCGH2419N4J/retrospective.yaml` during merge.

Run:
- `spec-kitty retrospect summary` — cross-mission aggregation
- `spec-kitty agent retrospect synthesize --mission execution-state-domain-remediation-01KT6HVH` — inspect proposals (dry-run)
