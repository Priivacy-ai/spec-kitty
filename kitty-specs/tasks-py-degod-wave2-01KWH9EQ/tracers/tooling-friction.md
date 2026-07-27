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

- **WP09**: mypy's transitional-quarantine override list (pyproject) makes
  verbatim moves OUT of `agent.tasks` fail `--strict` in the destination —
  the quarantine is per-module, so relocated legacy bodies need typing
  tightening in the same WP. Budget it in every degod move.
- **WP09**: the write-indicator token list of the coord-authority census
  includes `dumps` — routing inline emission through the Render port silently
  re-classifies write sites as reads, so a render-seam WP drains the census
  without touching a resolver; the drift only surfaces on the full arch sweep.
- **WP09**: gate-contract predictions written from the mission's own surface
  ("empty allowlist") should be validated against the FULL gate scope
  (directory glob) at plan time — a 2-minute grep would have caught the 9
  pre-existing sibling offenders before the contract froze the wording.
- **Post-merge (quarantine sweep, 2026-07-03)**: a degod wave that relocates a
  symbol must sweep the QUARANTINE set for stale literal-presence pins over
  that symbol before merge — `test_routed_files_import_the_seam` (quarantined
  by Wave 0) pinned `worktree_path`/`mission_dir_name`/`resolve_mid8` in
  tasks.py; the relocation broke 4/6 of its assertions while it was dark.
  Re-pinned + un-quarantined on PR #2308. Reusable point-cut for the degod
  program (#2057 merge.py, #2059 doctor.py).
