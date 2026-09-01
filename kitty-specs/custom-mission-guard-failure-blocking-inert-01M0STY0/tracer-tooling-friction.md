# Tooling Friction Log

> Log every place the tooling fought you so it can feed the tooling-gap backlog.

**Prompting questions**
- What tooling or command did you have to work around?
- What blocked you unexpectedly, and how long did it take to unblock?
- Was this a known issue or something discovered fresh?

---

## Entries

<!-- YYYY-MM-DD — 1-3 sentences: what happened, why it slowed you down. -->

2026-08-24 — `.venv/bin/spec-kitty plan --mission custom-mission-guard-failure-blocking-inert-01M0STY0 --json`
took >120s (backgrounded, completed under 3 min) and emitted several non-fatal warnings to
stderr before the JSON result line: `event journal capture failed: project sync store is
locked`, `Event routing failed: project sync store is locked`, `Event did not durably queue;
dropping from publication`, and `Explicit-context event capture failed: machine layout cutover
did not publish within the bounded wait`. The command still succeeded (`"result": "success"`,
`plan_file` written, `scaffold_only: true`) and the plan.md scaffold was written correctly
despite the noisy event-journal-lock warnings — did not block planning, just needed to be read
past. This is the SK-63/SK-65/SK-70 warning-signature family in SPEC-KITTY-LEDGER.md (identical
`event journal capture failed: project sync store is locked` /
`Explicit-context event capture failed: machine layout cutover did not publish within the
bounded wait` text, same command shape `spec-kitty plan --mission <slug> --json`), adjacent to
issue #3283's shared-lock-timeout class. Specifically, this occurrence matches SK-65's
milder variant — warned, stalled, then completed, JSON payload returned, `"result": "success"`
— not SK-70's full hang (partial state written, no JSON, no exit) nor SK-63's more severe
non-completing sibling (prints its success JSON but then never exits or commits at all). Not
re-diagnosed further here since it did not block this mission's work; see the ledger entries
for the tracked root cause and recommended fix.

2026-08-24 — The mission brief's blast-radius list named `doctrine/missions/step_projection.py`
alongside the actually-edited files. Reading it in full (rather than assuming it needed an edit
because it was listed) was necessary to correctly conclude it should stay read-only for this
mission (see plan.md's Seam and module placement table, final row, and the closing "Design
decisions" section) — a case where the mission brief's blast-radius framing ("read to
understand") needed to be distinguished from "necessarily edited," worth flagging for a future
mission brief to state that distinction more explicitly up front.

2026-08-24 (tasks phase) — `spec-kitty agent mission finalize-tasks --mission
custom-mission-guard-failure-blocking-inert-01M0STY0 --json` (v3.2.6rc3) **silently overwrites the
`planning_base_branch` and `branch_strategy` WP-frontmatter fields with values that contradict
this mission's own binding stacking instruction** — a real, load-bearing tooling defect, not
worked around here per instruction ("NEVER hand-edit... to work around a tooling problem — a
wrong-looking result is something you report, not patch around").

**What happened**: All 4 WP prompt files (`tasks/WP01-*.md` through `WP04-*.md`) were authored
with `planning_base_branch: "fix/org-tier-expected-artifacts-3703"` — the stacked parent branch —
per spec.md's own Clarifications section ("every WP's red-first ATDD verification MUST use
`planning_base_branch = fix/org-tier-expected-artifacts-3703`, not `main`") and plan.md's
ATDD-first-per-WP table (anchor column = that same branch for every WP), both already-PASSED,
reviewed artifacts. `finalize-tasks --validate-only --json` previewed exactly this overwrite
(`would_modify` showed `planning_base_branch` changing to `"fix/custom-mission-guard-3704"` — the
mission's own `target_branch` from `meta.json` — for all 4 WPs) before any commit was made. The
real (non-`--validate-only`) run then executed this overwrite for real, committing it at
`42a5d768199db5dde196443c6913d7b3e83f762f` ("Add tasks for feature
custom-mission-guard-failure-blocking-inert-01M0STY0"). Every WP's `branch_strategy` was
simultaneously overwritten from a mission-specific, stacking-aware sentence (naming
`fix/org-tier-expected-artifacts-3703`, PR #3708, and the red-first-anchor rationale) to a
generic templated sentence that never mentions the stack at all: *"Planning artifacts for this
mission were generated on fix/custom-mission-guard-3704. During /spec-kitty.implement this WP may
branch from a dependency-specific base, but completed changes must merge back into
fix/custom-mission-guard-3704 unless the human explicitly redirects the landing branch."*

**Root cause (inferred, not verified against source)**: `finalize-tasks`'s WP-frontmatter
bootstrap appears to treat `planning_base_branch` as always-equal-to-`target_branch` (the value
from `meta.json`), with no concept of a mission being stacked on an unmerged parent branch
different from its own target/merge branch. There is no `--target-branch`-style escape hatch for
this specific field (that flag overrides `target_branch` itself, which was already correct here —
the bug is elsewhere, in the `planning_base_branch` bootstrap logic unconditionally mirroring
`target_branch`).

**Impact**: every WP's frontmatter, as committed, now states its red-first ATDD-verification
anchor is `fix/custom-mission-guard-3704` (this mission's own branch, which currently has no
functional commits — verified via `git merge-base fix/org-tier-expected-artifacts-3703
fix/custom-mission-guard-3704` equaling `fix/org-tier-expected-artifacts-3703`'s own HEAD at
authoring time) rather than the true stacked-parent anchor. Practically, red-verifying against
either branch would currently produce the same result (no functional commits yet distinguish
them) — but this stops being true the moment WP01's first implementation commit lands, at which
point a WP-implementing agent trusting the committed frontmatter over the mission's own spec.md/
plan.md/tasks.md would red-verify against the wrong, moving target (this mission's own
in-progress branch) instead of the fixed stacked parent, silently defeating NFR-003's ATDD-first
discipline for this specific stacked mission.

**Disposition**: NOT hand-edited. `tasks.md` and every WP body still state the correct anchor
explicitly and prominently (tasks.md's own "ATDD-first discipline" section documents this exact
tension and resolution in advance, anticipating this could happen); a WP-implementing agent
reading the WP body (not just its frontmatter) has the correct instruction either way. Flagged
here and in the tasks-authoring session's final report to the orchestrator as a tooling gap:
`finalize-tasks`'s `planning_base_branch` bootstrap needs a stacked-mission-aware mode (or an
explicit override flag) before this class of stacked mission can trust its own frontmatter
output.

2026-08-24 (analyze phase) — `timeout 90 .venv/bin/spec-kitty agent mission record-analysis
--mission custom-mission-guard-failure-blocking-inert-01M0STY0 --input-file - --json` hit ledger
SK-93 (the dossier body-upload write-authority path) on the analyze phase's own persistence
command. The command was killed by the `timeout 90` wrapper — **exit 124** — and **no `--json`
payload was ever printed**: none of the usual `{"success": true, "result": "success", ...}` line
reached stdout before the kill. Stderr carried the SK-93/SK-65 warning signature exactly:
`event journal capture failed: project sync store is locked`, `Event routing failed: project sync
store is locked`, `Event did not durably queue; dropping from publication`, and
`Explicit-context event capture failed: machine layout cutover did not publish within the bounded
wait`.

Per SK-93's own guidance ("the only reliable check is `git status` plus the command's own printed
result line") — the printed result line was unavailable here, since the kill happened before it
ever printed — the persisted state was verified independently instead of trusting the hang or the
exit code: `git log --oneline -- kitty-specs/custom-mission-guard-failure-blocking-inert-01M0STY0/analysis-report.md`
showed a real commit (`23191cd0c`, "Add analysis report for mission
custom-mission-guard-failure-blocking-inert-01M0STY0"), `git status --porcelain -uno` was clean,
and the committed file's frontmatter read `verdict: ready` with `findings: []` and all
`issue_counts` at zero — exactly matching what was intended. **Nothing was hand-edited** to work
around the hang; the underlying write-then-commit had already landed before the sync/telemetry
layer stalled, and only the CLI's own `--json` echo was lost with the killed process. This
occurrence's shape (raised nothing to stdout, hung, exit 124, but real state already committed)
most closely matches SK-93's logged shape #4 (`agent action implement WP03`: new lock warning,
then silent hang, `EXIT: 124`) — same exit code, same "work landed before the stall" outcome —
now also confirmed on `record-analysis` specifically, which SK-93's own log did not previously
include as one of its four observed call sites.

2026-08-24 (analyze phase, fix round re-run) — `record-analysis` hit ledger SK-93 a **second**
time on this mission, same command, same warning signature (`event journal capture failed:
project sync store is locked`, `Event routing failed`, no `--json` payload printed), exit 124.
This time the underlying write landed on commit `2f0bcb762` ("Add analysis report for mission
custom-mission-guard-failure-blocking-inert-01M0STY0") — verified the same way as the first
occurrence: `git log`/`git status --porcelain -uno` read directly rather than trusting the hang
or exit code, confirming `verdict: ready`, `findings: []`. Nothing hand-edited; this is a
recurrence of the pattern already fully documented above, not a new root cause.

2026-08-24 (analyze phase, fix round 2 re-run) — `record-analysis` hit ledger SK-93 a **third** time on this mission, same command and warning signature, this time on commit `26c80c758` ("Add analysis report for mission custom-mission-guard-failure-blocking-inert-01M0STY0"); ground truth verified the same way (`git log`/`git status --porcelain -uno` read directly) confirming `verdict: ready`, `findings: []` — same recurring pattern, nothing hand-edited.

2026-08-24 (WP01 implement phase, Wrangler Wendy) — `timeout 60 .venv/bin/spec-kitty agent action
implement WP01 --agent claude --mission custom-mission-guard-failure-blocking-inert-01M0STY0` hit
ledger SK-93 a **fourth** time on this mission, on a new call site (`agent action implement`, not
previously logged for this mission — SK-93's own log lists `agent action implement WP03` from a
different mission as one of its four originally observed shapes, so this is that same shape
recurring on a different WP/mission pair): the command hung past the 60s timeout with exit 124 and
no visible completion output. Per SK-93 guidance, ground truth was verified independently rather
than trusting the exit code: `git worktree list` showed the lane-a worktree
(`.worktrees/custom-mission-guard-failure-blocking-inert-01M0STY0-lane-a`) already materialized on
branch `kitty/mission-custom-mission-guard-failure-blocking-inert-01M0STY0-lane-a` at commit
`8685dec23`, and `spec-kitty agent tasks status --mission ...` confirmed WP01 had already
transitioned to `in_progress` (claimed by `claude`, marked "stale: 10.3m" — the CLI's own staleness
detector noticing the same hang). So the underlying claim + worktree materialization had already
succeeded before the process stalled; nothing was hand-edited to work around it. Recommend SK-93's
tracked defect list be updated to include `agent action implement` (initial claim, not just
resume) as a fifth/recurring call site across missions, not just WP03-specific.

2026-08-24 (WP01 subtask bookkeeping, Wrangler Wendy) — `spec-kitty agent tasks mark-status
T001..T004 --status done --mission custom-mission-guard-failure-blocking-inert-01M0STY0` (run in a
loop) hit ledger SK-93 a **fifth** time on this mission: the first three (`T001`-`T003`) hung past
their individual `timeout 30`s (exit 124, no visible output before the kill) and the fourth
(`T004`) was cut off mid-hang when the surrounding shell loop itself hit its own outer timeout.
`T005`-`T007` (run individually afterward with `timeout 40`) printed the same
`LayoutCutoverIncompleteError: machine layout cutover did not publish within the bounded wait`
traceback to stderr but this time *also* printed the command's own `✓ Marked T00N as done` success
line and returned exit 0 — so for those three the printed result line WAS available and matched
ground truth. For `T001`-`T004`, per SK-93 guidance, ground truth was verified independently
instead of trusting the hang: `status.events.jsonl` already carried four `kind: annotation` events
(`delta: {"subtasks": {"T00N": "done"}}`) for `T001`-`T004` timestamped seconds after each command
was issued, and `status.json`'s materialized `work_packages.WP01.subtasks` reflected all four as
`"done"` — confirming the underlying writes had already landed before each process stalled on the
sync/telemetry tail. Nothing hand-edited to work around any of this. This occurrence's shape (a
CLI subcommand that both intermittently hangs AND intermittently prints a noisy-but-harmless
`LayoutCutoverIncompleteError` traceback while still succeeding) most closely matches SK-93's
already-logged pattern; recommend the ledger also note `agent tasks mark-status` as a repeat call
site, and that the `LayoutCutoverIncompleteError` traceback specifically is cosmetic noise on the
success path, not evidence of failure, when a `✓ Marked ... as done` line follows it.

2026-08-24 (WP02 implement phase) — `agent action implement WP02` hit ledger SK-93 a **sixth**
time on this mission: ran with `SPEC_KITTY_SYNC_MINIMAL_IMPORT=1` exported and `timeout 120`-wrapped
per this mission's own standing tracer guidance; the process printed **zero bytes of output** for
the full 120s before being killed (exit 143, `Terminated` — the outer shell's own timeout
signature, not the CLI's). Per SK-93 guidance, the exit code/hang was **not** treated as evidence
either way: ground truth was verified directly instead. `spec-kitty agent tasks status --mission
custom-mission-guard-failure-blocking-inert-01M0STY0` (repo-root primary partition; this mission's
`single_branch` topology routes status there) showed WP02 already in the "Doing" lane, `stale:
27.8m, agent: claude` — and `status.events.jsonl` on the repo-root primary checkout confirmed two
real events (`claimed` then `in_progress` for WP02, actor `claude`, `policy_metadata.shell_pid:
913164`), already committed on `fix/custom-mission-guard-3704` at commit `042880ea1` ("chore(spec-kitty):
status transition batch WP02"). The state transition had landed before the dossier body-upload
stall; only the CLI's own completion echo was lost with the killed process, same shape as every
prior SK-93 occurrence logged above. The same hang/silent-success shape recurred repeatedly on
`spec-kitty agent tasks mark-status T008..T015 --status done` (run in a loop and individually):
several individual invocations hit their own `timeout 30`/`timeout 60` wall with zero stdout
before being killed, yet `status.events.jsonl`'s `kind: annotation` / `delta.subtasks` entries for
every one of T008-T015 were present and correctly ordered afterward, confirmed via direct
`grep`/`git log`, not by trusting any exit code. Nothing hand-edited to work around any of this.

2026-08-24 (WP02 implement phase, kitty-specs/lane-branch near-miss) — a **new** friction shape,
distinct from SK-93: this WP's own tracer-file append (the entry directly above) was first
written and committed **on the lane worktree branch**
(`kitty/mission-custom-mission-guard-failure-blocking-inert-01M0STY0-lane-a`), because
`kitty-specs/` is a real, git-tracked directory inside that worktree and `spec-kitty safe-commit`
accepted the commit with only an advisory `[spec-kitty guard] WARNING: Protected path: ... —
implementation branches must not modify kitty-specs/` (not a hard block at commit time). The
lane worktree's copy of `kitty-specs/` was a **stale snapshot** relative to the planning branch
(`fix/custom-mission-guard-3704`) -- it predated WP01's own tracer entries and status/issue-matrix
updates that had already landed on the planning branch via WP01's own repo-root `safe-commit`
calls. Appending to the lane branch's stale copy and committing it there would have **silently
reverted WP01's planning-branch-only tracer entries and status updates** had it ever merged. The
defect surfaced only later, as a hard block: `spec-kitty agent tasks move-task WP02 --to
for_review` refused with `Cannot move WP02 to for_review ... kitty-specs/ changes are not allowed
on lane branches`, naming the offending commit and providing the exact recovery (`git restore
--source fix/custom-mission-guard-3704 --staged --worktree -- kitty-specs/`). Recovered by
following that guidance exactly (commit `e058350ed` on the lane branch, "chore: remove planning
artifacts from lane branch"), then re-applying this tracer entry directly on the planning branch
at the repo-root checkout instead. **Recommend**: `safe-commit` should refuse (not just warn) a
`kitty-specs/` write on an implementation lane branch at commit time, matching `move-task`'s own
enforcement -- the current advisory-warn-then-hard-block-later shape lets a lane-branch tracer/kitty-specs
commit land and only surfaces the problem at the next state transition, after the (wrong) commit is
already made.

2026-08-24 (WP02 F1 fix) — **The mission `.venv` lives at the checkout root
(`3704/.venv`), not inside the lane worktree** (`3704/.worktrees/<slug>-lane-a/`). Every
doctrine snippet and mission brief writes tool paths as relative `.venv/bin/mypy` /
`.venv/bin/ruff` / `.venv/bin/python`, which **fail from inside a lane worktree** — the
directory simply is not there. Agents working a WP must use the absolute path
`/home/jeroennouws/dev/SK-missions/3704/.venv/bin/{mypy,ruff,python}`. This cost one agent a
round of confusion and caused an earlier WP agent to borrow a `ruff` binary from an unrelated
sibling checkout rather than conclude the path was simply wrong. Worth stating in the WP-agent
brief: **lane worktrees do not carry the venv.**

2026-08-24 (WP02 F1 fix) — `spec-kitty safe-commit` requires **positional `FILES...`** and
warns that `--to-branch` becomes mandatory in v3.3. A bare `safe-commit -m "..."` — the shape
most generic guidance sketches — fails with `Missing argument 'FILES...'`. Not a defect, but
it means "use safe-commit for every commit" is under-specified guidance wherever it appears.
(Related: the orchestrator hit the same shape when the design-phase doctrine's "run the final
`spec-kitty spec-commit`" step turned out to need explicit `FILES...` too, with nothing
outstanding to pass it.)

2026-08-24 (WP02 F1 fix) — `safe-commit` emitted a non-fatal `ACTIVE_WP_CONTEXT_AMBIGUOUS`
guard warning on the lane branch (WP01 `approved`, WP02 `for_review`, so no single active WP)
and committed successfully anyway. Consistent with SK-93's lesson: the warning and the exit
code are both weak evidence — the artifact on disk was verified instead. An earlier
`ACTIVE_WP_CONTEXT_STALE` warning (`current_wp=WP01, canonical active_wp=WP02`) behaved the
same way.
