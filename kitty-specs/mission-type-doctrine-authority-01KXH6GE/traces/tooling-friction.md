# Tooling Friction Log

> Log every place the tooling fought you so it can feed the tooling-gap backlog.

**Prompting questions**
- What tooling or command did you have to work around?
- What blocked you unexpectedly, and how long did it take to unblock?
- Was this a known issue or something discovered fresh?

---

## Entries

<!-- YYYY-MM-DD — 1-3 sentences: what happened, why it slowed you down. -->

- 2026-07-15 — **Coord-authority read-path split-brain (#2160 class).** Every lifecycle `move-task` (for_review / approved) run *from inside a lane worktree* failed `Illegal transition: ... (stale lane-local status)` — the validator read the stale lane-local `status.events.jsonl` instead of the authoritative primary-checkout copy. This is a `lanes` topology (no coord branch), so the status authority is the primary checkout. Workaround adopted mission-wide: run all lifecycle transitions from the primary checkout `/…/spec-kitty-gate-doctrine`. Hit by every implementer and reviewer (WP01/02/03/09/…). This is exactly the friction the #2160 / #2017 cluster targets — live evidence.
- 2026-07-15 — **Clean-worktree guard vs. unrelated churn.** A 2.5-day-old runaway forked Claude session (PID 348359, `--permission-mode auto`, resuming an unrelated session) was continuously re-staging `.kittify/charter` + `.kittify/doctrine` + `synthesis-manifest.yaml` into the shared worktrees, tripping the clean-worktree guard and forcing `--force` on WP approvals (WP03 blocked until forced). The guard cannot distinguish an unrelated writer's churn from the WP's deliverables. Resolved by killing PID 348359 (operator-approved) → friction cleared; friction was environmental, not a WP defect.
- 2026-07-15 — **WP03 approval did not persist.** The reviewer's `move-task --to approved` reported success but the status board still showed WP03 in review (the coord-authority split-brain + rogue-session interference). Re-applied from the primary checkout with `--force`; the deliverables were already committed (`b5b407c47`).
- 2026-07-14 — **Implement gate requires an analysis-report first** (`analysis_report_required`). Not obvious from the tasks flow. Recorded via `spec-kitty agent mission record-analysis`, but a prose-only report yielded `verdict: unknown` — the command needs structured verdict/issue-count frontmatter, not just a markdown body, to register a `ready` verdict.
- 2026-07-15 — **Status-artifact commit friction between waves.** With auto-commit disabled, `agent action implement WP##` refuses to start while prior WPs' frontmatter/status changes are uncommitted; had to `git add -f kitty-specs && git commit` manually between each dependency wave.
