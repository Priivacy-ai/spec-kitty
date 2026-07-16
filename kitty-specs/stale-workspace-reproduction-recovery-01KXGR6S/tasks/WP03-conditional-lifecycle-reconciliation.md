---
work_package_id: WP03
title: Conditional lifecycle reconciliation
dependencies:
- WP02
requirement_refs:
- FR-003
- FR-005
- FR-006
- FR-008
- FR-009
- NFR-002
- NFR-003
- NFR-004
- C-001
- C-004
- C-005
- C-006
- C-008
tracker_refs: []
planning_base_branch: fix/stale-workspace-reproduction
merge_target_branch: fix/stale-workspace-reproduction
branch_strategy: Planning artifacts for this mission were generated on fix/stale-workspace-reproduction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/stale-workspace-reproduction unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
agent: "codex"
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/lanes/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/lanes/lifecycle_sync.py
- tests/integration/test_lane_lifecycle_sync.py
role: implementer
tags: []
shell_pid: "138606"
shell_pid_created_at: "1784023781.31"
---

# Work Package Prompt: WP03 – Conditional Lifecycle Reconciliation

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load python-pedro` before reading or changing anything else,
and behave according to that profile's guidance for the rest of this work package.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

Do not substitute an informal persona for the profile load. If the named profile
cannot be loaded, stop and report the profile-resolution failure to the
orchestrator rather than implementing without governance.

---

## Objective

Consume the committed, independently reviewed disposition checkpoint and change the lane lifecycle seam
only when it records a lifecycle/reconciliation row RED. For an activated RED, make
the existing canonical lifecycle owner classify the already-resolved workspace
as ready, recoverable, unavailable, or divergent before any missing-directory
`cwd` probe, while preserving the same workspace identity throughout the call.

An already-green lifecycle disposition is a valid completion: make no production
or test edits, record the no-op evidence in the WP handoff, and send WP03 directly
to independent review.

## Context

GitHub issue #2626 reports that persisted lane-workspace metadata can outlive its
worktree directory. The Mission is deliberately reproduction-first. WP01 owns the
real CLI witness; the orchestrator persists its independently reviewed result in
`disposition-matrix.md`. WP03 does not reinterpret, broaden, or replace that
evidence. It consumes only rows whose reached owner is the lane
lifecycle/reconciliation seam and whose disposition says `RED` plus `continue`.

The architecture already has a canonical workspace resolver and a canonical lane
lifecycle implementation. This WP must not create a resolver, reconstruct a path
or branch at a command call site, delete stale context, create arbitrary branches,
or fall back to the primary checkout. A persisted workspace record is evidence,
not authority. Current lane assignment and branch inventory determine whether the
same resolved identity is ready, recoverable, unavailable, or divergent.

The branch contract is fixed for this Mission:

- Planning base branch: `fix/stale-workspace-reproduction`
- Merge target branch: `fix/stale-workspace-reproduction`
- Branch strategy: implementation occurs only in the workspace returned by the
  canonical Spec Kitty implementation action and merges back to that target.
- DRAFT boundary: PR #2641 stays DRAFT; the human operator alone may mark it ready
  or merge it.

Prepare and enter the execution workspace with:

```bash
spec-kitty agent action implement WP03 --agent codex
```

Treat the command's returned workspace path and branch as the resolved lane
workspace contract. Run every edit, test, and commit from that returned workspace.
Do not guess a `.worktrees/...` directory, create a worktree manually, or continue
from the repository root checkout. Before editing, verify that the current branch
and workspace match the returned contract and that WP02 is approved or done.

WP03 owns exactly:

- `src/specify_cli/lanes/lifecycle_sync.py`
- `tests/integration/test_lane_lifecycle_sync.py`

Do not edit `wps.yaml`, WP01's witness, `disposition-matrix.md`, workspace resolver
modules, workflow call sites, Mission metadata, or unrelated tests. WP04 owns any
review-call-site wiring needed after this seam has an evidence-backed contract.

### Mandatory decision gate

Before selecting a code path, extract the following from the committed, independently reviewed disposition for
each lifecycle-owned row:

1. Baseline commit and exact registered CLI command.
2. Workspace state: healthy, matching-branch/missing-worktree, branch absent, or
   persisted-context divergent.
3. RED/GREEN result across the six observed consistency surfaces.
4. Reached existing owner.
5. Explicit `stop` or `continue` verdict.

Use this decision table without inference:

| WP02 result | WP03 action |
|---|---|
| All lifecycle-owned rows are GREEN/stop | No-op; preserve both owned files byte-for-byte and report evidence. |
| A row is RED/continue but owner is not `lifecycle_sync.py` | No-op here; return it to the orchestrator for the owning WP. |
| A lifecycle-owned row is RED/continue | Activate T012–T015 only for the proven state and behavior. |
| Evidence is missing, ambiguous, or only helper-level | Stop; do not authorize production changes. |

The GREEN/stop path is not an incomplete implementation. It is the required
FR-003 outcome when current code already satisfies the exact production-shaped
contract.

### Subtask T011: Consume the reviewed disposition and select no-op or remediation

**Purpose**: Enforce the reproduction-first boundary before any production edit.
The result of this subtask decides whether the remaining subtasks are evidence-only
or an activated RED→GREEN implementation sequence.

**Steps**:

1. Confirm WP02 is approved or done using the canonical task status surface.
   Do not rely only on the presence of a file or a verbal summary.
2. Read the committed, independently reviewed disposition matrix from the Mission planning surface.
   Locate every row that reached lane lifecycle or reconciliation behavior.
3. Cross-check each row against the contract's four states:
   - agreeing branch and present worktree: `ready`;
   - agreeing existing branch and absent worktree: `recoverable`;
   - absent authoritative branch and absent worktree: `unavailable`;
   - persisted identity disagreement: `divergent`.
4. Confirm that any claimed RED records the full six-surface delta and an exact
   command. A raw helper exception or mocked seam is insufficient authorization.
5. Record one of two WP handoff decisions:
   - `NO-OP/GREEN`: list the baseline, rows, commands, and GREEN/stop verdicts;
   - `ACTIVATED/RED`: list only the RED/continue rows owned by this WP.
6. On `NO-OP/GREEN`, compare both owned files before and after to prove they are
   byte-identical, run no formatting command, create no empty cleanup commit, and
   skip all production-edit steps in T012–T014; T015 still runs the no-op
   verification and handoff.
7. On `ACTIVATED/RED`, preserve the exact failing assertion as the acceptance
   witness. Do not weaken it, replace it with a helper-only test, or extend scope
   to an adjacent issue.
8. If the disposition points to #2160, #2367, or another owner without proving
   this exact seam, notify the orchestrator. Do not claim or absorb that issue.

**Files**:

- Read only: the orchestrator-committed reviewed disposition, WP01 witness, and
  Mission contract artifacts.
- On the no-op path: no files modified.
- On the activated path: subsequent subtasks may modify only the two owned files.

**Validation**:

- The handoff names the exact reviewed matrix row and one unambiguous decision.
- `git diff -- src/specify_cli/lanes/lifecycle_sync.py tests/integration/test_lane_lifecycle_sync.py`
  is empty on the no-op path.
- No production commit exists unless a lifecycle-owned RED/continue row exists.

### Subtask T012: Add canonical readiness classification only for a proven RED

**Purpose**: If and only if T011 activates remediation, close the demonstrated
lifecycle defect by classifying readiness before cwd-bound Git work. Keep the
classification inside the existing authority rather than creating a second
resolver or general recovery service.

**Steps**:

1. Add a focused failing integration test to
   `tests/integration/test_lane_lifecycle_sync.py` for each activated state. Commit
   the test-only RED before changing production code.
2. Build the fixture with a real temporary Git repository, real refs, canonical
   lane serialization, and genuine worktree operations. Do not monkeypatch Git,
   subprocess, root resolution, lifecycle sync, or workspace resolution.
3. Prove the test fails on `fix/stale-workspace-reproduction` at the recorded
   planning-base commit for the same reason as WP01's RED.
4. Reuse the existing lifecycle and workspace data structures. If a small local
   enum/dataclass is necessary to make the existing seam explicit, keep it within
   `lifecycle_sync.py`, expose only what the proven consumer needs, and avoid a
   new resolution authority.
5. Classify using the already-resolved branch/path/lane identity plus real branch
   inventory:
   - `ready`: agreeing branch and valid worktree exist;
   - `recoverable`: agreeing branch exists but worktree is absent;
   - `unavailable`: the authoritative branch needed for recovery is absent;
   - `divergent`: persisted and current assignment identities disagree.
6. Ensure classification is non-mutating. It must occur before `git worktree add`,
   auto-rebase, status mutation, tracking writes, lock creation, or a subprocess
   whose `cwd` is the absent worktree.
7. Preserve existing healthy behavior and existing matching-branch recovery. A
   recoverable classification may invoke the existing worktree lifecycle only;
   it may not make directories as a substitute for `git worktree add`.
8. For unavailable or divergent classifications, raise/return the existing
   structured lifecycle refusal shape extended only as required by the RED.
9. Keep `status.events.jsonl` as the sole lane-state authority and preserve
   PRIMARY/COORD artifact placement. This WP does not commit tracking artifacts.
10. Do not add a primary-checkout fallback, synthesize a missing branch, delete or
    rewrite persisted context, or treat whichever path exists as authoritative.

**Files**:

- `tests/integration/test_lane_lifecycle_sync.py`: focused real-Git RED and healthy
  positive controls; keep additions proportional to activated rows.
- `src/specify_cli/lanes/lifecycle_sync.py`: minimal classification/refusal change
  only after the RED commit exists.

**Validation**:

- The exact activated test is RED at the test-only commit and GREEN after the
  production commit.
- Existing clean rebase, missing-worktree recovery, and conflict-preservation
  tests remain green.
- Unavailable/divergent cases perform no Git command with the absent path as cwd.

### Subtask T013: Thread one resolved identity through lifecycle operations

**Purpose**: Prevent path/branch disagreement and raw missing-cwd failures by using
one canonical resolved workspace identity from classification through readiness,
recovery, and auto-rebase.

**Steps**:

1. Trace the activated call from its existing resolved workspace input into
   `sync_lane_after_coordination_commit`; document where path, branch, lane, and
   execution mode currently originate.
2. Prefer accepting or consuming the existing `ResolvedWorkspace` identity (or
   the narrow existing equivalent already passed by the owner) over recomputing
   `_worktree_path` or `lane_branch_name` from `lanes.json`.
3. Do not call `resolve_workspace_for_wp` inside lifecycle sync. Resolution belongs
   to the canonical caller and must happen once before durable mutation.
4. Use the resolved identity unchanged for:
   - readiness classification;
   - branch existence checks;
   - supported worktree reattachment/recreation;
   - auto-rebase invocation;
   - structured error fields.
5. If call-site wiring is required outside this WP's owned files, stop at the
   narrow lifecycle contract and give WP04 an exact signature/behavior handoff.
   Do not edit `workflow.py` or `workflow_executor.py` from this lane.
6. Order every repository-root Git probe before any worktree-cwd probe. Never pass
   an absent or husk directory as `subprocess.run(..., cwd=...)`.
7. Retain platform-neutral `pathlib.Path` and argument-list subprocess use. Do not
   compare paths by hard-coded separator, shell quoting, or POSIX-only string form.
8. Preserve mission-ID-aware branch identity. Do not fall back to an older branch
   name merely because its ref happens to exist if it disagrees with the resolved
   current assignment.
9. Add an assertion that an activated refusal preserves refs, path existence, and
   porcelain, not merely that an exception was raised.

**Files**:

- `src/specify_cli/lanes/lifecycle_sync.py`: reuse/thread the supplied identity;
  no new resolver module.
- `tests/integration/test_lane_lifecycle_sync.py`: identity and no-missing-cwd
  proof through real Git behavior.

**Validation**:

- One identity determines every path/branch field in the resulting report/error.
- No lifecycle path recomposes a competing branch or workspace for activated rows.
- A branch-absent state refuses before any worktree creation or cwd-bound probe.
- A divergent state does not silently choose either identity.

### Subtask T014: Make refusal structured, actionable, and platform-neutral

**Purpose**: Ensure an operator receives a truthful refusal rather than a raw
filesystem exception or a generic auto-rebase failure when safe recovery is not
available.

**Steps**:

1. Extend the existing structured lifecycle error only as needed to represent the
   activated unavailable/divergent RED. Do not invent a parallel exception family
   if `LaneAutoRebaseSyncError` can carry the contract safely.
2. Preserve a stable machine-readable error code and dictionary payload for JSON
   consumers. Human text and structured fields must describe the same outcome.
3. Include actionable context proven by the witness:
   - lane identifier;
   - resolved branch identity;
   - missing expected worktree path;
   - unavailable versus divergent reason;
   - one existing supported recovery action.
4. Name only a recovery command that exists in the current CLI. If no supported
   command can safely resolve the state, say that authority must be reconciled and
   hand control to the operator; do not fabricate a command.
5. Do not expose a raw `FileNotFoundError`, Python traceback, host-specific path
   assumption, or a misleading coordination-worktree path.
6. Ensure refusal completes before side effects and within the local fixture's
   two-second NFR-004 budget. Use deterministic assertions rather than narrow
   timing races; a generous upper bound may guard gross regressions.
7. Verify JSON serialization yields a single coherent payload when consumed by
   the owning command. Any review-command envelope wiring belongs to WP04 unless the
   activated RED proves this file is its existing owner.
8. Confirm error construction does not create directories, acquire locks, move
   refs, append events, or dirty a checkout.

**Files**:

- `src/specify_cli/lanes/lifecycle_sync.py`: structured refusal fields/message.
- `tests/integration/test_lane_lifecycle_sync.py`: payload, human-message,
  side-effect, and portability assertions.

**Validation**:

- `to_dict()` (or the existing structured surface) contains stable actionable
  fields and no unserializable `Path` values.
- Human output names the missing path/lane and supported recovery action.
- Unavailable/divergent failure leaves worktree existence, refs, and porcelain
  unchanged.

### Subtask T015: Complete focused RED→GREEN and quality verification

**Purpose**: Prove the activated fix, or the evidence-only no-op, without widening
scope or relying on retry-to-green.

**Steps**:

1. On the activated path, preserve the separate test-only RED commit and capture:
   - planning-base SHA;
   - test-only commit SHA;
   - exact pytest command and expected failure;
   - GREEN implementation commit SHA;
   - unchanged witness assertion evidence.
2. Run the focused integration module from the resolved lane workspace:

   ```bash
   PWHEADLESS=1 uv run --extra test pytest tests/integration/test_lane_lifecycle_sync.py -q
   ```

3. Run Ruff on exactly the owned source and test files:

   ```bash
   uv run ruff check src/specify_cli/lanes/lifecycle_sync.py tests/integration/test_lane_lifecycle_sync.py
   ```

4. Run strict mypy on the owned production module:

   ```bash
   uv run mypy --strict src/specify_cli/lanes/lifecycle_sync.py
   ```

5. Run any focused WP01 witness row requested by the orchestrator to prove the
   original registered CLI behavior, but do not edit WP01-owned tests.
6. Run each command once to a terminal result. Diagnose any failure; never rerun
   merely to obtain green output.
7. Check the diff for forbidden scope:

   ```bash
   git diff --check
   git status --short
   ```

8. On the no-op path, do not manufacture RED/GREEN history. Report WP01's GREEN
   baseline evidence, the empty owned-file diff, and skipped-as-not-applicable
   production checks explicitly.
9. Provide the reviewer with exact commands/results and the T011 disposition. Do
   not post step-by-step issue comments; Mission evidence belongs in the DRAFT PR.

**Files**:

- Activated path: only the two owned files.
- No-op path: no file changes.

**Validation**:

- Focused pytest, Ruff, and strict mypy pass for an activated change.
- The original RED fails before and passes after without assertion weakening.
- `git diff --check` passes and the workspace contains no unrelated dirt.
- The no-op path has a byte-empty diff and a complete evidence handoff.

## Definition of Done

- [ ] `/ad-hoc-profile-load python-pedro` was loaded before implementation.
- [ ] The canonical implement action returned the lane workspace and all work ran
      from that resolved location on the Mission branch contract.
- [ ] WP02 is approved/done and the reviewed lifecycle-owned disposition rows were consumed.
- [ ] T011 records exactly one outcome: `NO-OP/GREEN` or `ACTIVATED/RED`.
- [ ] No production change exists without a lifecycle-owned RED/continue row.
- [ ] On no-op, both owned files remain byte-identical and evidence explains why.
- [ ] On activation, a separate real-Git test-only commit proves RED first.
- [ ] Classification is limited to ready/recoverable/unavailable/divergent.
- [ ] The same resolved identity flows through classification and lifecycle work.
- [ ] No absent/husk workspace is used as subprocess cwd.
- [ ] No new resolver, arbitrary branch creation, directory fabrication, stale
      metadata deletion, or primary-checkout fallback was introduced.
- [ ] Unavailable/divergent refusal is structured, actionable, and pre-mutation.
- [ ] Healthy and matching-branch recovery behavior remains green.
- [ ] Focused pytest, Ruff, strict mypy, and `git diff --check` pass when applicable.
- [ ] Only owned files changed, and WP04 receives any required review call-site handoff.
- [ ] PR #2641 remains DRAFT and no merge/ready action was taken.

## Risks

- **Speculative remediation**: the historical recoverable arm may already be
  correct. Mitigation: T011 makes reviewed RED/continue evidence a hard activation
  gate and treats no-op as complete.
- **Duplicate workspace authority**: recomputing path or branch in lifecycle sync
  can disagree with persisted/current identity. Mitigation: consume one resolved
  identity and forbid a new resolver.
- **Missing-cwd raw failure**: probing Git in an absent worktree can leak a raw
  filesystem exception. Mitigation: repository-root branch checks and readiness
  classification happen first.
- **Unsafe recovery**: creating a directory or branch can conceal absent authority.
  Mitigation: only an agreeing existing branch is recoverable through the current
  worktree lifecycle.
- **Scope collision with WP04**: review call-site changes are not owned here.
  Mitigation: stop at a narrow lifecycle contract and provide an explicit handoff.
- **Platform drift**: path-string or shell assumptions can make the fix Linux-only.
  Mitigation: retain `Path`, list-form subprocess arguments, and real-Git fixtures.
- **Misleading green**: exception-only assertions may miss ref or dirt mutations.
  Mitigation: tests assert path existence, refs, payload, and porcelain together.

## Reviewer Guidance

Review T011 before reading the code diff. If no lifecycle-owned RED/continue row
exists, reject any production change regardless of how reasonable it appears.
For an activated implementation, independently replay the test-only commit on its
recorded base and verify the exact witness is RED for the same reason, then replay
the GREEN command without altering the test.

Focus review on these invariants:

1. The implementation consumes existing canonical identity; it does not resolve
   again or manufacture a second path/branch authority.
2. Ready/recoverable/unavailable/divergent are reconciled before side effects or
   any cwd-bound worktree probe.
3. Recovery happens only for an agreeing branch that already exists.
4. Unavailable/divergent states fail before path, ref, lock, event, tracking, or
   porcelain mutation and provide an actionable structured diagnostic.
5. Healthy and matching-branch recovery behavior is unchanged.
6. The diff is confined to the two owned files; workflow wiring is deferred to
   WP04 and adjacent issues remain unclaimed.
7. Test evidence includes real Git state and negative side-effect assertions, not
   mocks or an exception-only unit test.
8. The branch/PR contract remains `fix/stale-workspace-reproduction` into DRAFT
   PR #2641, with the human operator retaining ready/merge authority.

Approve a no-op WP when its evidence is complete and owned-file diff is empty.
Approve an activated WP only when RED→GREEN lineage, focused gates, scope, and
canonical-authority constraints all hold independently.

## Activity Log

- 2026-07-14T18:45:10Z – codex – shell_pid=138606 – Assigned agent via action command
- 2026-07-14T18:48:00Z – codex – shell_pid=138606 – NO-OP/GREEN evidence: reviewed matrix baseline 2d05c53d03ee794885954410ae6a63c29d432869 has no lifecycle-owned row; rows 6-8 reached WP02 move-task workspace readiness and rows 9-12 reached WP04 review claim/commit routing. Canonical status shows WP02 approved. Owned SHA256 before/after: lifecycle_sync.py=2548d5310c4f9a565df0e24f6f66bda7338f08a466f67964c749ec914477b28f; test_lane_lifecycle_sync.py=deb3bed685cedd980f50bcc67d5fa11b8ed593dd1b6fdecc86c262be92f0e614. Refs before/after unchanged: HEAD/lane-c=aa9271f1318b2ac1cf479e6f122f7d2b23103ddc, mission=c000fc3aeb2e9e83c6c9aec592ed845ccd03a621, lane-b=7e21dd908539ca3c9490a58ad4acdd46242ab3df. PWHEADLESS=1 uv run --extra test pytest tests/integration/test_lane_lifecycle_sync.py -q: 3 passed in 73.24s. Ruff and strict mypy passed; owned diff empty; lane clean. No production/test commit created.
- 2026-07-14T18:48:21Z – codex – shell_pid=138606 – Ready for review: NO-OP/GREEN; no reviewed row reached lifecycle owner; owned hashes and refs remained byte-identical; lifecycle integration 3 passed; Ruff and strict mypy passed.
- 2026-07-14T18:48:50Z – codex – shell_pid=138606 – Started review via action command
- 2026-07-14T18:51:34Z – user – shell_pid=138606 – Review passed: strict NO-OP/GREEN is mandatory because reviewed rows 6-8 belong to WP02 and rows 9-12 to WP04; no row reaches lifecycle_sync. Independently verified WP02 approved, no WP03 code/test commit, owned files byte-identical to baseline (2548d5310c4f9a565df0e24f6f66bda7338f08a466f67964c749ec914477b28f; deb3bed685cedd980f50bcc67d5fa11b8ed593dd1b6fdecc86c262be92f0e614), 3 lifecycle tests pass, Ruff and strict mypy pass, lane clean, PR remains DRAFT.
