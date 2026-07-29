---
work_package_id: WP05
title: Schema-generation integrity
dependencies:
- WP01
requirement_refs:
- FR-005
planning_base_branch: remediation/doctrine-silence-guards
merge_target_branch: remediation/doctrine-silence-guards
branch_strategy: Planning artifacts for this mission were generated on remediation/doctrine-silence-guards. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/doctrine-silence-guards unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
- T027
phase: Phase 1 - Guards
history:
- at: '2026-07-26T19:45:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: scripts/generate_schemas.py
create_intent:
- tests/doctrine/test_schema_generation_integrity.py
execution_mode: code_change
model: ''
owned_files:
- scripts/generate_schemas.py
- src/doctrine/schemas/paradigm.schema.yaml
- src/doctrine/schemas/tactic.schema.yaml
- src/doctrine/schemas/directive.schema.yaml
- src/doctrine/schemas/procedure.schema.yaml
- src/doctrine/schemas/styleguide.schema.yaml
- src/doctrine/schemas/toolguide.schema.yaml
- src/doctrine/schemas/mission.schema.yaml
- tests/doctrine/test_schema_generation_integrity.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 – Schema-generation integrity

## ⚡ Do This First: Load Agent Profile

Load the `python-pedro` profile via `/ad-hoc-profile-load` and behave according to its guidance before parsing the rest of this prompt.

---

## Objectives & Success Criteria

- `scripts/generate_schemas.py --check` **exits 0** on the reconciled tree.
- `structural_lint_config` is emitted by the generator; `point_in_time_marker` has a recorded adjudication.

**Requirement refs**: FR-005, SC-004

## Context & Constraints

Measured: `--check` **exits 1 today with 7 stale schemas**. Three divergence classes, **only one safe to accept**.

| Divergence | Disposition |
|---|---|
| `enhances`/`overrides` removed | **Safe** — finishes a half-done excision |
| `structural_lint_config` removed | **Generator bug — fix the generator.** It is a real declared field (`styleguides/models.py:92`) the generator fails to emit; accepting the deletion invalidates `common-docs.styleguide.yaml` |
| `point_in_time_marker` removed | Declared in **no model**, used by a shipped artefact — **adjudicate** |

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

### Subtask T023 – Failing-first test.

`--check` exits 1 with 7 stale schemas. Pin it.

### Subtask T024 – Fix the generator.

Emit `structural_lint_config`. **Do not accept its deletion** — that would invalidate a shipped artefact.

### Subtask T025 – Adjudicate `point_in_time_marker`.

Declared in no model, used by a shipped artefact — silently ignored today because the models lack `extra="forbid"`. Either add it to the model or remove it from the artefact. **Decide and record; do not regenerate blindly.**

### Subtask T026 – Verify the `paradigm_reference` rename.

A definition rename `reference` → `paradigm_reference`; confirm every `$ref` target resolves. `mission_step_template_ref` is newly emitted.

### Subtask T027 – Regenerate.

The 7 stale schemas, after T024–T026 — not before.

## ⚠️ Binding handoff from WP01's review — you will hit a floor, and how you fix it is checked

WP01's zero-producer lint carries two baseline-entry floors. **Excising the retired
`enhances`/`overrides` schema properties (T024) deletes 8 schema-side baseline entries and takes
that count 36 → 28 against a floor of 30. It will go red. That red is correct — your change is
correct — and it is a scheduled false-red, not a defect you introduced.**

**Do NOT hand-lower the floor 30 → 24.** The assertion message currently invites exactly that
("lower the floor deliberately in the same change"), and taking it at face value is how floors rot.
The two entry floors are absolute counts of a quantity this mission exists to drive to zero, so they
drop for two unrelated reasons — the producer scan broke, or someone paid the debt — and an author
who lowers one because it went red, without establishing which, erodes the gate.

**Convert them to the proportional form instead**, in `tests/architectural/_inert_slots.py`:

```python
# instead of an absolute MINIMUM_*_BASELINE_ENTRIES_STILL_FOUND
assert len(schema_entries) >= 0.8 * len(
    [e for e in baseline.entries if is_schema_declared(e.slot)]
)
```

Today 36/36 passes; after your excision 28/28 still passes with **no floor edit**; and the failure
mode the floors actually exist for still fires. WP01's reviewer verified that last point with a
mutation the implementer had not run: readmitting the generated schemas as producers gives
`0 schema-declared baseline entries … the floor is 30`. **That class is caught by the entry floors
and by nothing else** — it is the original vacuity bug that made the first version of the checker
useless. So the floors must not be deleted, only made burn-down-native.

**Reviewer of this WP:** check which of the two happened. A hand-lowered floor is a reject.

## Test Strategy

- `PYTHONPATH=src python scripts/generate_schemas.py --check` → must exit 0
- `PYTHONPATH=src python -m pytest tests/doctrine/ -q`

## Risks & Mitigations

- **Wiring the gate before this reconciliation puts a red gate on the branch** and invites someone to 'fix' it by accepting a regeneration that deletes valid schema. That is why WP10 does the wiring, after this lands.
- T025 is a judgement call — record the reasoning, do not silently pick.

## Review Guidance

- Verify red→green: the WP's first commit was RED on `remediation/doctrine-silence-guards` and is GREEN at the final commit.
- Verify every gate added is **non-vacuous**: it must reject a planted violation, and its allowlist must be empty.
- Verify the graph invariant where the WP claims it (311 nodes / 774 edges).

## Activity Log

> **CRITICAL**: entries in chronological order, oldest first. **Append** new entries at the END.

- 2026-07-26T19:45:15Z – system – Prompt created.
