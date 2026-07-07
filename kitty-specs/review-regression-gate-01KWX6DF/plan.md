# Implementation Plan: Auto-scoped review-time regression gate

**Branch**: `fix/review-regression-gate` | **Spec**: [spec.md](./spec.md)
**Issues**: Closes #572 + the per-WP review-blind-spot facet of #1979; Part of #2283 (M5 Phase 1)

## Summary

Today `move-task --to for_review` (`cli/commands/agent/tasks_move_task.py`) runs no tests and review is scoped to `owned_files`, so a WP that breaks a **consumer** outside its owned set reaches approval unnoticed (the #970 class). This mission adds a **warn-by-default, opt-in-block regression gate** at that transition:
1. **Derive the affected shards** from the WP's changed files via `_gate_coverage.aggregate_filter_groups()`, keyed on group shape: a **per-shard group** (carries `tests/**`) → its test globs; a **composite group** (src-only) → the census `_COMPOSITE_ROUTING` cone_roots for that dir. **Exclude catch-all groups** (`core_misc`/`e2e`/`any_src`) so cost stays bounded. (Read-only; guarded by an arch invariant covering BOTH shapes + the exclusion, so it can't drift from CI routing.)
2. **Run only those shards at head**, parse their JUnit, and compute **new failures** = `head_failures − base_failures` via `review/baseline.py`'s existing **JUnit parser + `diff_baseline`**. The shard-scoped invocation + the head-side run are **net-new** (baseline.py has neither); the parser + diff are the genuine reuse.
3. **Verdict → gate**: warn by default (surface + allow), block on new failures only when `review.fail_on_pre_review_regression` is on, with a `--force` escape recorded in the transition evidence. Overrides: frontmatter `pre_review_test_scope` > config `review.pre_review_test_command` > census-derived default.

## Technical Context
**Language/Version**: Python 3.11+
**Primary Dependencies**: existing internals only — `specify_cli.review.baseline` (JUnit parser + `diff_baseline`), `tests/architectural/_gate_coverage.py` (`aggregate_filter_groups`/`_parse_filter_groups`), `specify_cli.status.emit` / the `for_review` transition, `pytest` (subprocess-invoked for the scoped run). No new third-party deps.
**Storage**: files — the baseline JUnit + census/`ci-quality.yml` are read; no DB.
**Testing**: `pytest` — unit tests for the scope-derivation + verdict; an integration test driving `move-task --to for_review` with a fixture WP that breaks a consuming shard; an architectural invariant test for FR-006.
**Target Platform**: Linux/macOS dev + CI (the spec-kitty CLI).
**Project Type**: single (CLI/library).
**Performance Goals**: bounded review-time cost — run the affected shards only (a WP touching one cone runs ~that shard), never the whole `tests/` tree (NFR-002/FR-005).
**Constraints**: warn-default non-breaking rollout (NFR-001); no reverse-import-graph; read-only on `ci-quality.yml` (C-002); `ruff` + `mypy --strict` clean, no new suppressions (C-003).
**Scale/Scope**: one new module (the affected-shard scope + head-runner), a gate hook in `tasks_move_task.py`, config keys, an arch invariant test, fixtures. Small-to-medium, cohesive.

## Charter Check
*GATE: passes.* Reuses canonical surfaces (`review/baseline.py`, `_gate_coverage.py`) rather than reinventing (Canonical-Sources principle); single-source scope derivation with an arch invariant (Architectural-Gate-Discipline); warn-default rollout (no breakage); ATDD — the non-vacuous fixture (a WP that genuinely breaks a consumer, SC-001) is red-first. No new suppressions. No terminology drift.

## Project Structure

### Documentation (this mission)
```
kitty-specs/review-regression-gate-01KWX6DF/
├── plan.md · spec.md · tasks.md · tasks/ · research.md (optional) · contracts/
```

### Source Code (repository root)
```
src/specify_cli/review/
├── baseline.py                     # REUSE the JUnit parser + diff_baseline (unchanged)
└── pre_review_gate.py              # NEW: affected-shard derivation + head-side scoped runner + verdict
src/specify_cli/cli/commands/agent/
└── tasks_move_task.py              # HOOK: run the gate on --to for_review (warn/block/--force)
tests/architectural/
└── test_pre_review_scope_singlesource.py  # NEW: FR-006 invariant (derivation reads the live dorny groups + census)
tests/review/  (or tests/specify_cli/review/)
└── test_pre_review_gate.py         # NEW: scope-derivation + new-failure verdict + integration + override precedence
```
**Structure Decision**: one new `review/pre_review_gate.py` (scope + runner + verdict), a minimal hook in `tasks_move_task.py`, and the config keys — keeping `baseline.py` untouched (reuse its parser/diff) and `ci-quality.yml` read-only.

## Implementation Concern Map

### IC-01 — Affected scope (two group shapes + catch-all exclusion) + head-side scoped runner + new-failure verdict
- **Purpose**: derive the affected test set from changed files — per-shard groups' `tests/**` globs via `aggregate_filter_groups()` + composite groups' census `_COMPOSITE_ROUTING` cone_roots, excluding the catch-alls (`core_misc`/`e2e`/`any_src`) — run those at head, compute new-failures via baseline.py's parser + `diff_baseline`.
- **Relevant requirements**: FR-002, FR-003, FR-005, FR-006, NFR-002, C-001.
- **Affected surfaces**: `src/specify_cli/review/pre_review_gate.py` (new), `tests/architectural/test_pre_review_scope_singlesource.py` (new). Reads `review/baseline.py`, `_gate_coverage.py` (`aggregate_filter_groups` + `_COMPOSITE_ROUTING`).
- **Sequencing/depends-on**: none.
- **Risks**: composite dirs silently under-covered if only `aggregate_filter_groups()` is consulted (mitigate: the FR-006 invariant asserts BOTH shapes); catch-all groups exploding cost (mitigate: the exclusion set + surfaced count); recall>precision must not re-admit the catch-alls.

### IC-02 — The `for_review` gate hook + config/override precedence + warn/block/--force
- **Purpose**: wire the verdict into the `move-task --to for_review` transition — warn by default, opt-in block, overrides + `--force` recorded in evidence.
- **Relevant requirements**: FR-001, FR-004, NFR-001.
- **Affected surfaces**: `src/specify_cli/cli/commands/agent/tasks_move_task.py` (hook), config schema (`review.fail_on_pre_review_regression`, `review.pre_review_test_command`), WP frontmatter `pre_review_test_scope`, `tests/review/test_pre_review_gate.py` (new integration + precedence).
- **Sequencing/depends-on**: IC-01 (needs the verdict).
- **Risks**: blocking a transition that should warn (mitigate: warn-default NFR-001 + `--force`); baseline uncomputable → must degrade to warn, never hard-block (FR-003 edge). Pre-merge finding: `review.fail_on_pre_review_regression` is inert without `review.test_command` also configured (no baseline is ever captured, so the verdict can only be `no_coverage`/`unverified_baseline`, never `NEW_FAILURES`) — mitigated by an explicit, non-dim console warning naming the `review.test_command` prerequisite instead of a silent dim advisory (see `contracts/review-regression-gate-contract.md`).
