---
work_package_id: WP06
title: Layout gate second segment + enum ratchet
dependencies:
- WP01
- WP05
requirement_refs:
- FR-006
- FR-007
- NFR-001
planning_base_branch: remediation/doctrine-silence-guards
merge_target_branch: remediation/doctrine-silence-guards
branch_strategy: Planning artifacts for this mission were generated on remediation/doctrine-silence-guards. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/doctrine-silence-guards unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
- T032
- T033
phase: Phase 1 - Guards
history:
- at: '2026-07-26T19:45:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_doctrine_artefact_layout.py
create_intent:
- tests/architectural/test_reference_enum_ratchet.py
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_doctrine_artefact_layout.py
- tests/architectural/test_reference_enum_ratchet.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP06 – Layout gate second segment + enum ratchet

## ⚡ Do This First: Load Agent Profile

Load the `python-pedro` profile via `/ad-hoc-profile-load` and behave according to its guidance before parsing the rest of this prompt.

---

## Objectives & Success Criteria

- The layout gate validates **both** mandatory path segments.
- Adding a member to any of the four `<kind>_reference.type` enums fails a test.

**Requirement refs**: FR-006, FR-007, NFR-001, SC-005, SC-006

## Context & Constraints

The layout gate currently validates only `parts[0] == kind.plural`, so a **right-pack/wrong-type** file (a tactic under `assets/built-in/`) passes.

The enum freeze is a comment. FR-006 requires a **ratchet on the member sets**, because a comment did not stop the enum-widening attempt that started this programme.

This WP owns only test files — it deliberately does **not** own the schemas, which WP05 regenerates.

**Binding, every WP in this mission:**

- **Never run the full `tests/architectural/` directory** (C-003) — a known harness issue kills the session. Targeted single-file runs only.
- The 6 inherited `arch-adversarial` reds stay red (C-004). No greenwashing, no retry-to-green.
- **ATDD (C-006)**: the failing test is the **first commit** of this WP, RED on the planning base and GREEN at the final commit.
- New code passes `ruff` and `mypy --strict` with zero issues. No `# noqa` / `# type: ignore` to get there.
- Charter: `.kittify/charter/charter.md`. Spec: `../spec.md`. Plan: `../plan.md`. Manifest: `../tasks.md`.

## Branch Strategy

- **Planning base branch**: `remediation/doctrine-silence-guards`
- **Merge target branch**: `remediation/doctrine-silence-guards` → draft PR to `main`; the operator merges.

## Subtasks & Detailed Guidance

### Subtask T029 – Failing-first test.

A tactic under `assets/built-in/` currently passes the layout gate.

### Subtask T030 – Validate both segments.

`parts[0] == kind.plural` **and** `parts[1] == built-in`.

### Subtask T031 – Failing-first test [P].

A member added to a `<kind>_reference.type` enum currently passes.

### Subtask T032 – Ratchet the four enums [P].

Pin the member sets; growth fails.

### Subtask T033 – Allowlist discipline.

Layout allowlist must be exactly 0 entries. The 17 mission-tier step contracts stay a **positive** carve-out so the exception cannot hide a real stray.

## Test Strategy

- `PYTHONPATH=src python -m pytest tests/architectural/test_doctrine_artefact_layout.py -q`
- `PYTHONPATH=src python -m pytest tests/architectural/test_reference_enum_ratchet.py -q`

## Risks & Mitigations

- A ratchet that pins the wrong baseline freezes a bug. Derive the baseline from the schemas, do not hand-type it.

## Review Guidance

- Verify red→green: the WP's first commit was RED on `remediation/doctrine-silence-guards` and is GREEN at the final commit.
- Verify every gate added is **non-vacuous**: it must reject a planted violation, and its allowlist must be empty.
- Verify the graph invariant where the WP claims it (311 nodes / 774 edges).

## Activity Log

> **CRITICAL**: entries in chronological order, oldest first. **Append** new entries at the END.

- 2026-07-26T19:45:15Z – system – Prompt created.
