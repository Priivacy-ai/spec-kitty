# Tracer: Tooling Friction

**Mission**: refactor-stable-gate-substrate-01KWK3FY
**Created**: 2026-07-03 (seeded at planning per `mission-tracer-files` procedure)

## Inherited watch-list (degod Wave 2 + this session)

- Coord-topology: NEVER `git checkout <branch> -- kitty-specs/<mission>/` into the
  coord worktree (clobbers status.events.jsonl — recovered from history once).
- Lane worktrees share the primary venv: PYTHONPATH="$PWD/src" for pytest/mypy.
- graph.yaml freshness gates are byte-for-byte — regenerate via generate_graph only.
- Status bookkeeping commits on the primary between WPs; spec edits re-stale
  analysis-report → re-run record-analysis.
- Parallel ops in ONE checkout can clobber each other's edits (refactor-op reverted
  scrub-op files once) — sequence or scope-disjoint WITH no-revert instructions.
- Quarantine bypass for verification: SPEC_KITTY_RUN_QUARANTINE=1.

## New friction (append during implement)

_(none yet)_
