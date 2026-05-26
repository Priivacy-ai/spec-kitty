---
work_package_id: WP01
title: 'Wave 1 foundation: ADR + lint built-in fallback (FR-001..FR-004)'
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-ux-and-org-pack-vocabulary-01KSAF14
base_commit: 4edf744726c903f243b9e25a74efa30311f114a9
created_at: '2026-05-24T08:34:15.892047+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "1024099"
history:
- by: claude
  at: '2026-05-23T13:30:00+00:00'
  action: generated
agent_profile: python-pedro
authoritative_surface: src/specify_cli/charter_lint/
execution_mode: code_change
mission_id: 01KSAF14K8FZ56MHYT45EGWHHC
mission_slug: charter-ux-and-org-pack-vocabulary-01KSAF14
owned_files:
- architecture/3.x/adr/2026-05-DD-1-charter-freshness-ux-contract.md
- src/specify_cli/charter_lint/_drg.py
- src/specify_cli/charter_lint/engine.py
- src/specify_cli/charter_lint/findings.py
- src/specify_cli/charter_lint/__init__.py
- tests/specify_cli/charter_lint/test_engine.py
- tests/specify_cli/charter_lint/test_drg_fallback.py
priority: P0
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this work package, invoke the `/ad-hoc-profile-load` skill with argument `python-pedro`. Pedro's primary focus (Python 3.12+, pytest, type hints, pydantic, pathlib) matches every subtask in this WP. The profile sets your identity, governance scope (DIR-005..009 quality gates), and avoidance boundary (no design decisions — those are locked in `plan.md` and the ADR you will author here). After the profile is loaded, return here and continue with Objective.

## Objective

Land ADR-1, run the DIR-013 pre-existing test baseline, assign issue #1099 to the HiC (DIR-012), then implement the `charter lint` built-in fallback so a fresh-checkout project with no synthesized DRG no longer reports an empty `No decay detected / Scanned 0 nodes`. Introduce a tri-state `GraphState` enum (`merged` / `built_in_only` / `missing`) on `DecayReport` and propagate it through the CLI banner and `--json` output.

## Branch strategy

- Planning base branch: `main`
- Merge target branch: `main`
- Execution worktree: allocated by `finalize-tasks` (see `lanes.json` once that command runs). Do NOT create a worktree by hand.

## Context

Read these documents before starting:

- `kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/spec.md` — FR-001..FR-004
- `kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/plan.md` — Wave 1 row
- `kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/research.md` — R-1..R-4 decisions
- `kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/data-model.md` — §3 `DecayReport`
- `kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/contracts/charter-lint-json.md` — JSON shape
- `kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/research/mission-brief.md` — §2 Thread A row for #1099
- Existing source: `src/specify_cli/charter_lint/_drg.py`, `engine.py`, `findings.py`, `src/specify_cli/cli/commands/charter.py:charter_lint` (around line 3082)

## Subtask details

### T001 — ADR-1 (`2026-05-DD-1-charter-freshness-ux-contract.md`)

**Files**: `architecture/3.x/adr/2026-05-DD-1-charter-freshness-ux-contract.md` (NEW)

Replace `DD` with today's day-of-month (UTC).

Outline content per plan.md Cross-cutting table row:
- **Problem**: Issues #1099, #1100, #1101, #1104 — fragmented freshness signals.
- **Decision**: Introduce `graph_state` tri-state enum on `DecayReport`, freshness sub-payload on `charter status --json`, and a new `charter preflight` surface.
- **Alternatives considered**: Eager auto-refresh on every CLI invocation (rejected: NFR-001 budget).
- **Consequences**: Cross-references ADR `2026-05-16-1-doctrine-layer-merge-semantics.md`. Establishes the foundation for WP02-WP04.

### T002 — DIR-013 pre-existing test baseline

Run `PWHEADLESS=1 pytest tests/ -q` once and capture the output. If non-zero failures exist, open a GitHub issue per DIR-013:
- Title: `Pre-existing test failures observed during mission 01KSAF14`
- Body: command run, failure summary, justification why pre-existing.
- Link the issue from this WP's notes.

If the baseline is green, document that in the WP completion notes — no GH issue needed.

### T003 — DIR-012 assign #1099 to HiC

```bash
unset GITHUB_TOKEN
gh issue edit 1099 --add-assignee @stijn-dejongh --repo Priivacy-ai/spec-kitty
```

Confirm the assignment is reflected in `gh issue view 1099`.

### T004 — Add `GraphState` enum + `DecayReport.graph_state`

**Files**: `src/specify_cli/charter_lint/findings.py`

```python
from enum import StrEnum

class GraphState(StrEnum):
    MERGED = "merged"
    BUILT_IN_ONLY = "built_in_only"
    MISSING = "missing"
```

Extend `DecayReport`:
```python
class DecayReport(BaseModel):
    findings: list[LintFinding]
    scanned_at: str
    feature_scope: str | None
    duration_seconds: float
    drg_node_count: int
    drg_edge_count: int
    graph_state: GraphState  # NEW (default to MISSING via builder if you prefer)
```

Update `to_json()` to emit `graph_state` at the top level. Add `GraphState` to `__init__.py` public exports (charter `__all__` convention).

### T005 — Built-in fallback in `_drg.load_merged_drg`

**Files**: `src/specify_cli/charter_lint/_drg.py`

Change the signature to return both the graph and a `GraphState`:
```python
def load_merged_drg(repo_root: Path) -> tuple[Any | None, GraphState]:
    ...
```

Resolution order:
1. Try `.kittify/doctrine/graph.yaml` (and the legacy `merged_drg.json` / `drg.json` / `compiled_drg.json` fallbacks). If found → `(graph, MERGED)`.
2. If not found, try to load the built-in DRG via `doctrine.shared.resolve_doctrine_root() / "graph.yaml"`. If found → `(graph, BUILT_IN_ONLY)`.
3. Otherwise → `(None, MISSING)`.

Read DEFAULT shipping graph via `charter.catalog.resolve_doctrine_root()` (already imported elsewhere in this package).

### T006 — Wire `LintEngine.run()` + banner + JSON

**Files**: `src/specify_cli/charter_lint/engine.py`, `src/specify_cli/cli/commands/charter.py`

`engine.py`:
- Unpack the new tuple from `load_merged_drg`.
- On `GraphState.MISSING`: return an empty `DecayReport` with `graph_state=MISSING`.
- On `GraphState.BUILT_IN_ONLY`: run all checkers against the built-in graph; mark report `graph_state=BUILT_IN_ONLY`.
- On `GraphState.MERGED`: existing behaviour; mark `graph_state=MERGED`.

`charter.py::charter_lint`:
- After running the engine, branch the human banner on `report.graph_state` per `contracts/charter-lint-json.md` table.
- Ensure the per-layer markers (`[built-in]`, `[org:...]`, `[project]`) stay as-is.
- `--json` output already emits via `report.to_json()`, so FR-004 should be satisfied by T004.

### T007 — Tests for FR-001..FR-004

**Files**: `tests/specify_cli/charter_lint/test_engine.py` (extend), `tests/specify_cli/charter_lint/test_drg_fallback.py` (NEW)

Cases:
1. `test_lint_missing_graph_returns_missing_state` — repo with no graph file at all → `graph_state=MISSING`, banner says "no lintable graph".
2. `test_lint_built_in_only_returns_built_in_only_state` — repo with charter but no project DRG → `graph_state=BUILT_IN_ONLY`, banner mentions running `synthesize`.
3. `test_lint_merged_state_unchanged` — repo with project DRG → `graph_state=MERGED`, existing banner.
4. `test_lint_json_includes_graph_state` — `report.to_json()` parses and contains `"graph_state"`.

Use existing fixtures under `tests/specify_cli/charter_lint/conftest.py` as templates.

## Definition of Done

- [ ] ADR-1 file exists and references `2026-05-16-1-doctrine-layer-merge-semantics.md`.
- [ ] DIR-013 baseline documented (issue link OR "green baseline" note).
- [ ] Issue #1099 assigned to HiC.
- [ ] `GraphState` exported from `specify_cli.charter_lint`.
- [ ] `DecayReport.graph_state` populated by `LintEngine.run()` in all three branches.
- [ ] Human banner branches on `graph_state` per contract table.
- [ ] `charter lint --json` payload includes `graph_state` top-level key.
- [ ] `pytest tests/specify_cli/charter_lint/ -v` passes.
- [ ] `mypy --strict` passes on touched files.
- [ ] `ruff check` passes.

## Risks

- **Cyclic import**: pulling `charter.catalog.resolve_doctrine_root` into `charter_lint._drg` could create a cycle. Mitigation: lazy import inside the function (matches existing pattern at line 32-46 of `_drg.py`).
- **Test fixture drift**: existing `tests/integration/test_charter_lint_lints_all_layers.py` may assert on the old banner text. If so, update the assertions and document in the WP notes.

## Reviewer guidance

Reviewer should verify:
1. The ADR captures the actual decisions (R-1..R-4), not pseudo-prose.
2. No silent fallback semantics introduced — every branch of `load_merged_drg` returns an explicit `GraphState`.
3. The CLI banner change matches `contracts/charter-lint-json.md` exactly (the contract is the authoritative source).

## Activity Log

- 2026-05-24T08:34:16Z – claude:opus-4-7:python-pedro:implementer – shell_pid=928380 – Assigned agent via action command
- 2026-05-24T08:56:09Z – claude:opus-4-7:python-pedro:implementer – shell_pid=928380 – Ready for review: FR-001..FR-004 + DIR-013 baseline (#1298) + ADR-1 at 2026-05-24-1 + #1099 assigned. 84 charter-lint tests pass, ruff clean on diff.
- 2026-05-24T08:56:49Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1024099 – Started review via action command
- 2026-05-24T08:59:07Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1024099 – Review passed: GraphState tri-state landed (merged/built_in_only/missing), ADR-1 at 2026-05-24-1 with cross-reference to 2026-05-16-1, #1099 assigned to HiC, DIR-013 baseline filed as #1298, banner branches per contract table, load_merged_drg returns tuple per data-model §3, 84/84 charter-lint tests pass, ruff clean, live JSON sanity verified all three states. Single integration test failure (test_charter_lint_lints_all_layers) is pre-existing subprocess/install env issue, not introduced by this WP.
- 2026-05-24T11:46:49Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1024099 – Done override: Feature merged to main as squash commit 37407a3b2; status carried through from mission branch
