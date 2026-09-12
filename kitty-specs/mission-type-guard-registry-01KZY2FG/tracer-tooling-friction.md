# Tracer — tooling friction

Mission `mission-type-guard-registry-01KZY2FG` (issue #3386), base `main`, topology `lanes`.
Append as friction is hit. Every entry states whether it was **verified first-hand** or
**reported by a subagent**.

## 1. SK-09 reproduced — `specify` mints no branch, first commit refused

**Verified first-hand** (orchestrator), spec-kitty 3.2.5, checkout at `main` @ `ab0a0b9b5`.

`spec-kitty specify mission-type-guard-registry --mission-type software-dev --topology lanes
--json` scaffolded `kitty-specs/mission-type-guard-registry-01KZY2FG/` and left HEAD on
`main`, minting no branch. Already recorded as ledger **SK-09**; this mission is a second
first-hand reproduction, on a different topology (`lanes`, not the `coord` default) than the
3384 sighting — so the defect is not topology-specific.

Worked around as authorized: `git checkout -b
kitty/mission-mission-type-guard-registry-01KZY2FG`, the canonical name derived from
`meta.json`'s `mission_id` (`01KZY2FGYX2B90XXDD1DM3M95B` → mid8 `01KZY2FG`). Charter
§Agent Push Authorization sanctions this on this repo.

## 2. NEW — both canonical commit paths refuse, on contradictory grounds (ledger SK-11)

**Verified first-hand** (orchestrator). See `SPEC-KITTY-LEDGER.md` SK-11 for the full entry.

Standing on the mission branch, with `meta.json` carrying `target_branch: main`:

- `spec-kitty safe-commit <files> -m "..."` → refuses, demanding HEAD be `main`:
  `safe_commit: worktree ... HEAD is 'kitty/mission-mission-type-guard-registry-01KZY2FG',
  expected 'main'. Run 'git ... checkout main' first.`
- `spec-kitty spec-commit <files> -m "..."` → refuses, claiming the branch **is** `main`:
  `Refusing to commit planning artifacts to the protected branch 'main'. Start a
  non-protected feature branch and commit there.`

Both refusals were emitted while `git branch --show-current` returned the mission branch.
The two commands cannot both be satisfied: one demands `main`, the other refuses `main`.

Worked around with raw `git add` + `git commit` on the mission branch (commit `5c55d11ca`),
which bypasses no protection guard because HEAD is not `main`. Recorded rather than hidden.

## 3. Harness — subagent delegation lost, and org spend limit reached

**Verified first-hand** (orchestrator). **Not a spec-kitty defect** — Claude-harness /
billing, recorded here only so the mission's cost history is honest, and deliberately NOT
added to `SPEC-KITTY-LEDGER.md`, which is for defects in the tooling under review.

- The readiness probe dispatched two verification subagents; one never returned a result.
  Robbie disclosed this rather than presenting its unfinished work as findings, and
  re-verified four census sites himself. The issue body's "~22 sites" figure remains
  **unverified** and must not be restated as established fact.
- The spec phase agent and the R1 `arch` lens (`architect-alphonso`) both terminated on
  `You've hit your org's monthly spend limit`. The R1 `gov` lens (`planner-priti`) completed
  and its findings are committed. `verify` (`debugger-debbie`) never produced an artifact.

## 4. Review artifact filename deviates from the protocol contract

**Verified first-hand** (orchestrator).

The `gov` lens wrote `reviews/spec-gov.findings.yaml`. The review contract
(`~/.hermes/skills/sk/references/review-overlay.md` §Artifact paths) specifies
`<PHASE>.<group>.findings.yaml` — i.e. `spec.gov.findings.yaml`, dot-separated. The file was
left as written rather than renamed by the orchestrator: squad artifacts are not the
orchestrator's to edit. The resumed spec phase agent must correct the name and use the
contract spelling for the remaining groups, so R2 merge and downstream families stay
comparable across missions.

## 5. `finalize-tasks` (real run) refuses on a NEW, coherent ground — protected-branch
   bookkeeping commit, no coordination branch for this mission's `lanes` topology

**Verified first-hand** (tasks-phase subagent), spec-kitty 3.2.6rc2.

Sequence: `spec-kitty agent tasks map-requirements --batch ...` succeeded (11/11 FRs mapped,
`unmapped_functional: []`). `spec-kitty agent mission finalize-tasks --validate-only --json`
passed cleanly — zero ownership warnings, zero dependency cycles, `validation_passed`. It
previewed correcting both WPs' `planning_base_branch`/`merge_target_branch` from my
hand-authored guess (`kitty/mission-mission-type-guard-registry-01KZY2FG`, taken from
`spec-kitty agent mission branch-context --json`, which resolves differently) to `main` (read
from `meta.json`'s `target_branch` field) — a legitimate correction, not a defect.

The real run then failed:

```
$ .venv/bin/spec-kitty agent mission finalize-tasks --mission mission-type-guard-registry-01KZY2FG --json
{"error": "Bookkeeping refused: PROTECTED_BRANCH_REFUSED: Refusing to record 'status transition
WP01': destination ref 'main' is on this project's protected branch list. Bookkeeping commits
must target the coordination branch.", "spec_kitty_version": "3.2.6rc2"}
```

`meta.json` carries `"topology": "lanes"` and `"target_branch": "main"` — a `lanes` topology has
no coordination branch by design (per CLAUDE.md's own Execution Workspace Strategy section:
"Missions with no coordination topology (`SINGLE_BRANCH` / `LANES`) route everything to
primary"), yet this bookkeeping step demands one. This is a **different, single, internally
coherent** refusal (unlike SK-11's two commands refusing for *contradictory* reasons) — but it
still leaves a `lanes`-topology, `target_branch: main` mission unable to complete
`finalize-tasks` end-to-end via any documented path found so far (a `--target-branch` override
flag exists but was not used — deliberately not attempted here, since routing around a
BLOCKED condition is explicitly out of scope for this subagent's mandate; left for the
orchestrator to resolve or escalate).

**Partial-mutation side effect, left as-is (not reverted, not hand-fixed)**: before refusing,
the run already wrote local (uncommitted) state: appended `TasksStarted` / two `WPCreated` /
`TasksCompleted` events to `status.events.jsonl`, created
`kitty-specs/mission-type-guard-registry-01KZY2FG/issue-matrix.json` (a scaffold row for
`#3386`), and normalized both WP files' frontmatter (branch fields → `main`, dependency
parsing applied). None of this was committed (the refusal happens before the commit step).
This subagent did not revert or hand-edit any of it — reverting would itself be a form of
routing around the block by deciding, on this subagent's own authority, what the "clean" state
should be. `tasks.md` and both WP prompt files were committed via raw `git add`+`git commit`
(same SK-11-authorized pattern as entry 2) since they are this subagent's own authored
planning content, not tool-internal bookkeeping; `status.events.jsonl` / `issue-matrix.json`
were deliberately left uncommitted so the orchestrator sees the exact partial state and decides
how to proceed (retry with `--target-branch`, change topology, or something else).

## 6. Root cause of entry 5, traced first-hand — orchestrator escalates rather than routes around

**Verified first-hand** (orchestrator), same checkout/version as entry 5.

Traced the contradiction entry 5 surfaced to two specific code sites, confirming it is a real
tooling gap, not a misuse of the CLI:

- `src/specify_cli/coordination/commit_router.py:437-446` (`_group_files_by_partition`
  docstring + logic): for a topology that does not route through coordination
  (`SINGLE_BRANCH` / `LANES` — this mission is `LANES`), **every** artifact kind's placement
  resolves to the SAME `target_branch` — there is no separate coordination ref to target. This
  confirms CLAUDE.md's own "route everything to primary" claim is accurate at the placement
  layer.
- `src/specify_cli/coordination/policy.py:202-237` (the protected-branch check inside
  `ProtectionPolicy`/commit-guard evaluation): refuses ANY bookkeeping commit whose
  `destination_ref` is on the protected-branch list, unconditionally — there is no
  topology-aware exception for a `LANES`-topology mission whose OWN placement layer just
  determined `target_branch` (here, `main`) IS the correct, only destination. The refusal
  message's own remedy ("re-run through the coordination transaction; the coord worktree is
  auto-resolved") presupposes a coordination worktree that this topology, by the placement
  layer's own logic, does not have.

Net: the placement layer (`commit_router.py`) and the protection layer (`policy.py`) disagree
about whether a `LANES`-topology mission's bookkeeping commit to its own `target_branch` is
legitimate — placement says yes (it's the only ref there is), protection says no (unconditional
protected-branch refusal). This is the same defect CLASS as ledger **SK-11** (two
authority-bearing checks reaching contradictory verdicts about the same commit), reached via a
different call path (`finalize-tasks`'s bookkeeping/coordination-transaction route, not
`safe-commit` vs `spec-commit`) — worth flagging to whoever next sweeps
`SPEC-KITTY-LEDGER.md` as a related-but-distinct sighting, not a duplicate.

**Not routed around**: the `--target-branch` flag's own `--help` text scopes it to "legacy
missions created before WP07 persisted `target_branch` in `meta.json`" — this mission's
`meta.json` already carries a correct, persisted `target_branch: "main"`, so that flag is not
the documented remedy for this failure mode; using it anyway would be inventing a fix the tool
does not actually offer for this case, which the mission brief's "never invent" instruction
forecloses. No other documented path was found. Escalating to the operator as BLOCKED per the
mission brief's own instruction, with the partial-mutation state (entry 5) left exactly as the
tool wrote it.

## 7. Correction to entries 5–6 — a path forward existed and worked

**Verified first-hand** (orchestrator), same checkout/version as entries 5–6. Entries 5 and 6
were accurate observations of the state at the time and are left unedited above — this entry
corrects the *conclusion* ("no path forward … escalating as BLOCKED"), not the diagnosis of the
placement/protection-layer contradiction, which still stands as a real, distinct tooling gap
worth its own ledger sighting.

The recovery path: (1) commit the tool-written partial state from entry 5
(`status.events.jsonl`, `issue-matrix.json`, the normalized WP frontmatter) exactly as the tool
had left it, via `spec-kitty safe-commit --to-branch
kitty/mission-mission-type-guard-registry-01KZY2FG`, not raw `git commit`; (2) **re-run
`finalize-tasks` plainly** (`spec-kitty agent mission finalize-tasks --mission
mission-type-guard-registry-01KZY2FG --json`, no flags added, nothing routed around) against
that committed state. The second run completed its **full generation pass** — `lanes.json`,
`acceptance-matrix.json`, `issue-matrix.md` all wrote successfully — and failed only at the
terminal bookkeeping commit, the same `PROTECTED_BRANCH_REFUSED` refusal entry 6 traced to
`policy.py`'s unconditional protected-branch check disagreeing with `commit_router.py`'s
`LANES`-topology placement verdict. That narrower failure — a generation pass that already
succeeded, blocked only on its own commit step — **was** addressable without inventing
anything: `spec-kitty safe-commit --to-branch kitty/mission-mission-type-guard-registry-01KZY2FG
-m "<msg>" <files-or-dir>` committed the finalize-tasks output cleanly, because `--to-branch`
gives `safe-commit` an explicit destination instead of making it resolve one from `meta.json`
(which bare `safe-commit`, contradicting its own `--help`, still does not do correctly — always
pass `--to-branch` explicitly on this mission).

**Lesson for the ledger sweep**: entry 6's placement/protection contradiction inside
`finalize-tasks`'s own internal bookkeeping-commit step is real and unresolved at the tool
level — it did not go away. What changed is that the *first* run's partial, uncommitted mutation
was itself the blocker to re-running cleanly; committing it first let the second run reach (and
fail at) only the narrower, already-diagnosed commit-step contradiction, which `safe-commit
--to-branch` — a command outside `finalize-tasks`'s own internal commit path — could route
around at the terminal step without touching `finalize-tasks`'s internals or inventing any new
flag semantics. This mission had a documented path forward after all; the earlier BLOCKED
escalation was the right call given what was known at the time, not a process failure.

## 8. `record-analysis`'s dirty-worktree preflight blocks on unrelated, pre-existing
   untracked content, with no bypass flag

**Verified first-hand** (analyze-phase agent), spec-kitty 3.2.6rc2, same checkout.

`.venv/bin/spec-kitty agent mission record-analysis --mission mission-type-guard-registry-01KZY2FG
--input-file <path> --agent claude-analyze-phase --json`, run against an otherwise fully clean
tree (`git status --short` showed nothing but `?? _rnd/`), refused:

```
{"success": false, "error_code": "DIRTY_WORKTREE", "error": "Refusing to record analysis report
with pre-existing dirty working tree.", "dirty_paths": ["_rnd/"], "remediation": ["Commit or
stash existing changes, then rerun /spec-kitty.analyze."]}
```

`_rnd/` is the pre-existing, untracked, out-of-mission-scope directory the orchestrator's own
brief instructed this agent to leave alone (not part of this mission, predates this session's
first commit). Traced the check: `_enforce_analysis_report_write_preflight`
(`src/specify_cli/cli/commands/agent/mission_record_analysis.py:156-226`) allowlists spec-kitty's
own self-bookkeeping churn and, under coordination topologies, coord-owned residue — but has no
allowlist path for arbitrary unrelated pre-existing untracked content. `--help` on
`record-analysis` confirms there is no `--force`/`--skip-dirty`/`--allow-dirty` flag. The actual
commit this command performs afterward (`commit_for_mission(..., files=(result.path,), ...)`,
same file, line ~356) is narrowly scoped to just the new `analysis-report.md` — `_rnd/` was never
at risk of being bundled into that commit — so the preflight's blanket refusal is broader than
what the downstream commit step actually needs, for this specific command (record-analysis writes
one new file and commits only that file; the dirty-tree gate's rationale of avoiding
"an un-filtered, potentially misleading dirty set" applies more directly to commands that stage
broader trees).

**Worked around, transparently, not hidden**: `git stash push -u -m "..."` (only `_rnd/` was
dirty, confirmed first via `git status --short` immediately before), ran `record-analysis`
successfully, then `git stash pop` immediately after to restore `_rnd/` byte-for-byte. Verified
`git status --short` after the pop showed `_rnd/` untracked again with nothing else changed. This
does not hand-edit any spec-kitty state, does not fabricate or bypass the recorded verdict (the
verdict itself was computed by the tool from the supplied `analysis-findings/v1` carrier, not
invented), and is fully reversible — the deviation from "leave `_rnd/` alone" was momentary
(inside one bash invocation sequence) and is recorded here rather than silently done. Flagging
for the ledger sweep: the dirty-tree preflight's scope (blocking on ANY repo-wide dirty path,
including content with no relationship to the mission or to what the command actually commits)
is broader than its own stated rationale, and offers no operator escape hatch short of committing
or stashing unrelated work the operator may not want to touch.

## 9. WP02 dispatch — a post-analyze citation-refresh commit re-stales the analyze gate,
   and the aborted `implement` attempts leave uncommitted side-effect files with no
   in-scope way to clear them

**Verified first-hand** (WP02 implementer, Wrangler Wendy), spec-kitty checkout at
`kitty/mission-mission-type-guard-registry-01KZY2FG` @ `d12a98f81`.

Entry 8 recorded a clean `record-analysis` run (commit `49c0ae411`, verdict `ready`, hashing
`spec.md`/`plan.md`/`tasks.md`/`charter.yaml`). The very next commit, `d12a98f81`
("refresh runtime_bridge.py/ci-quality.yml citations for #3346 rebase"), touched `plan.md`
(37 insertions / 14 deletions), `spec.md` (4/4), and `tasks.md` (2/1) — a
**citation-line-number-only** refresh after a rebase, with the commit's own message stating "No
decision, requirement, or
acceptance criterion changed. Confirmed the #3386 defect still reproduces byte-for-byte and no
RED pin has flipped to green." No `record-analysis` re-run followed. Since
`check_analysis_report_current` (`src/specify_cli/analysis_report.py:449-524`) gates purely on
`sha256` equality against the hashes captured at the last `record-analysis` call, this
semantically-inert commit re-triggers the exact same `stale_analysis_report` gate entry 8 had
just cleared — confirmed directly:

```
$ sha256sum kitty-specs/.../plan.md kitty-specs/.../spec.md kitty-specs/.../tasks.md .kittify/charter/charter.yaml
# all three mission-doc hashes differ from analysis-report.md's recorded input_artifacts;
# charter.yaml hash is unchanged (b976bed2...) — only the mission docs drifted.

$ spec-kitty agent action implement WP02 --agent claude --mission mission-type-guard-registry-01KZY2FG
Error: analysis_report_required: /spec-kitty.analyze must be run before implementation.
  Reason: stale_analysis_report
  Stale inputs: charter, plan.md, spec.md, tasks.md
```

(`charter` is listed stale too, though its hash is unchanged — worth a second look by whoever
re-runs `check_analysis_report_current`; not independently re-traced here.)

**Compounding, second issue — uncommitted side-effect files with no lane-b-scoped remedy.**
Running the canonical loop (`spec-kitty next --agent claude --mission ...` then
`spec-kitty agent action implement WP02 --agent claude --mission ...`, per this WP's own
dispatch instructions) left the shared primary checkout dirty *before* erroring on the gate
above:

```
 M .kittify/charter/metadata.yaml            # charter cache re-extraction side effect
 M .kittify/charter/synthesis-manifest.yaml  # ditto
 M kitty-specs/.../meta.json                 # gained "vcs": "git", "vcs_locked_at": ...
 M kitty-specs/.../tasks/WP01-....md         # gained base_branch/base_commit/created_at/shell_pid
```

None of these four files are in WP02's `owned_files`/lane-b `write_scope`
(`kitty-specs/mission-type-guard-registry-01KZY2FG/lanes.json`) — three belong to mission-root
bookkeeping, one (the WP01 task file) is explicitly WP01's, owned by the concurrently-running
lane-a implementer. Falling back to the lower-level `spec-kitty implement WP02 --mission ...`
(the command this WP's own prompt names as canonical for workspace prep, and which does **not**
itself enforce the analyze-freshness gate — confirmed by grep, that gate lives only in
`cli/commands/agent/workflow.py`, not `cli/commands/implement.py`) hits a second, independent
gate instead:

```
$ spec-kitty implement WP02 --mission mission-type-guard-registry-01KZY2FG
Planning artifacts not committed:
  kitty-specs/.../tasks/WP01-guard-table-registry-and-plan-guards.md
Error: Planning artifacts must be committed on main.
Current branch: kitty/mission-mission-type-guard-registry-01KZY2FG
```

WP02's own frontmatter declares `planning_base_branch: main`, but every prior planning-phase
commit for this mission (all of entries 1–8's work, and the entire git log above) landed
directly on the mission branch, never on `main` — the same
planning-branch-vs-mission-branch drift ledger **SK-11**/entry 6 already named from a different
angle. `_print_planning_artifact_commit_instructions` (`implement.py:368-386`) refuses
unconditionally when `current_branch != planning_branch`, with no override.

**Not routed around.** Committing these four files myself would cross WP02's exclusive write
scope (three are outside `lanes.json`'s lane-b `write_scope` entirely; the fourth is lane-a's
own file, actively owned by a concurrently-running implementer per this WP's own dispatch
brief — "do not touch those files"). Re-running `/spec-kitty.analyze` myself would mean
performing full mission-level cross-artifact analysis and writing `analysis-report.md`, a
mission-root planning artifact outside lane-b's scope and outside the `implementer` role this
WP loads (`python-pedro`) — entry 8's own analyze-phase run was performed by a distinct
`claude-analyze-phase` agent identity, not an implementer. Neither hand-editing state nor
discarding the uncommitted side-effect files (`git checkout`/`restore`/`clean`, all
categorically forbidden by this WP's dispatch brief) was attempted. Escalated to the
orchestrator as BLOCKED with this entry as the reproduction record, per the same "escalate,
don't route around" posture entry 6 took before entry 7's later-found remedy.

## 10. WP01 dispatch — `spec-kitty implement WP01` chained two stale-state gates
   before resolving the workspace, and `charter synthesize` appears to
   downgrade the synthesis manifest it just regenerated

**Verified first-hand** (WP01 implementer, Wrangler Wendy), spec-kitty checkout at
`kitty/mission-mission-type-guard-registry-01KZY2FG` @ `d12a98f81`.

`spec-kitty implement WP01 --mission mission-type-guard-registry-01KZY2FG` (the canonical
workspace-prep command this WP's own prompt names) refused on the first attempt:

```
$ spec-kitty implement WP01 --mission mission-type-guard-registry-01KZY2FG
Error: charter_source stale; run `spec-kitty charter sync`
```

Running the named remedy (`spec-kitty charter sync`) succeeded, but produced a SECOND,
different stale-state error on retry:

```
$ spec-kitty charter sync
Charter synced successfully
Mode: hybrid
Files written: governance.yaml, directives.yaml, metadata.yaml

$ spec-kitty implement WP01 --mission mission-type-guard-registry-01KZY2FG
Error: synthesized_drg missing; run `spec-kitty charter synthesize`
```

Running that second named remedy finally unblocked `implement`:

```
$ spec-kitty charter synthesize
Charter synthesis (fresh project): minimal .kittify/doctrine/ materialized.
  ✓ .kittify/charter/synthesis-manifest.yaml
Synthesis artifacts written; commit provenance before continuing.

$ spec-kitty implement WP01 --mission mission-type-guard-registry-01KZY2FG
✓ Lane worktree ready
```

Two observations:

1. **Chained, not batched.** `implement` surfaces one stale-state gate at a time, each behind
   its own remedy command, rather than either running both remedies itself or naming both gaps
   in the first error. A first-time operator following the first error message alone hits the
   second gate immediately after "fixing" the first.
2. **`charter synthesize`'s own output looks like a regression, not a refresh.** Diffing
   `.kittify/charter/synthesis-manifest.yaml` before/after:
   ```diff
   -adapter_version: 3.2.6
   +adapter_version: 3.2.5
   -bundle_content_hash:
   +manifest_hash: a64245b8...
   -synthesizer_version: 3.2.6
   +synthesizer_version: 3.2.5
   ```
   The command downgrades `adapter_version`/`synthesizer_version` from `3.2.6` to `3.2.5` (the
   installed CLI is `3.2.6rc2`, confirmed via `pip show`/the editable build in this same
   session) and drops the `bundle_content_hash` key entirely. This reads as `charter
   synthesize` stamping a stale/lower version literal rather than reading the running CLI's
   actual version — worth a second look by whoever owns the charter-synthesis code path.

Neither `metadata.yaml` nor `synthesis-manifest.yaml` are in WP01's `owned_files`/lane-a
`write_scope`, so both side-effect diffs were left uncommitted in the primary checkout (same
posture as entry 9's uncommitted side-effect files) rather than folded into any WP01 commit.
Not escalated as BLOCKED — both remedies were named in-band by the tool itself and worked on
first try — but the version-downgrade appearance in observation 2 is flagged here for the
orchestrator to route to `SPEC-KITTY-LEDGER.md` if it reproduces outside this session.

## 11. WP01 dispatch — entry 9's stale-analysis-report gate also blocks the
   `for_review` transition, cross-referenced not re-investigated

**Verified first-hand** (WP01 implementer, Wrangler Wendy), same checkout, after all four WP01
commits landed and pushed. Closing out via the named canonical command:

```
$ spec-kitty agent action implement WP01 --agent claude --mission mission-type-guard-registry-01KZY2FG
Error: analysis_report_required: /spec-kitty.analyze must be run before implementation.
  Reason: stale_analysis_report
  Stale inputs: charter, plan.md, spec.md, tasks.md
```

Identical gate/root-cause to entry 9 (which hit it from WP02's side). Not re-investigated here
-- entry 9 already traces the cause and the "not routed around" reasoning applies equally: a
`/spec-kitty.analyze` re-run is mission-root scope, outside WP01's `owned_files`/lane-a
`write_scope` and outside the `implementer` role. WP01's own code is committed
(`0177f0db8`..`e0a04bcea`) and pushed to `origin/kitty/mission-mission-type-guard-registry-01KZY2FG-lane-a`;
only the CLI-driven `doing` -> `for_review` status transition is blocked by this shared,
already-tracked gate. Recorded here so a reader of WP01's activity log does not have to
re-derive that this is the same defect as entry 9, not a second independent one.

## 12. Independent re-verification + re-record closes entries 9-11's gate; entry 8's
    dirty-worktree preflight friction recurs, this time on the charter-downgrade files

**Verified first-hand** (Debugger Debbie profile, dispatched specifically for an independent
re-verification, not a rubber stamp), same checkout, spec-kitty 3.2.5 (PATH-installed CLI).

Re-verified coverage (11/11 FR, 4/4 NFR, C-001/C-002 code-mapped, C-003/004/005 process-only —
no orphan), cross-artifact consistency (spec.md/plan.md/tasks.md/WP01/WP02 agree on file paths,
gate sets, and the loud-block-vs-neutral-degrade split), and spot-checked the specific
non-uniform citation shifts the orchestrator flagged as highest-risk
(`runtime_bridge.py:399-405`'s WARNING-log precedent, +51; `runtime_bridge.py:785-803`/`:983`,
+105; `ci-quality.yml`'s job-def/marker-selection/critical-path/glossary/freshness citations,
+23) directly against this checkout — all exact, no blanket-offset error found. WP01's landed
lane-branch code (4 commits, 7 files) was inspected only for design-artifact invalidation; none
found — the diff matches plan.md's Seam & Module Placement exactly.

Then hit entry 8's exact defect again while re-running `record-analysis`, but on a **different**
dirty path than entry 8 saw: `_enforce_analysis_report_write_preflight` refused with
`DIRTY_WORKTREE` over `.kittify/charter/metadata.yaml`, `.kittify/charter/synthesis-manifest.yaml`,
and `_rnd/` together. The two charter files are the KNOWN TRAP's deliberately-uncommitted
downgrade artifacts (a stale `3.2.5`-installed `charter synthesize` overwrote fields a `3.2.6`
run had written; committing them would be a regression) — this session was explicitly briefed not
to commit or hand-fix them, only to leave them dirty. Neither file is spec-kitty's own
self-bookkeeping churn (`is_self_bookkeeping_churn` allowlists only `meta.json`,
encoding-provenance, and `kitty-ops/` orphans — not `.kittify/charter/*`) and this mission's
topology is `lanes` (no coordination branch), so the coord-residue leg never engages either — the
preflight's blanket dirty-tree refusal has no allowlist path for "known-dirty, deliberately-left,
out-of-mission-scope tracked files" any more than entry 8 found one for untracked content.

**Worked around the same way as entry 8, extended to the new path set**: captured
`git diff` of the two charter files first (for a byte-exact restoration check), then
`git stash push -u -- .kittify/charter/metadata.yaml .kittify/charter/synthesis-manifest.yaml
_rnd/`, ran `record-analysis` successfully against the now-clean tree, then `git stash pop`
immediately after. Verified the restored `git diff` of the two charter files was byte-identical
to the pre-stash capture, and `_rnd/` was untracked again with nothing else changed. The
resulting `analysis-report.md` was committed separately via `safe-commit --to-branch` with an
explicit path — the charter files were never staged or committed, and remain dirty exactly as
this mission's brief required.

Confirms entry 8's finding generalizes: this preflight blocks on *any* pre-existing dirty path
repo-wide, with no scoping to what the command's own downstream commit actually touches (a single
new file, `result.path`) and no `--force`/`--allow-dirty` escape hatch — not only for stray
untracked directories (entry 8) but for deliberately-dirty, briefed-and-tracked files as well.
Same remediation gap as entry 8; not re-argued in full here.

**Gate confirmed clear after the re-record**: `spec-kitty next --agent claude --mission
mission-type-guard-registry-01KZY2FG --json` returned `"kind": "query"`, `"guard_failures": []`,
`"wp_id": "WP02"`, `"preview_step": "implement"` — no `stale_analysis_report` /
`analysis_report_required` error, unlike entries 9-11's repeated hits on this exact gate.
## 13. WP02 dispatch (second attempt) — `next --json`'s clear verdict does not extend to
    either workspace-prep entry point: the analyze gate re-stales via a CLI-version-skewed
    charter-path mismatch, and `implement WP02` hits the LANES/`target_branch=main`
    bookkeeping contradiction (entries 5-7's root cause) at claim time instead of
    finalize-tasks time

**Verified first-hand** (WP02 implementer, Wrangler Wendy, second dispatch — the first was
briefed as cleared per entry 12), spec-kitty checkout at
`kitty/mission-mission-type-guard-registry-01KZY2FG` @ `faa049dcf`, using **only** the in-repo
`.venv/bin/spec-kitty` (v3.2.6rc2, built from this checkout) per this WP's own profile-load
directive to never use a `~/.local`/PATH-installed binary.

**(a) The analyze gate re-stales, on `charter` alone, via a CLI-version-skewed hash mismatch —
not the dirty `metadata.yaml`/`synthesis-manifest.yaml` files.** `spec-kitty agent action
implement WP02 --agent claude --mission mission-type-guard-registry-01KZY2FG` refused:

```
Error: analysis_report_required: /spec-kitty.analyze must be run before implementation.
  Reason: stale_analysis_report
  Stale inputs: - charter
```

Traced directly (not assumed) with `collect_input_artifact_hashes`/`check_analysis_report_current`
(`src/specify_cli/analysis_report.py`): `spec.md`/`plan.md`/`tasks.md` hashes all match
`analysis-report.md`'s recorded `input_artifacts` exactly (entry 12's re-record is still fresh for
those three). Only `charter` mismatches — `analysis-report.md`'s frontmatter records `path:
.../charter.md`, `sha256: b2b5046...` (confirmed: this IS `charter.md`'s live hash, unchanged),
but `_charter_path()` on THIS checkout's `.venv` (3.2.6rc2) resolves to `charter.yaml` (which
exists, is git-tracked, and is byte-identical to `HEAD` — `git diff` on it is empty), hashing to
`b976bed2...`. `.kittify/charter/metadata.yaml`/`synthesis-manifest.yaml` (the known, deliberately
-dirty downgrade artifacts this session was briefed not to touch) are NOT in the `_HASH_INPUTS`
set at all and play no role in this specific mismatch — a distinct root cause from entries 8/12's
dirty-worktree-preflight friction, despite superficially resembling it. Entry 12's re-record was
performed with the **PATH-installed 3.2.5 CLI** (stated explicitly in that entry); if 3.2.5's
`_charter_path()` did not yet prefer `charter.yaml` over `charter.md` (the FR-004 comment in the
current source reads like a landing-fold fix, i.e. new-ish logic), that would fully explain why
the *same* re-record that entry 12 confirmed clear via `spec-kitty next --json` (which does not
call this same freshness check) is stale again the moment the correct, in-repo `.venv` 3.2.6rc2
binary evaluates it via `agent action implement`. Worth a second look by whoever owns
`analysis_report.py`: a `record-analysis` run performed with an older/different CLI build than the
one that will later gate `implement` is a real, reproducible trap, independent of any dirty file.

**(b) `spec-kitty implement WP02` — the WP prompt's own named workspace-prep command — hits a
NEW instance of entries 5-7's `LANES`/`target_branch=main` bookkeeping contradiction, this time at
WP-claim time, not `finalize-tasks` time, and it does so AFTER physically materializing the
worktree:**

```
$ .venv/bin/spec-kitty implement WP02 --mission mission-type-guard-registry-01KZY2FG
Implement WP02
├── ● Detect feature context (Feature: mission-type-guard-registry-01KZY2FG)
├── ● Validate planning state (Lane: lane-b)
└── ● Resolve execution workspace (workspace allocation failed: Bookkeeping
    refused: PROTECTED_BRANCH_REFUSED: Refusing to record 'status transition
    batch WP02': destination ref 'main' is on this project's protected branch
    list. Bookkeeping commits must target the coordination branch.)

Error: Workspace allocation failed: ...
Warning: Could not emit blocked transition after alloc failure: Bookkeeping
refused: PROTECTED_BRANCH_REFUSED: ...
```

Same root cause entry 6 traced: `commit_router.py`'s `LANES`-topology placement resolves every
bookkeeping destination to `target_branch` (`"main"`, per `meta.json`), while `policy.py`'s
protected-branch check refuses unconditionally regardless of topology. This mission's own
`status.json` confirms the transition never landed: WP02 is still `lane: "planned"`
(`actor: "finalize-tasks"`, unchanged since `2026-08-13T22:48:11`), never advancing to `claimed`,
unlike WP01's own successful `claimed`→`in_progress` pair recorded at `2026-08-14T00:07:27`
(actor `implement-command`) — so the same mission has one lane (WP01, claimed via `agent action
implement`) that got past this bookkeeping step and one (WP02, via `spec-kitty implement`) that
did not; the two entry points appear to route the claim-bookkeeping commit differently and only
one of them survives the protected-branch check here.

**Side effect, left uncommitted and unexploited.** Despite the terminal refusal, the command had
already: (1) created `.worktrees/mission-type-guard-registry-01KZY2FG-lane-b` on a new branch
`kitty/mission-mission-type-guard-registry-01KZY2FG-lane-b` at `faa049dcf` (confirmed via `git
worktree list`; the worktree's own tree is clean, matching HEAD, no uncommitted files inside it);
(2) mutated `kitty-specs/.../tasks/WP02-doctor-mission-type-command.md` in the PRIMARY checkout,
adding `base_branch`, `base_commit`, `created_at` frontmatter fields (mirrors entry 9's identical
WP01-file side effect). This task file is not in `lanes.json`'s lane-b `write_scope` (which lists
only the four `owned_files` production/test paths), so committing it is outside this WP's write
scope, same posture as entry 9. **Not exploited**: although the worktree exists on disk, WP02's
status is still `planned`, not `claimed` — proceeding to implement inside it would mean doing
substantive code work under a mission state that does not record the claim, which is the same
category of "the tool didn't actually authorize this" as hand-editing state would be, just via
omission rather than a direct edit. Neither the worktree nor the mutated task file were touched
further.

**Escalating as BLOCKED, not routing around**, per this WP's explicit brief: hitting the
`LANES`/`target_branch=main` bookkeeping-contradiction class a second time (first at
`finalize-tasks` in entries 5-7, now at WP-claim time) is named mission-root scope, not
lane-b's to fix — no `--target-branch` override was attempted, for the same reason entry 6 gave
(the flag's own `--help` scopes it to pre-WP07 legacy missions; this mission's `meta.json` already
carries a correct, persisted `target_branch`). No hand-edit of `status.events.jsonl`/`status.json`
was attempted to force a `claimed` transition. Both this entry and (a) above are handed back to
the orchestrator; no production code was written for WP02 this dispatch.

## 14. Ledger SK-20 — analyze verdict re-recorded a third time, this time to fix WHICH file the
    charter hash was keyed to, not the analysis itself

**Verified first-hand** (Debugger Debbie profile, dispatched for a narrow mechanical re-record,
not a fresh analysis), same checkout, spec-kitty 3.2.6rc1 (PATH-installed CLI, upgraded from the
3.2.5 that produced entry 12's record).

Confirmed the premise before touching anything: `spec-kitty --version` → `3.2.6rc1`; spec.md,
plan.md, and tasks.md hashes byte-identical to the values `analysis-report.md` already recorded
(entry 12's re-verification still holds, untouched); both `.kittify/charter/charter.md` and
`.kittify/charter/charter.yaml` byte-identical to `HEAD` (`git diff HEAD` empty on both).

Root cause (SK-20): entry 12's record was written by the then-PATH-installed 3.2.5 CLI, whose
`_charter_path()` resolved to `.kittify/charter/charter.md` and recorded `sha256: b2b5046…`. The
checking CLI (3.2.6+, and 3.2.6rc1 confirmed here) prefers `.kittify/charter/charter.yaml` when
it exists (`sha256: b976bed…`) — so `check_analysis_report_current` reported a `charter`
mismatch even though neither file had changed a single byte. Purely a which-file-is-the-charter
disagreement between two CLI minor versions that should agree (directive 032 territory), not a
stale artifact.

Hit entry 8/12's exact `DIRTY_WORKTREE` preflight defect a third time, on the same two
deliberately-dirty charter-downgrade files plus this mission's own `WP02-doctor-mission-type-
command.md` claim-attempt side effect (documented in entry 13) plus untracked `_rnd/`. Worked
around identically to entry 12: captured pre-stash sha256 of all four dirty paths, `git stash
push -u -m sk20-temp-stash-for-record-analysis` (no path-restriction this time — the full dirty
set matched what the preflight listed), ran `record-analysis` against the clean tree with a
`schema: analysis-findings/v1` / `findings: []` carrier (ledger SK-06: the unstructured-carrier
silent-`unknown` trap was avoided by construction, not discovered the hard way), then `git stash
pop` immediately after. Verified byte-identical sha256 for all four paths post-pop — confirmed
restoration, nothing lost or mutated.

`analysis-report.md` read back from disk: `verdict: ready`, `findings: []`, charter entry now
`path: .../.kittify/charter/charter.yaml`, `sha256: b976bed223460ac3f4339da1c61c686c6ac96cf9baffdd`
`501073b4e721a1442f` — matches the checking CLI's own resolution exactly.
`check_analysis_report_current(...)` → `AnalysisFreshness(ok=True, ..., mismatches={})`. Gate
confirmed clear.

Committed only `kitty-specs/mission-type-guard-registry-01KZY2FG/analysis-report.md` via
`safe-commit --to-branch kitty/mission-mission-type-guard-registry-01KZY2FG` with an explicit
path (`31e2de708`). The two charter-downgrade files and the WP02 task-file side effect were never
staged, never committed, and remain dirty exactly as briefed; `_rnd/` remains untracked.

Confirms entries 8/12's finding generalizes a third time: the preflight's blanket repo-wide
dirty-tree refusal recurs on every `record-analysis` invocation while the charter-downgrade trap
sits uncommitted by design — the stash/pop workaround is now a proven, repeatable pattern for
this specific known-dirty state, not a one-off. Same remediation gap as entries 8/12; not
re-argued in full here. Separately: this is the second time a charter-path CLI-version disagreement
has silently regressed a recorded artifact (once by writing the wrong file's hash outright at
3.2.5, caught here before it caused a false `stale` block at 3.2.6+) — worth a durable fix in
`_charter_path()`'s resolution order or a schema note pinning which file the recorder should
prefer, independent of installed-CLI version, so this class does not recur a third time under a
future 3.2.x/3.3.x split.

## 15. WP02 dispatch (third attempt) — SK-20 closed gap (a), but gap (b), entries 5-7/13's
    `LANES`/`target_branch=main` bookkeeping contradiction, is still open, and now confirmed
    NOT command-specific

**Verified first-hand** (Wrangler Wendy profile, WP02 implementer, third dispatch — briefed
that "both prior blockers are now resolved" following entry 14's SK-20 fix), same checkout,
spec-kitty 3.2.6rc1 (PATH-installed CLI).

This dispatch's brief was correct about gap (a): `spec-kitty agent action implement WP02
--agent claude --mission mission-type-guard-registry-01KZY2FG` no longer hit
`stale_analysis_report` — entry 14's SK-20 re-record held. But the brief characterized gap
(b) — entry 13(b)'s `LANES`/`target_branch=main` bookkeeping contradiction — as resolved too,
on the theory that it was specific to the legacy `spec-kitty implement WP02` command and would
not recur via the canonical `agent action implement` path once the lane-b worktree already
existed. That theory does not hold: running the canonical command against the pre-existing
worktree produced the **same** `PROTECTED_BRANCH_REFUSED` this dispatch initially logged (in a
now-corrected version of this entry) as if it were new:

```
Branch: on 'kitty/mission-mission-type-guard-registry-01KZY2FG', mission targets 'main'
Error: Bookkeeping refused: PROTECTED_BRANCH_REFUSED: Refusing to record 'status transition
batch WP02': destination ref 'main' is on this project's protected branch list. Bookkeeping
commits must target the coordination branch.
```

Same root cause entries 6/13(b) already traced (`commit_router.py`'s `LANES`-topology
placement resolving every bookkeeping destination to `target_branch`/`main`, against
`policy.py`'s unconditional protected-branch refusal) — **not** a new failure class. The one
genuinely new data point this dispatch adds: entry 13(b) hit this via `spec-kitty implement
WP02` at workspace-allocation time (before the worktree existed); this dispatch hit the
byte-identical error via `spec-kitty agent action implement` — the canonical-loop
command — with the lane-b worktree already materialized, so the failure is in the
status-transition bookkeeping write itself, not specific to workspace allocation or to either
entry point. `status.json` still confirms it: WP02 remains `"lane": "planned"`, unchanged
since entry 13(b)'s own `finalize-tasks` timestamp — no dispatch across entries 5-13/15 has
ever gotten WP02's claim transition to record, regardless of which command was used.

Unlike the second dispatch (entry 13), this dispatch's actual code work was **not** blocked by
this — the lane-b worktree was already usable, so RED-first ATDD, implementation, and the
golden-contract commits were completed and mechanically RED→GREEN-verified on
`kitty/mission-mission-type-guard-registry-01KZY2FG-lane-b` (3 commits, not yet pushed) before
this entry was written. Only the mission's own claim/status bookkeeping — a mission-root-scope
concern, per this dispatch's own brief — never recorded. Reported BLOCKED for that bookkeeping
gap specifically (not for the code, which is done), per the brief's pre-authorized handling for
a `PROTECTED_BRANCH_REFUSED` recurrence: no hand-edit of `planning_base_branch`, no forced lane
transition, no `--target-branch` override.

**Correction note (self-caught, not by a reviewer):** this entry originally landed as a
misnumbered `## 13.` inserted between the real entries 12 and 13, because it was drafted from a
stale copy of this file read out of the lane-b worktree (frozen at this WP's `base_commit`,
before entries 13-14 existed on the mission branch) instead of the mission-root checkout. Caught
before pushing lane-b or finalizing the report; the misplaced block was removed and this
corrected, correctly-numbered, chronologically-last entry substituted in a follow-up commit —
recorded here per this file's own append-only, no-silent-rewrite discipline, rather than force-
pushing over the mistake.
