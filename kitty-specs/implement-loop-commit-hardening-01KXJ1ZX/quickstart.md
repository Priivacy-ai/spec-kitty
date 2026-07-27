# Quickstart — Reproduce & Verify

## #2647 — move-task from a lane worktree (RED→GREEN)

RED (current): from inside a lane worktree, `spec-kitty agent tasks move-task WP## --to for_review`
→ `Illegal transition: <from> -> <to>` (reads the worktree's stale surface); succeeds from repo root.
GREEN (after WP05): both invocations succeed identically.

Test: a real `tmp_path` git repo with a lane worktree; drive the move-task read path with
cwd set to the worktree; assert the transition matches the repo-root result.

## #2648 — protected-branch fallback is visible (RED→GREEN)

RED (current): a coord mission with `target_branch` protected + a dirty PRIMARY `spec.md`
takes the single-coordination fallback and prints only the generic success line — silent
under `--json`. GREEN (after WP01): a WARNING log record naming the branch, visible under
`--json`; the fallback destination is test-pinned.

## #2649 — degod (behavior-preserving)

Characterization tests pin the invariants FIRST; then decompose; existing suites + new
focused tests green; `ruff check` C901 ≤15 / params ≤13 on the six functions.

## #2650 — one partition authority (characterize → consolidate)

FR-006 gate: enumerate the three sites + the `kind=None` set (`meta.json` + unrecognized)
and pin `kind=None`→PRIMARY. FR-005: consolidate onto one shared callable; structural test
asserts no independent classifier remains; #2533 + #2648 regressions green.

## Test commands (use `uv run` — bare python imports the primary checkout)

```bash
PWHEADLESS=1 uv run pytest \
  tests/specify_cli/cli/commands/test_implement.py \
  tests/specify_cli/cli/commands/test_implement_cores.py \
  tests/specify_cli/cli/commands/test_implement_writeside.py \
  tests/specify_cli/coordination/ \
  tests/specify_cli/cli/commands/ -k "move_task or partition" -n auto --dist loadfile -q
uv run ruff check src/specify_cli/cli/commands/implement.py src/specify_cli/cli/commands/implement_cores.py \
  src/specify_cli/cli/commands/agent/tasks_move_task.py src/specify_cli/coordination/commit_router.py
uv run mypy --strict src/specify_cli/cli/commands/implement.py src/specify_cli/cli/commands/implement_cores.py \
  src/specify_cli/cli/commands/agent/tasks_move_task.py src/specify_cli/coordination/commit_router.py
```

## Sequencing / landing

- Lane A serial: WP01(#2648) → WP02(#2649-impl) → WP03(FR-006 char) → WP04(#2650). Lane B
  serial: WP05(#2647) → WP06(#2649-move). Lanes A ∥ B.
- WP06 rebases after draft PR #2639 (`_do_move_task` param); measure ≤13 post-rebase.
- The whole branch (with #2533) PRs after this mission (operator opens it).
