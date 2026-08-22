---
work_package_id: WP01
title: Remediation-effectiveness enforcement (lands RED)
dependencies: []
requirement_refs:
- FR-001
- FR-003
- NFR-001
- NFR-002
- C-001
planning_base_branch: fix/charter-preflight-remediation
merge_target_branch: fix/charter-preflight-remediation
branch_strategy: Planning artifacts for this mission were generated on fix/charter-preflight-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-preflight-remediation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-preflight-remediation-01KYG9WK
base_commit: e7b194671ceff742847a462f0f2ac9a0a5d516e4
created_at: '2026-07-26T23:43:41.238950+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
phase: Phase 1 - Foundation
history:
- at: '2026-07-26T23:24:39Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_remediation_effectiveness.py
execution_mode: code_change
owned_files:
- tests/architectural/test_remediation_effectiveness.py
- tests/specify_cli/charter_preflight/_fixtures.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Remediation-effectiveness enforcement (lands RED)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent tasks status`).
- **You must address all feedback** before your work is complete.
- **Report progress**: as you address each item, note what you changed.

---

## ⛔ THIS WORK PACKAGE MUST END RED

**Read this twice.** Every other WP in this repository ends green. This one does not.

You are building the enforcement mechanism for a defect that **currently exists in the tree**. When
you are done, the mechanism must **fail** — because `spec-kitty charter sync` genuinely cannot clear
the checks that emit it. That failure is the deliverable. It is the red-first evidence required by
NFR-002 and ADR `2026-07-17-1`, and WP02 is the change that turns it green.

**Do not**:
- weaken an assertion to make the run pass
- mark the failing states as exempt to make the run pass
- add `xfail`, `skip`, or a conditional that suppresses the failure
- "fix" `computer.py` yourself — that file is WP02's, and correcting it here destroys the evidence

**Do**: leave it red, capture the output, and hand over. If your run comes out **green**, something
is wrong with your mechanism — a green run at this point means it is not detecting a defect we have
already proven exists. Investigate rather than celebrate.

---

## Objectives & Success Criteria

Build a structural enforcement mechanism holding every preflight check to one rule:

> **Executing a check's remediation changes that check's state.**

Complete when:

1. The mechanism enumerates the preflight check registry and drives each remediation-emitting state.
2. It asserts against the **operator-visible** output, not merely a check's returned field.
3. It carries pinned floors so it cannot pass by finding nothing (NFR-001).
4. It fails on the four `spec-kitty charter sync` states in the current tree.
5. Introducing a deliberately ineffective remediation keeps it red (SC-005).

## Context & Constraints

**The defect (BC-2, the P0)**: `charter_runtime/freshness/computer.py` emits
`remediation="spec-kitty charter sync"` when `charter.yaml` is missing. But `charter/sync.py:18`
documents that command as never writing anything — *"it always reports `synced=False` /
`files_written=[]`"* — and every return path passes `files_written=[]`. The operator follows the
instruction, nothing changes, the gate refuses identically. There is no exit.

**Why a mechanism and not a corrected string**: `DIRECTIVE_043` and C-001 require closing the defect
*class* by construction. Research (R-006) already found a second live instance on the runner's
default path. A corrected string would leave that one standing and the next one unguarded.

**Canonical sources you must use** (`DIRECTIVE_044`):

| Need | Use this — do NOT author a new one |
|---|---|
| Isolated fixture projects | `tests/specify_cli/charter_preflight/_fixtures.py` |
| Charter presence check | `charter.bundle.first_missing_bundle_file` |
| Check registry | the three `_compute_*` producers in `charter_runtime/freshness/computer.py` |

Read before writing anything:
- `kitty-specs/charter-preflight-remediation-01KYG9WK/contracts/remediation-effectiveness.md` — the binding contract
- `kitty-specs/charter-preflight-remediation-01KYG9WK/research.md` — R-005 (registry census), R-006 (runner backfill)
- `kitty-specs/charter-preflight-remediation-01KYG9WK/data-model.md` — the four fixture shapes

## Branch Strategy

- **Planning base**: `fix/charter-preflight-remediation`
- **Merge target**: `fix/charter-preflight-remediation`
- Execution worktrees are allocated per computed lane from `lanes.json`. Use the workspace path
  `spec-kitty agent action implement WP01` gives you. Do not reconstruct it.

---

## Subtasks

### T001 — Extend `_fixtures.py` with the four fixture shapes

**Purpose**: give the mechanism a reliable way to construct each project state, reusing the helpers
that already exist rather than inventing a parallel mechanism.

`tests/specify_cli/charter_preflight/_fixtures.py` already provides `init_git_repo`,
`make_fresh_repo`, `seed_charter`, `seed_charter_yaml(valid=…)`, `seed_bundle_files`,
`seed_manifest`, `seed_graph`. Between them they can build every shape you need.

**Steps**:
1. Read the whole file first. Understand what each helper already does — several of them compose.
2. Add named builders for the four shapes in `data-model.md`:
   - `F1` — no charter at all (never initialised)
   - `F2` — legacy multi-file bundle present, **no** `charter.yaml` (the mission's trigger state)
   - `F3` — `charter.yaml` present and valid
   - `F4` — `charter.yaml` present but unparseable (`seed_charter_yaml(valid=False)`)
3. Each builder takes a `tmp_path`-style root and returns it, fully seeded and git-initialised.
4. Do **not** duplicate logic that an existing helper performs — compose them.

**Files**: `tests/specify_cli/charter_preflight/_fixtures.py` (extend)

**Validation**:
- Each builder produces a directory that the preflight runner can be pointed at
- F2 genuinely has no `charter.yaml` and does have the legacy bundle files
- Existing tests in `test_runner.py` and `test_computer.py` still pass unchanged

### T002 — Enumerate the check registry and declare the exemption set

**Purpose**: the mechanism must know the complete set of checks, and which of them legitimately have
no self-service remediation.

**Steps**:
1. Enumerate the three producers in `charter_runtime/freshness/computer.py`:
   `_compute_charter_source`, `_compute_synced_bundle`, `_compute_synthesized_drg`.
2. For each, enumerate the states it can return and which of those carry a non-`None` remediation.
   R-005 records the current census: 7 remediation-emitting states.
3. Declare the exemption set **explicitly** — as data, in the test module. Membership must never be
   inferred from a `None` remediation (C-EFF-2). A check is exempt because someone declared it so.
4. Right now the exemption set is expected to be **empty**. Declare it anyway, with the structure in
   place, so WP03 can populate it.

**Files**: `tests/architectural/test_remediation_effectiveness.py` (new)

**Validation**:
- Enumeration is derived from the module, not a hand-copied list that can silently drift
- The exemption set is a visible, reviewable declaration

### T003 — Build the effectiveness driver

**Purpose**: the core of the mechanism — prove empirically that a remediation works.

**Steps**:
1. For each remediation-emitting state:
   a. Build an isolated fixture project exhibiting that state (T001 builders).
   b. Evaluate the check; capture its state and remediation.
   c. Execute the emitted remediation against that fixture project.
   d. Re-evaluate the check.
   e. Assert the state **changed**.
2. "Changed" per C-EFF-1 means it no longer reports the same non-passing state. It does **not**
   require reaching a passing state in one step — a `missing` → `invalid` move is progress. What
   must not happen is an identical result, which is the loop the P0 describes.
3. **C-EFF-5 is binding**: never execute a remediation against the developer's or CI's own
   repository checkout. Every execution targets a fixture directory. Be deliberate about the working
   directory — a remediation that runs against the real repo could mutate the developer's charter.

**Files**: `tests/architectural/test_remediation_effectiveness.py`

**Validation**:
- Each remediation executes against a fixture root, never the repo root
- The assertion compares before/after state for the *same* check
- Test isolation: no fixture leaks into another

### T004 — Assert against operator-visible output

**Purpose**: prevent the mechanism from measuring the wrong surface.

This is the subtlest requirement in the WP. `preflight/runner.py:245` composes the operator's
message as:

```python
f"{check.name} {check.state}; run `{check.remediation or 'spec-kitty charter status'}`"
```

A mechanism inspecting only `check.remediation` would report **green** while the operator is still
being shown `spec-kitty charter status` — a reporter that cannot change anything. C-EFF-3 binds the
composed output, not the field.

**Steps**:
1. Drive the runner (not just the individual check producers) so the composed `blocked_reason` is
   what you assert against.
2. Extract the command from the composed output and prove *that* command is what gets executed and
   re-verified.
3. Where a check emits `None`, the composed output currently still contains a command — record this;
   WP03 fixes it, and T015 will extend your assertions to cover it.

**Files**: `tests/architectural/test_remediation_effectiveness.py`

**Validation**:
- The mechanism would fail if someone changed only the runner's fallback string to something
  ineffective, without touching any check

### T005 — Pin the floors

**Purpose**: NFR-001 — the mechanism must not be able to pass by finding nothing, nor by
reclassification.

**Steps**:
1. Assert a floor of **7** remediation-emitting states.
2. Assert a floor of **3** check producers.
3. Assert the **size** of the exemption set (currently 0).
4. Each floor gets a comment explaining why it exists and that updating it is a deliberate act
   reviewed in the same change — not a number to nudge when a run goes red.

**Why the exemption floor matters**: without it, a check failing the effectiveness assertion could
simply be moved into the exemption set to make the run pass, silently shrinking coverage. With it,
reclassification turns the mechanism red — which is exactly the spec's US1 Acceptance Scenario 3.

**Files**: `tests/architectural/test_remediation_effectiveness.py`

**Validation**:
- Deleting a check from the registry turns the mechanism red
- Moving a check into the exemption set turns the mechanism red

### T006 — Prove non-vacuity

**Purpose**: SC-005 / C-EFF-6 — a mechanism that cannot be shown to fail has not been shown to work.

**Steps**:
1. Add a test that injects a deliberately ineffective remediation and asserts the mechanism detects
   it.
2. Prefer a construction that does not mutate real source files. If you must temporarily patch a
   module, use monkeypatching that unwinds automatically.

**⚠️ Hard-won lesson from a previous mission in this repo**: a mutation-injection test that writes to
a source file and reverts it in teardown will leave the mutation committed if the run is interrupted
between inject and revert. If you use that pattern at all, ensure the revert is in a `finally` or
fixture teardown — and **never `git add -A`** in this worktree. Stage explicit paths only.

**Files**: `tests/architectural/test_remediation_effectiveness.py`

**Validation**:
- The injected-defect test passes (i.e. it successfully detects the injected defect)
- No source file is left mutated after the run — `git status` is clean of unexpected modifications

### T007 — Capture the RED run as red-first evidence

**Purpose**: NFR-002 — the reproduction is committed as a failing test **before** the corrective
change. This is the artifact that proves the fix fixes something.

**Steps**:
1. Run the mechanism against the unmodified tree.
2. Confirm it fails on the four `spec-kitty charter sync` states
   (`computer.py:309`, `:318`, `:348`, `:357`).
3. Record the exact failure output — counts and the failing state names — in your handoff note.
4. Commit with the mechanism **red**.

**Validation**:
- The failure names the `charter sync` states specifically, not a generic assertion error
- The handoff note carries the verbatim failure summary so WP02's reviewer can diff against it

---

## Definition of Done

- [ ] All four fixture shapes buildable from extended `_fixtures.py`
- [ ] Registry enumerated from the module; exemption set explicitly declared
- [ ] Effectiveness driver executes remediations in isolated fixtures only
- [ ] Assertions bind the operator-visible composed output (C-EFF-3)
- [ ] Floors pinned: 7 states, 3 producers, exemption-set size
- [ ] Non-vacuity proven (SC-005) with no source file left mutated
- [ ] **The mechanism is RED**, failing on the four `charter sync` states
- [ ] Verbatim failure output recorded in the handoff note
- [ ] `uv run ruff check <changed files>` exits 0
- [ ] `uv run mypy --strict` shows no new errors versus the merge base
- [ ] Existing `test_runner.py` / `test_computer.py` still pass

## Reviewer Guidance

**The single most important check: is this red for the right reason?**

Run it. Confirm it fails naming the `charter sync` states. Then apply the WP02-style fix locally
(change one remediation string to something effective) and confirm the corresponding assertion
flips to green. If it does not, the mechanism is not measuring what it claims.

Then verify:
1. **Not measuring the wrong surface** — does it bind the composed output, or just `check.remediation`?
   Change `runner.py`'s fallback string to something obviously ineffective and confirm it goes red.
2. **Not vacuous** — remove a check from the registry and confirm red. Move one into the exemption
   set and confirm red.
3. **Fixture isolation** — grep for anything that could execute a remediation against the repo root.
4. **Reused the canonical fixture base** — a hand-rolled parallel fixture mechanism is a
   `DIRECTIVE_044` violation and should be rejected.
5. **No scope creep into `computer.py`** — that is WP02's file. Any edit to it here destroys the
   red-first evidence and must be rejected.
