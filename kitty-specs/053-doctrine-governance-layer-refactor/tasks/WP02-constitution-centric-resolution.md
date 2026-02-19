---
work_package_id: WP02
title: Constitution-Centric Governance Resolution
lane: "done"
dependencies:
- WP01
base_branch: develop
base_commit: a5aca2fc5d8d365c0b7d0f7fa26d643d02f128f3
created_at: '2026-02-17T15:34:48.544153+00:00'
subtasks:
- T010
- T011
- T012
- T013
- T014
- T015
phase: Phase 2 - Activation Semantics
assignee: ''
agent: "codex_nonKitty"
shell_pid: '170105'
review_status: "approved"
reviewed_by: "Stijn Dejongh"
history:
- timestamp: '2026-02-17T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Constitution-Centric Governance Resolution

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

Depends on WP01 for schema availability.

## Objectives & Success Criteria

1. Governance activation reads constitution selections first.
2. Missing selected agent profiles produce hard-fail validation errors.
3. Unavailable constitution tools produce hard-fail validation errors.
4. Missing template-set selection is allowed and resolved via explicit fallback.
5. Tests lock mission-orchestration-only boundary and constitution authority.

## Context & Constraints

- Contract authority: `kitty-specs/053-doctrine-governance-layer-refactor/contracts/governance-layer-contracts.md`
- Decisions: `kitty-specs/053-doctrine-governance-layer-refactor/research.md`
- Architecture model: `architecture/diagrams/explicit-governance-layer-model.puml`

No mission-level constitution behavior may be introduced.

## Subtasks & Guidance

### T010: Add governance resolver

- Implement resolver module that assembles active governance set from constitution selections.
- Output should include resolved paradigms, directives, agent profiles, tools, and template-set decision (explicit or fallback).

### T011-T012: Enforce hard-fail references

- Validate selected profiles against available profile catalog.
- Validate available tools against runtime/tool registry assumptions.
- Fail fast with actionable, deterministic errors.

### T013: Optional template-set fallback

- If constitution omits template set, apply documented fallback behavior.
- Ensure fallback path is visible in logs/result metadata.

### T014-T015: Contract tests and helper path

- Add tests for success path and each hard-fail path.
- Add helper command/function used by planning/runtime checks to surface resolver diagnostics.

## Risks & Mitigations

- Risk: resolver implicitly reads mission behavior.
  Mitigation: enforce API boundary and add regression tests.
- Risk: fallback behavior becomes hidden default.
  Mitigation: require explicit fallback marker in resolver output.

## Activity Log

- 2026-02-17T15:34:48Z – codex_nonKitty – shell_pid=170105 – lane=doing – Assigned agent via workflow command
- 2026-02-17T15:44:35Z – codex_nonKitty – shell_pid=170105 – lane=for_review – Ready for review: governance resolver + validation + fallback + diagnostics
- 2026-02-17T15:50:33Z – codex_nonKitty – shell_pid=170105 – lane=doing – Started review via workflow command
- 2026-02-17T15:51:26Z – codex_nonKitty – shell_pid=170105 – lane=done – Review passed: constitution-first governance resolution
