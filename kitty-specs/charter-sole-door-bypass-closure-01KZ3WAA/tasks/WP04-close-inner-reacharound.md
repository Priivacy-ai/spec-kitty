---
work_package_id: WP04
title: Close the ._inner reach-around + Gate 5 (mission-wide)
dependencies:
- WP01
requirement_refs:
- FR-007
- FR-010
planning_base_branch: feat/charter-sole-door-bypass-closure
merge_target_branch: feat/charter-sole-door-bypass-closure
branch_strategy: Planning artifacts for this mission were generated on feat/charter-sole-door-bypass-closure. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/charter-sole-door-bypass-closure unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
phase: Phase 2 - Bypass closure
history:
- at: '2026-08-03T14:10:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
- at: '2026-08-03T15:00:00Z'
  actor: system
  action: Post-tasks squad restructure - fixed missing WP01 dependency (CRITICAL, found independently by 3 delegates), corrected accessor method name (get_provenance, not register_overlay/get_ancestors), absorbed the former WP09 Gate 5 into this WP's T017 since it guards only these two sites (paula-patterns finding), narrowed the gate to avoid false positives on unrelated ._inner accesses (debugger-debbie finding)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/invocation/
create_intent:
- tests/architectural/test_charter_sole_door_inner_reacharound.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/invocation/registry.py
- src/specify_cli/invocation/org_profiles.py
- tests/architectural/test_charter_sole_door_inner_reacharound.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – Close the `._inner` reach-around + Gate 5 (mission-wide)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load `python-pedro` (implementer role, claude agent) before parsing
the rest of this prompt.

---

## ⚠️ IMPORTANT: Review Feedback

Check `review_ref` in the event log before starting. Address all feedback; log changes in the Activity Log.

---

## Objectives & Success Criteria

Close the escape hatch a post-plan squad delegate found: `service._inner.agent_profiles` reads the raw,
unfiltered repository directly, bypassing every other WP's gating. Left open, this WP means the mission's
"sole door" claim is hollow. **This WP now also ships the mission-wide durability gate for this category**
(FR-007's Gate 5, absorbed from the former WP09 by a post-tasks squad — it only ever guarded these two
sites, so a separate WP for it added a dependency edge for no real benefit).

**Success criteria**: zero `._inner` attribute access on a `charter.activation.resolver.DoctrineService`/
`AgentProfileRepository`-typed expression anywhere in `src/` outside `src/charter/**`, gate-enforced with a
self-mutation proof, not a one-time grep.

## Context & Constraints

- **Depends on WP01** (declared in frontmatter) — both sites need WP01's `agent_profile_repository`
  accessor, not a re-derived reach-around workaround. Your worktree starts from WP01's completed lane, so
  the accessor already exists with the exact name WP01's prompt pins — use it verbatim.
- **Corrected method** (post-tasks squad — the original prompt named the wrong method): both
  `registry.py:64` and `org_profiles.py:117` need `get_provenance()`, not `register_overlay()` or
  `get_ancestors()`. Confirm this against the actual call sites' usage before assuming it's exhaustive.
- **Gate scope correction** (debugger-debbie finding): a bare `._inner` AST scan across all of `src/`
  produces false positives on unrelated `._inner` attributes in `auth/transport.py` and
  `events/decision_log.py` that have nothing to do with `DoctrineService`. Scope the gate to `._inner`
  access specifically on an expression that resolves to a `charter.activation.resolver.DoctrineService` or the
  `agent_profile_repository`/`agent_profiles` chain — not a bare `._inner` anywhere.

## Branch Strategy

- **Strategy**: lane-per-WP (normalized by `finalize-tasks`)
- **Planning base branch**: feat/charter-sole-door-bypass-closure
- **Merge target branch**: feat/charter-sole-door-bypass-closure

## Subtasks & Detailed Guidance

### Subtask T015 – Migrate `registry.py:64`

- **Purpose**: `inner_repo = service._inner.agent_profiles` reaches past the gate for a provenance lookup.
- **Steps**: Replace `service._inner.agent_profiles` with WP01's `agent_profile_repository` accessor, then
  call `.get_provenance(...)` on it. Confirm this site's existing doctrine-layer factory call (already
  correct, per FR-001's C-006 finding) is untouched — only the `._inner` reach is being closed.
- **Files**: `src/specify_cli/invocation/registry.py`.
- **Parallel?**: Yes.

### Subtask T016 – Migrate `org_profiles.py:117`

- **Purpose**: Same reach-around shape as T015, different call site.
- **Steps**: Replace `inner_repository = service._inner.agent_profiles` with WP01's accessor, calling
  `.get_provenance(...)`.
- **Files**: `src/specify_cli/invocation/org_profiles.py`.
- **Parallel?**: Yes.

### Subtask T017 – Mission-wide Gate 5: zero-tolerance `._inner` access, self-mutation proven

- **Purpose**: Non-fakeable, durable proof this closure holds AND cannot be silently reopened anywhere else
  in the codebase (absorbing the former WP09 Gate 5 scope).
- **Steps**:
  1. Write an architectural test that AST-walks all of `src/` for `._inner` attribute access where the
     receiver expression resolves (via type inference or a narrower syntactic pattern —
     e.g. `.<name>._inner` where `<name>` is bound to a `charter.activation.resolver.DoctrineService`/
     `agent_profile_repository`/`agent_profiles` chain) to a doctrine-service object, outside
     `src/charter/**`. Do NOT flag unrelated `._inner` attributes on unrelated classes (e.g.
     `auth/transport.py`, `events/decision_log.py` — confirmed false-positive risks if the pattern is too
     broad).
  2. Zero-tolerance — no exclusions expected once T015-T016 land.
  3. Self-mutation proof: inject `._inner` access on a doctrine-service-typed expression at function-local
     scope in a scratch module outside `src/charter/**`; assert the gate fails naming the exact line. Also
     assert the gate does NOT fire on an unrelated `._inner` access (e.g. a scratch class with its own
     `._inner` attribute) — proving the scoping is neither too broad nor too narrow.
  4. Write this test RED first (against the pre-T015/T016 code), confirm it fails naming both real sites,
     then implement T015-T016 and confirm it goes green.
- **Files**: `tests/architectural/test_charter_sole_door_inner_reacharound.py` (new — this WP's gate is now
  the mission's canonical Gate 5, not a narrower pre-cursor to a later one).
- **Parallel?**: No — depends on T015-T016.

## Test Strategy

- `pytest tests/specify_cli/invocation/ tests/architectural/ -k "inner_reacharound" -v`.
- `mypy --strict src/specify_cli/invocation/registry.py src/specify_cli/invocation/org_profiles.py`.

## Risks & Mitigations

- **Reinventing a second accessor instead of reusing WP01's.** If it doesn't fit cleanly, that's a finding
  to report against WP01, not grounds for a parallel mechanism (C-001).
- **A gate too broad (flags unrelated `._inner` uses) or too narrow (misses a new bypass shape).** Mitigation:
  T017's self-mutation proof explicitly tests both directions — confirm both assertions pass, not just the
  positive case.

## Review Guidance

- Confirm both sites call `get_provenance()`, not `register_overlay()`/`get_ancestors()`.
- Confirm T017's gate does not fire against `auth/transport.py` or `events/decision_log.py`'s existing
  `._inner` accesses (run the gate against current `main` pre-migration and confirm it's clean on those
  files specifically).
- Confirm the self-mutation proof tests both the true-positive and true-negative case.

## Activity Log

- 2026-08-03T14:10:00Z – system – Prompt created.
- 2026-08-03T15:00:00Z – system – Post-tasks squad restructure: fixed dependency, method name, absorbed Gate 5.
