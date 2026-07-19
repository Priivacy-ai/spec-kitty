---
work_package_id: WP01
title: Real CLI stale-workspace witness
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-007
- FR-008
- FR-009
- NFR-001
- NFR-004
- C-004
- C-005
- C-006
- C-007
tracker_refs: []
planning_base_branch: fix/stale-workspace-reproduction
merge_target_branch: fix/stale-workspace-reproduction
branch_strategy: Planning artifacts for this mission were generated on fix/stale-workspace-reproduction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/stale-workspace-reproduction unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Reproduction and disposition
assignee: ''
shell_pid_created_at: "1784023781.31"
agent: "codex"
shell_pid: "138606"
history:
- timestamp: '2026-07-14T00:00:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks-packages
agent_profile: debugger-debbie
authoritative_surface: tests/specify_cli/cli/commands/agent/
create_intent:
- tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py
execution_mode: code_change
model: ''
owned_files:
- tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before inspecting code, changing the fixture, or running the witness, load the
debugger profile:

```text
/ad-hoc-profile-load debugger-debbie
```

Use that profile for evidence-led reproduction. Do not begin production work in
this WP. The purpose is to establish current-base code truth through supported
operator entry points and record a disposition that governs later WPs.

## Objective

Build a deterministic, real-Git, real-CLI witness for issue #2626 that exercises
`mark-status`, `move-task`, and `agent action review` against healthy and stale
lane-workspace states. Record every entry-point/state result across the complete
consistency boundary, then authorize later production work only for rows that are
genuinely RED on the pinned planning base.

## Context

The historical report describes persisted lane metadata that points to a missing
worktree after coordination-branch recreation. A command may crash, mutate status
before failing, or report success while leaving tracking writes uncommitted. The
current planning base already contains partial recovery coverage, so the Mission
must not assume the old defect still exists.

This WP is the Mission's evidence gate. It owns only
`tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py`.
Return the completed disposition matrix verbatim in the implementation handoff;
after review, the orchestrator persists it as a PRIMARY planning artifact through
`spec-kitty spec-commit`. Do not edit any file under `kitty-specs/` from the
implementation lane.

Do not modify production code, `wps.yaml`, another WP prompt, existing test
modules, or generated agent copies. If the fixture exposes a helper need, keep it
inside the owned test module. A helper may orchestrate canonical serializers and
real Git commands, but it may not replace a production resolver or command seam.

The planning and merge target is `fix/stale-workspace-reproduction`. Start the WP
only through the canonical implementation action so Spec Kitty resolves the lane
workspace and branch:

```bash
spec-kitty agent action implement WP01 --agent <name> --mission stale-workspace-reproduction-recovery-01KXGR6S
```

Run all implementation commands from the resolved lane workspace returned by
Spec Kitty. Do not manually reconstruct its path, create an ad-hoc worktree, or
implement directly in the repository root checkout.

The witness is acceptance-test-first evidence. Commit the test-only witness
before any later Mission production commit. For each exact row, preserve the
observed planning-base verdict even if that verdict is GREEN/already-correct.

### Subtask T001: Build the realistic repository fixture and healthy controls

**Purpose**: Create one reusable fixture that models the actual Mission, lane,
coordination, placement, and persisted-workspace authorities without mocking the
behavior under test. Pair every stale row with a healthy positive control so a
failure cannot be explained by a broken fixture.

**Steps**:

1. Create
   `tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py`.
   Mark it for the CI slice used by the registered CLI tests, following nearby
   test-module marker conventions rather than inventing a new marker.
2. Initialize a real temporary Git repository through existing test utilities
   where suitable, while keeping all Git state genuine:
   - configure a local test identity;
   - create and commit the minimal project/Mission files needed by the commands;
   - create the planning/primary ref, coordination ref, and lane ref;
   - create genuine coordination and lane worktrees for the healthy baseline;
   - avoid assuming `main` as a generic default branch name.
3. Give the temporary Mission a coordination topology equivalent to
   `lanes_with_coord`, including canonical `meta.json`, lane membership, status
   event history/materialization, task tracking, and WP prompt inputs required by
   the registered command paths.
4. Persist the workspace context using the canonical serializer and the reported
   relative `.worktrees/...` shape. The recorded path must initially name the
   genuine lane worktree; stale variants remove the directory without rewriting
   the record.
5. Seed command-specific prerequisites without bypassing runtime validation:
   - a pending `T001` tracking item for `mark-status`;
   - WP01 in `in_progress`, completed subtasks, an implementation commit, and
     satisfied dependencies for `move-task`;
   - WP01 in `for_review`, an implementation commit, and materialized
     coordination status for review.
6. Provide fixture functions that snapshot repository state before and after one
   invocation. Keep setup data stable, explicit, and small enough for failures to
   show meaningful diffs.
7. Add healthy positive-control tests for each entry point before evaluating
   stale variants. Healthy controls must prove the command is registered, the
   fixture is valid, and expected canonical placement commits can land.
8. Isolate HOME/XDG/config/cache state using test fixtures. Cache clearing before
   the CLI invocation is allowed; replacing production lookup results is not.

**Files**:

- Create
  `tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py`
  (expected complete module size: approximately 450-750 lines; this subtask owns
  the shared fixture portion).

**Validation**:

- Healthy controls reach the intended registered commands and produce the
  expected durable outcome.
- The fixture contains real refs and real Git worktrees, not ordinary directories
  standing in for worktrees.
- Persisted workspace JSON retains a relative `.worktrees/...` path.
- Repeated fixture setup produces the same classification and no timing-only
  assertions.

### Subtask T002: Pin exact registered CLI invocations and prerequisites

**Purpose**: Ensure the witness enters through the same public command surface an
operator uses and cannot false-green by calling helper functions directly.

**Steps**:

1. Invoke commands through the repository's registered Typer application and its
   normal root/mission discovery. Do not call command callbacks, workflow helpers,
   status emitters, workspace resolvers, or lifecycle functions directly.
2. Pin the exact `mark-status` argv:

   ```text
   agent tasks mark-status T001 --status done --mission <slug> --json
   ```

   Prerequisites: `tasks.md` contains pending T001; Mission identity and PRIMARY
   task placement resolve normally. The stale lane context exists as a negative
   control and must not cause lane-workspace resolution or status/lane deltas.
3. Pin the exact `move-task` argv:

   ```text
   agent tasks move-task WP01 --to for_review --mission <slug> --agent codex --json
   ```

   Prerequisites: WP01 is `in_progress`; every subtask is complete; a genuine
   implementation commit exists on the lane ref; dependencies are satisfied;
   the event log and materialized state agree before invocation.
4. Pin the exact review argv:

   ```text
   agent action review WP01 --agent codex --mission <slug>
   ```

   Prerequisites: WP01 is `for_review`; a genuine implementation commit exists;
   coordination topology and status are materialized; persisted context selects
   the tested lane.
5. Use the temporary Mission's actual slug in place of `<slug>`. Preserve the
   token ordering above so the recorded argv and disposition matrix are directly
   comparable.
6. Capture exit code, stdout, and stderr for every invocation. JSON-mode stdout
   must parse as exactly one document; human-mode output must be preserved for
   diagnostic assertions.
7. Add a fixture-integrity assertion immediately before invocation. It must prove
   each prerequisite, expected ref, worktree state, and persisted-context value
   so an accidental setup drift fails with a fixture-specific message.

**Files**:

- Modify only the owned witness test module.

**Validation**:

- Every row records its exact argv and prerequisite classification.
- No test reaches a private callback or helper as a substitute for the CLI.
- JSON output is parsed as one document, with no unrelated stdout prefix/suffix.
- The healthy twin for each argv succeeds before its stale-state verdict is used.

### Subtask T003: Exercise all four workspace classifications per entry point

**Purpose**: Separate healthy, recoverable, unavailable, and divergent states so
the Mission does not treat three commands as one authority or convert an
already-correct path into speculative production scope.

**Steps**:

1. Parameterize or otherwise make explicit these four rows:

   | Row | Lane branch | Lane worktree | Persisted context | Classification |
   |---|---|---|---|---|
   | healthy | exists and agrees | exists | agrees | ready |
   | recoverable husk | exists and agrees | absent | agrees | recoverable |
   | unavailable authority | absent | absent | names expected lane | unavailable |
   | divergent authority | exists or absent | either | branch/lane disagrees with current assignment | divergent |

2. Create the healthy state first, then derive stale states using real Git
   operations. Removing a lane worktree must leave the persisted relative record
   unchanged. Do not simply point the record at an arbitrary malformed path.
3. For the recoverable-husk row, retain the agreeing canonical lane branch after
   the lane worktree is removed. Accept either successful canonical recreation or
   a truthful existing refusal only if it satisfies the Mission contract.
4. For unavailable authority, remove both the lane worktree and lane branch while
   leaving the stale record. Expect non-zero refusal before mutation whenever the
   entry point requires workspace readiness.
5. For divergence, make persisted branch/lane identity disagree with current lane
   assignment. Expect fail-closed behavior; the runtime must not choose whichever
   branch or directory happens to exist.
6. Preserve entry-point ownership distinctions:
   - `mark-status` is workspace-free and must remain the negative control;
   - `move-task` may require workspace readiness for its existing deliverable and
     pre-review checks, but must not gain a new global resolver;
   - review requires a ready workspace before its durable claim mutation.
7. If some workspace rows are not semantically applicable to an entry point,
   record them explicitly as negative-control outcomes rather than silently
   omitting them. The disposition matrix must still explain why the stale record
   is irrelevant or which owner was reached.
8. Keep diagnostic latency deterministic. For unavailable/divergent refusal,
   measure elapsed time with a generous stable upper assertion tied to NFR-004;
   do not use sleeps, races, or polling as the proof mechanism.

**Files**:

- Modify only the owned witness test module.

**Validation**:

- All four classifications are constructed and asserted from branch, worktree,
  persisted-context, and current-lane facts.
- The recoverable row retains its branch; the unavailable row proves it absent.
- The divergent row proves an identity disagreement rather than malformed input.
- No row bypasses dependency, review, or transition guards to reach a preferred
  result.

### Subtask T004: Capture the six consistency surfaces and commit path sets

**Purpose**: Make partial success and wrong-placement commits observable. A clean
porcelain or expected file bytes alone is insufficient evidence because a commit
may have landed on the wrong ref or a status event may have been partially
materialized.

**Steps**:

1. Define one before/after observation record containing all six surfaces:
   1. command exit/result plus stdout/stderr or JSON envelope;
   2. `status.events.jsonl` bytes plus reduced/materialized lane state;
   3. WP prompt and `tasks.md` tracking bytes;
   4. PRIMARY, COORD, and lane ref OIDs plus every new commit's changed path set;
   5. lock-file state and tested missing-path/worktree existence;
   6. porcelain for the repository root checkout and every relevant worktree.
2. Snapshot refs by explicit role, not current checkout coincidence. Record the
   exact OID before and after each invocation for PRIMARY, COORD, and lane refs.
3. For every non-empty OID range, enumerate every new commit in order and capture
   its changed path set. Assert canonical placement:
   - PRIMARY owns task/WP tracking;
   - COORD owns status events/materialization in coordinated topology;
   - lane owns implementation evidence, not tracking fallback commits.
4. For refusal rows, require empty OID ranges on every role. Byte-equivalent files
   are not enough: no compensating commit pair may hide a mutation.
5. For successful rows, assert every intended mutation is committed and all
   relevant checkouts are clean. Reject success combined with a warning about an
   uncommitted tracking write.
6. For review refusal, compare exact before/after event bytes, materialized status,
   WP/tracking bytes, OIDs, locks, path existence, and porcelain. There must be no
   `for_review -> in_review` claim if readiness cannot be established.
7. For JSON entry points, assert the envelope's status agrees with exit code and
   durable state. For human review, assert raw `FileNotFoundError` and misleading
   paths are absent; any refusal must name the missing workspace/lane, missing
   path, and a supported recovery action.
8. Observe production behavior without production monkeypatches. Prohibited
   patches include any production symbol, Git/subprocess call, root/target
   discovery, placement resolver, workspace resolver, lifecycle sync, commit
   router, status path, or CLI registration. Allowed test controls are canonical
   fixture serialization, environment isolation, and cache clearing before CLI
   entry.
9. Add an explicit test guard or clear fixture architecture that makes the
   no-production-monkeypatch rule reviewable. Prefer direct imports only for data
   inspection after the command, never to replace runtime behavior.

**Files**:

- Modify only the owned witness test module.

**Validation**:

- Every asserted success has expected OID movement, exact committed path sets,
  and clean porcelain.
- Every asserted refusal has zero OID movement and byte-identical durable state.
- Six surfaces are captured together for each disposition row.
- Searches of the test module show no monkeypatch of production resolution,
  subprocess, placement, lifecycle, commit, status, or CLI symbols.

### Subtask T005: Publish the disposition matrix and enforce the RED gate

**Purpose**: Convert raw witness results into the authoritative implementation
decision for the orchestrator checkpoint. Production changes are allowed only
after independent review, an orchestrator `spec-kitty spec-commit`, and a
row-specific `RED/continue` verdict; already-correct behavior is documented and
stopped.

**Steps**:

1. Construct the disposition matrix as structured handoff evidence. Do not write
   under `kitty-specs/` from the implementation lane. State the exact planning-base
   commit SHA and focused witness command used to generate results; the orchestrator
   will persist the reviewed matrix afterward.
2. Add one row for every entry-point/workspace-state combination exercised. Each
   row must record:
   - entry point and exact argv;
   - prerequisite facts;
   - workspace classification;
   - planning-base SHA;
   - RED or GREEN verdict;
   - exit/result and structured-output outcome;
   - six-surface before/after delta summary;
   - PRIMARY, COORD, and lane OID movement;
   - changed path sets for every new commit;
   - existing owner reached;
   - `stop` or `continue` disposition.
3. Define verdicts precisely:
   - **GREEN/stop**: behavior already satisfies the transition contract; no
     production change is authorized for that row;
   - **RED/continue**: current behavior violates an explicit contract assertion;
     name the failing assertion and the existing owning seam reached by the CLI;
   - fixture/setup failure: neither RED nor GREEN; repair the witness and rerun.
4. If all rows are GREEN, state that WP02, WP03, and WP04 production implementation
   must remain no-op unless their prompts contain independently activated evidence
   work. Do not
   manufacture a fix to make the Mission look substantive.
5. If verdicts are mixed, identify only the RED/continue rows and their proven
   owners. Do not generalize one review failure into `mark-status` or `move-task`.
6. If the review WP/status bundle is proven to commit on the wrong authority,
   label that exact row as a #2160-adjacent residual before production editing.
   Keep #2160 reference-only; do not claim, close, or silently absorb its broader
   scope.
7. Record #2367 as reference-only unless the witness proves the same owning seam.
   Any ownership coordination belongs in the DRAFT PR, not an additional issue
   comment.
8. Run the witness at least twice from clean fixture instances. Results must be
   identical in classification and verdict; normalize only inherently variable
   temporary paths/timestamps in presentation, never in assertions that matter.
9. Commit the complete test-only witness as the WP's RED evidence commit and
   include the full matrix in the handoff. If relevant rows are RED, preserve the
   exact commit so reviewers can prove RED on the planning base and GREEN only
   after later WPs.

**Files**:

- Finalize the sole owned witness test module.
- Return the disposition matrix in the implementation handoff (expected 80-180
  lines, depending on row count and evidence density); the orchestrator owns its
  independently reviewed, durable `spec-kitty spec-commit` checkpoint.

**Validation**:

- Run the focused witness twice:

  ```bash
  PWHEADLESS=1 uv run --extra test pytest tests/specify_cli/cli/commands/agent/test_stale_workspace_transition_contract.py -q --tb=short
  ```

- Confirm every row has a baseline SHA, exact argv, prerequisites, classification,
  verdict, six-surface delta, owner, and `stop`/`continue` decision.
- Confirm production changes are not authorized by GREEN/stop rows.
- Confirm the handoff matrix contains no unsupported claim that #2160 or
  #2367 is closed by this Mission.

## Definition of Done

- [ ] `/ad-hoc-profile-load debugger-debbie` was loaded before implementation.
- [ ] WP01 was started with `spec-kitty agent action implement`, and work occurred
      in the resolved lane workspace.
- [ ] Planning base and merge target remain
      `fix/stale-workspace-reproduction`.
- [ ] The owned test module builds a real Git repository with genuine primary,
      coordination, and lane refs/worktrees.
- [ ] Healthy positive controls pass for all three registered CLI entry points.
- [ ] Exact argv and prerequisites are pinned for `mark-status`, `move-task`, and
      `agent action review`.
- [ ] Ready, recoverable, unavailable, and divergent workspace rows are covered.
- [ ] Every row captures exit/output, event/materialized status, tracking bytes,
      OIDs/commit path sets, locks/path state, and all relevant porcelain.
- [ ] No production symbol, Git/subprocess boundary, resolver, placement,
      lifecycle, commit/status seam, or CLI entry point is monkeypatched.
- [ ] JSON stdout is exactly one parseable document and agrees with durable state.
- [ ] Successful rows leave intended writes committed at canonical placements and
      every relevant checkout clean.
- [ ] Refusal rows show zero durable delta, zero ref movement, no leaked lock or
      invocation-created path, and actionable diagnostics.
- [ ] The witness produces repeatable results across two clean runs.
- [ ] The handoff matrix records every required evidence field and an explicit
      `stop`/`continue` decision per row.
- [ ] Production implementation is authorized only by RED/continue rows.
- [ ] Only the sole declared `owned_files` test module was changed.
- [ ] The test-only RED evidence is committed separately before any later Mission
      production commit.

## Risks

- **Fixture false-green**: a helper-level call could bypass the bug. Mitigate by
  entering only through registered Typer argv and proving healthy controls.
- **Mocked authority**: patching Git, placement, or workspace resolution could
  predetermine the outcome. Mitigate with real repositories/worktrees and the
  explicit prohibition checklist.
- **Wrong-placement blindness**: clean files can hide commits on the wrong ref.
  Mitigate by recording before/after OIDs and every commit's path set by role.
- **Speculative scope growth**: one RED could be generalized across commands or
  adjacent issues. Mitigate with per-row owners and `stop`/`continue` decisions.
- **Platform/timing flake**: filesystem races could make the witness unreliable.
  Mitigate by deterministic Git operations, path-neutral assertions, and no
  sleeps or timing-only success conditions.
- **Fixture cost**: a full matrix of real repositories is slower than unit tests.
  Keep one reusable fixture architecture, focused data, and the single declared
  test module while preserving isolation per invocation.

## Reviewer Guidance

Review this WP as an evidence gate, not as a production fix. Confirm first that
the test reaches the registered CLI and that no production behavior is patched
away. Independently inspect the fixture's refs, worktrees, persisted relative
path, lane assignment, and command prerequisites.

For at least one success and one refusal row, manually trace all six observation
surfaces. Verify that ref OIDs and changed path sets prove placement rather than
assuming it from porcelain. A refusal must have an empty commit range and exact
before/after bytes; a success must have all intended commits and no dirt.

Compare the disposition matrix to the test parameters row by row. Reject missing
states, generalized owners, unrecorded fixture failures, or production work
authorized by GREEN behavior. If a RED is claimed, reproduce it on the pinned
planning base with the exact focused command and verify that the failing assertion
expresses the Mission contract rather than an incidental fixture detail.

Finally, confirm the diff contains only the sole owned path, the witness commit is
test/evidence-only, and later WPs can use the matrix without reinterpreting the
historical issue report.

## Activity Log

- 2026-07-14T16:52:57Z – codex – shell_pid=138606 – Assigned agent via action command
- 2026-07-14T17:09:23Z – codex – shell_pid=138606 – Ready for review: deterministic real-CLI stale-workspace witness; RED evidence preserved in 1902ce530
- 2026-07-14T17:10:34Z – codex – shell_pid=138606 – Started review via action command
- 2026-07-14T17:17:25Z – user – Moved to planned
- 2026-07-14T17:19:00Z – codex – shell_pid=138606 – Started implementation via action command
- 2026-07-14T17:29:54Z – codex – shell_pid=138606 – Moved to for_review
- 2026-07-14T17:30:42Z – codex – shell_pid=138606 – Started review via action command
- 2026-07-14T17:38:21Z – user – shell_pid=138606 – Arbiter override: cycle-1 rejection resolved by ff7eca5e2. Cycle-2 independent review proved real registered CLI/Git fixture; unverified_baseline occurs only after scoped test ran; all 12 rows assert exact argv/result, six surfaces, and path sets; unavailable/divergent <2s; two exact runs stable at 5 GREEN/stop + 7 RED/continue on planning base 2d05c53d0.
