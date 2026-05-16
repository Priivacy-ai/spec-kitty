---
work_package_id: WP01
title: Schema extensions for Directive.references and authority_paths
dependencies: []
requirement_refs:
- FR-006
- FR-008
- NFR-005
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-wp-prompt-governance-payload-01KRR8HS
base_commit: 3d1b1e7103382aa79a8961783ecea07cf342d6fe
created_at: '2026-05-16T11:50:28.893125+00:00'
subtasks:
- T001
- T002
- T003
agent: "claude:opus-4-7:python-pedro:implementer"
shell_pid: "1083623"
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/schemas.py
execution_mode: code_change
owned_files:
- src/charter/schemas.py
- tests/charter/test_schemas_additive_fields.py
role: implementer
tags: []
---

## Objective

Add two additive, default-empty fields to the charter pydantic schemas so that downstream
work packages can populate them without requiring any non-additive migration:

1. `Directive.references: list[str] = []` — catalog IDs (e.g. `DIRECTIVE_032`) cross-linked
   from the body of a charter-extracted directive.
2. `DoctrineSelectionConfig.authority_paths: list[str] = []` — repository-relative
   directories the prompt surfaces as authority pointers (e.g. `glossary/contexts/`).

This WP is **pure schema** with zero runtime behaviour change. NFR-005 (backwards
compatibility) is satisfied by construction: existing YAML files without the new fields
deserialize unchanged, and serialization preserves the empty-list default.

---

## Context

Two later WPs depend on these fields:

- WP02 (charter sync) populates `Directive.references` from cited catalog IDs detected in
  the directive body, and populates `DoctrineSelectionConfig.authority_paths` from the
  charter's fenced YAML block (FR-007 / FR-008).
- WP04 (rendering) reads `DoctrineSelectionConfig.authority_paths` when building the
  `Project authority paths:` section of the bootstrap context.

Doing the schema change as its own WP keeps the diff trivial and lets WP02 and WP03 start
in parallel.

---

## Branch Strategy

- **Planning/base branch**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Worktree**: allocated by `finalize-tasks`; check `lanes.json` for your lane
- **Implement command**: `spec-kitty agent action implement WP01 --agent claude`

---

## Subtask T001 — Add `references: list[str] = []` to `Directive`

**File**: `src/charter/schemas.py`

Locate the `Directive` pydantic model. Add an additive field:

```python
class Directive(BaseModel):
    id: str
    title: str
    description: str
    severity: Literal["info", "warn", "error"] = "warn"
    references: list[str] = []   # NEW — catalog IDs (e.g. ["DIRECTIVE_032"])
```

Field semantics: each entry is a string ID matching either the doctrine-catalog
directive namespace (`DIRECTIVE_\d{3}`) or a tactic-id slug. The resolver in WP03/WP04
looks each entry up via `DoctrineService` and surfaces the body.

---

## Subtask T002 — Add `authority_paths: list[str] = []` to `DoctrineSelectionConfig`

**File**: `src/charter/schemas.py`

Locate `DoctrineSelectionConfig`. Add the additive field:

```python
class DoctrineSelectionConfig(BaseModel):
    selected_paradigms: list[str] = []
    selected_directives: list[str] = []
    selected_tactics: list[str] = []
    available_tools: list[str] = []
    template_set: str | None = None
    authority_paths: list[str] = []   # NEW
```

Each entry is a repository-relative directory string (e.g. `glossary/contexts/`). The
renderer in WP04 only surfaces paths that exist on disk.

---

## Subtask T003 — Schema round-trip + backward-compat tests

**File**: `tests/charter/test_schemas_additive_fields.py` (new)

| Test | Scenario | Expectation |
|---|---|---|
| `test_directive_round_trip_without_references` | Existing YAML lacks `references:` | Loads with `references == []`; re-serializes identical bytes when round-tripped via `model_dump(exclude_defaults=True)` |
| `test_directive_round_trip_with_references` | YAML carries `references: [DIRECTIVE_032]` | Loads with `references == ["DIRECTIVE_032"]` |
| `test_doctrine_selection_round_trip_without_authority_paths` | Existing YAML lacks `authority_paths:` | Loads with `authority_paths == []` |
| `test_doctrine_selection_round_trip_with_authority_paths` | YAML carries `authority_paths: [glossary/contexts/, architecture/2.x/adr/]` | Loads with the list intact |
| `test_existing_directives_yaml_fixture_still_loads` | Load any existing `.kittify/charter/directives.yaml` fixture (or copy of) | No `ValidationError` |

---

## Definition of Done

- [ ] `src/charter/schemas.py::Directive` carries `references: list[str] = []`.
- [ ] `src/charter/schemas.py::DoctrineSelectionConfig` carries `authority_paths: list[str] = []`.
- [ ] `tests/charter/test_schemas_additive_fields.py` exists and passes (5 tests).
- [ ] All existing tests under `tests/charter/` still pass.
- [ ] `tests/architectural/test_layer_rules.py` (8 tests) still passes (NFR-004).
- [ ] No call site is required to change in this WP; both fields are read-only-default in WP01.

This WP is preparatory; no ATDD tests in `tests/specify_cli/next/test_wp_prompt_governance_contract.py`
turn green here. WP02 and WP03 depend on these schema additions.

---

## Risks

- **R-1**: Forgetting to default-construct the list (e.g. mistakenly typing
  `references: list[str]` without `= []`) would force every existing YAML file to declare
  the field. **Mitigation**: explicit `= []` default; test
  `test_directive_round_trip_without_references` is the gate.
- **R-2**: A consumer that uses `model_dump()` without `exclude_defaults=True` will emit
  the empty list into freshly-written YAML, changing bytes-on-disk for missions that never
  touched these fields. **Mitigation**: the existing sync writer already uses
  `exclude_defaults=True` (verify in WP02 review); document the constraint in the
  reviewer guidance below.

---

## Reviewer Guidance

Check that:

1. Both new fields use `= []` (default-empty list), not bare type annotations.
2. The order of fields in `DoctrineSelectionConfig` keeps `authority_paths` at the end
   (additive at the end is the convention for forward-compat).
3. No other module in this WP gains an import of `references` or `authority_paths` — this
   is a pure schema change.
4. The existing YAML fixtures under `tests/charter/fixtures/` (if any) load without
   modification.
5. Architectural layer tests still pass — no new `specify_cli` import has crept into
   `charter/`.

## Activity Log

- 2026-05-16T11:50:29Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1083623 – Assigned agent via action command
