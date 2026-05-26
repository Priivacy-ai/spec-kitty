# Spec — Test Stabilization & Architectural Debt Pass

**Mission ID:** 01KSF9HJBFKRBC617JVHKZXNE2
**Mission slug:** test-stabilization-and-debt-pass-01KSF9HJ
**Mission type:** software-dev
**Target branch:** main
**Status:** Draft
**Predecessor mission:** `charter-ux-and-org-pack-vocabulary-01KSAF14` (#122, merged 2026-05-24)
**Sources:** GitHub issue [#1298](https://github.com/Priivacy-ai/spec-kitty/issues/1298) (test failures), [#1163](https://github.com/Priivacy-ai/spec-kitty/issues/1163) (issue-matrix scaffolding), [`docs/engineering_notes/architectural-review/2026-05-25-deep-dive-architectural-review.md`](../../docs/engineering_notes/architectural-review/2026-05-25-deep-dive-architectural-review.md) §6.

---

## Overview

The just-merged mission #122 left two visible debts:

1. **Test fragility**: a full `pytest tests/` run reports 251 failures (217 pre-existing per #1298, +34 unrelated to the cutover per the mission-review investigation). 9 of the 251 were already closed in commit `64ddadc5f` via the protected-branch-guard bypass. The remaining 242 cluster across `tests/sync/`, `tests/test_dashboard/`, and `tests/tasks/` with different root causes that need targeted fixes.

2. **Small architectural debts**: Architect Alphonso's deep-dive review identified five logical-duplication findings (LD-1..LD-5) and two module-scope findings (MS-1, MS-2). The two highest-leverage items — LD-1 (consolidate `_apply_org_overrides` / `_apply_project_overrides`) and MS-1 (split `cli/commands/charter.py` per subcommand) — are tightly scoped and can land alongside the test fixes without expanding the mission.

This mission addresses both concerns in a single deliberate pass. It is **not** a full architectural overhaul — that would be `Beads state` (#1168) or a separate epic. This is a debt-repayment mission sized to ~6-8 work packages.

---

## Primary scenarios

### Scenario T — Triaged test stabilization (FR-001..FR-005)
An operator runs `pytest tests/ -q` on `main`. The current failure baseline drops from 242 to a documented sub-set, with each remaining failure either fixed in this mission, traced to a sub-mission-worthy follow-up issue, or explicitly marked `@pytest.mark.skip` with a documented rationale.

### Scenario A — Architectural debt consolidation (FR-006..FR-008, FR-013, FR-014)
A future contributor reading `src/doctrine/base.py` sees ONE overlay-application method instead of two near-identical ones (FR-006 / LD-1). A future contributor wiring a new `spec-kitty charter ...` subcommand opens ONE file (the new subcommand-specific module under `cli/commands/charter/`) rather than appending to a 3,328-line monolith (FR-007 / MS-1). A reader inspecting how freshness is computed sees it route through the canonical chokepoint, not duplicate the manifest-read logic (FR-013 / LD-3). And the four charter-runtime concerns (lint, freshness, preflight, facade) live under one umbrella package rather than spelled four times as siblings under `specify_cli/` (FR-014 / LD-5).

### Scenario Q — Small quality follow-ups (FR-009..FR-012, FR-015)
- `/spec-kitty.tasks` scaffolds `issue-matrix.md` when the mission references GitHub issues (#1163).
- The retrospective auto-generator mines `status.events.jsonl` for `--force` / arbiter transitions and surfaces them as `helped` / `not_helpful` entries (closes the F-04 finding from 01KSAF14).
- `WPMetadata` gains an optional `tracker_refs: list[str]` field that the orchestrator can populate per DIR-012 (closes F-10).
- The bulk-edit gate's allowed action vocabulary is documented in a discoverable place (closes F-01).
- **Two finalize-tasks fixes landed during this mission's own scaffolding** (commits `0f4e1a383` linter + `72ff0d723` lane-depth) get regression test coverage so they don't regress (FR-015). Surfaced when running `finalize-tasks` against this very mission.

---

## Functional Requirements

| ID | Description | Status | Source |
|---|---|---|---|
| **FR-001** | Triage the remaining 242 failures from #1298 by test file and cluster. Produce a `triage.md` document in the mission directory enumerating each cluster, its hypothesised root cause, and its resolution (fix-here / sub-issue / skip). | Draft | #1298 |
| **FR-002** | Fix the `tests/sync/test_events.py` `ModuleNotFoundError` cluster (~27 failures). Root cause is likely a vendored-events import path that drifted; document the fix in the WP commit message. | Draft | #1298 |
| **FR-003** | Fix `tests/test_dashboard/test_scanner.py::test_build_event_log_kanban_stats_tolerates_weighted_progress_failure`. | Draft | #1298 |
| **FR-004** | Fix `tests/tasks/test_move_task_git_validation_unit.py::test_move_for_review_from_worktree_does_not_mirror_commit_to_lane_branch` (assertion mismatch on commit message). | Draft | #1298 |
| **FR-005** | After fixes land, the `pytest tests/ -q` baseline MUST drop by at least 70% of the 242 starting failures. Failures NOT closed in this mission MUST be filed as follow-up sub-issues (#1298a, #1298b, etc.) with a one-line root-cause hypothesis and a per-failure suite list. | Draft | #1298 |
| **FR-006** | Consolidate `_apply_org_overrides` and `_apply_project_overrides` in `src/doctrine/base.py` into a single `_apply_overlay_layer(dirs, layer_name, *, built_in)` method. Existing tests of the merge behaviour MUST continue to pass without modification. (LD-1) | Draft | review §2 |
| **FR-007** | Split `src/specify_cli/cli/commands/charter.py` (3,328 lines) into a per-subcommand package `src/specify_cli/cli/commands/charter/` with one module per subcommand (`status.py`, `sync.py`, `synthesize.py`, `lint.py`, `preflight.py`, `bundle.py`, `resynthesize.py`). The typer registration pattern stays. No behavioural change. (MS-1) | Draft | review §3 |
| **FR-008** | The 5 augmentation field test files (`tests/doctrine/test_{tactic,styleguide,paradigm,procedure,agent_profile}_augmentation_fields.py`) are consolidated into ONE parametrised test file (~80 lines vs ~250 today). Coverage parity required. (LD-2) | Draft | review §2 |
| **FR-009** | `/spec-kitty.tasks` scaffolds `kitty-specs/<slug>/issue-matrix.md` when the mission spec references GitHub issue numbers in its `spec.md` (closes #1163; partially closes F-08 of mission 01KSAF14). | Draft | #1163 |
| **FR-010** | The retrospective auto-generator at `spec-kitty retrospect create` mines `status.events.jsonl` for `--force` transitions, arbiter overrides, and rejection cycles. Each becomes a finding entry. (Closes F-04 of mission 01KSAF14.) | Draft | F-04 |
| **FR-011** | `WPMetadata` Pydantic model gains an optional `tracker_refs: list[str]` field. The `map-requirements` and `move-task` commands accept the field. (Closes F-10 of mission 01KSAF14.) | Draft | F-10 |
| **FR-012** | The bulk-edit gate's allowed action vocabulary (`do_not_change`, `manual_review`, `rename`, `rename_if_user_visible`) and required top-level `target:` block are documented in a discoverable location (a `docs/reference/bulk-edit-gate.md` or equivalent). The `spec-kitty-bulk-edit-classification` skill prose is updated to match. (Closes F-01 of mission 01KSAF14.) | Draft | F-01 |
| **FR-013** | Route `src/specify_cli/charter_freshness/computer.py` manifest + graph reads through `charter.compiler.ensure_charter_bundle_fresh` (or a read-only sibling) so the chokepoint's refresh semantics apply to freshness reporting under concurrent invocation. Preserves the existing public `compute_freshness(repo_root) -> CharterFreshness` API. (Closes LD-3 / RISK-2 from the mission-review.) | Draft | review §2 LD-3 |
| **FR-014** | Group `charter_lint/`, `charter_freshness/`, `charter_preflight/` (and the existing `charter/` facade) under a single `src/specify_cli/charter_runtime/` umbrella package. Each becomes a submodule (`charter_runtime.lint`, `charter_runtime.freshness`, `charter_runtime.preflight`, `charter_runtime.facade`). Existing imports survive via top-level re-export shims for one release. (Closes LD-5.) | Draft | review §2 LD-5 |
| **FR-015** | Lock the finalize-tasks linter+lane-depth fixes (commits `0f4e1a383` and `72ff0d723` on `main`) with regression tests: (a) a unit test asserting that a WP frontmatter with explicit `owned_files: []` does NOT trigger body-text inference; (b) a unit test for `_compute_lane_depths` against a deliberately-cycle lane-deps graph asserts no recursion blow-up and produces a deterministic depth dict. Document the two fixes in `docs/reference/finalize-tasks-internals.md` (NEW). | Draft | self-surface (Slice Q escalation) |

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|---|---|---|---|
| **NFR-001** | Final `pytest tests/ -q` failure count on `main` after this mission lands. | ≤ 75 failures (from the current 242) | Draft |
| **NFR-002** | FR-006 and FR-007 MUST be behaviour-preserving. The doctrine layer-merge integration tests + the charter-subcommand integration tests MUST be green at HEAD before and after. | 0 behavioural regressions | Draft |
| **NFR-003** | Every new public symbol introduced by FR-009..FR-012 MUST be documented in user-visible reference docs (matching the NFR-002 of the predecessor mission). | 100% public-symbol coverage | Draft |
| **NFR-004** | Mission total work packages ≤ 10. With LD-3 (FR-013) and LD-5 (FR-014) pulled in-scope per HiC direction, the original 8-WP ceiling was raised by 2. If scope creeps past 10 WPs during planning, the stretch items (FR-008 test parametrisation, FR-012 bulk-edit-gate docs) are dropped from this mission and re-filed as separate sub-missions. FR-013 and FR-014 are NOT droppable — they were promoted to mission scope by explicit HiC direction. | ≤ 10 WPs | Locked |

## Constraints

| ID | Description | Status |
|---|---|---|
| **C-001** | The protected-branch guard bypass (`SPEC_KITTY_TEST_MODE` / `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS`) landed in commit `64ddadc5f` (rebased into mission #122's squash). Tests written for this mission MAY rely on it; production code MUST NOT introduce a new bypass path. | Locked |
| **C-002** | FR-006 (LD-1 consolidation) MUST cross-reference the ratified merge-semantics ADR `architecture/3.x/adr/2026-05-16-1-doctrine-layer-merge-semantics.md`. The consolidation does not change semantics; it makes the identical-by-design intent visible. | Locked |
| **C-003** | FR-007 (MS-1 split) MUST NOT delete the existing typer registration pattern. The split moves each subcommand handler to its own module but the `@app.command()` decorators stay typed against `charter_app`. | Locked |
| **C-004** | A `triage.md` (FR-001) is the FIRST WP. Without the triage document, the rest of the test-fix WPs cannot scope their work. | Locked |
| **C-005** | Linked GitHub issues (#1298, #1163) MUST be assigned to the HiC per DIR-012 when their respective WPs start implementing. | Locked |
| **C-006** | Any failure NOT closed in this mission MUST land in a follow-up issue with a non-trivial root-cause hypothesis. "Failure too broad — defer" is not an acceptable hypothesis. | Locked |
| **C-007** | FR-013 (chokepoint routing) MUST preserve the existing public API of `charter_freshness.compute_freshness`. Existing tests under `tests/specify_cli/charter_freshness/` MUST continue to pass without modification. The change is internal: the function delegates its reads instead of duplicating them. | Locked |
| **C-008** | FR-014 (charter_runtime/ umbrella) MUST leave top-level shim re-exports at the old paths (`src/specify_cli/charter_lint/__init__.py`, etc.) for one release cycle so external importers do not break in lock-step with the mission merge. A CHANGELOG entry MUST flag the canonical new import path AND the deprecation window for the shims. | Locked |

---

## Success criteria (measurable)

1. **Test-suite recovery.** `pytest tests/ -q` on `main` post-mission reports ≤ 75 failures (NFR-001). Each remaining failure has a follow-up issue linked from `triage.md`.
2. **Logical duplication closed (LD-1).** `git grep "def _apply_.*_overrides" src/doctrine/base.py` returns at most one definition.
3. **Module-scope improved (MS-1).** `wc -l src/specify_cli/cli/commands/charter.py` returns 0 (file removed) OR ≤ 150 (kept only as the typer-app wiring shim). The new per-subcommand modules under `src/specify_cli/cli/commands/charter/` are each ≤ 500 lines.
4. **Quality fixes verified.** Each of FR-009..FR-012 has a regression test exercising the new behaviour.
5. **Chokepoint routing closed (LD-3 / RISK-2).** `git grep -n "_safe_load_yaml\|.kittify/charter/synthesis-manifest\|.kittify/doctrine/graph.yaml" src/specify_cli/charter_freshness/` returns no direct reads outside the chokepoint adapter. The conflict-resolution rule (data-model §6) still surfaces correctly.
6. **Package umbrella landed (LD-5).** `ls -d src/specify_cli/charter_runtime/*/` shows the three submodules; the shim `__init__.py` files at the old paths re-export the new canonical paths; existing imports of `from specify_cli.charter_lint import ...` continue to resolve.

---

## Key entities

- **TestFailureCluster** (transient triage entity, scoped to `triage.md`): a set of failures sharing a hypothesised root cause. Has fields: `id` (e.g. `cluster-sync-events`), `test-files` (list), `failure-count`, `hypothesised-cause`, `resolution` (one of: `fixed-in-WP-XX`, `deferred-to-issue-NNNN`, `accepted-skip-with-rationale`).
- **OverlayLayer** (new in FR-006): a layer in the doctrine-merge order. Today: `built-in`, `org`, `project`. The consolidated method makes the layer enumerable.

## Out of scope

- LD-3 (charter_freshness chokepoint bypass) — **pulled IN scope per HiC direction (2026-05-25); see FR-013.**
- LD-5 (charter_runtime/ umbrella) — **pulled IN scope per HiC direction (2026-05-25); see FR-014.**
- LD-4 (unified `PreflightResult` base) — too design-y for this debt-pass; flagged for 3.3.0.
- MS-2 (specify_cli/ over-decomposition) — moratorium-pattern, not in-pass code change.
- The `Beads state` epic (#1168) and the schema-versioning launch-blocker cluster (#1200/#1203/#1281) — separate epics.

## Assumptions

- The 27 `tests/sync/test_events.py` failures share a single root cause (vendored-events import drift). If triage reveals N independent root causes, FR-002 is scoped to the largest cluster and the rest become sub-issues.
- FR-007 (charter.py split) does not require touching any consumer outside `src/specify_cli/cli/`. Importers that reference `src.specify_cli.cli.commands.charter` survive via a re-export in the new package's `__init__.py`.

## Open questions

1. Should FR-007 be split into two WPs (one for the package skeleton, one for moving handlers) or done in a single WP with careful staging? — Planner Priti to decide.
2. Should the bulk-edit-gate documentation (FR-012) live in `docs/reference/` or under `.kittify/doctrine/`? — Curator Carla to decide.
