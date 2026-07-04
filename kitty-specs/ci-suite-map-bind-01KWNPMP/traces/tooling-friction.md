# Tooling Friction Log

> Log every place the tooling fought you so it can feed the tooling-gap backlog.

**Prompting questions**
- What tooling or command did you have to work around?
- What blocked you unexpectedly, and how long did it take to unblock?
- Was this a known issue or something discovered fresh?

---

## Entries

<!-- YYYY-MM-DD — 1-3 sentences: what happened, why it slowed you down. -->

- 2026-07-04 — SEED (backfilled same-day; mission touches: spec-kitty implement/move-task loop, pytest marker/collect tooling, `_gate_coverage` census module, gh CLI, git worktrees). Tracer files were missed at planning seed; created at first implement. Process gap: the planning flow has no reminder for the tracer-files standing order — it relied on operator memory.
- 2026-07-04 — `move-task --to for_review/approved` subtask guard misattributes the NEXT WP's unchecked boxes to the current WP: the section-entry regex in `tasks_shared.py:_check_unchecked_subtasks` matches any heading *mentioning* the WP id, so `### WP03 … (depends: WP01, WP02)` re-enters WP02's section. Cost ~15 min to root-cause; filed #2346; worked around with documented `--force` (needed on BOTH the for_review and approved transitions).
- 2026-07-04 — The `approved` gate scans mission prose for `#NNNN` refs and demands an issue-matrix row for each: it flagged #2294/#2319, which are prior MERGED PRs cited in census prose, not addressed issues. Resolved with reference-only `verified-already-fixed` rows; gate is arguably over-broad (PR refs in evidence text ≠ mission scope), but the fix was cheap.
- 2026-07-04 — Bulk-edit inference warning fired on `implement WP01` (score 4/4 on 'rename/change/refactor' in spec prose) for a mission that is NOT a bulk edit; `--acknowledge-not-bulk-edit` must be re-passed on every implement invocation. Known/expected (predicted in mission memory), still noise per-WP.
- 2026-07-04 — Auto-commit disabled means every claim/mark-status/move-task leaves kitty-specs dirty in the primary checkout and blocks the NEXT claim until hand-committed ("Planning artifacts not committed" on implement WP02). Fine once known, but the loop is: run command → commit bookkeeping → run next command.
- 2026-07-04 — Lane commits touching the WP file's Activity Log trip a warning-only "implementation branches must not modify kitty-specs/" guard on every commit — contractually-required appends vs. guard advice disagree (WP02 implementer hit it twice).
- 2026-07-04 — Pre-commit hook's pinned interpreter (known issue, see commit-hook memory) forces `--no-verify` on all orchestrator bookkeeping commits.
- 2026-07-04 — Python 3.11 importlib gotcha (WP02): dynamically loading the decision script requires registering the module in `sys.modules` BEFORE `exec_module`, or dataclass field resolution crashes. Fixed in the test loader with an inline comment; fresh discovery, ~one debug cycle.
- 2026-07-04 — Post-squash-landing rebase: `git cherry` marks the individually-committed WP history as "+" (not upstream) even though its content landed via squash — patch-id equivalence is blind to squashes. Correct move was `rebase --onto upstream/main <last-pre-mission-commit>`, replaying only the 11 prep commits; a naive `git rebase upstream/main` would have replayed ~38 already-landed commits.
- 2026-07-04 — Lane-worktree venv skew (WP01): `uv run mypy src/` inside a fresh lane venv reports 6 phantom `types-toml` stub errors that the primary checkout doesn't (provisioning difference, zero src files touched). Verify against the primary env before believing lane-only mypy noise.
- 2026-07-04 — (WP03) Probe-PR diff pollution: probe PRs diff against fork main, so they carry the WHOLE mission branch — many dorny groups fire on every probe, and a live POSITIVE unmatched-catch-all probe is structurally impossible pre-merge (the mechanism PR always matches core_misc via self-mapping). Pre-merge probes prove negative/behavioral arms only; the positive arm needs stubbed-output execution + a WP04 fixture + the first post-merge unmapped-touch PR.
- 2026-07-04 — (WP03) `gh run` job logs don't expose `$GITHUB_OUTPUT` values — the quality-gate decision table tee'd to `$GITHUB_STEP_SUMMARY`/job log turned out to be the best per-run topology evidence. Worth institutionalizing: any routing mechanism should print its verdict table.
- 2026-07-04 — (WP03) Fork runner contention queued CI Quality ~30 min behind sibling workflows on probe PRs; budget for it when probes gate the loop. Also: zsh doesn't word-split `$var` (burned one evidence query).
- 2026-07-04 — (orchestration) Background-agent liveness is ambiguous during long tool calls: output-file mtime is NOT a signal (stale while the agent was demonstrably committing), and queued SendMessages only deliver at the next tool round — a 2h CI-watch loop looks identical to a hang. The queued-vs-resumed distinction in SendMessage's response is the only reliable liveness probe.
