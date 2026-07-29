---
work_package_id: WP04
title: 'Strict models: extra=forbid + writers + round-trip'
dependencies:
- WP03
requirement_refs:
- FR-004
- C-001
planning_base_branch: remediation/doctrine-silence-guards
merge_target_branch: remediation/doctrine-silence-guards
branch_strategy: Planning artifacts for this mission were generated on remediation/doctrine-silence-guards. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/doctrine-silence-guards unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T023a
- T018
- T019
- T020
- T021
- T022
phase: Phase 2 - Boundaries
history:
- at: '2026-07-26T19:45:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/models.py
create_intent:
- tests/doctrine/drg/test_model_strictness_roundtrip.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/models.py
- src/doctrine/drg/migration/extractor.py
- src/doctrine/agent_profiles/profile.py
- tests/doctrine/drg/test_model_strictness_roundtrip.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – `extra="forbid"` + writers + round-trip

## ⚡ Do This First: Load Agent Profile

Load the `python-pedro` profile via `/ad-hoc-profile-load` and behave according to its guidance before parsing the rest of this prompt.

---

## Objectives & Success Criteria

- An unknown field on `DRGNode`, `DRGEdge` or `AgentProfile` is a **load error**, not silence.
- A new `DRGEdge` field survives write→read.

**Requirement refs**: FR-004, C-001, SC-003

## Context & Constraints

Verified: **none of the three models declares `model_config`**, and the writers are field-by-field. So an extra field is silently ignored on load and silently dropped on write.

This is the mechanism that makes B1's `impacts`/`is_symmetric` and B2's `aliases` real rather than inert.

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

### Subtask T015 – Close `extractor.py:133-145` (`_KIND_MAP`).

**Moved here from WP03.** `_KIND_MAP` maps 11 of 16 `NodeKind` members, dropping `anti_pattern`,
`asset`, `glossary`, `glossary_pack`, `glossary_scope`. An unmapped kind must raise, not vanish.
It lands here rather than in WP03 because the ownership map forbids two WPs sharing `extractor.py`,
and C-009 requires the writer fix (T016) to land in the same commit as the model — so the file has
to belong to this WP. Verified graph-neutral today: no artefact references any dropped kind. The gap
goes live when mission C authors its 2 anti-patterns and 4 assets.

### Subtask T018 – Failing-first test.

An unknown field is currently accepted silently on all three models. Prove it.

### Subtask T019 – `extra="forbid"` on `DRGNode` and `DRGEdge`.

`model_config = ConfigDict(extra="forbid")`.

### Subtask T020 – `extra="forbid"` on `AgentProfile`.

Same, in `agent_profiles/profile.py`.

### Subtask T021 – Round-trip test.

A new `DRGEdge` field survives `_edge_to_dict` → read. **The writers are field-by-field, so this is the assertion that matters.**

### Subtask T022 – Coverage gate.

Prove the round-trip is exercised (C-001). Model + writer + round-trip land in **ONE commit**.

## Test Strategy

- `PYTHONPATH=src python -m pytest tests/doctrine/drg/ -q`
- `PYTHONPATH=src python -m pytest tests/architectural/test_no_inert_schema_slots.py -q` — WP01's lint must stay green.

## Risks & Mitigations

- `extra="forbid"` may surface existing extra fields in shipped YAML. If so, each is a finding: fix the artefact or the model, and **do not** relax the config.
- Landing the model without the writer ships a field that loads and never persists.

## Review Guidance

- Verify red→green: the WP's first commit was RED on `remediation/doctrine-silence-guards` and is GREEN at the final commit.
- Verify every gate added is **non-vacuous**: it must reject a planted violation, and its allowlist must be empty.
- Verify the graph invariant where the WP claims it (311 nodes / 774 edges).

## Activity Log

> **CRITICAL**: entries in chronological order, oldest first. **Append** new entries at the END.

- 2026-07-26T19:45:15Z – system – Prompt created.
