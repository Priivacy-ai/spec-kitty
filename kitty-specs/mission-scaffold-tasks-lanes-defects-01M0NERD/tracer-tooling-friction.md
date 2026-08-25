# Tracer — tooling friction

Mission: `mission-scaffold-tasks-lanes-defects-01M0NERD` (issue #3673)
spec-kitty 3.2.6rc3, checkout's own `.venv/bin/spec-kitty`.

Append as friction occurs. This file feeds `SPEC-KITTY-LEDGER.md`. Mark every entry
**verified first-hand** or **reported by a subagent** — an unverified entry is a lead,
not a finding.

---

## F1 — `agent mission create` emits four event-capture warnings, then succeeds

**Verified first-hand**, orchestrator, 2026-08-22, during the branch-first scaffold.

```
Warning: event journal capture failed: project sync store is locked
Warning: Event routing failed: project sync store is locked
Warning: Event did not durably queue; dropping from publication
Warning: Explicit-context event capture failed: machine layout cutover did not publish
  within the bounded wait; the event is routed to the loud surface rather than dropped
  to legacy
```

The command then returned `"result": "success"` and wrote every promised file. Same family
as ledger **SK-65** (machine layout sticks in `CUTOVER_PENDING`, event-emitting commands
stall then fail loudly). Here it did **not** stall for minutes and did **not** fail — it
warned and continued, with one event explicitly dropped from publication.

Not blocking. Recorded because a scaffold that drops an event from publication while
reporting success is exactly the silent/partial-success class this mission exists to close,
and because it is evidence about SK-65's current severity on rc3.

## F2 — branch-first scaffold worked as the ledger predicted

**Verified first-hand.** `agent mission create --start-branch` minted
`fix/mission-scaffold-lanes-defects-3673`, derived topology `single_branch`, and
auto-committed `meta.json` — no SK-62/SK-57/SK-36 dead end. Recorded as a positive
control: the branch-first workaround holds on 3.2.6rc3.

## F3 — `spec-kitty plan --mission <slug> --json` hangs indefinitely and never emits `PlanCompleted`

**Verified first-hand**, plan-authoring agent, 2026-08-22, `.venv/bin/spec-kitty`
(this checkout's own venv, 3.2.6rc3), invoked exactly as instructed:
`.venv/bin/spec-kitty plan --mission mission-scaffold-tasks-lanes-defects-01M0NERD --json`.

Ran under `timeout 90`; the process printed only the same event-capture warnings F1
already documents (`project sync store is locked`, event dropped from publication,
"machine layout cutover did not publish within the bounded wait") and then hung —
**no JSON payload, no exit, killed by the 90s timeout (exit 124)**. Two independent
runs (one implicit, one explicit) show the same shape:

1. **Implicit, pre-dating this session**: `status.events.jsonl` already carried a
   `PlanStarted` event with **no matching `PlanCompleted`**, and `plan.md` already
   existed on disk as the bare, unfilled scaffold template (`git status` shows it
   `??` — untracked, never committed). So an earlier `plan` invocation got far enough
   to write the template file and emit `PlanStarted`, then never returned.
2. **Explicit, this run**: re-invoking `plan --json` against the same mission
   reproduced the same hang (event-capture warnings, then silence) under a 90s
   timeout, with no additional output and no change to `plan.md` on disk.

**Not blocking** for this WP: `plan.md`'s scaffolded template was already present and
correct (matches the canonical `plan.md` template shape), so the plan-authoring agent
filled it in directly rather than re-attempting the hung command a third time, per the
reflexive-failure clause (no hand-edit of `meta.json`/status files was needed or done —
only `plan.md`, which is this step's own deliverable, was written).

**Likely same root cause as F1** (event journal / project sync store lock), but a more
severe manifestation on this invocation: F1 warned and **completed** (`result: "success"`);
this one warns and **never returns control to the caller** — an even sharper instance of
the silent/hung-success family this mission's own FR-001–FR-004 are about closing for a
different subsystem. Recorded as evidence for whichever future mission takes on the
event-capture/sync-store-lock defect class; not attributed to or fixed by this mission.

## F4 — `spec-kitty agent mission finalize-tasks --json` hangs after fully completing its
work: WPs bootstrapped and committed, `lanes.json` correctly computed and written, but the
process never returns control and the final artifact-commit step never runs

**Verified first-hand**, tasks-authoring agent, 2026-08-22, `.venv/bin/spec-kitty`
(this checkout's own venv, 3.2.6rc3), invoked exactly as instructed:
`timeout 120 .venv/bin/spec-kitty agent mission finalize-tasks --mission mission-scaffold-tasks-lanes-defects-01M0NERD --json`.

Same warning shape as F1/F3 (project sync store locked, machine layout cutover
did not publish within the bounded wait, event dropped from publication), then the
process printed no JSON payload and never exited — killed by the 120s timeout
(exit 124). This is the third first-hand hang reproduction on this mission (after
F3's `plan --json` hang) and, per the orchestrator's own briefing, was expected as a
live possibility for `finalize-tasks` specifically (ledger SK-70's own title names
`spec-kitty plan`, but the briefing flagged "any spec-kitty command may share the
root cause" — confirmed here).

**Unlike F3, this run's underlying work did NOT stall — it completed, including a
real git commit pipeline, before the trailing hang:**

- `status.events.jsonl` shows `TasksStarted` → `WPCreated` (WP01) → `WPCreated` (WP02)
  → `TasksCompleted` (`wp_count: 2`), all within the same second, followed by two
  `status.events.jsonl` lane-transition entries (`WP01`/`WP02` → `planned`, 11s apart —
  each a `spec-kitty agent status emit`-style commit under the hood).
- `git log` confirms four real commits landed during this run:
  `6d4bb481c chore(spec-kitty): status transition WP01`,
  `098b928d8 chore(spec-kitty): status transition WP02`,
  `96c6bb507 chore: update issue-matrix for mission-scaffold-tasks-lanes-defects-01M0NERD`,
  `43270f10a chore(mission-scaffold-tasks-lanes-defects-01M0NERD): scaffold acceptance-matrix`.
- `lanes.json` was written to disk with real, non-degenerate content (not the `(None,
  None)` FR-003 defect this very mission fixes — confirmed by reading it directly, see
  the orchestrator's own report for the exact JSON observed).
- But `kitty-specs/mission-scaffold-tasks-lanes-defects-01M0NERD/{tasks.md,lanes.json,
  wps.yaml,tasks/WP01-*.md,tasks/WP02-*.md}` are all `??` (untracked) in `git status` —
  the final commit step for these specific artifacts never ran. The process hung
  somewhere after `_compute_and_write_lanes` succeeded and after the acceptance-matrix
  scaffold commit, before whatever commits `tasks.md`/`lanes.json`/`wps.yaml`/the WP
  files themselves.

**Handled per the orchestrator's explicit instruction: no hand-edit, no hand-commit.**
The already-correct on-disk content was left exactly as the tool wrote it — none of
`meta.json`, WP frontmatter, or status files were hand-edited to route around the hang,
and the untracked artifacts were not `git commit`-ed by hand (the orchestrator's brief
explicitly forbids committing anything outside `finalize-tasks`'s own commit pipeline).
The command was re-invoked (still under a bounded `timeout`) to let the tool's own
pipeline finish the commit it started.

**Same shape as SK-70/SK-71, sharper evidence for the "not atomic" framing SK-71
already documents**: this is not merely "rejections aren't atomic" (SK-71's framing) —
here nothing was *rejected* at all, every check passed, and the run still left a
half-committed working tree because the process hung in what looks like trailing
event-capture/notification plumbing (the same warned-about sync-store lock from F1/F3),
not in any of the FR-002/FR-003/FR-004 validation logic itself. Recorded as evidence for
whichever future mission takes on the event-capture/sync-store-lock defect class or
SK-70/SK-71's atomicity fix; not attributed to or fixed by this mission.

**Retried twice more (3 attempts total), all under `timeout 120`, all identical
shape — this is not a transient contested lock:**

- Attempt 2: `finalize-tasks --json` again. No new `TasksStarted`/`WPCreated`/commit —
  the tool appears to short-circuit past the already-materialized WPs and go straight
  to the same trailing hang point (same warnings, exit 124, no new git activity, no
  new `status.events.jsonl` entries).
- Attempt 3: the prose-mode invocation (`finalize-tasks` without `--json`, as the
  `spec-kitty.tasks-finalize` skill names as its canonical command) got noticeably
  further before hanging — it printed `Scaffolded issue-matrix.json`, `Regenerated
  tasks.md from wps.yaml (2 WPs)`, `✓ Computed 2 execution lane(s)`, a parallelization-
  risk advisory (`0.24`, below the `0.60` threshold — confirms `lane-a`/`lane-b` are
  correctly read as low-conflict/independent), and `Scaffolded acceptance-matrix.json`
  — then hit the identical warning block and hung, exit 124, no new commit.
- Checked for a stale lock file or holding process before giving up: no `.lock` files
  under `~/.spec-kitty` (only `clock.json`), no `spec-kitty`/`specify_cli` process in
  `ps aux`, nothing in `lsof` referencing either. **This rules out a stale contested
  file lock as the cause** — "project sync store is locked" / "machine layout cutover
  did not publish within the bounded wait" is an in-process condition that trips every
  time, not an external resource a human can free by killing a stray process.

**Net state after 3 attempts, verified by direct read each time**: `tasks.md`,
`wps.yaml`, both WP files, and `lanes.json` are present on disk with correct,
consistent content across all 3 runs (the lane graph — `lane-a`={WP01},
`lane-b`={WP02}, both `depends_on_lanes: []`, both `parallel_group: 0` — was
identical every time it was recomputed), but remain **git-untracked**: the tool's own
final commit step for these specific artifacts has not completed in any of the 3
attempts. Per the mission briefing's explicit instruction, this was **not** worked
around by a hand `git commit` (forbidden — "do not commit anything outside what
finalize-tasks's own commit pipeline commits") and no mission state file was
hand-edited. Left for the orchestrator to decide: retry later once the underlying
event-capture hang is fixed elsewhere, or explicitly authorize an exception.

**Addendum to F4, orchestrator, 2026-08-22, verified first-hand.** After the tasks-authoring
agent's 3 hung attempts, the orchestrator independently checked for a lock file the
authoring agent's own `find ~/.spec-kitty -iname '*.lock'` had missed (its check likely ran
before the 3rd attempt's hang produced one). Found:

```
$ stat ~/.spec-kitty/projects/.layout-generation.lock
  Size: 0  Modify: 2026-08-22 23:31:32  (checked at 23:33:05, ~93s stale)
$ # scanned every /proc/*/fd for an open reference to this path — none found
$ ps aux | grep spec-kitty   # no spec-kitty/specify_cli process running at all
```

**A concrete, named artifact for the "project sync store is locked" / "machine layout
cutover did not publish within the bounded wait" warnings F1/F3/F4 all report but never
previously pinned to a file**: `~/.spec-kitty/projects/.layout-generation.lock`, 0 bytes,
present, and — at the moment checked — held by no live process. Whether this specific file
is the proximate cause of the trailing hang or a downstream symptom of it is not established
here (it could be written just before the hang and simply never cleaned up on a killed
process, rather than being what other processes contend on) — recorded as evidence, not a
diagnosis, for whoever takes on the SK-65/SK-70 event-capture/sync-store-lock family.
**Not deleted, not otherwise touched** — the phase brief's instruction not to hand-edit
tool/mission state to route around a hang was read to cover this file too, out of caution,
even though it is spec-kitty's own internal lock rather than a mission artifact.

**Second addendum, orchestrator, 2026-08-22, verified first-hand — root cause pinned down
precisely, not merely "suspected."** Read (not modified) `~/.spec-kitty/projects/.layout-generation.json`:

```json
{"generation":2,"migration_id":"auto-cutover-ab61886d4c1539e365fdbb92eb28b894",
 "mode":"cutover_pending","updated_at":"2026-08-16T18:46:09.491407+00:00"}
```

This is the global (cross-project) machine-layout migration state every "machine layout
cutover did not publish within the bounded wait" warning (F1, F3, F4) is waiting on. It has
been sitting in **`cutover_pending`** since **2026-08-16 — six days before this mission ran**,
across whatever number of intervening sessions/missions have touched `~/.spec-kitty/` in that
window. This is the concrete, named state behind ledger **SK-65**, and now direct evidence
that **SK-70's `plan --json` hang and this mission's own F4 `finalize-tasks` hang share not
merely a "suspected" root cause but the identical, currently-still-stuck migration record** —
any command that must wait for this cutover to publish is a candidate to hang, which matches
F1 (warned, did not wait, succeeded), F3 (`plan`, hung forever), and F4 (`finalize-tasks`,
hung forever after otherwise completing). **Not fixed here** — resolving a stuck cross-project
migration is squarely SK-65's territory, not this mission's fail-loud/reject-only scope (D1),
and the file was read only, never modified, per the phase brief's instruction.

## Analyze phase, 2026-08-23 — SK-22 and SK-32 both reproduced first-hand, exactly as documented

**SK-22 (`record-analysis` refuses `DIRTY_WORKTREE` against its own preceding review trail)
reproduced first-hand.** After the analyze-phase R1-R6 review squad finished (3 rounds: 3
initial confirmed findings, 2 fresh-sweep findings, 2 further fresh-sweep findings, all
resolved), running `record-analysis` against the finished draft report failed immediately:

```json
{"success": false, "error_code": "DIRTY_WORKTREE",
 "error": "Refusing to record analysis report with pre-existing dirty working tree.",
 "dirty_paths": ["kitty-specs/.../reviews/analyze-fresh-2.yaml", ... 11 files total],
 "remediation": ["Commit or stash existing changes, then rerun /spec-kitty.analyze."]}
```

The 11 dirty paths were exactly the review-squad's own `reviews/analyze*.yaml` artifacts
produced *by this analyze phase itself* (lens findings, merge, refute, confirmed, three
verify rounds, two fresh-sweep rounds) — not stray or unrelated dirt. This is SK-22's exact
shape: the documented analyze → fix → re-analyze cycle has no step that commits the review
trail before `record-analysis` runs, so the phase's own supporting artifacts block its own
persist step. **Followed SK-22's own guidance, not the stash workaround it warns against**:
committed the review trail first with `spec-kitty safe-commit kitty-specs/.../reviews/ -m
"docs(analyze): commit analyze-phase R1-R6 review trail..." --to-branch
fix/mission-scaffold-lanes-defects-3673` (commit `9f794fe12`), confirmed a clean
`git status --porcelain`, then re-ran `record-analysis` successfully. No `git stash` used —
SK-22 flags stash entries as an orphaned-state hazard for the next reader, so committing the
trail (which is git-history-eligible content anyway, per the phase's own "commit the whole
reviews/ trail" instruction) was the correct order rather than a workaround.

**SK-32 (`record-analysis` injects host-absolute paths into the committed artifact)
reproduced first-hand, exactly as the ledger predicts.** The draft report handed to
`record-analysis` contained zero host-absolute paths (verified: `grep -n "/home/"` on the
draft returned nothing). The committed `analysis-report.md`'s `input_artifacts` block gained
four:

```
path: /home/jeroennouws/dev/SK-missions/3673/kitty-specs/mission-scaffold-tasks-lanes-defects-01M0NERD/spec.md
path: /home/jeroennouws/dev/SK-missions/3673/kitty-specs/mission-scaffold-tasks-lanes-defects-01M0NERD/plan.md
path: /home/jeroennouws/dev/SK-missions/3673/kitty-specs/mission-scaffold-tasks-lanes-defects-01M0NERD/tasks.md
path: /home/jeroennouws/dev/SK-missions/3673/.kittify/charter/charter.yaml
```

Per SK-32's own guidance, **not hand-stripped** — the artifact was left as generated
(commit `65d977d06`), this note stands as the required record instead, and it is not treated
as a mission-introduced regression: it is upstream `#3398` reproducing on the 176th (at
minimum) `kitty-specs/*/analysis-report.md` file on `main`, not a defect this mission's D1
fail-loud/reject-only scope covers or could fix without adding exactly the kind of new
surface D1/C-001 forbid.

**The verdict field itself did NOT hit SK-06.** The draft report's carrier began with a
literal `---` on line 1, carried `schema: analysis-findings/v1` exactly, and used only the
closed `low`/`medium`/`high`/`critical` severity vocabulary throughout all three authoring/
fix rounds — `record-analysis` parsed it correctly and the committed `analysis-report.md`
reads `verdict: ready`, matching the derived-from-findings rule (5 `low` findings, 0
`high`/`critical`) exactly. Recorded here as a confirming data point for SK-06's own
"correct input shape, for copying into briefs" guidance, which the analyze-author subagent's
prompt followed verbatim and which held up across three separate fix-round edits to the same
carrier without ever silently regressing to `unknown`.

## F5 — `agent tasks mark-status` prints a `LayoutCutoverIncompleteError` traceback on every
call, then still succeeds (WP01)

**Verified first-hand**, WP01 implementer, 2026-08-23. Every
`SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 timeout 600 .venv/bin/spec-kitty agent tasks mark-status
<Txxx> --status done --mission mission-scaffold-tasks-lanes-defects-01M0NERD` invocation for
T001/T002-T004/T006/T005 printed a full Python traceback ending in
`specify_cli.sync.layout_generation.LayoutCutoverIncompleteError: machine layout cutover did
not publish within the bounded wait; the event is routed to the loud surface rather than
dropped to legacy`, sourced from `sync/body_queue.py:224` -> `sync/layout_generation.py:390`
-> `:694`. Every one of these five invocations still printed `✓ Marked <Txxx> as done` and the
task status was in fact persisted correctly (confirmed by re-reading `tasks.md`/`tasks/`
frontmatter after each call). Consistent with this mission briefing's own "Cutover warnings
print even on success — judge by exit code and JSON, never by warnings" guidance and with the
SK-65/SK-72 host-stall entries already on this ledger (this checkout carries 172 project dirs
under `~/.spec-kitty`); not re-diagnosed further here since the briefing already names this as
expected noise, but recorded because the traceback is loud enough (a full stack, not a one-line
warning) that a less-briefed implementer could plausibly mistake it for a real failure and
attempt an unnecessary hand-edit recovery.

## F6 — same `mark-status` friction as F5, but rendered as `Warning:` lines, not a traceback
(WP02)

**Verified first-hand**, WP02 implementer, 2026-08-23. The single batched invocation
`SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 timeout 600 .venv/bin/spec-kitty agent tasks mark-status
T008 T009 T010 T011 T012 T013 T014 T015 T016 T017 --status done --mission
mission-scaffold-tasks-lanes-defects-01M0NERD --json` printed FOUR `Warning:` lines
("event journal capture failed: machine layout cutover did not publish within the bounded
wait...", "Event routing failed...", "Event did not durably queue; dropping from
publication" x2) rather than F5's full Python traceback — same root cause (SK-65/SK-72
layout-cutover under 172 project dirs), different presentation this run. The trailing JSON
line was still well-formed and reported `"outcome": "updated"` for all 10 task IDs with
`"summary": {"updated": 10, "already_satisfied": 0, "not_found": 0}}`, and re-reading
`tasks.md`/the WP file's frontmatter confirmed all ten subtasks actually recorded. Consistent
with the briefing's "judge by exit code and JSON, never by warnings" guidance — noted here
because F5 described a traceback specifically, and a future implementer grepping for that
exact shape might not recognize this warning-only variant as the same known-noise class.
