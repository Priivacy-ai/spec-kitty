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
