---
work_package_id: WP11
title: Transition ordering and the durability signal
dependencies:
- WP06
- WP07
requirement_refs:
- FR-002
- FR-013
planning_base_branch: pr/review-verdict-write-integrity-01KZ1CGF
merge_target_branch: pr/review-verdict-write-integrity-01KZ1CGF
branch_strategy: Planning artifacts for this mission were generated on pr/review-verdict-write-integrity-01KZ1CGF. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/review-verdict-write-integrity-01KZ1CGF unless the human explicitly redirects the landing branch.
created_at: '2026-08-03T08:13:56Z'
subtasks:
- T047
- T048
- T049
- T050
agent: claude
history:
- at: '2026-08-03T08:13:56Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent:
- src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py
- tests/specify_cli/cli/commands/agent/test_move_task_durability.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py
- tests/specify_cli/cli/commands/agent/test_move_task_durability.py
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP11 - Transition ordering and the durability signal

> **On `create_intent` in this WP's frontmatter.** It lists
> `tasks_verdict_persistence.py`, which **WP06 creates, not this WP**. The entry is
> required by the ownership gate, which rejects any literal `owned_files` path
> matching zero files unless it is declared planned-new — and at validation time
> that module does not exist yet. Read it as "this path is planned-new at mission
> level", not as a claim that this WP creates it. By the time this WP starts, WP06
> has already extracted the module.

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

## Objective

**FR-002** requires that no readable verdict survive a failed transition. Today
the call order is backwards for that guarantee: `_do_move_task`
(`src/specify_cli/cli/commands/agent/tasks_move_task.py:2369-2370`) calls
`_mt_finalize_plan(st, ports)` — which writes and commits the review-cycle
artifact via `create_rejected_review_cycle` — **before** `_mt_execute(st,
ports)`, which is what actually emits the lane transition (under
`feature_status_lock`). If the transition emit fails AFTER the verdict has
already been durably written and committed, the artifact survives as a
readable, committed record for a WP that never moved — the exact
committed-orphan state FR-002 exists to close.

**Reproduced** (spec.md, Edge Cases: "Transition fails after the verdict is
written" — marked `Reproduced`, evidenced at `research/wave3-partial-atomicity.diff`):
this leaves a committed `approved` orphan, and — this is the trap a naive fix
falls into — **the retry then short-circuits**. `_persist_approved_review_cycle`
(`tasks_move_task.py`, inside `_mt_finalize_plan`) checks `if latest is None or
latest.verdict != "rejected": return` before writing anything. After the orphan
write, `latest.verdict` is already `"approved"`, so the retry's no-op guard
fires, the writer is never called again, and the command reports SUCCESS having
written and committed **nothing new** on the retry — while the WP is STILL not
in the approved lane, because the transition never happened either time. **A
naive fix that only reorders the calls or only patches the no-op guard makes
SC-003 falsely green**: SC-003 says "the identical retry both exits zero AND
records the correct verdict" — an implementation that exits zero while having
recorded NOTHING is passing the exit-code half of the assertion while failing
the half that matters. The acceptance criterion for this WP's tests MUST assert
**what was actually recorded** (the artifact's verdict, its presence, its
commit state), never just the process exit code.

**Data-model.md's own correction applies here** (IC-05c's risk note, carried
into this WP): *"I-1 is not deliverable under the recorded serialization
boundary — the write+commit runs before the event emit and the compensator
cannot un-commit."* The buildable form is the weaker, honest statement: **no
UNCOMMITTED artifact survives a failure** (already close to true after WP10's
compensator work) is not the same claim as **no COMMITTED artifact survives a
FAILED TRANSITION** (which requires actually reordering the calls, or adding a
compensating action after a transition failure). This WP's job is to make the
call ORDER match the guarantee FR-002 actually needs: emit the transition
FIRST, write/commit the verdict record SECOND, conditioned on the transition
having succeeded — inverting today's order — is **not available to this WP,
and must not be implemented.** After WP07 the status event is the
authoritative verdict: emitting it first would create a durable,
gate-readable `approved` transition before the verdict record backing it
exists. A transition failure injected *after* that emit (the "write-after-
transition" direction spec.md's Independent Test requires be tested
alongside "transition-after-write") would then leave exactly the hazard this
mission exists to close — a merge gate reading a completed, authoritative
`approved` transition for a work package whose verdict payload was never
durably written. That is spec.md US1 Acceptance Scenario 3 inverted
verbatim: *"Given a transition that has completed, When the durable write
fails, Then the work package has not moved."* Emit-first makes the
transition complete before the write is even attempted, which is the
prohibited state, not the fix. **Emit-first is forbidden under FR-001's
authority split — full stop, not a design option to weigh.**

The only permitted mechanism is the **revert-compensator**: keep today's
write-then-emit order, and on a transition-emit failure, actively revert the
verdict write that already landed (uncommit and delete it), rather than
tolerating it as an orphan. Re-derive from the current code exactly what
"revert" requires (uncommitting a landed commit, deleting the artifact file,
or both) without assuming the reorder was ever a live option.

**FR-013**: `--no-auto-commit` is the ONE sanctioned non-durable path — the only
way a caller can legitimately end up with a verdict written but not committed.
Every OTHER route to that state is a defect this mission closes elsewhere, not a
case to warn about. This WP makes that one sanctioned path ANNOUNCE itself: the
`--json` payload must carry a named key stating the record was written but not
durably persisted, matching what the human-readable console output already
says. **This module already suppresses console prints under `--json`**
(`tasks_move_task.py` guards its warnings/notices with `if not json_output:`
throughout — see the arbiter-persist warning at the `_mt_arbiter_override`-family
call site as one example of the pattern) — meaning a plain `console.print(...)`
call for the non-durable-write notice is, today, completely INVISIBLE to any
machine consumer of `--json` output. A human operator sees the warning; a script
parsing `--json` sees nothing and cannot distinguish "durably recorded" from
"written but not committed."

**`st.skip_target_branch_commit` is not threaded to the writer.** It is computed
at `tasks_move_task.py:316-319` (`st.skip_target_branch_commit =
_tasks._skip_target_branch_commit(...) if st.resolved_auto_commit else False`)
and used at line 326 to gate the STATUS-EVENT protected-branch refusal — but
`_persist_approved_review_cycle`'s and the rejection call site's
`commit_router=ports.coord if st.resolved_auto_commit else None` (lines ~1756,
~1769) does NOT consult it. On a protected-primary coordination topology, the
status-event commit correctly skips (via `skip_target_branch_commit`), but the
review-cycle artifact's `commit_router` is still passed because
`resolved_auto_commit` alone is `True` — so `_commit_review_cycle_artifact`
attempts to commit the artifact onto the SAME protected branch the status event
just declined to touch. The likely outcome is the underlying `commit_artifact`
port refusing the commit (via its own `ProtectionPolicy` check), which raises
`ReviewCycleError`, which is NOT caught anywhere in `_mt_finalize_plan` — so the
whole `move-task` invocation raises for BOTH the approval and rejection paths on
this topology. **Neither verdict can be recorded at all** under
protected-primary coord, which is worse than the sanctioned `--no-auto-commit`
path: at least that one announces itself (once T049 lands); this one currently
crashes.

## Context & Constraints

- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/spec.md` — FR-002, FR-013, User Story 1 Acceptance Scenarios 2, 3, 8; Edge Cases ("Transition fails after the verdict is written", "Protected-primary under coord topology")
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/plan.md` — IC-05c ("Transition ordering")
- `kitty-specs/review-cycle-verdict-seam-rebuild-01KZ2W7W/data-model.md` — I-1, the Failure-state model table's "Neither verdict recordable at all under protected-primary coord" row (closed by FR-013 scope)
- `src/specify_cli/cli/commands/agent/tasks_move_task.py:1688-1803` — `_mt_finalize_plan`, `_persist_approved_review_cycle` (nested closure)
- `src/specify_cli/cli/commands/agent/tasks_move_task.py:2211-2233` — `_mt_execute`
- `src/specify_cli/cli/commands/agent/tasks_move_task.py:2321-2390` (approx.) — `_do_move_task`, the top-level caller establishing the `_mt_finalize_plan(st, ports)` then `_mt_execute(st, ports)` order
- `src/specify_cli/cli/commands/agent/tasks_move_task.py:300-330` (approx.) — `st.skip_target_branch_commit` computation and its (incomplete) use

**This WP's surface has moved.** By the time this WP starts, WP06 has already
extracted the four verdict-relevant sites (including `_mt_finalize_plan`'s
review-cycle-writer calls) OUT of `tasks_move_task.py` and INTO the new
`src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py` module — this
WP's `owned_files` names that new module, not `tasks_move_task.py`, precisely
because WP06 is a listed dependency. Locate the moved functions by their NEW
names/location (WP06's extraction should have preserved behavior and largely
preserved names — confirm the exact post-move shape by reading WP06's actual
diff/the new module directly, rather than assuming the line numbers cited above
still apply verbatim). If WP06 has not actually landed by the time you start
this WP (dependency violation), stop and escalate rather than reconstructing the
extraction yourself.

**Constraints (binding)**:
- **C-002**: do not weaken any of the three named behaviour floors. This WP changes CALL ORDER and adds a `--json` key and a `skip_target_branch_commit` parameter — it must not touch `_content_identity`, the compensator's unlink-on-failure, or the two-leg writer's collision-avoidance.
- This WP is a convergence point for `tasks_verdict_persistence.py`, serialized `WP06 → WP11 → WP12` per `tasks.md`'s ownership table — WP12 depends on THIS WP landing first because it touches the same new module.
- Do not attempt a full I-1 "true atomicity" fix via an emit-first reorder — that reorder is forbidden (see Objective). The honest, buildable statement (no uncommitted artifact survives; a committed artifact from a FAILED transition is actively reverted, not just tolerated) is the actual FR-002 bar for this WP, per data-model.md's own correction.

## Subtasks & Detailed Guidance

### Subtask T047 – Red-first reproduction of the orphan surviving a failed transition

- **Purpose**: Per C-011, prove the exact failure this WP closes, including the falsely-green-SC-003 trap, BEFORE reordering anything — so the fix is verified against a real observed failure, and so the test itself is shaped to catch a naive, incomplete fix.
- **Steps**:
  1. In `tests/specify_cli/cli/commands/agent/test_move_task_durability.py` (new file — this is this WP's `create_intent`), set up a fixture WP whose latest review-cycle artifact is `rejected`, and inject a failure into the transition-emit path (e.g. monkeypatch whatever `_mt_execute`/`_mt_emit_transitions` calls to raise, using the existing `FakeCoordCommitRouter`/fault-injection seam plan.md's Technical Context names, or a direct monkeypatch on the emit function `_do_move_task` resolves from module globals — confirm which seam WP06's extraction preserved).
  2. Call the move-task flow with `--to approved` against that fixture and confirm — TODAY, before this WP's fix — that: (a) a NEW `review-cycle-N.md` with `verdict: approved` exists on disk AND is committed (verify via `git log`/`git status` in the fixture repo, not just file existence), while (b) the WP's lane is STILL the pre-transition lane (the transition never actually completed).
  3. Then simulate the retry: call the SAME move-task invocation again (same fixture, transition failure removed this time, simulating "the reviewer retries the identical command"). Confirm — this is the SC-003-trap reproduction — that the command reports success (exit 0) WHILE the artifact directory shows NO new write (the no-op guard short-circuited because `latest.verdict` is already `"approved"` from the orphan), and the WP's lane is STILL not approved.
  4. Assert BOTH halves explicitly in the test: `exit_code == 0` is necessary but NOT sufficient — also assert on the actual recorded state (lane, and whichever artifact/event fields distinguish "this retry actually recorded the approval" from "this retry silently did nothing"). A test that only checks `exit_code == 0` would pass on the CURRENT broken behavior and must NOT be how this reproduction is written.
- **Files**: `tests/specify_cli/cli/commands/agent/test_move_task_durability.py`
- **Parallel?**: No — must be authored and observed failing before T048's fix.
- **Notes**: This is the single most important test in this WP. Read spec.md's SC-003 wording again before writing it: *"After an interruption including SIGKILL, the identical retry both exits zero AND records the correct verdict, with zero manual cleanup steps."* — write the assertion for "records the correct verdict" as its own explicit check, never inferred from the exit code.

### Subtask T048 – Revert the verdict write when the transition emit fails

- **Purpose**: Make FR-002's guarantee hold — a committed verdict record must not survive a transition that did not complete — via the ONE mechanism this WP is permitted to use: a revert-compensator. **Emitting the transition before writing the verdict is forbidden**, not a design alternative to weigh against the compensator; see the Objective section above for why (it violates spec.md US1 Acceptance Scenario 3 under FR-001's authority split — a durable, gate-readable `approved` transition would exist before its verdict payload does).
  1. In `tasks_verdict_persistence.py` (post-WP06), keep today's call order:
     the verdict record is written/committed, then the transition is emitted.
     Do not reorder these calls. Do not investigate, prototype, or leave a
     partially-built emit-first path in the diff — the dependency-direction
     question ("does the emit need the artifact's path first, or can the
     event carry a not-yet-written pointer") is moot, because emit-first is
     ruled out regardless of the answer.
  2. Wrap the transition-emit call so that when it fails, the verdict write
     that already landed is ACTIVELY reverted: uncommit and delete the
     artifact, using the SAME compensator pattern WP10 built for commit/
     validation failures (widen or reuse it — do not invent a second,
     independent compensator implementation for the same guarantee).
  3. Confirm the revert is complete before `_do_move_task` returns an error to
     the caller — a partially-reverted state (uncommitted but not deleted, or
     vice versa) is itself a new orphan shape and must not occur.
  4. Fix `_persist_approved_review_cycle`'s no-op guard so a retry after a
     FAILED first attempt is distinguishable from a retry after a SUCCESSFUL
     first attempt — the guard's `if latest is None or latest.verdict !=
     "rejected": return` must not treat "the orphan from a failed attempt
     happens to already say approved" the same as "a prior attempt genuinely
     succeeded." With T048's revert in place, a failed attempt should leave NO
     orphan at all, which makes this guard correct again by construction —
     confirm that is actually true after your fix, rather than patching the
     guard's logic directly as a second, independent change.
  5. Update T047's red test to assert the GREEN outcome: after a transition
     failure, no readable committed verdict exists for that WP (query however
     the census's readers would — directly via `ReviewCycleArtifact.latest`/
     `latest_review_artifact_verdict`, not just raw file listing), and the
     retry (with the injected failure removed) succeeds AND records the
     approval for real.
- **Files**: `src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py`, `tests/specify_cli/cli/commands/agent/test_move_task_durability.py`
- **Parallel?**: No — depends on T047's red state; interacts with WP10's lock/compensator work landing correctly (this WP depends on WP07 for the reducer-level reader but shares the writer's compensator machinery with WP10's fixes).
- **Notes**: data-model.md's own correction states the buildable form is "no UNCOMMITTED artifact survives" plus "budget a revert-commit compensator" — this subtask implements the revert-commit compensator as the primary, and only, path. Do not resurrect the "weaken I-1" framing as license to skip the revert and merely tolerate an orphan; the compensator must actively undo the write, not just decline to strengthen the guarantee further.

### Subtask T049 – Emit the `--json` durability key for `--no-auto-commit`

- **Purpose**: Make the ONE sanctioned non-durable path visible to machine consumers of `--json`, not just human console readers.
- **Steps**:
  1. Locate every place the human-readable, `if not json_output:`-guarded console notice for a non-durable write currently fires (search for the existing `--no-auto-commit`-conditioned print in the verdict-persistence path, post-WP06's extraction).
  2. Add a named key to the `--json` result payload — e.g. `"verdict_durably_persisted": false` (or whatever naming convention the rest of this command's `--json` envelope already uses; check `_mt_output`'s `result: dict[str, object]` construction in `tasks_move_task.py` — post-WP06 this may live in the new module — for the established key-naming style before inventing a new one) — populated precisely when the write happened but the commit was skipped because of `--no-auto-commit` (i.e., `commit_router=None` was passed for THIS reason specifically, not for any other reason).
  3. Ensure the key is present (and `true`, or simply absent/omitted per whatever convention this command's `--json` schema uses for "the normal case") on every OTHER path — do not make the key's mere ABSENCE the only signal; an explicit `false` is more machine-legible than "look for a missing key."
  4. Confirm the human-readable console message and the `--json` key say the SAME thing — do not let them diverge (e.g. the console warns about one condition while the JSON key tracks a subtly different one).
  5. Add a test in `test_move_task_durability.py` asserting: `--no-auto-commit` + a rejection or approval move produces `--json` output containing the new key set to the non-durable value, while an ordinary (auto-commit) move either omits the key or sets it to the durable value.
- **Files**: `src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py`, `tests/specify_cli/cli/commands/agent/test_move_task_durability.py`
- **Parallel?**: [P] with T050 — different facet of the same module, low overlap risk, but confirm no line-level collision before finalizing.
- **Notes**: FR-013's own wording is explicit that this is the ONLY case licensed to be non-durable — do not let this subtask's key double as a generic "something went wrong with the commit" signal; that is a different concept (an actual commit FAILURE, which per FR-002 must not leave a readable verdict at all, not merely announce itself).

### Subtask T050 – Thread `skip_target_branch_commit` to the writer

- **Purpose**: Close the "neither verdict recordable at all" defect on protected-primary coord topology, where today the status-event commit correctly skips but the review-cycle artifact commit does not know to, and crashes the whole command instead.
- **Steps**:
  1. Extend whichever function in `tasks_verdict_persistence.py` calls the review-cycle writer (post-WP06's extraction of `_persist_approved_review_cycle` and the rejection call site) to accept/consult `st.skip_target_branch_commit` alongside the existing `st.resolved_auto_commit` check.
  2. Change the `commit_router=ports.coord if st.resolved_auto_commit else None` pattern (both call sites) to also treat `skip_target_branch_commit=True` as a reason to pass `commit_router=None` — i.e., `commit_router=ports.coord if (st.resolved_auto_commit and not st.skip_target_branch_commit) else None`, mirroring EXACTLY the condition already used to gate the status-event commit at `tasks_move_task.py:326` (`if st.resolved_auto_commit and not st.skip_target_branch_commit:`).
  3. Verify the resulting behaviour is coherent with T049: when the write happens with `commit_router=None` BECAUSE of `skip_target_branch_commit` (not because of `--no-auto-commit`), decide and implement what the `--json` payload should say. This is a DIFFERENT reason for non-durability than FR-013's sanctioned `--no-auto-commit` case — spec.md's Edge Cases text implies this is a scope-boundary case for FR-013 ("Protected-primary under coord topology... `skip_target_branch_commit` is not threaded to the verdict writer, so neither verdict can be recorded at all" is listed under "Reproduction owed" separately from the `--no-auto-commit` announcement requirement). Do not silently reuse FR-013's exact key/message for a structurally different cause without confirming that's the intended design — if in doubt, add a distinct reason/cause field alongside the boolean, e.g. `"verdict_durability_skip_reason": "no_auto_commit" | "protected_target_branch"`, so a machine consumer can tell the two apart.
  4. Add a test in `test_move_task_durability.py` reproducing the CURRENT crash first (protected-primary coord topology + `resolved_auto_commit=True` + `skip_target_branch_commit=True` → confirm today's code raises `ReviewCycleError` uncaught from `_mt_finalize_plan`/its WP06-extracted equivalent), then confirm the fix makes both the approval and rejection paths complete WITHOUT raising, with the artifact written but not committed to the protected branch, and the durability signal from step 3 correctly populated.
- **Files**: `src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py`, `tests/specify_cli/cli/commands/agent/test_move_task_durability.py`
- **Parallel?**: [P] with T049 for authoring, but resolve the "same key or distinct key" design question (step 3) jointly — do not land two independently-designed durability signals that overlap awkwardly.
- **Notes**: This subtask does NOT change the status-event side's existing `skip_target_branch_commit` gating at `tasks_move_task.py:326` — that logic is already correct; this subtask only makes the review-cycle-artifact commit consult the SAME already-computed flag it was previously ignoring.

## Test Strategy

- `pytest tests/specify_cli/cli/commands/agent/test_move_task_durability.py -v`
- Full scoped regression: `pytest tests/specify_cli/cli/commands/agent/ tests/review/ tests/post_merge/ -q` (NFR-001 — zero regressions; this WP touches a shared, heavily-tested call path)
- `mypy --strict src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py`
- `ruff check src/specify_cli/cli/commands/agent/tasks_verdict_persistence.py tests/specify_cli/cli/commands/agent/test_move_task_durability.py`
- Re-run WP10's C-002-pinned regression tests explicitly after this WP's revert-compensator (T048) lands — a new failure-path compensator is exactly the kind of edit that can silently perturb an unrelated compensator's assumptions about what state already exists when it runs.

## Branch Strategy

Planning artifacts for this mission were generated on
`pr/review-verdict-write-integrity-01KZ1CGF`. During `/spec-kitty.implement` this
WP may branch from a dependency-specific base (WP06 and WP07 must be merged
into whatever base this WP branches from), but completed changes must merge
back into `pr/review-verdict-write-integrity-01KZ1CGF` unless the human
explicitly redirects the landing branch.

## Definition of Done

- [ ] T047: the reproduction test asserts on recorded state (lane, artifact
      presence/verdict/commit status), never on `exit_code == 0` alone, and
      the pre-fix red state (committed orphan; retry short-circuits reporting
      success while recording nothing) is observed and recorded before T048
      begins.
- [ ] T048: the call order is unchanged (write-then-emit); emit-first is
      **not** present anywhere in the diff, prototyped or otherwise. On a
      transition-emit failure, the verdict write that already landed is
      actively reverted (uncommitted and deleted) before `_do_move_task`
      returns an error — no partially-reverted state is possible.
      `_persist_approved_review_cycle`'s no-op guard correctly distinguishes a
      retry after a failed attempt from a retry after a genuinely successful
      one.
- [ ] T049: the `--json` payload carries a named key stating the record was
      written but not durably persisted, present precisely for the
      `--no-auto-commit` case and matching the human-readable console message;
      the key is absent or falsy on every other path.
- [ ] T050: `skip_target_branch_commit` is consulted by the review-cycle
      writer's `commit_router` gating, mirroring exactly the condition already
      used to gate the status-event commit; the protected-primary-coord crash
      is reproduced red before the fix and both approval and rejection paths
      complete without raising after it.
- [ ] The three C-002-pinned regression tests (content-identity, compensator
      unlink-on-failure, two-leg-writer collision-avoidance) remain green
      after this WP's full diff.
- [ ] NFR-002: every function touched by this WP ends at cyclomatic complexity
      ≤15 (`ruff C901`).
- [ ] NFR-003: `ruff` and `mypy --strict` report zero issues on every touched
      file, with zero new suppressions.
- [ ] Full scoped regression (`pytest tests/specify_cli/cli/commands/agent/
      tests/review/ tests/post_merge/ -q`) shows no new failures beyond
      `research/baseline-8466727eb.md`'s two rows (NFR-001).

## Risks & Mitigations

- **The falsely-green-SC-003 trap**: the single biggest risk in this WP is landing a fix that makes the retry exit 0 without actually recording anything, and calling that "done" because the existing test suite's assertions happen to only check exit codes. Mitigate by writing T047's reproduction to assert on RECORDED STATE explicitly (lane, artifact presence/verdict/commit-status), never inferring correctness from `exit_code == 0` alone.
- **Reaching for emit-first anyway**: emit-first reads as the more "complete" fix and is forbidden precisely because it is tempting — it would create a durable, gate-readable `approved` transition before the verdict payload backing it exists, inverting spec.md US1 Acceptance Scenario 3 under FR-001's authority split. Mitigate by treating T048's call order as fixed and building only the revert-compensator; do not prototype or partially land a reorder.
- **Two independently-designed durability signals (T049, T050) that don't compose**: since both subtasks add machine-readable non-durability signals to the same `--json` envelope, landing them independently risks two overlapping-but-inconsistent keys. Resolve the "shared key + reason field" vs. "two separate keys" design question once, across both subtasks, before either lands.
- **WP06 extraction not yet complete / not matching assumed shape**: this WP's `owned_files` names `tasks_verdict_persistence.py`, which does not exist until WP06 lands. If WP06's actual extraction shape differs materially from what this prompt assumes (different function names, different call signatures), re-derive the correct call sites from WP06's actual diff rather than forcing this WP's design onto a shape WP06 did not produce.

## Reviewer Guidance

- Confirm T047's reproduction test asserts on recorded state, not just exit code — this is the single most important thing to check in this WP's review.
- Confirm the fix (T048) is a genuine revert-compensator (write-then-emit order preserved, active uncommit-and-delete on emit failure) — not a guard-logic patch alone that leaves the orphan-then-no-op-retry shape intact under a different disguise, and not an emit-first reorder, which is forbidden.
- Confirm the `--json` payload for BOTH the `--no-auto-commit` case (T049) and the protected-primary-coord case (T050) is populated, human-readable-console-consistent, and — per the design resolution above — either shares one key with a distinguishing reason field or uses two clearly-named separate keys, not an ad hoc mix.
- Confirm the protected-primary-coord crash (T050) is reproduced FIRST as a red test before the fix, matching this WP's other subtasks' ATDD discipline.
- Confirm no C-002-protected behaviour (content-identity, compensator, two-leg writer) regressed as a side effect of the new revert-compensator — re-run the three pinned regression tests explicitly, don't just trust the full-suite green.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-08-03T08:13:56Z – system – lane=planned – Prompt created.

- 2026-08-04T00:00:00Z – claude – lane=doing – T047: wrote red-first reproduction
  (`test_move_task_durability.py`, real git fixture, real `RealCoordCommitRouter.
  commit_artifact`) of a transition-emit failure leaving a COMMITTED
  `verdict: approved` orphan for a WP still `in_review` — confirmed via
  `git log`/`git status`, not file existence. Empirically DISPROVED the
  Objective section's retry claim: an identical retry's transition-emit is
  INDEPENDENT of the artifact no-op guard and DOES move the lane to approved;
  rewrote the second reproduction to the verified bug instead (a retry with a
  DIFFERENT `--approval-ref` silently keeps the failed first attempt's stale
  reference even though the lane moves to approved).
- 2026-08-04T00:00:00Z – claude – lane=doing – T048 (revert-compensator):
  investigated and determined this is NOT deliverable inside `owned_files`.
  The write (`_mt_finalize_plan`) and the transition emit (`_mt_execute`) are
  both orchestrated from `_do_move_task` in `tasks_move_task.py`, which WP11
  does not own; there is no existing hook this module can use to be notified
  of a later `_mt_execute` failure. Per the "STOP and report" rule, did not
  edit `tasks_move_task.py`. NOT DONE — escalated in the WP11 report.
- 2026-08-04T00:00:00Z – claude – lane=doing – T050: fixed the protected-
  primary-coord crash. Added `_resolve_verdict_commit_router` /
  `VerdictDurabilitySignal` to `tasks_verdict_persistence.py`; both call sites
  now gate `commit_router` on `resolved_auto_commit and not
  skip_target_branch_commit`, mirroring `tasks_move_task.py`'s status-event
  gate. Red-first crash reproduced by inlining the pre-fix expression
  (`test_pre_fix_naive_commit_router_gating_crashes_on_protected_target_branch`),
  green confirmed for both approval and rejection call sites.
- 2026-08-04T00:00:00Z – claude – lane=doing – T049: added the console notice
  (`_announce_verdict_durability_gap`) for the `--no-auto-commit` case,
  suppressed under `--json`. The `--json` KEY itself is NOT wired: `_mt_output`
  (the function that builds the `result` dict) and `_MoveTaskState`'s field
  list both live in `tasks_move_task.py`, outside `owned_files`. Computed and
  returned `VerdictDurabilitySignal` from both writers for direct testability;
  full CLI wiring escalated in the WP11 report.
- 2026-08-04T00:00:00Z – claude – lane=doing – Cross-check: verdict-seam
  census (`tests/architectural/test_verdict_seam_census.py`, incl.
  `test_derived_census_matches_fixture`) stayed GREEN with no fixture edit —
  the new helpers did not trip the one-hop-closure classifier.
- 2026-08-04T00:00:00Z – claude – lane=doing – Ownership widened by the
  coordinator to include `tasks_move_task.py` for exactly two purposes
  (`DM-01KZ6JE62Q6CQ24DMBX8KZZ5R9`). T048 landed: added
  `VerdictDurabilitySignal.artifact_path`/`cycle_number` +
  `revert_committed_verdict_write`/`VerdictRevertError` to
  `tasks_verdict_persistence.py`; `_mt_finalize_plan` now captures the
  writer's return onto a new `_MoveTaskState.pending_verdict_write` field;
  `_do_move_task` wraps `_mt_execute` in-line (not a new named helper — a new
  top-level symbol in `tasks_move_task.py` would also need a row in
  `test_tasks_compat_surface.py`'s consolidated re-export guard plus a
  `tasks.py` re-export, a third file outside the two named purposes) so a
  transition-emit failure reverts the already-committed write before the
  error propagates. `_mt_output` now surfaces `verdict_durably_persisted` /
  `verdict_durability_skip_reason` in the `--json` envelope (T049/T050's
  wiring). The no-op guard needed NO independent patch — confirmed correct
  by construction once no orphan survives.
  Both T047 tests reshaped to the GREEN outcome (compensator lands): no
  readable committed verdict survives a failed transition
  (`latest_review_artifact_verdict` + `git cat-file -e HEAD:<path>`), and the
  retry with its own `--approval-ref` now records the real approval (no
  orphan left to fall back on). `revert_committed_verdict_write` initially
  used `ports.coord.commit_artifact` (mirroring the original write) — this
  FAILED for real (`no_op_wrong_surface`: that port pre-checks the artifact
  exists, refusing a deletion) and was corrected to `specify_cli.git.
  safe_commit` directly, resolving the destination via
  `mission_runtime.placement_seam(...).write_target(kind)` (not
  `CommitTarget(ref=st.target_branch)` — that hand-built form tripped two
  architectural gates, `test_no_write_side_rederivation.py` /
  `test_safe_commit_import_boundary.py`, both fixed).
  Two disclosed cross-boundary fixes, both legitimate regressions from this
  diff, neither part of the two named purposes: (1)
  `tests/architectural/census/verdict_seam_IC01.yaml` gained one `writer` row
  for `revert_committed_verdict_write` (a real new git-commit call site,
  correctly flagged by the one-hop closure — added per the WP01 census's
  standing precedent); (2)
  `tests/specify_cli/cli/commands/agent/test_tasks_move_task_seam.py`'s
  `test_persist_rejected_review_cycle_for_rollback_writes_and_updates_state`
  had a `SimpleNamespace` mock missing the two new fields
  `persist_rejected_review_cycle_for_rollback` now reads
  (`artifact_path`/`artifact.cycle_number`) — two fields added to the fake.
---

### Updating Lane Status

Use: `spec-kitty agent tasks move-task WP11 --to <lane> --note "message"`

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
