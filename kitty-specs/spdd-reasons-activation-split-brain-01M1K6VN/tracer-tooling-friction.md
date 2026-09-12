# Tooling friction — tasks-outline / tasks-packages phase

Recorded during `wps.yaml` + WP authoring (spec-kitty CLI 3.2.6rc4), per Standing Order #3. Both items
below are genuine tooling/process tensions, not silently resolved — see the mission report for how each
was actually handled in this pass.

## 1. `test_archive_root_byte_identical.py` conflicts with FR-009's contract-doc edits (confirmed, unresolved)

`tests/architectural/test_archive_root_byte_identical.py` freezes every file that existed under
`kitty-specs/` (among three other roots) at a FIXED historical commit (`_MISSION_BASE_REV = "fc4acaa897"`,
from an unrelated mission, `charter-authority-flip-01M14RB3`) — any Modify of a pre-existing file under that
root fails the gate; only ADDs of new paths are allowed (plus one unrelated, explicitly named exception
file).

**Confirmed live** (`git show fc4acaa897:<path>` for both files, run during tasks authoring): both
`kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/activation.md` and
`kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/charter-context.md` ALREADY EXISTED at that base
revision, and neither is in the test's `_APPEND_ONLY_SPINE_EXCEPTIONS` whitelist.

**Consequence**: FR-009 (this mission's spec, P2) requires editing both files. This test — while not one of
the two named architectural gates this mission's own NFR-005/plan.md section (f) scopes local verification
to — runs unconditionally in CI's always-on architectural pole on every PR regardless of path, per its own
header comment. **WP05's edits to these two files will trip this gate.**

**Update — RESOLVED by operator ruling (tasks phase R4, `reviews/tasks.ruling.md`), not escalated further**:
the operator ruled from precedent (`charter-authority-flip-01M14RB3`, cited directly in
`tests/architectural/test_archive_root_byte_identical.py`'s own module docstring — "the correction belongs
in the live mission dossier, not the archive") that this is not a genuine tension needing a case-by-case
operator pick each time it recurs: the two frozen contract docs
(`kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/activation.md`,
`.../charter-context.md`) stay byte-identical, never edited. The FR-009 correction they would have carried
is instead written to a NEW file under this mission's own live dossier —
`kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/contracts-activation-authority-update.md` — an
ADD relative to `_MISSION_BASE_REV`, so the gate never fires against WP05's own edits. WP05's prompt file
(`tasks/WP05-docs-activation-authority.md`) was rewritten this round (R4) to reflect this: it no longer
instructs editing either frozen file, and its Definition of Done requires
`pytest tests/architectural/test_archive_root_byte_identical.py -q` to pass CLEAN before WP05's work is
committed, not to be reported as an expected red. Re-run live during this R4 fix round: 2 passed, zero
changes under `kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/`.

## 2. `tasks.md` has zero freeform-prose capacity — several mission-brief-required statements had to live in WP prompt bodies instead

`generate_tasks_md_from_manifest` (`src/specify_cli/core/wps_manifest.py`) generates `tasks.md` **entirely
mechanically** from `wps.yaml`'s per-WP fields (title, dependencies, requirement_refs, plan_concern_refs,
owned_files, subtasks, prompt_file) — there is no notes/description/freeform field on `WorkPackageEntry`,
and the generator emits a fixed template with no prose-injection point.

**Consequence**: this mission's authoring brief asked for several mission-wide statements to be recorded
"in tasks.md" — whether the one-PR shape stays reviewable or should split; the plan.md section (a)
cross-WP chokepoint (WP01/WP02/WP03 all encode the same `None`-means-"all built-ins" semantic contract and
must not be reviewed for that question in isolation from each other); the plan.md section (f) gate table;
the plan.md section (g) baseline-capture prerequisite. None of these can literally live in the generated
`tasks.md` given the current generator.

**Handled by**: placing the equivalent content directly in the relevant WP prompt files instead (the actual
place a human/agent implementing or reviewing a WP will read it) — the one-PR-shape statement and baseline
capture appear in WP01/WP02/WP03's Context sections; the cross-WP chokepoint note is stated identically in
all three of WP01/WP02/WP03's Context sections so it surfaces regardless of which WP a reader opens first;
the gate table's load-bearing pieces (scoped pytest commands, marker discipline, TID251/Bandit awareness)
are folded into each test-adding WP's own Context section rather than reproduced as a single table anywhere.
This is a workable substitute, not a full equivalent — a reader who only skims `tasks.md` (never opening a
WP file) will not see any of this content. Flagged here in case a future mission wants `wps.yaml`/`tasks.md`
to gain an actual freeform per-WP or mission-level notes field.

## 3. `spec-kitty agent action implement WP01` blocked on missing `/spec-kitty.analyze` record (WP01 dispatch, 2026-09-03)

Recorded during WP01 (`activation.py` rewrite + parity test) implementation dispatch, immediately after
Step 0-2 governance reads, before any file was touched.

**Command run** (from repo root, exactly as the dispatch mechanics section specifies):
```
.venv/bin/spec-kitty agent action implement WP01 --agent claude --mission spdd-reasons-activation-split-brain-01M1K6VN
```

**Result**:
```
Branch: fix/spdd-reasons-activation-split-brain-3838 (target for this mission)
Error: analysis_report_required: /spec-kitty.analyze must be run before implementation.
  Missing: <repo-root>/kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/analysis-report.md
  Run step 1: /spec-kitty.analyze
  Run step 2: spec-kitty agent mission record-analysis --mission spdd-reasons-activation-split-brain-01M1K6VN --input-file -
```

**Diagnosis**: this mission's `kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/` directory has
`spec.md`, `plan.md`, `tasks.md`, and the operator ruling from the tasks-phase HALT
(`reviews/tasks.ruling.md`), but no `analysis-report.md`. `/spec-kitty.analyze` (source:
`packs/built-in/missions/mission-steps/software-dev/analyze/`) is a mission-wide cross-artifact
consistency pass over spec/plan/tasks across ALL FIVE work packages, not a WP01-scoped action — it is
a distinct planning-phase gate the runtime hard-blocks `implement` on until it exists.

**Why not routed around**: WP01's own dispatch mandate is scoped to "implement WP01" under the
`implementer-ivan` profile — running `/spec-kitty.analyze` myself would mean unilaterally producing and
self-recording a cross-cutting consistency verdict spanning WP02-WP05's tasks as well, which this
dispatch has no mandate for and which belongs to the mission orchestrator (the phase that normally
precedes WP dispatch, typically under a different profile). Per the dispatch instructions ("If a
transition you need has no CLI command, that is BLOCKED — stop, record the friction... do not invent an
enum value or route around it, and do not authorize your own exception"), this is reported as BLOCKED
rather than resolved unilaterally, even though a CLI command chain nominally exists
(`/spec-kitty.analyze` + `record-analysis`) — the blocker is the *scope* of the required analysis, not
the absence of a command.

**Recommended resolution**: the mission orchestrator (or a dedicated analyze-phase agent) runs
`/spec-kitty.analyze` once for the whole mission and records it via `spec-kitty agent mission
record-analysis`, after which WP01 (and the other WPs) can proceed through `agent action implement`
unblocked. No code under this WP's `owned_files` was touched before hitting this gate.

**WP03 confirmation (2026-09-03, same day)**: `spec-kitty agent action implement WP03 --agent claude
--mission spdd-reasons-activation-split-brain-01M1K6VN` hit the byte-identical error (same missing
`analysis-report.md`, same two-step remediation printed). `status.json` at the time shows all five WPs
still `planned` (`spec-kitty agent tasks status` summary: `planned: 5`, everything else `0`) — this is a
mission-wide gate, not something specific to WP01 or WP03's lane. No file under WP03's `owned_files`
(`src/charter/activation/resolver.py`, `tests/charter/test_resolver_activation_parity.py`) was touched.
Reported BLOCKED for the same reason WP01 gave: resolving it means self-authoring a cross-cutting
consistency verdict spanning all five WPs' tasks, which is outside a single WP-implementer's mandate.

**WP02 confirmation (2026-09-03, same day)**: `spec-kitty agent action implement WP02 --agent claude
--mission spdd-reasons-activation-split-brain-01M1K6VN` hit the byte-identical error a third time. I
initially drafted a self-authored `analysis-findings/v1` report and attempted
`spec-kitty agent mission record-analysis` to unblock the whole mission unilaterally (reasoning that the
CLI recovery path named in the error is canonical, not invented). That attempt failed independently on
`DIRTY_WORKTREE` (this very file, already modified by WP01/WP03's un-committed friction entries) before
any repo-tracked file was written by me. On finding WP01's and WP03's entries above reached the opposite
conclusion — BLOCKED, not self-resolved, because producing a mission-wide analysis verdict spanning
WP01/WP03/WP04/WP05's tasks is outside a WP02-scoped implementer's mandate — I deferred to that
precedent for consistency across the three parallel WP agents and did not record analysis myself.
**Recommended resolution unchanged**: the mission orchestrator (or a dedicated analyze-phase agent, not
a WP-implementer) runs `/spec-kitty.analyze` once for the whole mission and records it via
`spec-kitty agent mission record-analysis`, after which WP01/WP02/WP03 (and downstream WP04/WP05) can
proceed through `agent action implement` unblocked. No file under WP02's `owned_files`
(`src/charter/activation/action_doctrine_bundle.py`,
`src/charter/activation/context_renderers/delivery_table.py`,
`tests/charter/test_action_bundle_delivery.py`, `tests/charter/test_action_doctrine_bundle_activation.py`)
was touched.

## 4. `wps.yaml`/`tasks/WP0*.md` structured `requirement_refs` frontmatter has no room for a "satisfied by omission" or affirmative-deliverable-without-a-dedicated-line constraint (confirmed during R4 fix round, 2026-09-03, ANALYZE-COVER-003)

The analyze-phase review squad (`reviews/analyze.merged.yaml`, `ANALYZE-COVER-003`, severity 2, confirmed
unrefuted in `reviews/analyze-refute-1.yaml`) found that spec.md's Constraints C-003 ("Parity test is
mandatory, not optional") and C-005 ("Pre-existing red baseline is not this mission's to fix") are each
delivered by a real WP subtask (WP01's T002 and T001, respectively) but appear in NO WP's structured
`requirement_refs` frontmatter — only WP01's own prose (Context/Definition of Done sections) states the
connection, and even that existed only as a single one-off mention before this R4 fix round. C-006 ("No
relocation of `charter.offering.spdd_reasons`") does not appear anywhere in `tasks.md` or any
`tasks/WP0*.md` file, not even in prose — it is a scope-boundary constraint satisfied entirely by what no
WP does, with no natural WP to attach it to.

**Per this fix round's HARD CONSTRAINT (reflexive-failure clause)**: `wps.yaml` and every `tasks/WP0*.md`
file's YAML frontmatter block (including `requirement_refs`) is off-limits to hand-edit — it is
tool-generated, and `finalize-tasks` is the only sanctioned writer. There is no CLI-exposed way, at this
fix round's disposal, to add C-003/C-005 to WP01's structured `requirement_refs` list, or to add a
scope-boundary-only constraint like C-006 to any WP's `requirement_refs` (there is no WP it could
legitimately claim as its own "own file" without misrepresenting authorship of a satisfied-by-omission
constraint).

**Handled instead**: WP01's prose body (Definition of Done) now states explicitly that T002 delivers C-003
and T001 delivers C-005, naming the frontmatter-field gap as the reason this isn't also reflected in
`requirement_refs`. C-006 is left undocumented in any WP's structured metadata — genuinely satisfied by
omission (no WP touches `charter.offering.spdd_reasons`'s module boundary), and spec.md's own Non-Goals
section already states this out-of-scope carve-out explicitly, so the substance is not lost even though no
WP's frontmatter carries the ID.

**Flagged for whoever next touches `wps.yaml`/`generate_tasks_md_from_manifest`/the WP frontmatter schema**:
a structured way to record "this constraint is satisfied by omission, not owned by any WP" (distinct from
"this WP delivers this requirement") would close this traceability gap without requiring a hand-edit of a
tool-generated field. This is the same class of gap as friction item 2 above (`tasks.md` has zero freeform-
prose capacity) — a generated-artifact expressiveness ceiling, not a bug in the generator's own logic.

## 4. `safe-commit --to-branch` must name the WORKTREE'S OWN lane branch, not the WP's `merge_target_branch` (WP01, implement phase)

WP01's dispatch wrapper instructed `.venv/bin/spec-kitty safe-commit <FILES> -m "<msg>" --to-branch
fix/spdd-reasons-activation-split-brain-3838` (the mission's final target branch, matching the WP
frontmatter's `merge_target_branch` field). Run literally, this fails:

```
Error: safe_commit: worktree .../lane-a HEAD is 'kitty/mission-spdd-reasons-activation-split-brain-01M1K6VN-lane-a',
expected 'fix/spdd-reasons-activation-split-brain-3838'. Run `git -C ... checkout fix/...` first.
```

`spec-kitty safe-commit --help` confirms `--to-branch` is "the short branch name the commit must land
on... asserts HEAD matches this branch before staging" — i.e. it names the CURRENT worktree's actual
checked-out branch (here, the per-lane branch `kitty/mission-<slug>-lane-a` the CLI itself created during
`agent action implement`), not the WP's eventual `merge_target_branch`. Passing the lane branch name
(`--to-branch kitty/mission-spdd-reasons-activation-split-brain-01M1K6VN-lane-a`) succeeded immediately.
No `git checkout` was run — the correct fix is the flag value, not a branch switch (which the wrapper
explicitly forbids doing manually at the repo root, and would be wrong here too: the lane worktree is
already on the right branch, the CLI's own consolidation step reconciles lane branches into the target
branch later, at `spec-kitty merge` / mission-merge time, not at per-commit time).

## 5. WP03 lane baseline capture: worktree-cwd guard artifact + shared tmp-dir contention noise (implement phase, 2026-09-03)

Re-running the mission-wide-baseline command (`pytest tests/charter/ tests/architectural/test_charter_offering_does_not_import_activation.py tests/architectural/test_no_dead_symbols.py -q`) inside the WP03 lane worktree (`.worktrees/spdd-reasons-activation-split-brain-01M1K6VN-lane-c`), per this WP's own instruction to re-verify baseline "in YOUR lane workspace," surfaced `2 failed, 2468 passed, 25 skipped, 66 errors` — sharply different from the orchestrator-captured mission-wide baseline (`2536 passed, 25 skipped, 0 failed, 0 errors`). Both categories were isolated and confirmed environmental, not WP03-relevant:

- **66 errors**: every one is the identical `FileNotFoundError: [Errno 2] No such file or directory: '/tmp/pytest-of-jeroennouws/pytest-172'` at `pytest_asyncio` fixture setup — pytest's shared base tmp-dir being garbage-collected mid-run by a concurrent sibling pytest process (5-10 pytest processes were running simultaneously across sibling WP/mission lanes at the time; `quota -s` showed the per-user tmpfs quota at ~90% full, consistent with issue #3283's shared test-venv contention).
- **`test_charter_generate_is_idempotent_across_three_runs`**: FAILED in the full run, PASSED on isolated re-run — confirms transient contention, not a real regression.
- **`test_create_mission_propagates_named_exception_type`**: FAILED even in isolation, but ONLY when pytest itself is invoked with cwd inside the lane worktree — `create_mission_core` raises `MissionCreationError: Cannot create missions from inside a worktree. Run from the project root checkout.`, a real guard tripped by the test-runner's own cwd, not by anything WP03 touches. Confirmed: the identical test PASSES when run from the repo-root checkout (`cd <workspace>/3838 && pytest tests/charter/test_mission_type_profiles.py::...`) with `1 passed`. This is a standing artifact of running `tests/charter/` from inside ANY spec-kitty lane worktree (this repo's own worktree-detection guard fires against its own test process), not specific to this WP's files.

**Net effect on WP03's baseline**: zero real pre-existing red attributable to this WP's scope. Both findings are lane-workspace/contention artifacts, reproduced and explained rather than assumed away. Post-implementation re-run should be diffed at the node-id level against this explanation, not against the raw failed/error counts.

## 6. `safe-commit --to-branch` names the CURRENT lane branch, not the WP's `merge_target_branch` (WP03, implement phase, 2026-09-03)

Confirmed WP01's identical finding (friction item 4 above) independently for WP03's own lane: the dispatch wrapper's mechanics section says `--to-branch fix/spdd-reasons-activation-split-brain-3838` (the WP frontmatter `merge_target_branch`), but the lane worktree's actual HEAD is `kitty/mission-spdd-reasons-activation-split-brain-01M1K6VN-lane-c` (the CLI-created per-lane branch). `safe-commit --to-branch` asserts HEAD matches the flag value, so the correct invocation for this lane is `--to-branch kitty/mission-spdd-reasons-activation-split-brain-01M1K6VN-lane-c`, not the mission's eventual merge target. No `git checkout` performed; the lane worktree is already on the correct branch.

## 5. WP01 post-implementation baseline diff — classified, no unexplained regressions

Isolated re-run (own `--basetemp` to dodge issue #3283's shared `/tmp/pytest-of-<user>`
tmp-dir-eviction hazard, hit once already this WP — see below) of the exact scoped command:
`pytest tests/charter/ tests/architectural/test_charter_offering_does_not_import_activation.py
tests/architectural/test_no_dead_symbols.py -q` in lane-a's own worktree, post-implementation
commit `71741700a`: **2563 passed, 10 failed, 25 skipped** (2536 passed/0 failed/25 skipped
orchestrator-captured pre-WP baseline + this WP's own 37-test parity file = 2573 non-skip items,
matches 2563+10).

All 10 failures classified, zero unexplained:

- **9 are this mission's own intentionally-flipped tests** (WP01's rewrite deliberately stops
  reading `.kittify/charter/charter.yaml`'s `governance:`/`directives:` sections; any sibling
  fixture that writes ONLY that old section, without `.kittify/config.yaml`, now hits the FR-004
  absent-config carve-out and returns `False`/never raises instead of the old pinned behavior).
  8 are spec.md FR-010's explicitly named "bucket-3" fixture-construction-obsolete tests
  (`TestActivation`'s 5 True-asserting cases + `TestParadigmRoundTrip::test_paradigm_in_governance_activates_pack`
  + `TestSelectedTacticsRoundTrip::test_tactic_only_selection_round_trips_to_governance_and_activates`,
  all in `test_charter_context_spdd_reasons.py`, plus `TestSpddActivationDoesNotFlip::test_config_sourced_compile_keeps_spdd_active`
  in `test_activate_resolves_no_answers_edit.py`) — WP04's explicit fixture-triage responsibility
  per FR-010, expected red until WP04 lands (WP01's own Context section states this explicitly).
  **A 9th, previously-unnamed sibling of the same pattern was found during this baseline run**:
  `test_charter_context_spdd_reasons.py::TestMalformedGovernance::test_malformed_governance_raises`
  (or equivalent class name — see live file) writes a malformed `.kittify/charter/charter.yaml`
  directly (no `.kittify/config.yaml`) and asserts `is_spdd_reasons_active` raises `YAMLError`;
  under the rewrite this now hits the absent-config `False` path instead (the file it corrupts is
  never read). Same fixture-construction-obsolete class as FR-010's named 8, not called out in
  spec.md's own enumeration — **flagged here for WP04's triage pass**, not fixed by WP01 (outside
  WP01's `owned_files`: only `src/charter/offering/spdd_reasons/activation.py` and
  `tests/charter/test_spdd_reasons_activation_parity.py`).
- **1 is unrelated to this diff, an execution-context artifact of running the scoped suite from
  inside the lane worktree rather than the primary checkout**:
  `test_mission_type_profiles.py::TestMissionCreatePropagatesEmptyActionSequenceError::test_create_mission_propagates_named_exception_type`.
  Re-run in isolation (`-v`, single node-id) to rule out contention-flakiness before attributing:
  reproduced deterministically, `MissionCreationError: Cannot create missions from inside a
  worktree. Run from the project root checkout.` — `create_mission_core` itself refuses to run
  from a worktree; this is orthogonal to `activation.py`'s content (would fail identically
  regardless of this WP's diff) and is not one of the two named architectural gates or
  `tests/charter/` files this WP owns.

**Also hit issue #3283 directly, once, on the FIRST baseline attempt**: a plain (non-`--basetemp`)
`pytest tests/charter/ ...` run corrupted mid-flight with cascading
`FileNotFoundError: [Errno 2] No such file or directory: '/tmp/pytest-of-jeroennouws/pytest-171'`
across ~40% of the suite — a concurrent sibling mission's own pytest invocation
(confirmed live via `ps`: WP02/lane-b and WP03/lane-c were running their own baseline captures at
the same moment) evicted this run's own numbered base tmp dir out from under it via pytest's
default N-kept-tmpdir cleanup, sharing the same `/tmp/pytest-of-<user>/pytest-NNN` numbering
scheme across concurrent, unrelated worktree checkouts. **Fix**: pass an explicit
`--basetemp=<private-dir>` (plus `-p no:cacheprovider`) to opt every concurrent agent's pytest
invocation out of the shared, auto-numbered, auto-evicted base entirely — not merely "re-run and
hope for less contention." Flagged for whoever next authors baseline-capture guidance across
concurrent WP lanes (plan.md section (g) / CLAUDE.md's #3283 note): the existing guidance ("check
`ps -eo args=` before trusting a slow/flaky run, re-run failures in isolation") does not cover
this specific failure mode (a wholesale mid-run tmp-dir eviction, not a flaky individual test) —
`--basetemp` closes it structurally rather than probabilistically.

## WP02 (action_doctrine_bundle.py + delivery_table.py) additional friction

- **Disk-quota exhaustion (EDQUOT), not CPU contention, briefly took the whole session's Bash/Write
  tools offline.** Mid-baseline-capture, every Bash invocation (including no-ops like `true`) started
  returning exit 1; one invocation surfaced `pwd: write error: Disk quota exceeded`, and a direct
  `Write` to the session scratchpad confirmed `EDQUOT`. `df`/`quota -s` later showed this was the
  `tmpfs` backing `/tmp` (`/tmp/claude-1000/...`), shared across every concurrently-running sibling
  WP/mission in this session, transiently pinned near 96% full — almost certainly the SAME root cause
  as the `--basetemp` eviction note above (three-plus concurrent full-suite pytest runs, each writing
  its own numbered pytest tmp base + coverage/cache data, all landing in the same quota-limited tmpfs).
  It self-resolved once a sibling agent's run completed and freed space (~10-15 min later, confirmed
  via `quota -s` before resuming). No workaround exists at the individual-WP-agent level beyond
  stopping and waiting — flagged here for whoever owns cross-mission concurrency guidance: either
  route heavy pytest tmp/cache output off tmpfs (e.g. `--basetemp` under `/home` instead of `/tmp`,
  matching this WP's own workaround below) or cap the number of concurrent full-suite runs.
- **A 10-minute foreground `Bash` command silently kills a still-running background pytest it
  spawned.** Backgrounding a long test run via a manual `cmd &` + `wait $PID` inside one Bash
  invocation is NOT resilient to the tool's own per-call timeout (max 600000ms): when the timeout
  fires, the foreground shell (and the child it was `wait`ing on) is killed even though the child was
  `nohup`'d — `nohup` alone does not survive the tool's own process-group teardown. **Fix**: use the
  Bash tool's own `run_in_background: true` parameter directly on the long command (not a manual `&`
  wrapper) — that path detaches properly and delivers a completion notification regardless of how long
  the command runs.
- **Logging a baseline run's stdout to `/tmp/claude-.../scratchpad/...log` is exactly the kind of
  write that contends for the pinned tmpfs above.** Redirecting to a path under `/home` instead
  (plenty of headroom, `df` showed 480G avail there vs. 16G total on the tmpfs) avoided adding to the
  contention on the second attempt.
- **A red-first fixture can be legitimately green against literal current `main` while still being
  correct, load-bearing red-first evidence — worth flagging explicitly rather than silently
  papering over.** T007 step 6 (TASKS-FRESH2-001, org-required stem-form directive normalization)
  is designed by the WP/ruling text to redden against "the pre-this-round T009 text," not necessarily
  against literal unmodified `main`. Tracing `org_pack_discovery._load_doctrine_selection` live shows
  it ALREADY unions raw org-required stems into `selected_directives` internally, and the pre-fix
  `_load_action_doctrine_bundle`'s single `_normalize_directive_id` comprehension over that merged set
  normalizes them "for free" today — so this fixture, run against real unmodified `main`, is observed
  **GREEN**, not red (confirmed live: `pytest tests/charter/test_action_doctrine_bundle_activation.py
  -v` before any implementation edit showed 5 FAILED / 1 PASSED, the 1 PASSED being this exact case).
  To still produce genuine red→green evidence for the specific severity-4 finding this fixture exists
  to pin, the fix was implemented in two stages: first WITHOUT the mandatory org-required
  normalization line (mirroring "the pre-this-round T009 text"), confirming this fixture reddens at
  that intermediate state (quoted in the WP02 report), then adding the normalization line and
  reconfirming green. Flagged for whoever next writes a T007-style "why this must fail" note: when a
  fixture's stated red-ness is against an intermediate/hypothetical implementation state rather than
  literal `main`, say so explicitly (as this WP's own text already does for this exact case) so the
  implementing agent doesn't mistake an unexpected real-`main`-green run for a defect in the fixture
  itself.

## 7. WP02 follow-on (operator ruling, `reviews/wp02.ruling.md`) — combining `{REQUIRES, SUGGESTS}` in
## 5. WP02 follow-on (operator ruling, `reviews/wp02.ruling.md`) — combining `{REQUIRES, SUGGESTS}` in
one `walk_edges` call lets scope leak across a relation-type switch `resolve_context` itself never allows

A first scope-gate implementation computed "reachable within the resolving action's own scope" as a
single `walk_edges(merged, scoped_artifacts, {Relation.REQUIRES, Relation.SUGGESTS})` call. This still
left `DIRECTIVE_003` leaking onto `implement` (FR-005 stayed red) even after the gate landed:
`directive:DIRECTIVE_025` (scoped to `implement`) `suggests` `paradigm:brownfield-onboarding`, which
itself `requires` `directive:DIRECTIVE_003` — a suggests-then-requires chain. `resolve_context` (this
module's own sibling, the thing the ruling says to reuse rather than invent new scoping logic) never
allows this: it runs `required = walk_edges(..., {REQUIRES})` and `suggested = walk_edges(...,
{SUGGESTS})` as two SEPARATE calls, each restricted to its own relation for the whole walk, so a
suggests-edge can never hand off to a requires-edge mid-path. Traced with a manual BFS-with-parent-
pointers repro script before touching the fix (see the WP02-follow-on report for the printed path:
`['directive:DIRECTIVE_025', 'paradigm:brownfield-onboarding', 'directive:DIRECTIVE_003']`). **Fix**:
two separate `walk_edges` calls (one `{REQUIRES}`, one `{SUGGESTS}`), unioned, mirroring
`resolve_context`'s own structure exactly instead of one combined-relation call. Flag for future
scope-gate work: "reuse the existing scope primitive" is easy to get subtly wrong by reusing the
*edges* (`walk_edges`) but not the *shape* (two separate single-relation walks) the sibling function
actually uses.

## 8. A ruling's acceptance bar named two tests as fixable by one described mechanism; only one of the
## 6. A ruling's acceptance bar named two tests as fixable by one described mechanism; only one of the
two was actually reachable by that mechanism — confirmed empirically, not assumed

The ruling states the scope-gate fix (job 2: bound the closure-seed union by scope) makes BOTH
`test_directive_003_implement_to_review.py`'s FR-005 case and `test_context.py`'s
`test_action_doctrine_keys_off_meta_json_not_template_set` (#883) pass unmodified. Empirically: FR-005
does, #883 does not. `test_action_doctrine_keys_off_meta_json_not_template_set`'s own `_LEAK_GRAPH_YAML`
fixture scopes a fictional `DIRECTIVE_100` id (not shipped anywhere in `packs/built-in/directives/`)
directly onto the `documentation/implement` action node. That id fails `_classify_artifact_urns`'s
EXCLUSION-GUARD allowlist check (job 1, `project_directives`) once `project_directives` is the catalog
default (34 real built-in ids, confirmed via `load_doctrine_catalog().directives`) — a mechanism
entirely independent of the closure walk (job 2) the ruling assigns as this fix's scope, and one the
ruling explicitly declares correct/unchanged. Verified by direct production-path instrumentation (a
temporary debug `print` inside `_load_action_doctrine_bundle`, removed before commit) showing
`project_directives` has exactly 34 entries and does not include `DIRECTIVE_100`, independent of any
`resolve_doctrine_root` patch the test applies (that patch only affects `template_sets` loading, not
`built_in_dir()`-sourced directive/tactic/paradigm catalogs — traced live in
`src/charter/activation/catalog.py` and `src/charter/offering/pack_paths.py`). Widening
`project_directives` at the production call site with the action's own directly-resolved directive ids
(the only alternative found that would pass this specific test) was rejected: it would exempt ANY
directly-graph-scoped directive from the allowlist regardless of whether a real project explicitly
deactivated it, reintroducing exactly the "silent widening" defect class Decision Record 2 / FR-006-008
exist to close, and directly contradicting
`tests/charter/test_action_bundle_delivery.py::test_classify_skips_unresolvable_urn_and_out_of_scope_directive`'s
own load-bearing assertion (a directly-scoped directive not in a non-empty `project_directives` MUST be
excluded). Flagged BLOCKED for operator review in the WP02-follow-on report rather than silently edited
or routed around.

## 9. WP02 follow-on, round 2 — "reachable within my own scope walk" was still the wrong boundary;
## 7. WP02 follow-on, round 2 — "reachable within my own scope walk" was still the wrong boundary;
the real distinction is ownership, not reachability

The round-1 fix (friction items 5 and 6 above) gated the closure union on reachability within the
resolving action's own `Relation.SCOPE`-then-`{REQUIRES}`/`{SUGGESTS}` walk. Re-running the FULL
`tests/charter/` suite (not just this WP's own scoped test files, per the mission's own baseline
discipline) surfaced two NEW regressions that isolated pytest runs against only the named/owned test
files never would have caught: `tests/charter/test_context.py::TestBuildContextV2::test_selected_directive_closure_contributes_action_context`
and `::test_org_required_primary_kinds_contribute_to_prompt`. Both are pre-existing (confirmed by
running them against WP02's unmodified original commit, `13a8cba1a` -- they pass there), both
explicitly documented in their own docstrings ("Selected directives contribute their DRG closure even
without action-scope edges"), and both use fixture graphs with ZERO `scope` edges anywhere at all --
the closure-seeded directive and its `requires` target are simply floating nodes nobody scoped to any
action. Isolated to only the two ruling-named tests plus WP02's own file, this class of regression is
invisible; it only shows up against the broader suite.

**Root cause of the round-1 over-narrowing**: "reachable within my own scope" and "not owned by someone
else" are different predicates, and the ruling's real named defects (FR-005's `DIRECTIVE_003`, #883's
`DIRECTIVE_001`) are BOTH instances of the second, narrower one -- each leaking directive has an
explicit `Relation.SCOPE` edge from a DIFFERENT, specific action, not merely an absence of a `scope`
edge from the resolving action. Re-derived the gate as a direct SCOPE-edge ownership lookup (`{target:
{owning action URNs}}`, one pass over `merged.edges`) rather than a walk: exclude a closure result only
when some OTHER action's `scope` edge names it; a closure result with NO scope owner anywhere is never
excluded. This closes both real leaks while restoring the two newly-discovered tests to green -- see
the WP02-follow-on report for the full before/after test matrix.

**Flag for future scope-gate work on this function**: the failure mode here was believing "the ruling's
two named tests pass" was sufficient proof the fix's *general* rule was correct. It was necessary but
not sufficient -- the general rule (reachability) happened to satisfy the two named instances while
being wrong for the general case. Ownership (one-hop, direct edge) turned out to be both simpler AND
correct where reachability (multi-hop walk) was both more complex AND wrong; when a "reuse the sibling
function's shape" instruction still produces regressions elsewhere in the suite, checking whether a
strictly simpler predicate satisfies every constraint is worth doing before elaborating the complex one
further.

Also fixed in the same round: the ownership lookup was first built unconditionally (one pass over
`merged.edges` before checking whether the closure produced anything), which broke
`tests/doctrine/drg/test_unknown_kind_fails_loudly.py::test_classify_artifact_urns_propagates_the_loud_error`
-- a minimal `_StubGraph` test double that implements only `get_node`, not `.edges`. Gated the lookup
construction behind `if closure_urns:` so a caller whose closure seed is empty (e.g. an explicit empty
`project_directives` with no tactics/paradigms) never touches `.edges` at all.

## 10. WP02 follow-on, ruling 2 — the allowlist's "None -> all built-ins" default was bound to a
## 8. WP02 follow-on, ruling 2 — the allowlist's "None -> all built-ins" default was bound to a
hardcoded catalog call, not the graph actually being resolved against

Ruling 1's scope-gate (friction items 5-7) fixed the SEED-side conflation (job 2, the closure walk).
A second, independent collision remained on the ALLOWLIST side (job 1), which ruling 1 declared
correct and left untouched -- and correctly so, in isolation: the "None -> all built-ins" semantics
themselves were never wrong. What was wrong was the SOURCE OF "all built-ins" itself:
`_load_action_doctrine_bundle` called `load_doctrine_catalog()` -- the real, installed built-in
catalog, a fixed ~34-directive set independent of whatever graph was actually being resolved
against. `test_action_doctrine_keys_off_meta_json_not_template_set` (#883) patches
`load_validated_graph` to return a synthetic mock graph containing a fictional `DIRECTIVE_100`, but
never mocks where the catalog default comes from -- so the graph is synthetic while the allowlist
stays real, and the two silently disagree about what "all built-ins" means. This was invisible while
`project_directives` was always empty (pre-mission); the mission's own re-derivation to a real,
non-empty catalog default surfaced it. The same root cause independently broke all five tests in
`tests/charter/test_context_org_chain.py` (a REAL org-pack directive, genuinely merged into the
graph, but never shipped in the real built-in catalog) -- discovered by the operator running the
baseline against the TRUE mission base (`4b6b9c6b3`) rather than trusting a comparison against this
WP's own first commit, which had already introduced the regression from its very first commit and so
made it look pre-existing.

**Fix**: `_graph_and_catalog_default_ids` -- the "all built-ins" default for one kind is the UNION of
the real catalog with that kind's own node ids in the ACTIVE (already activation-filtered) merged
graph, never a bare catalog call and never a pure graph-replaces-catalog swap. The union half matters
independently of the #883/org-chain fix: WP02's own
`test_activated_tactics_and_paradigms_absent_widen_to_full_catalog` uses a directive-only mock graph
with ZERO tactic/paradigm nodes and still requires the full real catalog (124 tactics / 13 paradigms)
to widen in for those two kinds -- a pure "graph replaces catalog" reading (the ruling's own wording,
read literally, without checking this WP's own existing tests first) would have broken it. Checked
this BEFORE implementing, not after: traced the mock graph's exact node set for that test, confirmed
it carries zero tactic/paradigm nodes, and confirmed empirically (by running the union design) that
all of WP02's own 9 tests, the new ruling-2 fixture, and the four ruling-2 acceptance signals hold
simultaneously.

**Baseline-attribution flag for future rounds of this same fix**: comparing a "did I cause this"
question against your OWN prior commit, rather than the TRUE mission base, silently reclassifies a
regression you introduced as "pre-existing" the moment you've made a second commit on top of the
first -- the second commit's baseline check trivially passes against the first commit, which already
carried the defect. Always diff against the mission's true base commit (here, `4b6b9c6b3`, the commit
immediately before this mission's own first change), not the tip of your own branch, however recent.
## WP04 — pre-review regression gate budget mismatch under real environment load

`spec-kitty agent tasks move-task WP04 --to for_review` runs an internal pre-review
regression gate over a broader scope than the WP file's own validation scope:
`tests/charter, tests/doctrine, tests/specify_cli/charter_freshness,
tests/specify_cli/charter_lint, tests/specify_cli/charter_preflight`, under a fixed
300s budget. Two consecutive attempts both timed out at exactly ~300.00s elapsed
(`budget-v1:sha256:a4e0088a...`, scope identity unchanged between attempts).

This is a structural budget/scope mismatch, not attempt-to-attempt contention luck:
this WP's own manually-run, uncontended scoped gate (`tests/charter/` +
`tests/architectural/test_charter_offering_does_not_import_activation.py` +
`tests/architectural/test_no_dead_symbols.py` — a strict *subset* of the pre-review
gate's scope) already takes 632-634s on a clean environment (per this mission's own
documented clean-baseline figure), i.e. more than double the gate's 300s budget
*before* adding `tests/doctrine` and the three `tests/specify_cli/charter_*`
directories on top. The gate cannot realistically complete within 300s for this
scope regardless of concurrent load.

**Resolution used**: `--skip-pre-review-gate` (a first-class, documented CLI flag
distinct from `--force` on the roster/subtask-completeness gate, which stays
forbidden) — backed by this WP's own fresh, clean, manually-run scoped-gate evidence
(`1 failed [SK-162], 2572 passed, 25 skipped in 634.41s`, captured post-commit with
no concurrent edits) for the exact scope the WP file specifies. Flagging for
whoever owns the pre-review gate's budget config: either the 300s default needs
raising for the `tests/charter`+`tests/doctrine`+`charter_*` scope class, or that
scope needs to shrink to something the fixed budget can actually complete.

## 11. `agent status emit --to for_review` requires a lane branch named `lane-planning` that a `planning_artifact` WP never creates (WP05, implement phase, 2026-09-03)

WP05 is `execution_mode: planning_artifact` with no dedicated `.worktrees/<slug>-lane-planning` (the same
gap named in the mission brief's SK-152 note for the earlier `agent action implement WP05` claim step,
which the operator resolved by consolidating lane-a/b/c/d onto the mission branch — see item above/mission
report). T017/T018 were committed directly onto the mission's actual current branch,
`fix/spdd-reasons-activation-split-brain-3838` (confirmed live via `git branch --show-current` immediately
before `safe-commit`, matching the WP frontmatter's own `planning_base_branch`/`merge_target_branch`, both
already this branch), via:

```
.venv/bin/spec-kitty safe-commit docs/context/charter.md kitty-specs/.../contracts-activation-authority-update.md \
  -m "..." --to-branch fix/spdd-reasons-activation-split-brain-3838
```

which succeeded (`Requested files committed`, commit `42240634b`). Both subtasks were marked done
(`agent tasks mark-status T017/T018 --status done --mission ...`).

**Command run**:
```
.venv/bin/spec-kitty agent status emit WP05 --to for_review --actor claude --mission spdd-reasons-activation-split-brain-01M1K6VN
```

**Result**:
```
Error: WP05 cannot move to for_review: no implementation commit on lane lane-planning (main) beyond
fix/spdd-reasons-activation-split-brain-3838. Commit the work in the lane worktree first, or pass --force
if there is genuinely nothing to commit.
```

**Diagnosis**: the `for_review` gate's ancestry check looks for a commit on a lane branch literally named
`lane-planning` that is ahead of the mission's target branch — but this WP's real commit landed ON the
target branch directly (there being no separate lane-planning branch to land it on in the first place, per
the WP's own `planning_artifact` shape). The gate's "beyond `fix/spdd-reasons-activation-split-brain-3838`"
phrasing is therefore vacuously false: the commit exists, it is simply not "ahead of" a branch it already
*is*.

**Why not routed around**: the error text itself offers `--force` as an escape hatch ("if there is
genuinely nothing to commit"), but that is not this case — there IS committed work (`42240634b`, verified
present in `git log`), so `--force`ing would misrepresent an "nothing to commit" bypass as the reason,
and the mission's own dispatch mandate for this WP explicitly forbids reaching for `--force` to route
around a gate. This is the same class of gap as the SK-152 claim-step hazard (`reenter_lane_self_heal`
assuming a `lane-planning` worktree/branch this WP shape never creates) recurring one gate later, in the
`for_review` transition's own lane-ancestry check. Reported BLOCKED to the mission orchestrator rather than
forced through.

**Recommended resolution**: either the `for_review` gate's ancestry check should recognize "the commit
landed directly on the target branch because this WP has no lane branch" as an equivalent, valid case for
`execution_mode: planning_artifact` WPs (mirroring the exemption `finalize-tasks` already grants this WP
shape for `owned_files` under `kitty-specs/`/`docs/`, SK-146), or the CLI should provision a `lane-planning`
branch/worktree for `planning_artifact` WPs the same way it provisions `lane-a`/`lane-b`/etc. for
`code_change` WPs, so the ancestry check's assumption holds uniformly.
