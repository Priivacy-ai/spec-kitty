---
work_package_id: WP04
title: 'Dispatch propagation to canonical skill + #1810/#1804 closure'
dependencies:
- WP03
requirement_refs:
- C-004
- FR-006
- FR-007
- NFR-002
tracker_refs: []
planning_base_branch: feat/mission-lifecycle-dispatch-drg-closeout
merge_target_branch: feat/mission-lifecycle-dispatch-drg-closeout
branch_strategy: Planning artifacts for this mission were generated on feat/mission-lifecycle-dispatch-drg-closeout. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/mission-lifecycle-dispatch-drg-closeout unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "2941884"
history:
- at: '2026-06-13T16:37:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/doctrine/skills/spec-kitty.advise/
create_intent: []
execution_mode: code_change
owned_files:
- src/doctrine/skills/spec-kitty.advise/**
- .kittify/command-skills-manifest.json
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Dispatch propagation to canonical skill + #1810/#1804 closure

## ⚡ Do This First: Load Agent Profile

Load your assigned implementer profile (recommended `python-pedro`) via the profile-load skill —
governed context, not a bare name — before reading further.

## Objectives & Success Criteria

Propagate `dispatch` to the SINGLE canonical command-skill + manifest, and close #1810 / epic #1804.

- `dispatch` documented in `src/doctrine/skills/spec-kitty.advise/SKILL.md` (the one generated skill
  that documents the do/ask/advise trio) alongside the retained aliases.
- `.kittify/command-skills-manifest.json` refreshed via the skills install path (hash updated).
- Skill-routing prose that names the trio includes `dispatch`.
- #1810 closed; epic #1804 verified substantially-complete and closed.

## Context & Constraints

- Read: `plan.md` (IC-06, IC-07), `research.md` (D-B4 — RESOLVED), `spec.md` (FR-006/FR-007), quickstart §9.
- **Verified:** there is exactly ONE generated command-skill for the trio,
  `src/doctrine/skills/spec-kitty.advise/SKILL.md`. There are NO separate `do`/`ask` skills and NO
  per-agent hand-maintained command copies. This is NOT a 19-way edit.
- **C-004:** edit the SOURCE skill + manifest only — never hand-edit generated agent copies. Refresh
  the manifest through the skills install/migration path, not by hand-poking JSON if avoidable.
- Depends on WP03 (the `dispatch` command must exist before its skill documents it).
- Closure verdicts are set at the mission accept/merge gate — prepare the issue-matrix rows, do not
  finalize them in this WP.

## Branch Strategy

- **Strategy**: execution worktree per computed lane (lanes.json)
- **Planning base branch**: feat/mission-lifecycle-dispatch-drg-closeout
- **Merge target branch**: feat/mission-lifecycle-dispatch-drg-closeout

## Subtasks & Detailed Guidance

### T015 – Add dispatch to the SOURCE skill + manifest
- Edit `src/doctrine/skills/spec-kitty.advise/SKILL.md` to document `spec-kitty dispatch` as the
  canonical command with do/ask/advise as retained aliases (mirror their semantics). Refresh
  `.kittify/command-skills-manifest.json` (content hash) via the canonical skills install path.

### T016 – Skill-routing prose
- Update the skill-routing prose that names the trio (e.g. the runtime/agent routing docs) to include
  `dispatch`. Keep edits to canonical sources; do not touch generated agent copies (C-004).

### T017 – #1810 / #1804 closure
- Verify #1810 is delivered by WP03 (+ this WP's propagation). Verify epic #1804 is substantially
  complete (governed do/ask/advise + Op lifecycle shipped; #1810 was its blocking child). Prepare
  the issue-matrix rows for terminal verdicts at accept; note any genuine ops-layer refinements as
  out-of-scope follow-ups (not gaps).

## Test Strategy

- Assert `dispatch` appears in the SOURCE SKILL.md and the manifest hash is refreshed (a focused
  test or the existing command-skills manifest test). Run the terminology guard
  (`pytest tests/architectural/test_no_legacy_terminology.py`) since this edits doctrine prose.
  Paste commands + exit codes into handoff.

## Definition of Done

- `dispatch` in the canonical skill + manifest + routing prose; terminology guard green; #1810/#1804
  closure readiness recorded; no generated agent copy hand-edited.

## Risks

- Over-scoping into a fabricated 19-way edit (there is one skill). Hand-editing generated copies
  (C-004 violation). Forgetting the manifest refresh (drift).

## Reviewer Guidance

- Reviewer: `reviewer-renata`. Confirm exactly the one SOURCE skill + manifest changed (no agent-copy
  edits), prose names `dispatch`, and the #1804 closure is honest (substantially-complete, not forced).

## Activity Log

- 2026-06-13T17:23:34Z – claude:sonnet:python-pedro:implementer – shell_pid=2865912 – Assigned agent via action command
- 2026-06-13T17:34:16Z – claude:sonnet:python-pedro:implementer – shell_pid=2865912 – T015: dispatch documented as canonical in spec-kitty.advise/SKILL.md; do/ask/advise retained as first-class aliases with identical Op lifecycle. T016: skill-routing prose updated in spec-kitty-runtime-next/SKILL.md + session_presence/content.py (orientation block). T017: #1810 delivered by WP03+WP04; #1804 substantially complete - ready for terminal verdicts at accept gate. Terminology guard exit 0 (2 passed). Note: command-skills-manifest.json has no spec-kitty.advise entry (it is a doctrine skill, not a CANONICAL_COMMAND); manifest refresh is a no-op for this WP. session_presence/content.py edit outside owned_files has inline rationale (only source generating orientation block routing prose). Pre-existing README governance test failures not introduced by this WP.
- 2026-06-13T17:35:01Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=2904978 – Started review via action command
- 2026-06-13T17:42:33Z – user – shell_pid=2904978 – Moved to planned
- 2026-06-13T17:43:24Z – claude:sonnet:python-pedro:implementer – shell_pid=2930839 – Started implementation via action command
- 2026-06-13T17:46:07Z – claude:sonnet:python-pedro:implementer – shell_pid=2930839 – cycle1: FR-006 + T016 pinning tests added; green
- 2026-06-13T17:46:34Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=2941884 – Started review via action command
- 2026-06-13T17:48:17Z – user – shell_pid=2941884 – cycle2 verified: FR-006 (6 doctrine tests) + T016 (1 session_presence pin) added in commit 972b2520; source SKILL.md unchanged; all gates green (6+1+22+2 passed); cycle-2 rejected artifact is the cycle-1 feedback that prompted this fix cycle — correctly superseded by verified passing re-review
