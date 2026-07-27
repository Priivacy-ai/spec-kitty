# Tooling Friction Log

> Log every place the tooling fought you so it can feed the tooling-gap backlog.

Mission: `sync-batch-400-poison-isolation-01KXW08B` · #2736 batch-400 poison isolation.
Seeded at planning with a **watch-list** carried in from THIS session's two prior mission runs
(`merge-coord-rollback-transactionality-01KXTM59`, the #2794 sk-op remediation) so the recurring
tooling / implement-loop gaps are visible, not re-discovered. **Append every real hit during implement;
assess at close and file the durable ones to the tooling-gap backlog (#2017 / #1931).**

Operator note (2026-07-19): recent missions have tackled (or attempted) many of these —
`loop-friction-quickwins-2-01KXBWA4`, `lifecycle-tooling-friction-01KW4V6C`,
`implement-loop-commit-hardening-01KXJ1ZX`, `implement-review-loop-recovery-01KXG2TD`,
`ci-local-preflight-parity-01KWXWY0`. Each entry flags **[STILL BITES]** vs **[improved]** as observed
on the merge-coord mission run so we can tell what remains.

## Watch-list carried in from this session's mission runs

- **F1 — Analysis-report staleness churn. [STILL BITES]** `mark-status` writes `[D]` progress markers into
  `tasks.md`, changing the content-hash the analysis report is pinned to, so `agent action implement WP##`
  refuses with `stale_analysis_report` and forces a `record-analysis` re-run **before each gated implement**
  (recurred at every WP boundary on the merge-coord run, 5×). Candidate fix: exclude progress-marker-only
  `tasks.md` deltas from the analysis freshness hash, or auto-refresh on the implement path.

- **F2 — `record-analysis` refuses on a dirty tree AND doesn't auto-commit.** Errors `Refusing to record
  analysis report with pre-existing dirty working tree` (blocks on any tracked-modified file) and returns
  `commit_hash: null` (report left uncommitted). Loop becomes: commit bookkeeping → record → commit report
  → retry. Couples F1's churn to F3's preflight.

- **F3 — `move-task` preflight blocks on uncommitted *owned* files (analysis-report / lane bookkeeping).**
  Every transition (`for_review`, `approved`) fails until the mission-dir bookkeeping is committed — repeated
  commit-then-retry. The "N unrelated dirty files ignored" line is good, but the owned-file block fires on
  the analysis-report the gate itself just wrote (see F2).

- **F4 — Approval gate needs `issue-matrix.md` verdicts filled — discovered LATE (first approval blocked).**
  `move-task --to approved` refuses with `issue-matrix.md has unresolved entries` naming every referenced
  issue. The matrix lives on the **coord branch** (not the primary working tree), so it isn't obvious it
  needs filling. Worse: `in-mission` verdicts are accepted at per-WP `approved` but **rejected at mission
  `done`** — a second late surprise. Candidate: surface the matrix requirement at mission-create / first
  implement, not at first approval.

- **F5 — Review-artifact frontmatter schema is strict + undocumented at the point of use. [STILL BITES]**
  A hand-written `review-cycle-N.md` (plain-markdown feedback) → `move-task --to approved` fails with
  `has no parseable review verdict`. The gate (`_get_wp_review_verdict`) needs YAML frontmatter
  (`review_cycle` / `verdict: approved|rejected` / `reviewer` / …). The `--review-feedback-file` (reject)
  path does NOT stamp this frontmatter, so the reviewer authors it by hand. Two schemas coexist in-tree
  (older `work_package_id`/`changes_requested` vs current `cycle_number`/`approved|rejected`).

- **F6 — `finalize-tasks` did not parse the `tasks.md` "Depends on WP##" phrasing.** Even with the exact
  regex-matching phrasing (verified against `core/dependency_parser.py`), `finalize-tasks` wrote `deps: []`
  (`updated_wp_count: 0`). Workaround: set `dependencies` in each WP frontmatter directly + rely on the
  **preserve-existing** path. The CLI's internal reader diverges from the standalone parser — a real bug to
  file.

- **F7 — Coord/primary partition footguns (the load-bearing trap this session). [partially improved]**
  `issue-matrix.md`, `review-cycle-*.md`, status runtime files live on the **coord branch**; `spec-commit`
  materializes the coord worktree and lands there ("Spec artifact(s) unchanged" when already on coord); the
  primary working tree lacks them. Editing the matrix required `cd`-ing into `.worktrees/…-coord`. When
  consolidating a clean PR branch off upstream/main, tracked planning files vanish on branch-switch and had
  to be `git checkout`-ed back per-partition.

- **F8 — Lane `.venv` missing pytest in the pre-review gate scoped run. [noise, non-blocking]** The gate's
  scoped run reported `No module named pytest` / `no_coverage — scoped test run did not complete` from the
  freshly-`uv`-built lane venv, but the transition still succeeded. Reads like a failure; isn't one.

- **F9 — Pre-review gate scope-exclusion silently let red-first tests through.** `move-task --to for_review`
  on a red-first WP returned `no_coverage — excluded scope` (the `tests/regression/` files fell into a
  catch-all group) and passed — the desired outcome here, but it means the gate isn't running the changed
  tests for those paths. A coverage gap worth noting.

- **F10 — Baseline-red attribution cost (the gotcha).** Broad local/backgrounded `pytest` sweeps surface
  reds that are NOT the diff's (known-P0, CI-env sync-toggles — #2794 — stale-install). Navigated correctly
  via the AGENTS.md gotcha, but it costs attribution time each sweep.

## Mission-specific tooling to watch (this run)

- The pre-review gate reuses the **sync disable toggles** — the very #2794 coupling being fixed elsewhere.
  When running this mission's `tests/delivery/` / `tests/sync/` in parallel, watch for the
  `SPEC_KITTY_SYNC_MINIMAL_IMPORT` leak (my #2794 fix is on a separate branch, not yet on this base).
- `spec-commit` with backticks in `-m` triggered shell command-substitution and dropped a phrase from a
  commit body (my error) — use a heredoc / `-F -` for messages containing backticks.

## Post-plan squad additions

- 2026-07-19 — **No new tooling friction from the post-plan squad itself** — the three delegates (alphonso /
  pedro / renata) ran clean via the Agent surface, profile-loaded, and returned structured findings. The
  squad's value landed as *design* corrections (see approach.md / design-decisions.md), not tooling gaps.
- 2026-07-19 — **Observation (not a friction, a gap the squad would have missed without reading it):** the
  layer-rules gate (`tests/architectural/test_layer_rules.py`) polices edges only at top-level package
  granularity, so an intra-`specify_cli` `sync → delivery` cycle is **legal-by-omission**. This is exactly
  the DIR-043 "wrong thing is not caught" smell — worth a tooling-backlog note: consider an intra-package
  edge guard for the `core`/`delivery`/`sync` leaves. (Design was fixed by placement; the *gate gap* remains.)

- 2026-07-19 — **F9 CONFIRMED with specifics (debbie, post-tasks squad).** The pre-review gate green-washes
  this mission's entire P0 as `no_coverage`. Verified from `.github/workflows/ci-quality.yml` +
  `review/pre_review_gate.py`: `tests/delivery/**`, `src/specify_cli/delivery/**`, `tests/core/**`,
  `src/specify_cli/core/**`, and `tests/architectural/**` are ALL only in the excluded `core_misc` catch-all
  (no focused `delivery`/`core` group exists), so `derive_test_scope` returns empty → `evaluate_with_scope` →
  `GateOutcome.NO_COVERAGE`. The release-blocking WP02 acceptance tests are **never executed by the automated
  pre-review gate** — only post-push CI's `integration-tests-core-misc` shard runs them. A reviewer reading
  the gate's `no_coverage` warn as "clean" could approve a red fix. **Backlog candidate:** add focused
  `delivery`/`core` CI groups (mirroring the existing `sync`/`status` groups) so the per-WP gate exercises
  delivery/core changes. Mitigation this mission: explicit "gate is blind here, run manually + rely on CI"
  warnings folded into WP01/WP02/WP05 prompts. (`tests/sync/**` and `tests/status/**` HAVE focused groups —
  WP04 and WP03 are gate-covered; only delivery/core/architectural are blind.)

## Entries (append dated, in-the-moment)

- 2026-07-19 — Seeded from the merge-coord + #2794 mission runs (this session). No implement-loop entries
  for THIS mission yet (planning stage).
