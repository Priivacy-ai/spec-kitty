# Implementation Plan: CI Suite Stability & Test-Isolation

**Branch**: `issue-4017-ci-suite-stability` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)
**Input**: #4017 (runtime concurrency) + #4015 (timing-guard residual), epic #1931. Spec squad-hardened (commit 9081d9a).

## Summary

Two independent clusters. **Cluster A (#4017)** fixes a real cold-start TOCTOU race: the existing anchor flock serializes cold installers, but the post-lock re-check validates the loser's *stale* empty-home plan and the apply ops are non-idempotent — so narrowing alone converts `"Global asset input changed"` into `"global_asset_write_failed: File exists"`. The fix is **re-assess under the held lock** (loser recomputes effects against the now-warm home → `effects==[]` → warm return), with **observe()-role-tagging** (source vs destination) as the enabler, landed in the **generic** `check_assets`/`ensure_runtime` seam (HiC-confirmed: all owners race identically). **Cluster B (#4015)** is a mechanical sweep moving the timing-guard residual off the per-PR path without losing functional coverage.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: stdlib (`fcntl` flock, `pathlib`, `ast`), pytest (+ xdist), ruamel.yaml. **No new dependencies.**
**Storage**: Filesystem — `spec-kitty-home` (`~/.kittify`) destination tree + package-source asset tree; the fix changes how the recheck *classifies* these (source vs destination), not storage.
**Testing**: pytest (`tests/e2e/` concurrency harness — `e2e`/`stress` markers; `tests/runtime/`; `tests/architectural/test_performance_marker_guard.py`); real installed-CLI e2e DRIVEN (not asserted from API). `ci-nightly.yml` is the sole `-m performance`/`-m e2e` lane.
**Target Platform**: Linux/macOS CLI (POSIX flock).
**Project Type**: single.
**Performance Goals**: N/A; NFR-002 requires the warm startup path to take no new lock / exactly one assess.
**Constraints**: re-assess fires only on the cold/effects path (C-001); do NOT strip observations (C-002); functional asserts never deleted (C-003); no suppression / no vocab widening (C-004); OPERATOR_SIGNAL_CONTRACT — the defer/re-assess outcome emits a human+machine operator-visible signal.
**Scale/Scope**: #4017 — `runtime/asset_preparation.py`, `runtime/bootstrap.py`, maybe `runtime/merge.py` (triple-nested recheck), + un-skip 2 e2e tests + new deterministic-interleave + source-drift + #4082-regression tests. #4015 — 74 mixed split (~40 files/23 subsystems) + 9 vocab-blocked + 1 shared helper.

## Constitution Check

*GATE: pass before Phase 0; re-check after Phase 1.*

- **Single canonical authority (DIRECTIVE_044).** ✅ The re-assess + role-tag land once at the generic `check_assets`/`ensure_runtime` seam (HiC-confirmed generic scope), not duplicated per owner or per recheck-nesting.
- **OPERATOR_SIGNAL_CONTRACT (internal directive).** ✅ The absent/defer/re-assess outcome emits a human sentence + machine signal on an existing operator-visible surface; the red-first asserts on the SIGNAL, not just the machine shape.
- **ATDD / red-first (DIRECTIVE_041).** ✅ FR-006 — RED-first reproduces the exact `"Global asset input changed"` signal via the installed-CLI concurrent harness, plus a deterministic apply-interleave test as the structural guarantee.
- **Tidy-first (DIRECTIVE_025).** ✅ Enabler WPs first — role-tagging (A) and the `assert_timing_budget` helper (B) precede the functional fixes.
- **Architectural gate non-vacuity (DIRECTIVE_043).** ✅ The source-drift guard (FR-003) keeps the recheck non-vacuous — narrowing must not silence genuine source-change detection.
- **Test remediation discipline (DIRECTIVE_041/034).** ✅ #4015 judges each test (split / helper / rename / delete-with-evidence+signoff); functional asserts kept.
- **No version prescription (DIRECTIVE_045).** ✅

No Complexity-Tracking violations.

## Supply-Chain Security & Adversarial Evidence
- **Dependencies**: none added/removed → supply-chain checks N/A (recorded per the plan step contract).
- **Adversarial evidence**: pre-mission grounding squad (3 lenses) + post-spec squad (2 lenses) ran; all dispositions (incl. the BLOCKER that reshaped #4017) recorded in [research.md](./research.md) §Adversarial Evidence. No contested finding dropped.

## Project Structure

```
src/specify_cli/runtime/
├── asset_preparation.py   # observe() role-tag (source/destination); check_assets compare-site filter; re-assess support
├── bootstrap.py           # ensure_runtime: re-assess-under-lock on cold/effects path; warm fast-path preserved; operator signal
└── merge.py               # triple-nested recheck — inherits the seam

tests/
├── e2e/test_worktree_owned_root_concurrency.py   # un-skip + DRIVE (installed-CLI concurrent harness)
├── <charter epic golden-path test quarantined by 90d9be8823>  # un-skip + DRIVE
├── runtime/test_*concurrency*.py (NEW)           # deterministic apply-interleave + source-drift + warm-path + #4082-regression
├── _perf_helpers.py (NEW)                        # assert_timing_budget(measured, budget)
├── architectural/test_performance_marker_guard.py  # stays green (#3665)
└── <74 mixed across ~23 subsystems> + <9 vocab-blocked>  # split / remediate (#4015)
```

**Structure Decision**: Single project, two independent lanes. Cluster A concentrates in `runtime/`; Cluster B is test-tree-wide but mechanical.

## Complexity Tracking
No violations — section intentionally empty.

## Parallel Work Analysis

### Dependency Graph (refined per post-plan brownfield squad)
```
Lane A (#4017):
  WP-A0 RED-FIRST CAPTURE (before any code change): snapshot the exact "Global asset input
        changed" repro via the installed-CLI concurrent harness + the deterministic interleave;
        hand the red artifact to A1/A2 (role-tag alone flips the signal to "File exists", so it
        must be captured first — planner #1).
  ─► WP-A1 role-tag enabler (observe source/destination + check_assets compare-site filter);
        assert/document the intermediate "File exists" state after role-tag-alone (proves P1).
  ─► WP-A2 re-assess-under-lock fix + operator signal; un-skip+DRIVE both quarantined e2e;
        source-drift guard; FR-007 live-composition-interplay regression.
  ─► WP-A3 generic-scope acceptance: drive the real global_assets batch path through a
        NON-runtime owner + the merge.py recheck nesting; verify-or-exclude _recheck_command_completion
        (managed_skills.py:165, separate #4082 recheck) — the HiC "Generic" ruling must ship verified.
Lane B (#4015):
  WP-B1 assert_timing_budget helper + TRIAGE ALL delete candidates once (flake-rate + AST
        zero-functional-assert) → ONE consolidated operator sign-off (HiC) on the full list;
        owns the master per-split coverage-mapping table.
  ─► { WP-B2 vocab-blocked 9 ; WP-B3..Bn 74 mixed split — grouped by EFFORT not taxonomy
        (collapse 1-2-file subsystems into shared WPs; dedicated WPs only for heavy subsystems);
        each split WP appends rows to B1's master coverage-mapping table. }
```
Lanes A and B are **independent** (share only epic #1931) — parallelizable. Within each lane, the enabler/red-first WP precedes the rest.

### Work Distribution
- **Sequential within lane**: A1→A2; B1→(B2, B-split WPs).
- **Parallel**: Lane A and Lane B run concurrently; within Lane B the split WPs (grouped by subsystem) are parallel once B1 lands.
- **Agent assignments**: #4017 = python-pedro (high rigour — runtime concurrency); #4015 = python-pedro (mechanical); review = reviewer-renata (distinct). Profiles LOADED.

### Coordination Points
- WP-A2 must publish the operator-signal shape before its tests assert on it.
- WP-B1 (helper) must publish `assert_timing_budget` signature + the consolidated delete sign-off before the split/vocab WPs consume them.
- **Cross-lane shard-map conflict (planner #5):** BOTH lanes add/relocate test files, and every new/relocated test file must register in the single shared `tests/_next_shard_map.py` (Blacksmith completeness gate) — Lane A's new `tests/runtime/` concurrency tests and Lane B's 74-file split will both edit that one file → a real merge-conflict point. Serialize shard-map edits (or union-resolve at merge); do not treat the lanes as fully conflict-free. (`test_lane_dependency_cycle_performance.py` is NOT under `tests/runtime/`, so no file-level clash there — only the shard-map.)
- Acceptance oracles: the 2 un-skipped e2e tests + deterministic-interleave + the WP-A3 generic/merge-nesting drive (A); the #3665 guard + B1's master coverage-mapping + nightly-lane collection (B).

### HiC escalation points (operator-in-command)
- ✅ **check_assets scope** → resolved GENERIC (all owners) this plan.
- ⏳ **#4015 DELETE dispositions** → FRONT-LOADED: WP-B1 triages ALL candidates once (flake-rate + AST zero-functional-assert) into ONE consolidated operator sign-off (not ~25 scattered interrupts); split WPs execute pre-approved dispositions (FR-011/SC-010).
- ⏳ Any further fork surfaced by the post-plan/post-tasks brownfield squads.
