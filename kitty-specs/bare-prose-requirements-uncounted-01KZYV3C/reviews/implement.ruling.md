# Ruling: `coordination_branch` flatten — operator-authorised doctrine exception

**Date**: 2026-08-14
**Mission**: bare-prose-requirements-uncounted-01KZYV3C (issue #3396)
**Actor**: fixer pass, on `pr/bare-prose-requirements-uncounted` @ `72c92e187`

## Blocker

`spec-kitty implement WP04` (and `spec-kitty implement WP04 --base pr/bare-prose-requirements-uncounted`)
both fail identically with:

```
workspace allocation failed: cannot auto-merge the recorded planning commit
'9b03ca2978993e76edee5a6e95249463e1c010bb' into lane 'lane-c': the merge conflicts.
```

## Root cause (verified first-hand)

- `meta.json` declares `topology: "coord"` and
  `coordination_branch: "kitty/mission-bare-prose-requirements-uncounted-01KZYV3C"`.
- That coordination branch is at `14b9bc367`. This mission's real work branch,
  `pr/bare-prose-requirements-uncounted`, is at `72c92e187`.
- `git merge-base 72c92e187 kitty/mission-bare-prose-requirements-uncounted-01KZYV3C` →
  `ab15225ea8b08c93779da904a4c7f7f30f3efbac` — the two lines diverged at the mission's own base
  and share **no** commits since. `git merge-base --is-ancestor` confirms neither is an
  ancestor of the other.
- The coordination branch's 12 commits (`d6c1c9a21`, `c8670ba1e`, `14b9bc367`, …) are a **stale
  parallel copy** of this mission frozen at its earlier 9-WP stage: status-transition events for
  WP01–WP09, an older `tasks.md`, older WP files and tracers. All of it is superseded by the
  reviewed 7-WP structure that actually landed on `pr/bare-prose-requirements-uncounted`.
- The coordination transit was **never used in practice**: all ~30 commits of real mission work
  landed via `spec-kitty safe-commit --to-branch pr/bare-prose-requirements-uncounted`. The
  mission has been branch-flat in practice since it began; `topology: "coord"` and
  `coordination_branch` are stale metadata, not an active transit.
- Attempting the tool's own suggested manual recovery
  (`git merge --no-commit --no-ff 9b03ca297` inside the `lane-c` worktree) reproduces `add/add`
  conflicts in exactly the files this mission's operating rules forbid hand-editing
  (`lanes.json`, `status.events.jsonl`, `status.json`, `tasks.md`, one WP prompt file) — not
  safely resolvable without violating those rules. Aborted immediately
  (`git merge --abort`); worktree confirmed clean afterward. See
  `tracer-tooling-friction.md`'s `spec-kitty implement WP04` row for the full first attempt.

## No CLI command reconciles this

Checked and confirmed absent:
- `doctor workspaces` / `doctor workspaces --fix` — reports only husk directories (missing
  `.git`); both `-coord` and `-lane-c` worktrees here are healthy git worktrees, not husks, so
  this surface reports nothing.
- `doctor topology` — report-only, no `--fix`.
- `migrate`, `mission`, `sync`, `agent` subcommand groups — none offer a "flatten
  coordination topology" or "clear coordination_branch" operation.

This is **ledger SK-01** ("CLI prescribes a `coordination_branch` remedy it cannot perform"):
the error's own prescribed remedy is "flatten the mission by removing the
`coordination_branch` key from `meta.json`", but no command does this — the only route is a
hand-edit of mission state, which doctrine otherwise forbids. SK-01 documents this exact class
of exception already having been taken twice before, both as documented, operator-authorized
doctrine exceptions: `spec-kitty-saas` PR #900 (one mission, merged) and PR #903 (18 missions,
open).

## Operator authorisation

The operator explicitly authorised this hand-edit as a documented doctrine exception on
2026-08-14, scoped to exactly one change (see below) and no other state mutation.

## The precise change made

In `kitty-specs/bare-prose-requirements-uncounted-01KZYV3C/meta.json`: remove the
`coordination_branch` key. **`topology: "coord"` is left unchanged** — SK-01's prescribed
remedy is removing the key, not changing `topology` to a different enum value; inventing a new
`topology` value is a separately forbidden action (a prior mission corrupted its state doing
exactly that). No other key in `meta.json` is touched.

## Worktree cleanup (separate, also authorised)

`.worktrees/bare-prose-requirements-uncounted-01KZYV3C-coord` and
`.worktrees/bare-prose-requirements-uncounted-01KZYV3C-lane-c` both sit at `14b9bc367` on the
diverged, superseded lineage. Both re-verified clean (`git status --porcelain` empty) before
removal via `git worktree remove` + `git worktree prune`. The branches
`kitty/mission-bare-prose-requirements-uncounted-01KZYV3C` and
`kitty/mission-bare-prose-requirements-uncounted-01KZYV3C-lane-c` are **not** deleted — only
their working directories are — so the 12 stale commits remain recoverable if ever needed.

## Why this is not a rogue state mutation

This record exists precisely so a later reviewer does not read the `meta.json` edit as an
undocumented, unauthorized hand-edit of mission state. The blocker, its root cause, the absence
of any CLI remedy, the operator's authorization, and the exact scope of the change are all
recorded here, matching the same exception class SK-01 already documents as precedent.
