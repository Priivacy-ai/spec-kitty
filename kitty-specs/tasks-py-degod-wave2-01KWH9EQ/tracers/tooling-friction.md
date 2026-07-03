# Tracer: Tooling Friction

**Mission**: tasks-py-degod-wave2-01KWH9EQ
**Created**: 2026-07-02 (seeded at planning per `mission-tracer-files` procedure)
**Lifecycle**: seed at planning → append during implement → assess at close

## Inherited watch-list (from Wave 1's tracer — read before every WP)

- strict-mypy on changed src+test files **together** (attr-defined only surfaces with both in scope); expect 2–3 step narrowing cascades.
- Golden `--help` fixtures are typer/rich-version-coupled — pin the venv to `uv.lock` before running or re-freezing.
- FR-coverage scanner tokenizes `FR-\d+` from prose — descoping an FR requires de-tokenizing every prose mention.
- Status bookkeeping commits on the primary checkout between WPs; spec edits re-stale `analysis-report.md` → re-run `record-analysis`.
- Approve gate needs terminal issue-matrix verdicts — use `in-mission` until close.
- Census/arch gates go red mid-mission from line-drift in `(qualname, line)` allowlists — budget a drain/re-pin step.
- Lane worktrees have no own `.venv` — validate via pytest, not bare imports.
- Coord-topology: acceptance-matrix/issue-matrix/review artifacts live on the coordination branch — edit the coord worktree copy.
- Merge blocks on a latest-rejected `review-cycle-N.md` even after approval — scan all WPs up front at merge time.

## New friction (append during implement)

_(none yet)_
