# Data Model — agent/tasks.py decomposition

This is a structural refactor; the "entities" are the target module topology and the
contracts between the residual shim and the extracted seams. No runtime data schema changes.

## Target module topology

```
src/specify_cli/cli/commands/agent/
├── tasks.py                       # RESIDUAL SHIM: typer `app` + 9 thinned command handlers + orchestration glue
├── tasks_outline.py               # SEAM 1: tasks.md / manifest parsing, WP-id resolution
├── tasks_materialization.py       # SEAM 2: frontmatter & file persistence, markdown-row mutation
├── tasks_finalize_validation.py   # SEAM 3: dependency/cycle validation, lane metadata, bootstrap glue
├── tasks_dependency_graph.py      # SEAM 4: dependency readiness / dependent-gating glue
└── tasks_parsing_validation.py    # SEAM 5: readiness / verdict / issue-matrix validation
```

> The final seam set and file names are a plan-phase decision; this is the research recommendation.
> Commit-routing logic (the 3 tails) routes through the existing `coordination/commit_router.py:commit_for_mission`
> rather than into a new seam — the router is the canonical home.

## Entities & relationships

| Entity | Role | Relationships |
|--------|------|---------------|
| `tasks.py` (shim) | Owns the typer `app` and all `@app.command` signatures (the frozen public contract). Each handler unpacks options, calls seams, emits results. | imports → all 5 seams + `commit_for_mission`; **never imported BY a seam** (one-way) |
| Seam modules (×5) | Pure-ish, independently-importable units of extracted logic. Each carries focused tests. | may import each other (e.g. materialization → outline) and shared deps; never import the shim |
| Shared module constants/types | `TASKS_MD_FILENAME`, `SPEC_MD_FILENAME`, `_QUALIFIED_TASK_ID_RE`, `_VALID_VERDICTS`, `_FORWARD_ORDER`, `_RUNTIME_STATE_DENY_LIST`, WP/inline regexes, `TaskIdResolutionOutcome/Format`, `TaskIdResult` | relocated to the seam that owns them or a small shared module; re-exported from `tasks.py` if any test/CLI imports them by path |
| `commit_for_mission` (existing) | Canonical commit router; the 3 tails call it. | consumed by shim handlers `move_task`, `mark_status`, `map_requirements` |
| Mega-functions (to sub-decompose) | `move_task`(778), `status`(483), `map_requirements`(382), `_validate_ready_for_review`(348), `finalize_tasks`(218), `mark_status`(265) | each split into ≤15-CC helpers distributed to seams + a thin orchestrating body in the shim |

## Invariants (must hold after refactor)

- **INV-1** The set of typer commands, their names, arguments, flags, and exit codes is byte-identical to pre-refactor (FR-001/C-001). Verified by golden CLI test.
- **INV-2** Import direction is acyclic: shim → seams → shared deps. No seam imports `tasks.py`.
- **INV-3** Every function (shim or seam) has cyclomatic complexity ≤ 15 (NFR-001).
- **INV-4** The 3 commit tails reach git **only** via `commit_for_mission`; no residual direct `safe_commit` / `_planning_commit_worktree` calls in `tasks.py` (FR-006), and no bespoke `is_protected` pre-checks remain (FR-007).
- **INV-5** New/changed code ≥ 90% line coverage (NFR-002); ruff + mypy --strict clean (NFR-003).
