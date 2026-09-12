# Tracer — Tooling Friction

Seeded during the plan phase (charter standing order 3 requires this file; the spec phase
seeded `tracer-approach.md` and `tracer-design-decisions.md` but omitted this one and
reported "deviations: none" — that omission is itself recorded below).

## 1. `agent mission create` auto-commits with a commitlint-invalid, Terminology-Canon-violating message

**Verified first-hand by the orchestrator.** Commit `826fc2056` on this branch's own history
(`git log --oneline` shows it immediately after the mission's base) reads literally:

```
Add meta for feature cascade-asset-silent-drop-01M0RME0
```

No conventional-commit type prefix (`feat:`, `chore:`, etc — commitlint enforces this on the
repo's own commits), and the word "feature" violates the repo's Terminology Canon, whose
canonical term is **Mission**, not Feature. This matches ledger entry SK-64.

**Disposition**: must be dealt with at PR-prep (folded into a properly-typed, canon-correct
commit or otherwise reconciled before the PR opens). Do **not** amend this commit mid-mission
— amending would rewrite a commit other tooling (safe-commit's branch tracking, the mission's
own event log) may already reference by hash.

## 2. `safe-commit` deprecation warning — `--to-branch` will become required

**Verified first-hand by the orchestrator** (observed on the spec phase's trail commit, prior
to this phase's dispatch): `spec-kitty safe-commit` printed an advisory deprecation warning
that `--to-branch` will be required starting v3.3, and that it should be passed explicitly.
This is advisory and non-blocking today.

**Disposition**: future missions (including the implementation phase of this one) should pass
`--to-branch` explicitly on every `safe-commit` invocation to avoid the warning and to be
ready ahead of the v3.3 breaking change.

## 3. `agent mission create` leaves its own `status.events.jsonl` untracked

**Verified first-hand by the orchestrator.** `git status --short` in this checkout shows
`status.events.jsonl` and `tasks/` as untracked (`??`), while `meta.json` was committed by the
scaffold command (see item 1's commit `826fc2056`). The scaffold's own event log is not part
of the commit it makes for itself — an inconsistency between what the scaffold commits and
what it creates.

**Disposition**: recorded as an observation only. Per explicit instruction, this file is NOT
to be "fixed" by committing `status.events.jsonl` — that file is expressly not this phase's to
touch (see the mission brief's STATE ON DISK section: "Untracked and not yours to touch:
`status.events.jsonl`, `tasks/`").

## Additional friction observed during the plan phase

### 4. `DeactivationPlan`'s symbol-level dead-code allowlist entry is body-hash-keyed and will need updating

**Verified first-hand by the orchestrator.** `DeactivationPlan` is declared in
`cascade.py`'s `__all__` (line 69) but is never imported by name from
`src/specify_cli/cli/commands/charter/deactivate.py` (that file imports only the
`deactivation_plan` FUNCTION, `deactivate.py:32`) — so the symbol-level dead-code gate
(`tests/architectural/test_no_dead_symbols.py`) treats it as a symbol with zero non-test
callers and carries a hand-curated allowlist entry for it
(`tests/architectural/test_no_dead_symbols.py:955-956`,
`SymbolKey("DeactivationPlan", "527c491b7...", source_module="charter.cascade")`).
`ReferencedArtifact` and `SharedSkip` (also in `__all__`, also un-imported-by-name from
`deactivate.py`) carry the identical pattern (lines 961-963). Confirmed live in
`tests/architectural/_symbol_key.py` (`body_hash()`, line 205) that this hash is computed over
the normalized token span of the class body itself — so adding a field to `DeactivationPlan`'s
dataclass body (FR-007) WILL change its body hash and invalidate that allowlist entry.

`CascadeActivationResult` and `NoCascadeReport` do NOT have this problem — neither is declared
in `cascade.py`'s `__all__` (confirmed: `__all__` lists only `REFERENCE_RELATIONS`,
`CascadeScope`, `DeactivationPlan`, `ReferencedArtifact`, `SharedSkip`,
`cascade_activation_targets`, `deactivation_plan`, `referenced_but_not_cascaded`) — so the
symbol-level gate does not walk them at all, and adding a field to either is invisible to this
gate.

**Disposition**: whichever WP implements FR-007 (`DeactivationPlan`'s new field) must also
update the literal body-hash string in `tests/architectural/test_no_dead_symbols.py:955-956` to
match the new class body — this is a content update to an existing allowlist entry (the symbol
is not newly added, not newly dead, and the entry count does not grow), not a violation of the
Burn-down Policy's shrink-only ratchet. Recorded here so the WP author does not get a
surprising, hard-to-diagnose CI failure on `test_no_dead_symbols.py` and mistake it for an
introduced regression rather than expected mechanical maintenance. Not fixed proactively in
this plan phase — that edit belongs to the implementation WP that actually changes
`DeactivationPlan`'s body, per this repo's own "do not hand-edit ahead of the change" discipline.

## 5. `requirement_mapping.py`'s coverage-gate regexes are blind to letter-suffixed FR ids (e.g. `FR-005a`)

**Verified first-hand — independently, three times** (both R1 lens groups and the R3 refuter
all live-ran the regex against this mission's own artifacts and got the same empty result).
`src/specify_cli/requirement_mapping.py:15-16` (`_REF_PATTERN` / `_REF_FIND_PATTERN =
re.compile(r"\b(?:FR|NFR|C)-\d+\b")`) and `:68` (`_TABLE_ROW_ID_PATTERN`) match only a
trailing run of digits, so a letter-suffixed id like `FR-005a` is invisible to both patterns —
confirmed live against `spec.md`'s own declared-requirements table (`_declared_ids()` returns
`FR-005` but not `FR-005a`) and against WP frontmatter mapping. This is structural, not
mission-specific: `requirement_mapping.py:375-379` already carries a code comment documenting
the identical gap for `C-007-mission` / `C-009-mirror` style ids, so letter/word-suffixed FR
ids have never been covered by the mechanical coverage gate.

Concretely for this mission: WP03's own prompt-file frontmatter `requirement_refs` had drifted
to omit `FR-005a` (present in `wps.yaml` and `tasks.md`, both of which were populated before
the frontmatter was hand-checked) and `finalize-tasks`'s coverage gate did not catch the drift
on either side — neither the spec-declared side nor the WP-mapped side — because the regex
family cannot match `FR-005a` on either side.

**Disposition**: out of scope for this mission's tasks phase (WP03's frontmatter drift itself
was fixed directly — see item near the top of this phase's commit — but the regex is upstream
spec-kitty tooling, not this mission's deliverable). Recorded here as a ledger candidate for
the orchestrator to pass upstream: either extend `_REF_PATTERN` / `_REF_FIND_PATTERN` /
`_TABLE_ROW_ID_PATTERN` to accept an optional trailing lowercase-letter suffix, or explicitly
document letter-suffixed FR/NFR/C ids as unsupported by the mechanical coverage gate so future
missions don't rely on a gate that silently can't see them.

## 6. Re-running `finalize-tasks` after a WP-frontmatter fix would silently regress the fix

**Verified first-hand by the orchestrator**, tasks phase, mission `cascade-asset-silent-drop-01M0RME0`
(issue #3705), CLI `3.2.6rc3`, 2026-08-24 — following the pipeline's own instruction to re-run
`finalize-tasks` after the R1-R6 review/fix loop, run as a preflight:

```
SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 .venv/bin/spec-kitty agent mission finalize-tasks \
  --validate-only --mission cascade-asset-silent-drop-01M0RME0 --json
```

Output included:

```json
"would_modify": [{"wp_id": "WP03", "changes": {"requirement_refs":
  ["FR-005", "C-002", "NFR-001", "NFR-004"]}}]
```

i.e. running the real (mutating) `finalize-tasks` at this point would have overwritten WP03's
frontmatter and **dropped `FR-005a`** — silently regressing the exact fix landed in commit
`8c5a30ced` for confirmed adversarial-review finding `TASKS-DECOMP-001`, and re-verified resolved
by the R5a anchored-verification round. Root cause is the same regex gap recorded in item 5 above
(`_REF_FIND_PATTERN`/`_TABLE_ROW_ID_PATTERN` in `src/specify_cli/requirement_mapping.py` cannot
match letter-suffixed ids like `FR-005a`) — `finalize-tasks`'s mutation pass re-derives each WP's
`requirement_refs` from a source blind to `FR-005a`, so any manual correction that restores it is
one `finalize-tasks` re-run away from being silently undone, with a bare `"result": "success"` and
no warning that a previously-correct field was just downgraded.

**Disposition**: did NOT run the mutating `finalize-tasks` after the review loop. The lane graph
in `validate-only`'s output was otherwise identical to the already-committed `lanes.json` (same 3
`write_scope_overlap` collapse events, same single `lane-a`, same WP01→WP02→WP03→WP04 chain) —
confirming nothing structural (dependencies, owned_files, WP list) changed during the review/fix
rounds, so there was no genuine need to re-finalize. The already-committed `tasks.md`/`wps.yaml`/
WP frontmatter (as of commit `eaa35f556`) remain the valid, internally-consistent final state.
Flagging this as a sharper, concrete instance of the same upstream `requirement_mapping.py`
letter-suffix gap, worth a dedicated ledger entry: **`finalize-tasks` is not idempotent with
respect to a manually-corrected, tool-blind-spot field — re-running it can regress a confirmed
fix with a clean success exit code.**

## Additional friction observed during the analyze phase

### 7. `record-analysis` behaved correctly, on this mission, contrary to two ledger entries (SK-06, SK-63) and NOT contrary to a third (SK-32)

**Verified first-hand by the orchestrator.** `SPEC_KITTY_SYNC_MINIMAL_IMPORT=1
.venv/bin/spec-kitty agent mission record-analysis --mission cascade-asset-silent-drop-01M0RME0
--input-file <well-formed analysis-findings/v1 carrier, zero findings> --json` returned promptly
(no SK-63 hang), exited 0, and wrote a `verdict: ready` / empty-findings `analysis-report.md` that
matches the well-formed input carrier — no SK-06 silent-`unknown` fallback triggered, because the
input carrier opened with a literal `---` on line 1 and `schema: analysis-findings/v1` exactly, the
two documented trigger conditions from the SK-06 ledger entry. Recording this as a **positive**
first-hand data point against SK-06 and SK-63, not a refutation of either (both entries document
real, reproduced-elsewhere failure modes; this run simply did not hit their trigger conditions).

**SK-32 (host-absolute paths) DID reproduce**, unchanged: `analysis-report.md`'s
`input_artifacts[*].path` values are all `/home/jeroennouws/dev/SK-missions/3705/...` absolute
paths (4 of 4 entries: spec.md, plan.md, tasks.md, charter.yaml). Left as generated, per SK-32's
own guidance — not hand-scrubbed. This is the same live, growing-corpus defect (#3398).

### 8. `record-analysis` auto-commits `analysis-report.md` itself — the opposite of ledger SK-43's documented behaviour, on this run

**Verified first-hand by the orchestrator.** Ledger SK-43 documents `record-analysis` leaving its
report **untracked**, requiring an explicit follow-up `safe-commit`. On this run, the command
auto-committed `analysis-report.md` by itself as commit `779e1598e` ("Add analysis report for
mission cascade-asset-silent-drop-01M0RME0"), authored under a generic bot identity, containing
only that one file (216 insertions) — `git show --stat` confirms. The orchestrator's dispatched
subagent was explicitly instructed not to commit and did not run any git command itself; this
commit is `record-analysis`'s own side effect. `record-analysis` also modified but did NOT commit
a second file as a side effect: `.kittify/dossiers/cascade-asset-silent-drop-01M0RME0/
snapshot-latest.json` (a machine-generated parity-hash manifest, regenerated to include the newly
committed report) — that one WAS left dirty/untracked-to-a-commit, matching SK-43's pattern. The
orchestrator committed it separately via `spec-kitty safe-commit` (commit `60fba6b6c`).

**Disposition**: not treated as a defect to fix — both files ended up correctly committed on the
mission branch, verified via `git status` (clean) and `git log` (both commits present, correct
branch) before this phase closed. Flagging the inconsistency (commits one generated artifact,
leaves a second, related generated artifact dirty, in the same command invocation) as worth a
ledger note: `record-analysis`'s commit behaviour is not uniform across the artifacts it touches
in one run, so a caller cannot safely assume either "always commits" or "never commits" — `git
status` must be checked after every invocation regardless of which way SK-43 or this entry lean.

## Additional friction observed during WP01 implementation

### 9. `agent action implement WP01` hangs on the dossier body-upload sync step even WITH `SPEC_KITTY_SYNC_MINIMAL_IMPORT=1` set, and spins up a lane worktree that contradicts the direct-checkout workspace the mission was dispatched into

**Verified first-hand by the WP01 implementer.** The WP01 implementation work (RED-first ATDD
test, then the `_referenced_artifacts` seam change) was completed and committed directly on
`fix/cascade-asset-silent-drop-3705` in the repository-root checkout, per the explicit
WORKSPACE/BRANCH assignment in the WP01 dispatch. Running the canonical
`SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 timeout 300 .venv/bin/spec-kitty agent action implement WP01
--agent claude --mission cascade-asset-silent-drop-01M0RME0` command AFTER that work was already
committed (to record the state transition through the canonical surface, not to hand-edit state):

- Correctly recorded `WP01: planned → claimed → in_progress` in `status.events.jsonl` (event ids
  `01M0RWWEPQGRD3EVD0XR2PC52J`/`...52K`) and auto-committed two small status-only commits
  (`16d703d6b`, `9d69468ba`) directly onto `fix/cascade-asset-silent-drop-3705` — the correct
  branch, matching the mission's `single_branch` topology and single-lane `lanes.json`.
- Correctly created a lane worktree (`.worktrees/cascade-asset-silent-drop-01M0RME0-lane-a`,
  branch `kitty/mission-cascade-asset-silent-drop-01M0RME0-lane-a`) based at `cf5264c15` — the
  WP01 implementation commit already on `fix/cascade-asset-silent-drop-3705` — so no divergence
  was introduced; the worktree is additive, not a competing base.
- Then printed the `cd` instruction to the new lane worktree and, in the SAME invocation, hung
  during "Body upload preparation" inside `sync/dossier_pipeline.py::_prepare_bodies` →
  `sync/body_upload.py::prepare_body_uploads` → `body_queue.py::enqueue` →
  `self._authority.execute_write(...)`, past which no further output was produced. The process
  was still alive at the 300s internal `timeout` deadline and was killed (exit 143). This is the
  same failure family SK-72/SK-65 document (a store-authority write blocking) but it reproduced
  **with** `SPEC_KITTY_SYNC_MINIMAL_IMPORT=1` already set — SK-72/SK-65's fix does not cover this
  code path (dossier body-upload queueing), only the store-cutover path they name.
- The kill left two files dirty in the repository-root checkout: `meta.json` (gained `vcs`/
  `vcs_locked_at` keys — a legitimate, harmless side effect of the earlier "VCS locked to git"
  step) and the dossier `snapshot-latest.json`. Both were auto-generated by the interrupted CLI
  process, not hand-edited; committed via `spec-kitty safe-commit` (not a hand-edit — persisting,
  not authoring, the CLI's own output) to leave a clean tree.

**Disposition**: WP01's own deliverable (code + ATDD test) was already correct and committed
before this command ran, so the hang did not block or corrupt WP01's work — it only left status
bookkeeping to finish, which the two auto-committed status commits already captured before the
hang. Not treated as a WP01 defect to fix (out of this WP's `owned_files`/`authoritative_surface`).
Flagging as a ledger candidate: (a) the dossier body-upload write path can hang independently of
the SK-72/SK-65 store-cutover path even with the documented env-var workaround set, and (b)
running `agent action implement <WP>` on a WP whose code is already committed directly to the
mission's target branch is safe (it recognizes the existing commit as the lane-worktree base) but
still attempts a sync step that can hang — callers in this situation should expect to need the
same 300s+-timeout-and-kill pattern used here, not assume the command returns promptly just
because no state repair was needed.

**Follow-up data point (same session):** `spec-kitty agent tasks mark-status T001..T007 --status
done --mission cascade-asset-silent-drop-01M0RME0` (also with `SPEC_KITTY_SYNC_MINIMAL_IMPORT=1`)
hit the *identical* code path (`sync/body_upload.py` → `sync/body_queue.py::enqueue` →
`sync/layout_generation.py::execute_write` → `_await_publish_or_loud`) but this time it did NOT
hang — it raised `LayoutCutoverIncompleteError` ("machine layout cutover did not publish within
the bounded wait; the event is routed to the loud surface rather than dropped to legacy") to
stderr and then completed anyway (`✓ Marked 7 subtasks as done: T001, T002, T003, T004, T005,
T006, T007`, exit 0). The command's own mutation (tasks.md/status.events.jsonl/status.json) is
correct and was committed via `safe-commit`; the dossier-sync side effect is the unreliable part.
So this same write-authority path is observed with TWO distinct outcomes across two invocations
in one session: a silent hang requiring an external kill, and a loud-but-swallowed exception that
still lets the caller's actual work through. Neither outcome is "clean" — a caller cannot rely on
either the command returning promptly, or on a raised exception meaning the command's own effect
failed — `git status` + the command's own stated result (not its exit code or stderr alone) must
be checked after every invocation that touches this dossier/sync surface.

### 10. Same dossier body-upload write-authority path, THIRD distinct failure shape on this mission: raise-then-hang

**Verified first-hand by the WP02 implementer.** Following the same protocol as item 9 (WP02's
code + RED-first ATDD test were already committed directly on
`fix/cascade-asset-silent-drop-3705` before this command ran, per the WP dispatch's explicit
instruction to attempt the implement command exactly once, bounded, and proceed directly if it
hangs), ran:

```
SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 timeout 300 .venv/bin/spec-kitty agent action implement WP02 \
  --agent claude --mission cascade-asset-silent-drop-01M0RME0
```

The command's captured log shows it reached and **raised**
`specify_cli.sync.layout_generation.LayoutCutoverIncompleteError` from
`layout_generation.py:694` in `_await_publish_or_loud` ("machine layout cutover did not publish
within the bounded wait; the event is routed to the loud surface rather than dropped to legacy"),
via the identical call chain item 9 already names (`dossier_pipeline.py::_prepare_bodies` →
`body_upload.py::prepare_body_uploads` → `_process_artifact` → `_enqueue_artifact` →
`body_queue.py::enqueue` → `layout_generation.py::execute_write` →
`_await_publish_or_loud`). Unlike the earlier "Follow-up data point" in item 9 (where
`mark-status` raised this SAME exception and then **completed anyway**, exit 0), this invocation
raised the exception and then **kept hanging** — no further output, no shell return, no exit code
line ever printed by the wrapping `echo "EXIT: $?"` sentinel that was chained after it. It was
still alive when the outer bounded `timeout 300` should have (and apparently did) terminate it;
the process was ultimately reaped by the harness's own background-task completion detection, not
by returning control normally.

This is a **third distinct failure shape** for the same write-authority path, all three observed
within this one mission:

1. **Silent hang, no exception at all** (item 9, WP01's own invocation) — no output past "Body
   upload preparation", killed externally at the timeout deadline.
2. **Raise, then complete correctly** (item 9's "Follow-up data point", the `mark-status`
   invocation) — `LayoutCutoverIncompleteError` printed to stderr, but the command's own mutation
   still completed and returned exit 0.
3. **Raise, then hang anyway** (this item, WP02's `agent action implement` invocation) — the same
   exception fires and is logged, but the process does not return afterward; it required the
   outer bounded timeout to end it.

**Disposition**: WP02's own deliverable (RED-first test, then the `_render_cascade_activation`
kind-filtered rendering change) was already correct and committed before this command ran, so —
as with WP01 — the hang did not block or corrupt the actual WP work. The only side effect was a
dirtied dossier snapshot (`kitty-specs/cascade-asset-silent-drop-01M0RME0/.kittify/dossiers/
cascade-asset-silent-drop-01M0RME0/snapshot-latest.json`), persisted via `spec-kitty safe-commit`
per the same handling item 9 established. With three occurrences and three distinct shapes now
observed on this single mission, this is no longer a lead — it is a **confirmed defect** in the
dossier body-upload write-authority path (`layout_generation.py::_await_publish_or_loud` /
`body_queue.py::enqueue`): the caller cannot rely on the command hanging, raising-and-returning,
or raising-and-hanging for the same underlying condition, and must always verify actual effect via
`git status` / the command's own stated result rather than trusting its return behaviour. Strong
ledger candidate.

### 11. Same dossier body-upload write-authority path, FOURTH distinct failure shape on this mission: a NEW warning message, then silent hang until the outer bound kills it (exit 124)

**Verified first-hand by the WP03 implementer.** Following the same protocol as items 9/10 (WP03's
RED-first ATDD test commit, then the `NoCascadeReport`/`_render_no_cascade_warning` kind-filtered
implementation commit, were already completed and committed directly on
`fix/cascade-asset-silent-drop-3705` before this command ran, per the WP dispatch's explicit
instruction to attempt the implement command exactly once, bounded, and proceed directly if it
hangs), ran:

```
SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 timeout 300 .venv/bin/spec-kitty agent action implement WP03 \
  --agent claude --mission cascade-asset-silent-drop-01M0RME0
```

The command's captured log shows a single line this mission has not printed before at this site:

```
WARNING  Dossier sync failed for cascade-asset-silent-drop-01M0RME0: project sync store is locked
```

— no traceback, no `LayoutCutoverIncompleteError` (the exception items 9/10 name). After printing
that one warning line the process produced **no further output at all** and did not return; it was
tracked continuously via `kill -0` on its PID and confirmed still alive at 297s wall-clock elapsed.
It was ultimately terminated by the outer bounded `timeout 300` itself: the wrapping shell's
`echo "EXIT: $?"` sentinel printed `EXIT: 124` (`timeout`'s standard "killed on deadline" exit
code) once the process was reaped — the clearest of the four observed endings, in the narrow sense
that a definite exit code was captured this time (unlike item 9's WP01 case, which needed an
external kill with no code at all).

This is a **fourth distinct failure shape** for the same write-authority path, all four now
observed within this one mission:

1. **Silent hang, no exception at all, no exit code captured** (item 9, WP01) — killed externally
   at the timeout deadline.
2. **Raise, then complete correctly, exit 0** (item 9's follow-up, `mark-status`) —
   `LayoutCutoverIncompleteError` logged, but the command's own mutation still completed.
3. **Raise, then hang anyway, no exit code captured** (item 10, WP02) — the same exception fires
   and is logged, but the process never returns.
4. **A different warning ("project sync store is locked"), then hang, exit 124 captured** (this
   item, WP03) — no exception raised at all this time; the outer `timeout 300` is what actually
   ends it, with a clean, unambiguous exit code.

**Disposition**: WP03's own deliverable (the RED-first test, then the `NoCascadeReport` field +
`has_skipped` guard fix + `_render_no_cascade_warning` rendering change) was already correct and
committed before this command ran, so — as with WP01/WP02 — the hang did not block or corrupt the
actual WP work. Unlike items 9/10, this run left **no dirtied dossier snapshot** to persist (`git
status` was clean immediately after the process was reaped) — but it DID leave one real, wanted
side effect already committed: the WP03 lane transition `planned` -> `claimed` -> `in_progress`
(commit `9090eb96f`, "chore(spec-kitty): status transition batch WP03"), which the command
completed and auto-committed BEFORE it reached the dossier-sync step and hung. So the workspace/
status-setup half of `agent action implement` succeeded here even though the dossier-sync half did
not — a caller cannot assume "the command didn't return cleanly" means "nothing it did landed."

With four occurrences and four distinct shapes now observed on this single mission (a fifth
symptom variant — "sync store is locked" — on top of the three from items 9/10), the write-
authority path at `layout_generation.py::_await_publish_or_loud` / `body_queue.py::enqueue` (and
now also whatever locking primitive backs "project sync store is locked") is confirmed unreliable
across every invocation shape tried on this mission: two of four raised an exception, two did not;
two hung indefinitely, one hung until the outer bound killed it, one completed normally despite
raising. The only invariant across all four is that the caller must verify actual effect via `git
status` / the command's own committed state, never via the command's return behaviour, exit code,
or absence of a raised exception. Strong ledger candidate — now with independent confirmation
across three different WPs (WP01, WP02, WP03) in one mission.

---

## Item 11 (WP04, verified first-hand) — SK-93 did NOT recur this WP: real work bypassed the affected path entirely

Unlike WP01/WP02/WP03, this WP's actual implementation (the RED-first ATDD commit `ddc9d1d33`
and the implementation commit `2ee12551b`) was authored and committed directly with `git`/`spec-kitty
safe-commit`, never through `spec-kitty agent action implement WP04 --agent claude`. The operator's
dispatch for this WP did not route through that command at all, so `sync/dossier_pipeline.py`'s
write-authority path (`_prepare_bodies` -> `body_upload.py` -> `body_queue.py::enqueue` ->
`layout_generation.py::_await_publish_or_loud`) — the exact seam items 9/10/10-follow-up/this-file's
item-above all hit — was never invoked this WP, so there is no fifth failure shape to record from
direct observation this time. Recording this explicitly rather than staying silent: the absence of
a new data point here is a fact about *which command ran*, not evidence the underlying SK-93 defect
is any less live — items 9-10 above already establish it as unreliable across every invocation shape
tried (WP01/WP02/WP03, four distinct shapes). A future WP/mission that DOES route through
`agent action implement` should expect to keep hitting it until SK-93 itself is fixed upstream.

Also verified this WP: pytest-cov's parallel run under `-n auto --dist loadfile` writes
transient `.coverage.<host>.<pid>.*` combine-worker files during the run; by the time both shard
runs completed and I inspected the working tree, only the single combined `.coverage` file
remained (no stray `.coverage.<host>.<pid>*` files) and it is covered by `.gitignore`'s exact
`.coverage` pattern (`.gitignore:171`; `git status --ignored` confirms `!! .coverage`). Nothing
was staged or committed from the coverage run.
