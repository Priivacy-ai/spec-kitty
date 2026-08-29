---
work_package_id: WP02
title: Migrate AgentProfileRepository sites + NFR-005 measurement
dependencies:
- WP01
requirement_refs:
- FR-001
- NFR-005
planning_base_branch: feat/charter-sole-door-bypass-closure
merge_target_branch: feat/charter-sole-door-bypass-closure
branch_strategy: Planning artifacts for this mission were generated on feat/charter-sole-door-bypass-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-sole-door-bypass-closure unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
phase: Phase 2 - Bypass closure
history:
- at: '2026-08-03T14:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/agent/tasks_status_cmd.py
create_intent:
- tests/perf/test_tasks_status_baseline.py
execution_mode: code_change
model: ''
owned_files:
- src/runtime/next/runtime_bridge_io.py
- src/specify_cli/tool_surface/profiles/projection.py
- src/specify_cli/cli/commands/agent/tasks_status_cmd.py
- src/charter/activation/profile_resolution.py
- tests/perf/test_tasks_status_baseline.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Migrate AgentProfileRepository sites + NFR-005 measurement

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (implementer role, claude agent) before parsing
the rest of this prompt.

---

## ⚠️ IMPORTANT: Review Feedback

Check `review_ref` in the event log before starting. Address all feedback; log changes in the Activity Log.

---

## Objectives & Success Criteria

Close the 5 in-scope direct `AgentProfileRepository` construction sites (FR-001), and prove no perf
regression on the two sites whose removed "boundary ratchet" comment named a construction-cost concern
(NFR-005).

**Success criteria**:
- `runtime_bridge_io.py:576`, `projection.py:84`, `tasks_status_cmd.py:712`, `tasks_status_cmd.py:823` route
  through `charter.activation.resolver.DoctrineService` (or WP01's `agent_profile_repository` accessor where mutation
  is needed) instead of constructing `AgentProfileRepository` directly. `charter/profile_resolution.py:81`
  is confirmed a genuine bootstrap carve-out (T010, corrected scope) and is documented, not migrated.
- A pre-mission p95 latency baseline for `spec-kitty agent tasks status` is captured and recorded BEFORE
  `tasks_status_cmd.py` is touched; a post-migration measurement is within 10% of it.

## Context & Constraints

- **Depends on WP01** (declared in frontmatter) — the unified builder and the new
  `agent_profile_repository` accessor (pinned in WP01's prompt) must exist first. Your worktree starts from
  WP01's completed lane, so the accessor already exists with the exact name/shape WP01's prompt specifies —
  use it verbatim, do not re-derive or rename.
- Read `research.md`'s R3 and R5 sections: the "boundary ratchet" comment is confirmed a red herring against
  the existing import-scanning gate; the real, unmeasured risk is construction cost — that is what T009
  measures.
- Two of these five sites need the accessor (mutation), not the plain gated property — **corrected by the
  post-tasks squad** (the original method list was wrong for one site):
  - `runtime_bridge_io.py:576` needs `resolve_profile()` (lineage composition) → use the accessor.
  - `projection.py:84` needs `register_overlay()` only (NOT `get_ancestors()` — that method is unused by
    this call site; do not call it speculatively) → use the accessor.
  - `tasks_status_cmd.py:712,823` and `profile_resolution.py:81` only need the gated `agent_profiles`
    property — no accessor needed.

## Branch Strategy

- **Strategy**: lane-per-WP (normalized by `finalize-tasks`)
- **Planning base branch**: feat/charter-sole-door-bypass-closure
- **Merge target branch**: feat/charter-sole-door-bypass-closure

## Subtasks & Detailed Guidance

### Subtask T006 – Capture the pre-mission p95 baseline

- **Purpose**: Make NFR-005's "within 10% of baseline" falsifiable — this MUST run before T007-T009 touch
  any of the migrated sites.
- **Steps**:
  1. Confirm or build a fixture project with 100+ work packages (check `tests/fixtures/` for an existing
     large-mission fixture before creating a new one).
  2. On the merge-base commit (before this WP's changes), run `spec-kitty agent tasks status --mission
     <fixture>` repeatedly (e.g. 10 runs) and record the **raw timing series** (not just a derived p95
     constant — post-tasks squad correction: a single committed number is author-written and unfalsifiable;
     the raw pre-change and post-change series must both exist so a reviewer can recompute p95 independently,
     and both series must come from the same session/machine, since cross-machine comparison is invalid).
  3. Record the raw series in the mission's tracer file (`tooling-friction.md` or equivalent, per Standing
     Order #3) and in a new lightweight regression harness `tests/perf/test_tasks_status_baseline.py`.
- **Files**: `tests/perf/test_tasks_status_baseline.py` (new).
- **Parallel?**: No — must run first, before T007-T009.
- **Notes**: This is measurement, not a code change to the production surfaces. Do not skip it — it is the
  only thing that makes T009's comparison meaningful.

### Subtask T007 – Migrate `runtime_bridge_io.py:576`

- **Purpose**: `_resolve_tech_stack_for_profile` needs `resolve_profile()` (lineage-composed), not the plain
  filtered dict.
- **Steps**: Replace the direct `AgentProfileRepository(...)` construction with WP01's
  `agent_profile_repository` accessor on a `charter.activation.resolver.DoctrineService` instance (built via the
  unified builder, `repo_root` already available as a function parameter). Call
  `.resolve_profile(profile_id)` on the accessor's returned repository.
- **Files**: `src/runtime/next/runtime_bridge_io.py`.
- **Parallel?**: Yes — different file from T008-T010.

### Subtask T008 – Migrate `projection.py:84`

- **Purpose**: `default_profile_repository` needs `register_overlay()` (mutation) — that alone, not lineage
  traversal (post-tasks squad correction: `get_ancestors()` is unused by this call site).
- **Steps**: Replace the direct construction with WP01's `agent_profile_repository` accessor. Confirm
  `register_overlay()` calls still mutate the correct underlying repository object.
- **Files**: `src/specify_cli/tool_surface/profiles/projection.py`.
- **Parallel?**: Yes.

### Subtask T009 – Migrate `tasks_status_cmd.py:712,823`; re-measure and compare

- **Purpose**: Close the two sites whose comment cited the (now-confirmed-non-blocking) boundary ratchet;
  prove NFR-005 holds.
- **Steps**:
  1. Replace both direct `AgentProfileRepository(...)` constructions with the gated `agent_profiles`
     property on a factory instance (no accessor needed — dashboard icon rendering only reads).
  2. Remove the "boundary ratchet" comment; replace with a one-line note citing why it was a false concern
     (function-local imports aren't scanned by the existing gate — cite `research.md` R3) — do not just
     delete the comment silently.
  3. In the SAME session/machine as T006's baseline run, re-run the identical measurement against the
     migrated code on the same fixture, capturing another raw timing series. Compute p95 from both series
     and compare. If it regresses beyond 10%, do NOT accept it — add caching or lazy construction to close
     the gap (NFR-005 is explicit that the fix must be architectural, not accepted).
- **Files**: `src/specify_cli/cli/commands/agent/tasks_status_cmd.py`.
- **Parallel?**: No — must run after T006.

### Subtask T010 – Confirm `charter/profile_resolution.py:81` is a genuine bootstrap case, document, do not migrate

- **Purpose corrected by the post-tasks squad**: this subtask was originally scoped as a migration, but
  `_default_agent_profile_repository()` (`profile_resolution.py:70-82`) is a zero-argument, module-level
  cached function that constructs `AgentProfileRepository()` with **no `repo_root` and no org-pack context
  at all** — there is nothing to build a `charter.activation.resolver.DoctrineService` from at this call site. This is
  the real, literal instance of the bootstrap edge case named in spec.md's Edge Cases section (R7): the
  "no repo context, no org packs" fast path that `_resolve_agent_profile_record` (`:142-159`) falls back to
  when `repo_root is None` OR no org roots exist. The *other*, org-aware branch of that same function
  (`_activation_aware_profile_map`, `:120-139`) already routes through
  `charter.activation.doctrine_service_builder._build_activation_aware_doctrine_service` correctly — there is nothing
  left to migrate in this file.
- **Steps**:
  1. Read `profile_resolution.py` lines 60-160 in full to confirm the above structure independently.
  2. Do **not** change `_default_agent_profile_repository()` — there is no `pack_context`/`repo_root` to
     route through the factory.
  3. Add a one-line comment at the function noting it's a confirmed, documented bootstrap carve-out (C-002)
     — surfaced, not silently skipped.
  4. Note this confirmation in the PR description alongside FR-001's scope statement.
- **Files**: `src/charter/activation/profile_resolution.py` (comment only, no behavioural change).
- **Parallel?**: Yes.

## Test Strategy

- `pytest tests/runtime/ tests/specify_cli/tool_surface/ tests/specify_cli/cli/commands/agent/
  tests/charter/ -v` — targeted surfaces for the 4 modified modules.
- `pytest tests/perf/test_tasks_status_baseline.py -v` — the NFR-005 gate.
- `mypy --strict` on all 4 changed modules.

## Risks & Mitigations

- **Measuring the baseline after the change, not before.** Mitigation: T006's ordering is load-bearing —
  reviewers should check the tracer file's timestamp precedes T009's commit.
- **Using the plain gated property where the accessor was actually needed (or vice versa).** Mitigation:
  re-check each site's need against `research.md`'s per-site verdict table before writing the migration.

## Review Guidance

- Confirm the baseline was captured on the merge-base, not after any of this WP's changes.
- Confirm `runtime_bridge_io.py` and `projection.py` use the accessor, not the plain gated property.
- Confirm the removed "boundary ratchet" comment is replaced with an accurate one, not silently deleted.

## Activity Log

- 2026-08-03T14:10:00Z – system – Prompt created.
- 2026-08-03T19:27:08Z – claude – shell_pid=4127212 – T008 CONFIRMED BLOCKER (not a silent skip): projection.py:84's default_profile_repository was NOT migrated onto the factory. Empirically verified that routing it through build_activation_aware_doctrine_service(...).agent_profile_repository silently drops every .kittify/agent_profiles/*.agent.yaml project-overlay profile -- the factory's builder has no parameter to point its inner project directory at that path (only .kittify/doctrine, src/doctrine, or doctrine). This would break test_projection.py, test_projection_collision_precedence.py, and test_projection_org_visibility.py. Left unmigrated with a detailed in-code comment (mirrors the C-006 .kittify/profiles carve-out shape). Needs an operator/architect decision: (a) extend WP01's builder with a project-dir override, or (b) add an explicit FR-001 exclusion for this site. T006/T007/T009/T010 completed cleanly; NFR-005 baseline confirmed no regression (~2% delta) after a controlled A/B re-measurement -- see traces/tooling-friction.md.
