# Implementation Plan: Governed-State-Surface Coherence

**Branch**: `feat/governed-state-surface-coherence` | **Date**: 2026-06-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/governed-state-surface-coherence-01KVCGQC/spec.md`
**Merge target**: `main` (PR-bound). Planning/base branch: `feat/governed-state-surface-coherence`.

## Summary

Bind three governed-state surfaces to their existing canonical seams instead of re-deriving by hand, extract one cohesive merge-baseline unit out of an oversized command module, and repair the architectural CI gate that went red on `main` post-#2024. Technical approach is settled by a 4-agent live-verified pre-spec squad (see [research.md](./research.md) + [research/00-prespec-synthesis.md](./research/00-prespec-synthesis.md)). Four goals (A #2016, B #2009, C extract, D green-main); WP01 = Goal D so the rest lands on a green base.

## Technical Context

**Language/Version**: Python 3.11+ (CI matrix includes 3.12)
**Primary Dependencies**: typer, rich, ruamel.yaml, pytest, ruff, mypy (existing repo deps — **no new dependencies**)
**Storage**: filesystem (`meta.json`, `status.events.jsonl`, charter bundle `metadata.yaml`/`graph.yaml`) — N/A DB
**Testing**: pytest (`-n auto --dist loadfile`); markers `fast`/`integration`/`git_repo`/`architectural`; CI shards by marker. TDD-first; topology-true fixtures (full 26-char ULID, real coord paths)
**Target Platform**: Linux/macOS dev + CI (Ubuntu/macOS, Python 3.12 installed package, parallel)
**Project Type**: single (Python CLI package `src/specify_cli` + sibling `src/charter`)
**Performance Goals**: N/A (correctness/behavior-preserving mission)
**Constraints**: ruff+mypy clean, complexity ≤15, zero new suppressions; behavior-preserving for Goal C; structural-not-reactive for #2009; CI-condition verification for Goal D
**Scale/Scope**: 4 goals / 13 FRs / ~6 source modules + ~10 test files; ~204 LOC relocated; net new ~2 helpers

## Charter Check

*GATE: software-dev-default charter (compact mode). Directives DIR-001..013 active.*

- **DIR-001 (bounded-context integrity):** each fix adopts the ONE canonical seam (no second resolver/hash) — PASS by design (NFR-005, C-003).
- **DIR-013 (god-module decomposition):** Goal C advances it (merge.py 3460→~3256 LOC; tracked under epic #2026, sibling to doctor.py #1623) — PASS.
- **Terminology canon:** new module/prose use "Mission"; legacy `feature_dir`/`feature_slug` code identifiers are immutable, not renamed (scope discipline) — PASS.
- **No charter conflict.** Re-check post-design: none introduced (behavior-preserving + structural-residue downgrade do not touch governance vocabulary).

## Implementation Concern Map (IC-##)

Decomposition of architectural intent into ownership-disjoint concerns for `/tasks`. **WP ordering: IC-D first (WP01); IC-A / IC-B / IC-C are independent lanes on the greened base.**

| IC | Concern | Owned surfaces | Depends on | FRs | Ticket |
|----|---------|----------------|------------|-----|--------|
| **IC-D** (WP01) | Green main: repair the un-masked architectural gate | `tests/specify_cli/missions/test_read_path_resolver_validation.py` (markers); `tests/architectural/test_no_worktree_name_guess.py` (remove diff-scoped test + reconcile ratchet baselines) | — | FR-011, FR-012, FR-013 | #2025 |
| **IC-A** | #2016 orchestrator coord-read adoption | `src/specify_cli/orchestrator_api/commands.py`; `tests/specify_cli/regression/test_issue_1615_1616_1617_1618.py` (the #2016 class) | IC-D (green base) | FR-001, FR-002, FR-003, FR-004 | #2016 |
| **IC-B** | #2009 charter coherence (residue downgrade + JSON-safe + unlink-consolidation + pins) | `src/specify_cli/charter_runtime/freshness/computer.py`; `src/specify_cli/cli/commands/charter/{_status_collectors.py,status.py,_fresh_doctrine.py}`; `src/charter/synthesizer/project_drg.py`; charter tests | IC-D | FR-005..FR-009 | #2009 |
| **IC-C** | merge.py baseline extract (behavior-preserving) | `src/specify_cli/cli/commands/merge.py`; new `src/specify_cli/merge/baseline.py`; `src/specify_cli/merge/__init__.py`; baseline tests | IC-D | FR-010 | #2027 (epic #2026) |

**Ownership-overlap resolution (binding for `/tasks`):** the marker fix on `test_read_path_resolver_validation.py` is **D1's** and stays in **IC-D / WP01**, NOT in IC-A — so IC-A owns only `orchestrator_api/commands.py` + the #2016 regression test. No two ICs share `owned_files`.

**IC-B may split in `/tasks`** if the WP exceeds ~7 subtasks: a natural cut is IC-B1 (FR-005 JSON-safe + FR-008 pins — `status` surfaces) vs IC-B2 (FR-006 residue downgrade + FR-007 unlink-consolidation — `computer.py`/`project_drg.py`/`_fresh_doctrine.py`). C2-e (FR-009) lives with IC-B2 (live-repro-first). Decide grain at task time.

## Design notes per IC

- **IC-A:** prefer refactoring `_coord_mid8`'s cascade into a small shared helper that both `surface_resolver` and `_resolve_mission_dir` call (one sanctioned cascade, NFR-005), rather than duplicating the tier logic. Preserve `StatusReadPathNotFound` typed fail-closed. Fold `_fail -> NoReturn` + delete the two unreachable raises (FR-004). Fixture: coord-only, full 26-char ULID, no fake primary meta (C-001).
- **IC-B:** FR-006 — at `computer.py:345–357`, replace the terminal `invalid` return for `built_in_only ∧ graph-present` with a `built_in_only` report + a non-blocking "stale graph residue" diagnostic field (the reader trusts the manifest's declared authority). FR-007 — extract one `unlink_stale_project_graph(doctrine_dir)` helper called by both `project_drg.apply_post_condition` (:343) and `_fresh_doctrine` (:119). FR-005 — serialize the `status` payload JSON-safely (e.g. `default=str` or normalize `last_sync` to ISO string at the collector). FR-008 — pin C2-a (no mutator in status read path) + C2-d (sync/status/freshness hash agree). FR-009 — reproduce C2-e live first; fix-or-document.
- **IC-C:** move the 5 functions verbatim to `merge/baseline.py`; hoist `META_JSON = "meta.json"` for the moved occurrences; re-export `record_baseline_merge_commit`/`assert_baseline_merge_commit_on_target`/`BaselineMergeCommitError` via `merge/__init__.py`; `merge.py` imports them for its 2 call sites (:2675, :2842). No logic change (NFR-001).
- **IC-D:** D1 markers (`fast`→`integration`+`git_repo`); D2 delete/neutralize the mission-diff-scoped `test_nfr001_…`; D3 reconcile the 3 re-keyed ratchet baselines and **verify GREEN on CI** (NFR-003), not just local py3.11.

## Project Structure

```
src/specify_cli/
  orchestrator_api/commands.py        # IC-A
  charter_runtime/freshness/computer.py   # IC-B
  cli/commands/charter/{_status_collectors,status,_fresh_doctrine}.py  # IC-B
  cli/commands/merge.py               # IC-C (source)
  merge/baseline.py                   # IC-C (NEW)
  merge/__init__.py                   # IC-C (re-export)
src/charter/synthesizer/project_drg.py    # IC-B (unlink site)
tests/
  specify_cli/missions/test_read_path_resolver_validation.py  # IC-D (markers)
  architectural/test_no_worktree_name_guess.py                # IC-D (ratchets)
  specify_cli/regression/test_issue_1615_1616_1617_1618.py    # IC-A (#2016)
  specify_cli/merge/test_1827_baseline_regression.py + 8 more # IC-C net
```

## Brownfield checks (post-planning, pre-tasks) — OUTCOME

- **Foldable-issue search:** Goal C had no tracker home → new epic **#2026** + slice **#2027** filed (priti). #2016→#1868, #2009→#2007, #2025→#1931 wired. No other open issue folds in (the merge mega-function split stays a *future* slice under #2026; out of scope here per C-002).
- **Split-brain / LOC scan:** touched modules — `commands.py` 1398, `computer.py` 464, `_status_collectors.py` 445, `status.py` 311, `merge.py` 3460 (the extract trims it ~204). No split-brain duplication introduced; IC-A consolidates a duplicated cascade (reduces split-brain).
- **Deprecation check:** no due/overdue deprecations in the touched files (the `merge.py:1338` one-shot is the `--feature` alias warning, unrelated; not removed here). Nothing to remove this mission.
- **Topology:** mission flattened (no coordination_branch) — planning artifacts all on `feat/governed-state-surface-coherence`.

## Phase 0 / Phase 1 status

- **Phase 0 (research):** COMPLETE — [research.md](./research.md) re-verifies the full census against HEAD `9f98d89fe`; all decisions of record D-1..D-5 recorded. No open NEEDS CLARIFICATION.
- **Phase 1 (design):** no new data model / API contracts — this is a brownfield bug-fix + behavior-preserving-refactor mission against existing surfaces (the "contracts" are the existing typed errors, the `_coord_mid8` cascade, the freshness sub-state vocabulary, and the baseline function signatures). `data-model.md` / `contracts/` intentionally omitted (N/A); the IC Map above is the design artifact `/tasks` consumes.

## Branch contract (restated)

- Current branch at plan start: `feat/governed-state-surface-coherence`
- Planning/base branch: `feat/governed-state-surface-coherence`
- Final merge target: `main` (via PR)
- `branch_matches_target`: true

**Next command:** `/spec-kitty.tasks` (decompose the IC Map into work packages; WP01 = IC-D).
