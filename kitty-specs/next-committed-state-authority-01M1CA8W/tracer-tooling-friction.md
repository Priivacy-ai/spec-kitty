# Mission Tracer — Tooling Friction

**Mission**: next-committed-state-authority-01M1CA8W · Issues #2947 + #3780

Append-only log of friction hit while running the toolkit — feeds the next mission.

## Planning (2026-08-31)

- The installed `spec-kitty` CLI is editable-installed from a **sibling** clone (`fork/spec-kitty/src`), not this shadow clone. Planning commands operate on this repo's files (CWD-resolved repo_root), which is fine — but shell-out repros / live `next` verification will need an editable install (or PYTHONPATH pin) of *this* worktree before they exercise this mission's code. Noted for implement/verify.
- Repo's configured `primary_branch` is `symbolkey-source-module-3552`, so `branch-context` reports "staying on main is fine" (current_is_primary=false). Created the mission on a dedicated PR-bound `fix/` branch anyway, to keep planning artifacts off the `main` integration branch per charter.

## Implementation

- **Test execution in lane worktrees**: this worktree has a `.venv` editable-installed to ITS OWN src, but the global `python`/`pytest` (pyenv shims) resolve `specify_cli` to the sibling clone (`fork/spec-kitty/src`). Implementers in lane worktrees (`.worktrees/<slug>-<mid8>-lane-*`) must run tests as `PYTHONPATH=<lane-worktree>/src python -m pytest <targets>` (global deps + the lane's src), per CLAUDE.md. Do NOT `uv run` (destroys the hand-built `.venv`).
- **WP02 live `next` proof (C-007)**: shelling out to `spec-kitty next` uses the sibling install, not the lane's code. Run the live proof against the lane's code via `PYTHONPATH=<lane>/src` + the module entry, or a scoped editable install — decide at WP02 implement time.
- (append as encountered)
