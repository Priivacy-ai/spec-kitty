# Quickstart — Reproduce & Verify #2533

## Reproduce the defect (RED)

Simulated end-to-end (the shape WP02 automates through the real claim gate):

1. Create a solo PR-bound mission on a feature branch:
   `spec-kitty agent mission create "<slug>" --pr-bound --branch-strategy already-confirmed --start-branch feat/<slug>` → topology `coord`, an empty coordination branch is materialized.
2. Author + commit `spec.md`, `plan.md`, `tasks.md`, `tasks/WP01-*.md`, `lanes.json`
   on the **feature branch** (the coordination branch stays empty).
3. Claim the first work package:
   `spec-kitty agent action implement WP01 --mission <slug> --agent claude`.

**Observed (buggy):** the claim aborts with
`Planning artifacts not committed:` listing the feature-branch-committed artifacts,
plus `git add -f kitty-specs/<slug> …` instructions. Root cause: the precondition
diffs those PRIMARY artifacts against the empty coordination branch.

## Verify the fix (GREEN)

After WP01+WP02:

- The same claim **proceeds** — no "Planning artifacts not committed" output, no
  manual `git add -f`, and `meta.json` topology is unchanged (`coord`).
- Unit: `resolve_precondition_ref(None) == "HEAD"`; a PRIMARY artifact committed at
  HEAD is absent from `_files_changed_vs_ref(..., None)`.
- Regression: a `lanes_with_coord` mission still routes COORD-owned status files to
  the coordination ref (no regression).
- Move-task: `_mt_untracked_planning_artifact_paths` staging unchanged.

## Test commands

```bash
# Pure unit + integration for the claim precondition (parallel-safe):
PWHEADLESS=1 uv run pytest tests/specify_cli/cli/commands/test_implement_cores.py \
  tests/specify_cli/cli/commands/test_implement.py -n auto --dist loadfile -q

# Quality gates (must be zero new issues):
uv run ruff check src/specify_cli/cli/commands/
uv run mypy --strict src/specify_cli/cli/commands/implement_cores.py

# Terminology guard (docs campsite touches doctrine-adjacent prose):
uv run pytest tests/architectural/test_no_legacy_terminology.py -q
```

## Sequencing note

The WP that edits `tasks_move_task.py` must be rebased onto `upstream/main` **after
PR #2639 merges** (it line-shifts the `:1364` consumer). `#2570 WP01` is already in
base, so `implement_cores.py` needs no reconciliation.
