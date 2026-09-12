---
work_package_id: WP05
title: list_cmd.py honest org-tier reporting
dependencies:
- WP02
- WP03
requirement_refs:
- FR-006
- NFR-006
planning_base_branch: up-org-template-fsm
merge_target_branch: up-org-template-fsm
branch_strategy: Planning artifacts for this mission were generated on up-org-template-fsm. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into up-org-template-fsm unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
phase: Phase 3 - Reporting honesty
history:
- at: '2026-08-17T00:02:22Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/specify_cli/cli/commands/charter/list_cmd.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/charter/list_cmd.py
- tests/specify_cli/test_charter_list.py
role: ''
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 – `list_cmd.py` Reports the Org Tier Honestly

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any
user-defined profile), and behave according to its guidance before parsing the rest of this
prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for
`task_type: implement` and `authoritative_surface:
src/specify_cli/cli/commands/charter/list_cmd.py`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting if this WP was returned from review.
Address every feedback item and update the Activity Log as you go.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

This WP is **IC-05** from `plan.md`'s Implementation Concern Map. It fixes
`_template_tier_roots`'s org branch (`list_cmd.py`) so `charter list --all` stops advertising a path
the resolver does not read and a tier that does not describe what actually resolved.

Today, the org branch resolves `<org_root> / "doctrine" / "missions"` (nested) and tags it
`ResolutionTier.GLOBAL_MISSION` (borrowed from a different tier). Neither matches what WP03's org
tier actually reads (`<org_root> / "missions"`, flat, tagged `ResolutionTier.ORG`).

**Success criteria** (FR-006, SC-006): `charter list --all` reports the org template tier as `ORG`
at the flat `<org_root>/missions/software-dev/templates/` path.

## Context & Constraints

Read before starting:
- `kitty-specs/up-org-template-fsm-01M06F9K/spec.md` — DEC-007, DEC-009, User Story 1 Acceptance
  Scenario 3, FR-006, C-004.
- `kitty-specs/up-org-template-fsm-01M06F9K/plan.md` — IC-05's Purpose/Risks; Plan-Time
  Verification's citation for `list_cmd.py:48-90`.

**This mission is dogfooded inside spec-kitty's own repository — a PUBLIC repo based on `main`.**
No host paths, no usernames, no absolute local paths in any committed file — sweep your diff before
finishing.

**DEC-007 already confirmed no new architectural allow-list entry is needed.** Checked directly
against the two gates a `<org_root> / "missions"` join could plausibly trip:
`tests/architectural/test_charter_path_literal_authority.py` polices only `.kittify` /
`charter.{yaml,md}` literal joins — unrelated. `tests/architectural/test_built_in_location_authority.py`'s
join-only AST ratchet polices only joins against the literal `"built-in"` segment — also unrelated;
this fix changes `org_root / "doctrine" / "missions"` to `org_root / "missions"`, composing against
the already-resolved `org_root`, never `"built-in"`. T029 below re-confirms this directly rather
than trusting the citation.

**DEC-009 is explicitly out of scope**: `_template_tier_roots`'s **project**-tier path
(`project_root / "doctrine" / "missions"`) is a separate, pre-existing mismatch — do not touch it
in this WP (C-004).

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

Implementation command (with dependencies):
```bash
spec-kitty agent action implement WP05 --agent <name>
```

## Subtasks & Detailed Guidance

### Subtask T027 – Red-first `charter list --all` test

**Purpose**: Prove the "before" state for FR-006/SC-006.

**Steps**:
1. In `tests/specify_cli/test_charter_list.py` (which already has a `layered_project` fixture and
   template-kind-row tests — reuse that fixture's pattern rather than inventing a new one), assert
   that (pre-fix) `charter list --all` reports the org template tier as `GLOBAL_MISSION` at the
   nested `<org_root>/doctrine/missions/` path.

**Files**: `tests/specify_cli/test_charter_list.py`.

**Parallel?**: No — must exist before T028.

### Subtask T028 – Fix `_template_tier_roots`'s org branch

**Purpose**: Implement FR-006.

**Steps**:
1. In `src/specify_cli/cli/commands/charter/list_cmd.py:_template_tier_roots`, locate the org
   branch (currently around lines 76-86 — re-verify live):
   ```python
   org_root = layer_roots.get("org")
   if org_root is not None:
       missions = org_root / "doctrine" / "missions"
       if missions.is_dir():
           tier_roots.append(
               TierRoot(
                   tier=ResolutionTier.GLOBAL_MISSION,
                   missions_root=missions,
               )
           )
   ```
2. Change `missions = org_root / "doctrine" / "missions"` to `missions = org_root / "missions"`
   (flat — matching what the resolver actually reads per WP03).
3. Change `tier=ResolutionTier.GLOBAL_MISSION` to `tier=ResolutionTier.ORG`.
4. Do **not** touch the project-tier branch above it (DEC-009/C-004 — out of scope).
5. Confirm T027's test now reports `ORG` at the flat path.

**Files**: `src/specify_cli/cli/commands/charter/list_cmd.py`.

**Parallel?**: No — depends on T027.

### Subtask T029 – Confirm the architectural-gate ruling holds

**Purpose**: Re-verify DEC-007 directly rather than trusting the citation from planning.

**Steps**:
1. Run `pytest tests/architectural/test_charter_path_literal_authority.py
   tests/architectural/test_built_in_location_authority.py -q` after T028's change.
2. Confirm both stay green with **zero new allow-list entries** added to either test's ratchet
   list. If either test requires a new allow-list entry, stop and report this as a finding — it
   would mean DEC-007's ruling does not hold as written, and the WP should not proceed with a
   silent allow-list addition.

**Files**: None (verification-only subtask).

**Parallel?**: No — depends on T028.

### Subtask T030 – Focused unit test for the org branch

**Purpose**: This surface is **not** in the diff-coverage critical-path list (NFR-006) — a missed
test here will not fail CI's numeric gate the way a missed WP03/WP04 test would. This subtask is
the actual regression guard, per the repo's Sonar new-code-coverage expectation.

**Steps**:
1. Add a focused unit test directly on `_template_tier_roots` (not only the end-to-end `charter
   list --all` CLI-invocation test from T027) asserting the returned `TierRoot` for the org branch
   has `tier == ResolutionTier.ORG` and `missions_root == org_root / "missions"`.

**Files**: `tests/specify_cli/test_charter_list.py`.

**Parallel?**: No — do this last.

## Test Strategy

```bash
pytest tests/specify_cli/test_charter_list.py -q
pytest tests/architectural/test_charter_path_literal_authority.py tests/architectural/test_built_in_location_authority.py -q
```

## Risks & Mitigations

- **Low structural risk** (DEC-007 already confirmed no allow-list entry needed) — T029 re-verifies
  this directly rather than assuming the citation is still accurate.
- **NFR-006 risk**: this surface has no numeric CI backstop — do not skip T030 because CI would not
  catch it.
- **Scope creep risk**: do not fix the project-tier path mismatch (DEC-009/C-004) while you are in
  this function — it is explicitly out of scope for this mission.

## Review Guidance

A reviewer should confirm:
1. Only the org branch changed — the project-tier branch above it is untouched.
2. T029 was actually run (not just cited) and both architectural tests are confirmed green with no
   new allow-list entries.
3. The reported path is flat (`<org_root>/missions/`), not nested.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Format**: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>`

- 2026-08-17T00:02:22Z – system – Prompt created.
