# Spec-Kitty Workflow Failures Observed During Mission 01KTXRVR

**Recorded for the retrospective** (per operator instruction, 2026-06-12). Every failure below was hit live while running the canonical specify → plan → tasks → analyze → implement → review → accept → merge pipeline for `coordination-merge-stabilization-01KTXRVR` on spec-kitty 3.2.0rc42, coordination topology, protected local main. Several are fresh instances of the very bug classes this mission fixed; most are already cited in umbrella **#1878** — this log is the consolidated session record.

## A. Planning-phase failures (specify/plan)

1. **Coord-unaware `is_committed` entry gate.** `setup-plan` refused (`SPEC_NOT_SUBSTANTIVE_OR_UNCOMMITTED`) because `is_committed()` (`missions/_substantive.py:214-239`) checks only the primary checkout's HEAD; a spec.md committed on the coordination branch is invisible. Workaround: `git merge --ff-only` the coordination branch into local main before every gate. (In #1878.)
2. **setup-plan auto-commit fallback diverges from the #1784 fix.** The plan auto-commit refused on protected main even though direct invocation of `_resolve_planning_placement` + `_planning_commit_worktree` routes correctly to the coordination worktree — some call path inside setup-plan bypasses the catch-22 fix. (In #1878.)
3. **Lifecycle event emission targets protected main.** setup-plan's phase-event emission attempted a safe_commit on the primary main checkout; only `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS=1` unblocked it. (In #1878.)
4. **`safe-commit` from primary cannot route planning artifacts.** Bare `spec-kitty safe-commit` (the exact command the canonical specify prompt prescribes at `src/doctrine/missions/mission-steps/software-dev/specify/prompt.md:124`) refuses on protected main; `--to-branch` only asserts HEAD, it does not route. Operator must know to cd into the coordination worktree. Doc/UX gap.
5. **Surface anchoring is inconsistent across commands.** `agent context resolve --action tasks` anchors feature_dir in the coordination worktree; `check-prerequisites` (run from the same worktree) anchors it on the primary checkout. Artifacts must be manually rsync'd between surfaces.

## B. Tasks/finalize-phase failures

6. **`map-requirements` "Unknown WP IDs" when WP files exist only on the authoring surface** (primary) — it reads the coordination worktree. Same split-surface confusion as (5).
7. **`finalize-tasks` validate-only switches the operator's checkout** — bug #1861, hit live during this mission's own planning (and fixed by this mission's WP02).
8. **`mission create` scaffold (`tasks/.gitkeep`) later trips dirty-tree gates** — `record-analysis` refused on it. (In #1878 as adjacent observation.)

## C. Analyze-phase failures

9. **`record-analysis` refuses on ANY untracked primary-checkout file** — the #1814 mechanism, hit live three separate times (`spec-kitty-3.2-release-evaluation.md`, `tasks/.gitkeep`, daemon-materialized `status.json`). WP02 fixed the finalize-residue subset; unrelated-untracked-file refusal remains (`--allow`-style escape absent).
10. **Background/foreground materialization recreates other missions' `status.json` on the primary** (`pre-and-post-mission-lifecycle-support-01KTNK1G/status.json` reappeared 4+ times, each time re-blocking a gate). Accepted Class E residual per the validation analyses — but it actively fights the dirty-tree gates.
11. **Analysis staleness gate re-fires after any planning-artifact commit** (#1764 behavior): committing the analyze-recommended I1/I2/U2 adjustments invalidated the just-recorded analysis, blocking all `implement` claims until re-record.
12. **`record-analysis` leaves `analysis-report.md` uncommitted on the primary** — the next command's dirty/commit gates then trip over the file the tool itself wrote.

## D. Implement/review-phase failures

13. **Dashboard is coordination-topology-blind** (#1572 family): it reads primary-checkout surfaces while transitions commit to the coordination branch; it silently shows stale state. Workaround: ff-merge after every transition.
14. **`spec-kitty next --agent ... --mission 01KTXRVR` returned "[QUERY — no result provided, state not advanced], Mission Type: unknown"** — unusable for orchestration; fell back to `agent tasks status` + manual sequencing.
15. **Reviewer hit a missing `issue-matrix.md` hard-gate on first approval** — finalize-tasks never scaffolded it despite spec.md referencing issues; the reviewer had to author it mid-review (17 verdicts) to unblock `move-task --to approved`.
16. **`move-task` to for_review refused when the lane is behind the mission branch** — every lane (WP02/WP03/WP05) had to rebase mid-flight because each earlier WP's status commits advanced the mission branch. Rote, predictable, unautomated (#771 family).
17. **WP frontmatter `owned_files` path typo propagation**: finalize-tasks validated ownership against a nonexistent path (`tests/specify_cli/test_wp06...` vs real `tests/specify_cli/cli/commands/test_wp06...`) without warning — the no-overlap guard validates patterns, not existence.

## E. Accept-phase failures

18. **`spec-kitty accept` is a self-defeating gate**: it mutates WP frontmatter/`tasks.md`/`acceptance-matrix.json` in the coordination worktree during its run, snapshots `git status` AFTER its own writes, fails `git_dirty` on them, then (in `--no-commit` mode) restores the tree — so the gate can never pass under coordination topology. Verified: tree clean before and after, dirty only in the report. The merge proceeded on the strength of 5/5 approvals + recorded matrix; accept never returned ok=true.
19. **accept regressed WP01's frontmatter** to an older snapshot on one run (lost two activity-log entries — restored from git). Lane-state materialization racing the event log.
20. **Acceptance matrix scaffold is generated with placeholder criteria** ("Verify FR-001 is satisfied", proof TODO) only at accept time, with no command surface to record verdicts — the orchestrator had to edit `acceptance-matrix.json` by hand to record the 13 per-FR verdicts/evidence.

## F. Merge-phase failures

21. **`merge --mission <mid8>` does not resolve mid8** (`Mission directory not found: kitty-specs/01KTXRVR`) — violates the mission-identity selector contract (mid8 must disambiguate); full slug required. Resolver gap in `mission_runtime/resolution.py:_resolve_mission_slug`.
22. **Merge cannot delete the mission branch while the coordination worktree exists** ("cannot delete branch ... used by worktree") — merge cleans lane worktrees but not the coordination worktree it created; manual `git worktree remove` + `branch -D` needed.
23. **Stale-assertion checker false positive**: flagged `test_merge_coord_worktree_resync_1826.py:566` for containing the string `update-ref` — but the assertion deliberately tests that the backstop *message* names the cause; the checker conflates message-content assertions with code references.

## G. Cross-cutting

24. **The ff-merge treadmill**: under coordination topology + protected main, the operator must manually `git merge --ff-only` the coordination branch into local main after essentially every phase (gates read primary; transitions write coordination). This was needed ~10 times this session. The single largest workflow tax observed.
25. **Untracked-file collisions on every ff-merge**: tool-written untracked files on the primary (status.events.jsonl, analysis-report.md, status.json, .gitkeep) repeatedly collided with the same files committed on the coordination branch, aborting ff-merges with cryptic output.

## Positive observations (for balance)

- The 9-lane status model, per-WP review prompts with correct diff bases, lane isolation, and `safe-commit`'s backstop all worked exactly as designed.
- PR #1850's placement resolver held: zero #1784-class failures in paths that actually route through it.
- The dirty-tree gates, while noisy, never allowed an inconsistent commit.

## H. Post-merge failures (appended after merge)

26. **Terminus retrospective not generated at merge** despite `DIRECTIVE_terminus_retrospective_always_on` — `.kittify/missions/01KTXRVR.../retrospective.yaml` was absent after `spec-kitty merge` completed; `retrospect create` had to be run manually, and its findings generator returned `ran_no_findings` (0 gaps) for a mission with 26 documented workflow failures.
27. **#1771 residual — explicit `retrospect create` still writes to the gitignored path.** The terminus/merge writer was fixed (PR #1850 WP08, `test_record_committable_1771.py`), but `spec-kitty retrospect create` wrote `.kittify/missions/<mission_id>/retrospective.yaml`, which `git check-ignore` confirms is ignored — the record is not committable. WP01 closed #1771 citing the fix; this path was not covered. Recorded as a comment on #1771 and in umbrella #1878 scope.

**Retrospective source of truth:** this log (committed in the mission directory). The YAML record exists locally but is gitignored (see #27).
28. **Mission squash-merge commits duplicate planning artifacts under `.worktrees/<slug>-coord/kitty-specs/...`** — 27 such paths entered main's index from this mission's merge (precedented: 26 identical-pattern paths from prior missions already exist on origin/main, e.g. commits 43fa4b6e3, 9299d39ae, a5f30616e). Removed ours in the PR; the mechanism (coordination-worktree-relative paths captured by merge/accept bookkeeping) belongs in #1878.
