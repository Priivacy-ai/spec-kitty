# Tracer: Tooling Friction

Mission: runtime-advance-guard-topology-wp-completion-01M1W6VZ (issues #3883, #3884)

## 2026-09-06/07 — plan-phase verification friction (first-hand orchestrator
observation)

`SPEC-KITTY-LEDGER.md`, which the repo's own `CLAUDE.md` instructs every agent to
read before starting ("it lists what is currently broken in spec-kitty, found while
running real missions"), does not exist anywhere in this checkout (`find . -iname
"SPEC-KITTY-LEDGER.md"` returns nothing). This did not block planning — spec.md was
treated as the authoritative source per the mission dispatch's own instruction — but
a pointer to a file that is not present is itself a small piece of drift worth
recording rather than silently working around.

Extensive line-citation verification during this plan phase (re-checking essentially
every FR/AC/Constraint citation in spec.md against the live source) found the spec's
own citations accurate to a striking degree given three prior adversarial review
rounds — with exactly one exception, recorded in plan.md's "Flagged Deviations"
section (`_should_advance_wp_step`'s `except ValueError` branch is at
`runtime_bridge.py:768-773`, not `:763-767` as spec.md states). This is a useful
data point for future missions on this seam: the spec's heavy citation-drift review
history clearly paid off — nearly everything checked out — but "adversarially
reviewed three times" still did not catch this one, so a plan-phase re-verification
pass is not redundant busywork even after a heavily-reviewed spec.

## 2026-09-07 — Scope-narrowing friction

Confirming PR #3923's true file count required the paginated GitHub API, not a
plain `gh pr view --json files` — that command silently truncates at 100 files and
would have hidden that the PR touches `runtime_bridge_io.py` at all for a PR this
large (125 files). Any future check of a large PR's touched-files set should use
pagination (or `gh api` directly) rather than trusting `gh pr view --json files`'s
apparent completeness.

The empirical spike this narrowing ran directly (which exception
`placement_seam(...).read_dir(...)` raises for a corrupt/missing `meta.json`
fixture) turned out to depend on WHICH `MissionArtifactKind` is queried in a way
the pre-narrowing draft's own citation of `resolve_artifact_surface`'s docstring
already hinted at but did not spell out: `resolve_artifact_surface`'s internal
`mission_slug`->primary-directory resolution step always uses
`MissionArtifactKind.PRIMARY_METADATA` internally regardless of the caller's
requested `kind` — so the mission_slug-resolution behavior (including which
exceptions it can raise) is representative across kinds, but the FINAL
raise-or-not verdict (whether the requested `kind` is COORD- or PRIMARY-partition)
still depends on the actual `kind` parameter. Running the spike against the wrong
kind (e.g. `PRIMARY_METADATA` when the real call site uses `WORK_PACKAGE_TASK`)
would have happened to give the same answer here (both are PRIMARY-partition
kinds), but that agreement is not guaranteed for every kind pair — future spikes
on this seam should query the ACTUAL kind the call site under test uses, not a
representative stand-in, even when the two are expected to agree.

## 2026-09-07 — record-analysis verdict check (SK-06/#3133 did not reproduce this run)

Re-ran `/spec-kitty.analyze` after the scope-narrowing edit (spec.md/plan.md/
tasks.md/wps.yaml/WP files rewritten to #3884-only). Self-computed verdict from the
submitted `analysis-findings/v1` carrier: **ready** (0 critical, 0 high, 0 medium, 1
low — an informational finding about the deliberately-preserved plan.md review
history, not a defect). `spec-kitty agent mission record-analysis --json` returned
`"verdict": "ready"`, and the persisted `analysis-report.md` frontmatter also reads
`verdict: ready` — matching the submitted carrier. CLAUDE.md/mission memory records
SK-06/#3133 (record-analysis persisting `verdict: unknown` regardless of the
submitted carrier) as reproduced twice earlier on this mission; it did **not**
reproduce on this run — recorded here per that gotcha's own "state the true
self-computed verdict explicitly alongside the persisted one" instruction, even
though the two agreed this time.

## 2026-09-07 — mark-status has no work-package scoping flag (SK-135)

Subtask ids collide across work packages in this mission, and
`spec-kitty agent tasks mark-status <TASK_ID> --status <status>` takes no
`--wp`/`--work-package` flag to disambiguate which WP's copy of a colliding id to
target — every lifecycle transition recorded in `status.events.jsonl` for both
WP01 and WP02 needed `--force` (`force_count: 2` each in `status.json`;
`force: true` confirmed directly in `status.events.jsonl` on both WPs'
`in_progress` -> `for_review` transitions). This is a tooling limitation, not
incomplete work on this mission's part — every forced transition carried a
written rationale at the time, and the lane's actual review/approval outcome is
unaffected by the forcing.

## 2026-09-07 — finalize-tasks is topology-blind (SK-133)

`finalize-tasks` wrote this mission's WP files with a generic `branch_strategy`
narrative that did not match this mission's actual `single_branch` topology (per
`meta.json`) — corrected by hand in commit `89550f775` ("tasks: correct
finalize-tasks' generic branch_strategy to this mission's single_branch topology
(SK-133)"). Left uncorrected, the WP files' own `branch_strategy` prose ("this
mission has no coordination branch, no per-WP branches, and no worktrees") would
have actively misled a later reader: `lanes.json` shows this mission DOES route
WP01/WP02 through per-WP lane worktrees (`lane-a`, `lane-b`) — only WP03 itself
has no lane worktree of its own. See the next entry for the concrete cost of that
same gap surfacing again downstream, in WP03's own run.

## 2026-09-07 — a mission-branch gate count taken before lane consolidation reads as a regression, with nothing warning about it

Discovered live during WP03's own baseline re-verification, independently by both
WP03 and the orchestrator running the same commands in parallel. WP01 and WP02
were `approved` in `status.json` (reviewed, reproduced, both reviewer-verified
against their own lane worktrees) but their lane branches had not yet been merged
into the mission branch `fix/runtime-advance-guard-3883`. Every NFR-001 gate
command run directly on the mission branch therefore measured the **unfixed**
tree and produced the plan.md-cited pre-change baseline (598 / 672+1 / 745+1 /
1666+1-325) instead of the post-fix counts the WP01 reviewer had already verified
on lane-a (618 / 672+1 / 765+1 / 1686+1-325) — a difference large enough, and
shaped enough like the exact NFR-001 table, to read as a regression at a glance.
Nothing in spec-kitty's own output (a plain `git status`/`pytest` run) names which
branch a count was taken on, or that lane consolidation is still outstanding — a
command that runs cleanly against the wrong (pre-consolidation) tree gives no
signal that it did so. **A gate count is meaningless without naming the
branch/commit it was measured on**; future missions on this seam should record
that alongside every count, not only after a mismatch is first noticed.

## 2026-09-07 — `cd` into a lane/mission worktree silently redirects all later `spec-kitty` state commands

`cd` persists across shell calls in this harness. Once an agent `cd`s into a lane
worktree (e.g. `.worktrees/<mission>-lane-a`), every subsequent `spec-kitty`
command run from that shell targets *that worktree's frozen copy* of
`status.json`/`status.events.jsonl` — and reports `OK` while silently writing to
the wrong surface, rather than failing. Reading state back from the same shell
afterward shows every work package sitting at its genesis lane, which looks
exactly like state corruption; the real mission-branch state was correct
throughout the incident this was first observed on. A command that succeeds
loudly against the wrong copy is materially worse than one that fails outright —
always run `spec-kitty` from the mission's primary checkout and verify `pwd`
before any state-touching command.

## 2026-09-07 — closing note on the record-analysis verdict defect (SK-06/#3133)

Already recorded in full above ("2026-09-07 — record-analysis verdict check"):
reproduced twice, then did **not** reproduce on a third run — intermittent, not
constant, refining this ledger entry's prior "constant" framing. No new
reproduction to add at WP03 close-out; recorded here only as the closing
cross-reference this file's own append-only discipline expects.
