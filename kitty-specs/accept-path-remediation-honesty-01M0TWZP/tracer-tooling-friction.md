# Tracer: Tooling Friction

Mission: accept-path-remediation-honesty-01M0TWZP (issues #3730, #3085)

## 2026-08-24 — scaffold-time friction (first-hand orchestrator observation)

`spec-kitty agent mission create` succeeded (the scaffold — `meta.json`, `spec.md`
placeholder, `tasks/`, `research/`, `checklists/` — completed correctly and is present
on disk), but emitted the following during the run (CLI 3.2.6rc3, mission checkout,
2026-08-24):

- `project sync store is locked`
- `Event routing failed`
- `Event did not durably queue; dropping from publication`
- `machine layout cutover did not publish within the bounded wait`

Per the reflexive-failure clause, this is recorded here rather than hand-fixed. The
scaffold artifacts themselves are intact and usable, so this did not block the mission,
but the durability/event-routing chain around `mission create` is suspect and should be
checked by whoever next touches `agent mission create`'s sync/event plumbing.

## 2026-08-24 — scaffold commit message defect

The scaffold's auto-commit (`e2ecee4ee`) reads `Add meta for feature
accept-path-remediation-honesty-01M0TWZP` — both commitlint-invalid (no
`type(scope): subject` form) and a Terminology Canon violation (uses "feature"
instead of "Mission"). Per instruction, **not amended mid-mission** — this is a
PR-prep concern, noted here for sk-implement / sk-review to pick up.

## 2026-08-24 — pre-existing claim comment on #3085

`gh issue view 3085 --comments` shows a `MOES-Media` comment: "Claiming: mission
`accept-path-remediation-honesty` in progress. This mission covers #3730 and #3085
together." Per prior mission learning (claim comments reserve nothing; re-check
upstream state before resuming), this was noted but not treated as blocking since the
orchestrator explicitly directed resumption of this scaffolded mission on this branch.
Flagged for the operator in case of a duplicate concurrent effort.

## 2026-08-25 — `finalize-tasks` (lanes.json branch/surface-prediction defect confirmed first-hand)

The real (non-`--validate-only`) `spec-kitty agent mission finalize-tasks --mission
accept-path-remediation-honesty-01M0TWZP --json` run at the end of the tasks phase
reported `"result": "success"` and did seed genesis→planned events for all four WPs
correctly (a separately suspected lane-seeding defect did **not** reproduce on this run —
`status.events.jsonl` shows real
`from_lane: genesis, to_lane: planned` transitions for WP01-WP04, each with a distinct
`event_id`/timestamp). `tasks.md`, `wps.yaml`, and all four WP files' `dependencies`
frontmatter match exactly what the tasks-phase review squad approved (WP01→WP02→WP01,WP02→
WP01,WP02,WP03 chain) — no lane-graph/tasks.md contradiction observed either.

However, `lanes.json` (written by the same command) confirms the following defect
first-hand:
- `mission_branch: "kitty/mission-accept-path-remediation-honesty-01M0TWZP"` — this
  branch does not exist anywhere in this checkout (`git rev-parse --verify` fails). The
  mission's real topology is `single_branch` (per `meta.json`), working entirely on
  `fix/accept-path-remediation-honesty-3730` — there was never a separate
  `kitty/mission-*` branch to reference.
- `predicted_surfaces: ["api", "app-shell", "artifact-rendering", "legacy-cleanup",
  "tests", "tracker-integration"]` — four of these six labels (`api`, `app-shell`,
  `artifact-rendering`, `tracker-integration`) are unrelated to this mission's actual
  blast radius (`src/specify_cli/validators/`, `src/specify_cli/acceptance/`,
  `src/specify_cli/cli/commands/accept.py` — a CLI path-validation reporting fix with no
  API/app-shell/artifact-rendering/tracker-integration surface at all).

Per instruction, **not hand-edited** — `lanes.json` is left as the tool wrote it. Neither
field is consumed by anything this mission's own WPs read (the WP files' own
`planning_base_branch`/`merge_target_branch` frontmatter correctly reference
`fix/accept-path-remediation-honesty-3730`, not the phantom `kitty/mission-*` branch), so
this did not block the phase, but it is a live, reproducible confirmation of the
`lanes.json` branch/surface-prediction defect described above.

Also observed: the JSON output's top-level `commit_hash`/`commit_hashes` report only the
**last** of the commits `finalize-tasks` actually created on this run — `git log` shows
seven new commits (`576cbc813` issue-matrix update, four per-WP `chore(spec-kitty): status
transition WP0N` commits, `7a41439bc` acceptance-matrix scaffold, then `f6f05c4e1` the
final "Add tasks for feature..." commit carrying `tasks.md`/`wps.yaml`/the WP files/
`lanes.json`), not the single commit the summary implies. Not itself a correctness defect
(all seven commits are real, non-empty, and land on the correct branch), but worth noting
for anyone reading the command's JSON output expecting a 1:1 commit-count correspondence.

## 2026-08-25 — `record-analysis` (analyze phase) — no verdict/tracking/path-leak reproduction

`spec-kitty agent mission record-analysis --mission accept-path-remediation-honesty-01M0TWZP
--input-file <temp>.md --agent claude-sonnet --json` (CLI 3.2.6rc3) persisted
`analysis-report.md` correctly on first attempt: `verdict: ready` was written verbatim
(matching the computed carrier — 0 high/critical findings, 3 low + 1 medium), so the
separately suspected silent-`verdict: unknown`-for-a-legacy/malformed-carrier defect did
not reproduce here — the
`analysis-findings/v1` frontmatter carrier from the author was well-formed. `analysis-report.md`
landed tracked and committed in the same run (`41cf739c9`, `docs(record-analysis): record
analysis report for mission accept-path-remediation-honesty-01M0TWZP`) — the separately
suspected report-left-untracked-or-uncommitted defect did not reproduce either.
`grep -n "/home/" analysis-report.md`
returned no matches — the separately suspected host-absolute-path-injected-into-the-committed-artifact
defect did
not reproduce; the committed `input_artifacts` hashes use repo-relative paths only (consistent
with `_relativize_or_raise`/FR-007 in `src/specify_cli/analysis_report.py`, which appears to
be a landed fix for exactly this class). No hang after `"success": true` was observed
(the separately suspected hang-after-success defect did not reproduce) and no
`_charter_path` mismatch surfaced — the
charter hash resolved against `.kittify/charter/charter.yaml` without error. The
project-sync-store lock warnings noted at scaffold time (2026-08-24 entry above) recurred
here on event emission but were non-blocking, consistent with the "live, noisy,
non-blocking" characterization already on file.

Separately: the subagent that ran this command stranded itself waiting on a notification for
its own background CLI invocation after the command had already completed and committed
(the spec-kitty agent-harness pattern of a subagent blocking on its own background work rather than
the harness's completion signal) — a dispatch-hygiene observation for the orchestrator, not
a spec-kitty CLI defect.

## 2026-08-25 — `record-analysis` (analyze phase, first-hand)

`.venv/bin/spec-kitty agent mission record-analysis --mission
accept-path-remediation-honesty-01M0TWZP --input-file <temp-report> --agent
claude-sonnet --json`, run from repo root on this checkout (CLI 3.2.6rc3).

**Symptom-by-symptom check** (per this phase's own instruction to check for a fixed
set of previously-tracked defects — verdict-writing, tracking, path-leak, and hang
behaviour among them):

- **Verdict silently written as `unknown`**: did **not** fire. The persisted
  `analysis-report.md`'s `verdict:` field reads literally `ready`, computed correctly
  from the submitted carrier (0 critical/high, 1 medium, 3 low findings) — confirmed
  by reading the committed file directly, not just the command's own JSON summary.
- **Report left untracked/uncommitted**: did **not** fire for the report
  itself — `analysis-report.md` is tracked and committed
  (`41cf739c9 docs(record-analysis): record analysis report for mission
  accept-path-remediation-honesty-01M0TWZP`), `git diff --stat` on the file is empty.
  **However, a related side-effect artifact WAS left dirty by this same command
  run**: `.kittify/dossiers/accept-path-remediation-honesty-01M0TWZP/snapshot-latest.json`
  was regenerated (a fresh `snapshot_id`, `total_artifacts` growing from 4 to 57,
  a new `parity_hash_sha256`) but `git status --porcelain` shows it as modified,
  not committed — `record-analysis`'s own auto-commit covered only
  `analysis-report.md`, not the dossier snapshot its own run also touched. This is
  the same class of imprecise side-effect commit bookkeeping already noted for
  `finalize-tasks` (see the entry above, same file, 2026-08-25) — a different command,
  same pattern: the tool mutates more on disk than what its own commit captures.
  Not hand-fixed per instruction (non-remediating step; do not commit files not
  explicitly authorized) — left for whoever next touches `record-analysis`'s
  dossier-refresh side effect.
- **A further previously-tracked defect, not otherwise characterized in this
  record**: no symptom observed matching it in this run (not enough
  independent context to confirm absence beyond "nothing matching fired here").
- **Host-absolute path injected into the committed artifact**: did **not**
  fire — `grep -n "/home/" analysis-report.md` returns no match (exit code 1).
- **Hangs after printing `"success": true`, never returns or commits**: did
  **not** fire in the strict sense — the command exceeded the foreground 120s
  timeout and had to be moved to a background task, but it then completed normally
  on its own (exit code 0) with `"success": true"` as the LAST line printed before
  natural process exit, and the commit (`41cf739c9`) is real. This is **slowness**,
  not the hang-after-success pattern — worth distinguishing explicitly since
  they'd otherwise look identical from partial output. The delay coincided with the
  same sync-store lock contention below, so likely the same root cause as that
  reported symptom, just not severe enough to fully hang this run.
- **`_charter_path` mismatch**: no symptom observed matching this defect in this run.

**Sync-store lock warnings** (noisy, non-blocking — same class already recorded for
`mission create` and `finalize-tasks` above): every run of this command printed
`Warning: event journal capture failed: project sync store is locked`,
`Warning: Event routing failed: project sync store is locked`,
`Warning: Event did not durably queue; dropping from publication`, and
`Warning: Explicit-context event capture failed: machine layout cutover did not
publish within the bounded wait ...` — repeated multiple times over the run's
duration. Did not block the command's actual success or the report's correctness;
recorded here for the same reason as the prior two entries (durability/event-routing
chain around agent commands is suspect and should be checked by whoever next
touches that plumbing) and as the likely explanation for this run's slowness noted
under the hang-after-success entry above.

## 2026-08-25 — WP01 implementer friction (first-hand, Wrangler Wendy)

- **`spec-kitty agent action implement WP01 --agent claude` required an explicit
  `--mission` flag despite `spec-kitty next --agent claude --mission <slug>` already
  resolving and reporting the mission unambiguously immediately before it in the same
  session.** Without it the command fails fast with `Error: --mission <slug> is
  required` — a small papercut, not a defect, but the two commands in the documented
  canonical loop don't share context, so the operator/agent must repeat the mission
  slug on every `agent action` invocation even mid-session.
- **`agent action implement WP01 --agent claude --mission <slug>` exceeded the 120s
  foreground timeout and was silently moved to a background task by the harness.**
  Unlike the `record-analysis` slowness noted above (2026-08-24 entry), this command's
  background output file was **empty on completion** — no captured stdout at all,
  despite the run visibly succeeding (worktree `.worktrees/<mission>-lane-a` created,
  WP01 frontmatter gained `base_branch`/`base_commit`, and `status.events.jsonl` grew
  two real transitions, `planned`→`claimed`→`in_progress`, plus a profile-resolution
  annotation event). The only way to confirm the command's actual effect was to read
  `lanes.json`, the WP frontmatter diff, and the event log directly — the command's own
  output channel gave zero signal either way. This is a diagnostic gap: a command that
  silently succeeds past its foreground timeout should still leave a real transcript in
  its backgrounded output file.
- **The venv is not present inside the WP's own worktree** (`.worktrees/<mission>-lane-a/.venv`
  does not exist — only the mission checkout root has `.venv/`). Running tests against
  code edited inside the worktree therefore requires `PYTHONPATH=<worktree>/src`
  prepended ahead of the root `.venv/bin/python`, confirmed by checking
  `import specify_cli; specify_cli.__file__` resolves to the worktree copy before
  trusting any test result — otherwise the root venv's editable install (pointed at the
  mission checkout's own `src/`, not the worktree's) silently tests the WRONG copy of
  the code with zero error. Matches the documented CLAUDE.md guidance
  (`PYTHONPATH=<worktree>/src`) but is easy to miss if you don't already know to look
  for it, and a wrong-copy false-green here would be maximally deceptive (tests appear
  to pass, but never touched the actual edit).
- **First test run under `tests/conftest.py`'s session-scoped `test_venv` autouse
  fixture triggered a real network `pip install` of the full dependency set** (~1
  minute, dozens of packages) building a *separate*, isolated CLI-execution test venv —
  distinct from and not destructive to the hand-built root `.venv`. Confirmed
  non-destructive: `.venv/bin/ruff`/`mypy`/`pytest` all still resolved correctly
  afterward. Matches the known-live `#3283` shared-test-venv-lock friction named in this
  WP's own dispatch prompt; recorded here as first-hand confirmation of the specific
  symptom (network install on first touch, not a hang) rather than a new defect.
- **`spec-kitty safe-commit` on this very tracer file printed a guard warning it did
  not block on**: `[spec-kitty guard] WARNING: Protected path:
  kitty-specs/accept-path-remediation-honesty-01M0TWZP/tracer-tooling-friction.md —
  implementation branches must not modify kitty-specs/`, then committed anyway
  (`Requested files committed`, exit 0). This is the exact file this WP's own dispatch
  prompt instructs the implementer to append to during implementation — so the guard's
  rule ("implementation branches must not modify `kitty-specs/`") and this mission's own
  governed instruction ("append during implementation") are in direct tension for tracer
  files specifically. Non-blocking today (a WARNING, not a hard reject), so it did not
  stop this WP, but the mismatch is worth resolving upstream: either the guard should
  carve out an exception for tracer files, or the mission-authoring guidance should stop
  directing implementers to write to a path the guard considers off-limits for their
  branch kind.

## 2026-08-25 -- WP02 implementer friction (first-hand, Wrangler Wendy): sandbox ENOSPC after implement WP02

`spec-kitty agent action implement WP02 --agent claude --mission
accept-path-remediation-honesty-01M0TWZP` exceeded the 120s foreground timeout and was
moved to a background task by the harness (same class as WP01's own noted friction,
entry above). Its own captured-output file was empty when checked. Immediately after
this, every subsequent Bash tool invocation in the session -- including trivial
no-op commands (`true`, `echo`) -- failed with `ENOSPC: no space left on device`,
writing to the harness's own `/tmp/claude-.../tasks/*.output` capture path (not a
path this mission's code touches). `Write` to the session scratchpad failed the same
way. `Read` continued to work; `Edit` needed a smaller, single-line anchor string to
succeed (a larger multi-paragraph anchor silently failed to match despite the text
reading identical on screen -- possibly itself a symptom of the same resource
exhaustion). This is a session/sandbox-level resource-exhaustion condition, not a
spec-kitty CLI defect as far as could be determined without shell access to inspect
disk usage -- but the backgrounded `implement WP02` invocation is the only thing that
changed state immediately beforehand, so a causal link (e.g. that command or its
event/sync-store plumbing writing unbounded output/logs) cannot be ruled out and is
flagged for whoever next investigates the `agent action implement` background-task
path. Recorded here per instruction rather than worked around, since no Bash-based
workaround was available.

## 2026-08-25 -- WP03 implementer friction (first-hand, Wrangler Wendy): safe-commit guard warns ACTIVE_WP_CONTEXT_AMBIGUOUS on a WP still marked `planned`

Both `spec-kitty safe-commit` invocations for WP03's two subtask commits (T012 tests,
then T010/T011 source) printed a non-blocking guard warning:
`[spec-kitty guard] WARNING: ACTIVE_WP_CONTEXT_AMBIGUOUS: Cannot prove active WP for
branch kitty/mission-accept-path-remediation-honesty-01M0TWZP-lane-a; lane_id=lane-a;
active candidates: none; lane states: WP01=approved, WP02=approved, WP03=planned,
WP04=planned`, then committed anyway (`Requested files committed`, exit 0). This
mission's dispatch instructions explicitly forbid running `spec-kitty agent action
implement` on this WP (it has repeatedly backgrounded past timeout and stranded prior
sessions -- see the WP02 entry above), so WP03's lane status was never transitioned out
of `planned` before this implementer began editing files directly. The guard appears to
expect the `implement` verb to have run first to establish "active WP" context for
`safe-commit`'s own bookkeeping; skipping it per this mission's own operating
instructions produces a WARNING every commit, not a hard block. Recorded as new
friction distinct from the already-noted kitty-specs protected-path warning (WP01/WP02
entries above) and the implement-backgrounding friction itself -- this is the
*downstream* effect on `safe-commit` of deliberately avoiding the backgrounding verb.

## 2026-08-25 -- WP04 implementer friction (first-hand, Wrangler Wendy): baseline pass-count off by one before this WP's own additions

This WP's dispatch prompt cited an orchestrator-captured cumulative baseline of 190
passed (post-WP03) across the committed accountability surface (`tests/specify_cli/
acceptance/`, `tests/specify_cli/cli/commands/test_accept_warnings_render.py`,
`tests/agent/test_validators_unit.py`, `tests/characterization/test_trio_json_envelope.py`).
Measured first-hand, with this WP's own new file temporarily removed from the working
tree to isolate the pre-existing count: 189 passed, not 190 -- a one-test discrepancy
present before this WP touched anything (confirmed via `git status --porcelain`
showing zero modifications to any pre-existing file at measurement time). Not chased
further (out of this WP's scope to bisect which prior WP's own count was off by one,
and the mission's Definition of Done only requires the surface stay green and the
count reach `>= 180`, which it does: 192 without the architectural suite, 202 with
it). Recorded so a reviewer reconciling the mission's cumulative pass-count narrative
against a fresh count is not surprised by the one-off delta.

## 2026-08-25 -- WP04 implementer friction (first-hand, Wrangler Wendy): `spec-kitty agent tasks mark-status` hangs with zero output

`spec-kitty agent tasks mark-status T013 --status done --mission
accept-path-remediation-honesty-01M0TWZP` produced NO output at all and hung past a
2-minute foreground timeout. Two further attempts also hung with zero output: a single
task with a 100s `timeout`, and all three tasks (`T013 T014 T015`) together with
`--no-auto-commit --json` and a 60s `timeout` -- ruling out both the auto-commit git
step and JSON-vs-text rendering as the cause. `mark-status --help` itself returns
instantly, so the binary and argument parsing are fine; the hang is inside the command
body before any output is flushed. Not an ENOSPC condition -- `df -h /tmp` showed 4.6G
free and `/home` showed 534G free at the time, and no orphaned `spec-kitty` process was
left behind after the `timeout` kills. Per this mission's own operating instruction not
to retry failing commands in a loop, this was not retried a fourth time. Consequence:
T013-T015 status was NOT recorded via the event-sourced `mark-status` command as the WP
file's Definition of Done specifies; the actual deliverable (the fixture file, red-first
verification, and gates) is complete and reported directly in this WP's hand-off
instead. Flagged for whoever next touches the `agent tasks mark-status` command path --
this is a distinct symptom from the already-noted `agent action implement`
backgrounding-past-timeout friction (this one never even starts producing output).
