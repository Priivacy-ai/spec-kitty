---
work_package_id: WP01
title: Converge the forked _resolve_asset tier-1 probe
dependencies: []
requirement_refs:
- FR-001
- NFR-005
planning_base_branch: up-org-template-fsm
merge_target_branch: up-org-template-fsm
branch_strategy: Planning artifacts for this mission were generated on up-org-template-fsm. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into up-org-template-fsm unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-up-org-template-fsm-01M06F9K
base_commit: e1ef69b991dcc0393d1f2d230b5dfe7f22e7145a
created_at: '2026-08-17T01:00:57.123998+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Convergence (prerequisite)
history:
- at: '2026-08-17T00:02:22Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/runtime/resolver.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/runtime/resolver.py
- tests/runtime/test_resolver_unit.py
role: ''
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Converge the Forked `_resolve_asset` Tier-1 Probe

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any
user-defined profile), and behave according to its guidance before parsing the rest of this
prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for
`task_type: implement` and `authoritative_surface: src/specify_cli/runtime/resolver.py`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via
  `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete.
- **Report progress**: As you address each feedback item, update the Activity Log.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``. Use language identifiers in code
blocks: ` ```python `, ` ```bash `.

---

## Objectives & Success Criteria

This WP is **IC-01** from `plan.md`'s Implementation Concern Map (Step 0 of the mission). It is
**the mission's prerequisite work package** — every later WP that touches
`src/specify_cli/runtime/resolver.py` depends on it landing first.

`src/doctrine/resolver.py:_resolve_asset` (the doctrine-layer "sole door", used by `charter
list`/`show-origin`) already probes a mission-scoped override path at tier 1
(`.kittify/overrides/missions/{mission}/{subdir}/{name}`, checked before the global
`.kittify/overrides/{subdir}/{name}` fallback). `src/specify_cli/runtime/resolver.py:_resolve_asset`
(the production `mission create` / plan-setup lane) does **not** — it only checks the global,
non-mission-scoped override. This is a real, reproducible defect: a template installed at the
mission-scoped path resolves for `charter list` but raises `FileNotFoundError` through `mission
create`.

**Success criteria**:
- A new test proves the regression exists (red) before your fix.
- `specify_cli/runtime/resolver.py:_resolve_asset` gains the identical mission-scoped probe,
  mirroring `doctrine/resolver.py:172-179` verbatim.
- A new parametrized test proves both resolver modules now agree, byte-for-byte, on `(path, tier)`
  for the identical fixture.
- Zero behavior change for any caller that does not use a mission-scoped override (NFR-005).

## Context & Constraints

Read before starting:
- `.kittify/charter/charter.md` — governing charter.
- `kitty-specs/up-org-template-fsm-01M06F9K/spec.md` — DEC-001, DEC-002, DEC-003, User Story 2,
  FR-001.
- `kitty-specs/up-org-template-fsm-01M06F9K/plan.md` — IC-01's Purpose/Risks, and the
  "Plan-Time Verification" section's citations for `src/doctrine/resolver.py:145-179` and
  `src/specify_cli/runtime/resolver.py:259-286`.
- `kitty-specs/up-org-template-fsm-01M06F9K/tasks.md` — WP01's row and the mission-wide dependency
  table.

**This mission is dogfooded inside spec-kitty's own repository — a PUBLIC repo based on `main`.**
Its own `AGENTS.md`/`CLAUDE.md`/`CONTRIBUTING.md` govern. **No host paths, no usernames, no
absolute local paths in any committed file** — sweep your diff for these before finishing (a spec
in this mission already had to be corrected for citing a path that only exists outside the repo).

**DEC-002 is binding**: this WP is **additive-only**. Do not delete, import, or otherwise unify
`doctrine/resolver.py` and `specify_cli/runtime/resolver.py` — they stay two modules.
`tests/architectural/test_charter_sole_door_resolver_imports.py:1-20` gate-mandates that
`doctrine.resolver`'s tier functions stay reachable, from outside `src/charter/**`/`src/doctrine/**`,
only via `charter.resolver.DoctrineService`. A real merge would make
`specify_cli/runtime/resolver.py` import `doctrine.resolver` directly and red this gate immediately
(zero-tolerance, no allow-list).

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

> These fields are populated automatically by `spec-kitty agent mission finalize-tasks`. Do NOT
> change them manually unless you are certain the branch topology has changed.

Implementation command (no dependencies):
```bash
spec-kitty agent action implement WP01 --agent <name>
```

## Subtasks & Detailed Guidance

### Subtask T001 – Red-first regression test

**Purpose**: Capture the "before" state per User Story 2's Independent Test and SC-002's required
shape — the regression must be proven red before it is fixed, or the before/after evidence is
lost.

**Steps**:
1. In `tests/runtime/test_resolver_unit.py`, add a fixture that writes a template file at
   `.kittify/overrides/missions/software-dev/templates/spec-template.md` under a `tmp_path`
   project.
2. Assert that (pre-fix) calling `specify_cli.runtime.resolver.resolve_template("spec-template.md",
   "templates", project_dir, "software-dev")` raises `FileNotFoundError`.
3. In the same test, assert that `doctrine.resolver.resolve_template` (or the equivalent
   `doctrine.resolver._resolve_asset`-backed helper) succeeds on the **identical** fixture at
   `tier == ResolutionTier.OVERRIDE` — proving the two modules disagree today.
4. Run the test, capture the exact failure message (`FileNotFoundError: ...`) for the WP report.

**Files**: `tests/runtime/test_resolver_unit.py` (add to the existing file — do not create a new
test module for this).

**Parallel?**: No — this must exist before T002.

**Notes**: This test will *keep passing* after your fix only if you invert its assertion in T003
(or replace it with T003's equality test). Do not leave a permanently-red test in the suite —
either convert this test's assertion in place once the fix lands, or fold it into T003.

### Subtask T002 – Add the tier-1 mission-scoped override probe

**Purpose**: Mirror `doctrine/resolver.py:172-179`'s mission-scoped probe into
`specify_cli/runtime/resolver.py:_resolve_asset`, verbatim in behavior.

**Steps**:
1. Open `src/doctrine/resolver.py` and re-read the exact tier-1 block (currently around
   lines 172-183 — verify the live line numbers yourself, they may have shifted since this prompt
   was written):
   ```python
   mission_scoped_override = kittify / "overrides" / "missions" / mission / subdir / name
   if mission_scoped_override.is_file():
       return ResolutionResult(path=mission_scoped_override, tier=ResolutionTier.OVERRIDE, mission=mission)

   override = kittify / "overrides" / subdir / name
   if override.is_file():
       return ResolutionResult(path=override, tier=ResolutionTier.OVERRIDE, mission=mission)
   ```
2. In `src/specify_cli/runtime/resolver.py:_resolve_asset`, insert the identical mission-scoped
   probe **before** the existing global-override check (currently the sole "Tier 1" check, around
   lines 259-286 — re-verify live). Mission-scoped wins over global, matching
   `doctrine/resolver.py`'s ordering.
3. Do not change the function signature, the tier-2..tier-5 logic, or anything else in the file.
   This is a ~6 LOC, purely additive change per the spec's own sizing estimate.

**Files**: `src/specify_cli/runtime/resolver.py`.

**Parallel?**: No — depends on T001 existing (red-first).

**Notes**: This is the exact prerequisite WP03 depends on. Do not proceed to add an org tier here
— that is out of scope for WP01 and belongs to WP03.

### Subtask T003 – Cross-module parity test (SC-002)

**Purpose**: Prove both resolver modules now agree, not just that the regression is fixed in
isolation.

**Steps**:
1. Add a parametrized test (or extend T001's test) asserting that
   `specify_cli.runtime.resolver.resolve_template(...)` and `doctrine.resolver.resolve_template(...)`
   return the **identical** `path` and `tier` for the identical mission-scoped-override fixture.
2. Assert `tier == ResolutionTier.OVERRIDE` explicitly by name — not merely "no exception raised".
   This is the exact measurement `plan.md`'s Verification Design table requires for FR-001: "Resolves
   at `tier == ResolutionTier.OVERRIDE`, identical `(path, tier)` to `doctrine.resolver.resolve_template`
   on the same fixture."

**Files**: `tests/runtime/test_resolver_unit.py`.

**Parallel?**: No — depends on T002.

### Subtask T004 – Docstring update

**Purpose**: DIR-007 (docstrings for public APIs) — `_resolve_asset`'s docstring must reflect the
tier it now actually implements.

**Steps**:
1. Update `specify_cli/runtime/resolver.py:_resolve_asset`'s docstring to document the two-shape
   tier-1 check (mission-scoped first, then global fallback), matching
   `doctrine/resolver.py:_resolve_asset`'s docstring style (`Tier 1 (override) checks two shapes,
   mission-scoped first: ...`).

**Files**: `src/specify_cli/runtime/resolver.py`.

**Parallel?**: Yes — can be done alongside T003.

### Subtask T005 – NFR-005 regression check

**Purpose**: Prove zero behavior change for every caller that does **not** use a mission-scoped
override.

**Steps**:
1. Run the full resolver test module: `pytest tests/runtime/test_resolver_unit.py -q`.
2. Confirm every pre-existing test still passes unmodified (except T001's test, which you converted
   or folded per T001's note).
3. If any pre-existing test goes red, classify it per AGENTS.md's baseline-red gotcha (pre-existing
   known reds vs. a regression this WP introduced) before treating it as yours to fix.

**Files**: None (verification-only subtask).

**Parallel?**: No — run last, after T002-T004 land.

## Test Strategy

All new tests live in `tests/runtime/test_resolver_unit.py` (the existing test module for
`specify_cli.runtime.resolver`). Run:
```bash
pytest tests/runtime/test_resolver_unit.py -q
```
`src/specify_cli/runtime/resolver.py` is **not** in the diff-coverage critical-path list
(NFR-006) — it is covered only by the advisory full-diff step. That does not lower the bar: T001
and T003 are the tests that actually prove SC-002, and there is no numeric gate acting as a
backstop if you skip them.

## Risks & Mitigations

- **Reflex risk**: treating this as "just add a line" and skipping the red-first test — this loses
  the regression-proof shape SC-002 explicitly requires. Do T001 before T002, not after.
- **Scope creep risk**: do not add the org tier here. That is WP03's job and it has a hard
  dependency on this WP landing cleanly first (DEC-002/DEC-003).
- **NFR-005 risk**: verify the new probe does not change resolution for projects with no
  mission-scoped override configured — T005 exists specifically to catch this.

## Review Guidance

A reviewer should confirm:
1. T001's red-first test failure message is reported and is the expected `FileNotFoundError`.
2. The added probe is a verbatim behavioral mirror of `doctrine/resolver.py`'s tier-1 block — no
   creative reinterpretation.
3. T003's parity test asserts `tier == ResolutionTier.OVERRIDE` by name, not merely "no exception".
4. No changes outside `_resolve_asset`'s tier-1 block and its docstring.
5. `doctrine/resolver.py` was **not** touched by this WP (it is unchanged — WP02/WP03 touch it).

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Format**: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>`

- 2026-08-17T00:02:22Z – system – Prompt created.
