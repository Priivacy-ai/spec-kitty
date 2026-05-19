---
work_package_id: WP02
title: Charter Sync Extensions (extract selected_<kind> + activations)
dependencies:
- WP01
requirement_refs:
- FR-004
- FR-006
- NFR-005
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T009
agent: "claude:opus-4-7:reviewer-renata:reviewer"
agent_profile: python-pedro
authoritative_surface: src/charter/extractor.py
execution_mode: code_change
owned_files:
- src/charter/extractor.py
- src/charter/sync.py
- tests/charter/test_extractor_selection.py
- tests/charter/test_extractor_activations.py
role: implementer
history: []
tags: []
shell_pid: "1666985"
---

## Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Teach `charter.extractor` to read the 5 new `selected_<kind>` fields and the new top-level `activations:` block from `charter.md`'s fenced YAML resolution-hints block. Round-trip both surfaces through `governance.yaml`.

After this WP, a user can write `selected_styleguides: [caveman-comments]` in their charter and a follow-up `spec-kitty charter sync` will persist it. Rendering happens in WP04 / WP05.

---

## Context

Today's `_apply_selection_row` (in `src/charter/extractor.py:435`) handles only the 3 existing `selected_<kind>` fields plus `available_tools` and `template_set`. The pattern is to use `_get_list_value(normalized, ("<canonical>", "<alias>"))` per field and assign to the `DoctrineSelectionConfig` instance.

The activation registry is a sibling top-level block in the charter YAML (not inside the doctrine selection block). It needs a new applier method and a new field on `GovernanceConfig`.

See:
- [plan.md §2.3](../plan.md)
- [contracts/selection-schema.md](../contracts/selection-schema.md)
- [contracts/activation-registry.md](../contracts/activation-registry.md)

---

## Branch Strategy

- **Planning/base**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Implement command**: `spec-kitty agent action implement WP02 --agent claude`

---

## Subtasks

### T006 — Extend `_apply_selection_row`

**File**: `src/charter/extractor.py`

Extend the existing method to read the 5 new fields. Pattern mirrors the existing `selected_paradigms` / `selected_directives` / `selected_tactics` lines (lines 439–449):

```python
styleguides = self._get_list_value(normalized, ("selected_styleguides", "styleguides"))
if styleguides:
    doctrine.selected_styleguides = styleguides

toolguides = self._get_list_value(normalized, ("selected_toolguides", "toolguides"))
if toolguides:
    doctrine.selected_toolguides = toolguides

procedures = self._get_list_value(normalized, ("selected_procedures", "procedures"))
if procedures:
    doctrine.selected_procedures = procedures

agent_profiles = self._get_list_value(
    normalized, ("selected_agent_profiles", "agent_profiles", "agent-profiles")
)
if agent_profiles:
    doctrine.selected_agent_profiles = agent_profiles

mission_step_contracts = self._get_list_value(
    normalized,
    ("selected_mission_step_contracts", "mission_step_contracts", "mission-step-contracts"),
)
if mission_step_contracts:
    doctrine.selected_mission_step_contracts = mission_step_contracts
```

### T007 — Add `_apply_activations_block` handler

**File**: `src/charter/extractor.py`

Add a new method that reads the top-level `activations:` key from a parsed YAML block and produces a list of `ActivationEntry` instances:

```python
def _apply_activations_block(
    self, parsed_yaml: dict[str, Any], governance: GovernanceConfig
) -> None:
    activations_raw = parsed_yaml.get("activations")
    if not isinstance(activations_raw, list):
        return
    from charter.activations import ActivationEntry
    entries: list[ActivationEntry] = []
    for item in activations_raw:
        if not isinstance(item, dict):
            continue
        try:
            entries.append(ActivationEntry.model_validate(item))
        except Exception as exc:  # noqa: BLE001
            # Surface a clear error; resolution failures are recoverable in
            # the prompt path. Validation failures must be loud.
            raise ValueError(
                f"charter activations: invalid entry {item!r}: {exc}"
            ) from exc
    if entries:
        governance.activations = entries
```

Call the new method from the same code path that currently calls `_apply_selection_row` on a parsed fenced YAML block.

### T008 — Add `activations` field to `GovernanceConfig`

**File**: `src/charter/schemas.py`

Add the top-level field:

```python
class GovernanceConfig(BaseModel):
    ...
    activations: list["ActivationEntry"] = Field(default_factory=list)
```

Import `ActivationEntry` via `from charter.activations import ActivationEntry` (`schemas.py` already lives in `src/charter/`; same-package import).

Extend `_OPTIONAL_EMPTY_OMIT_KEYS` with `"activations"` so an empty list omits the block from `governance.yaml`.

### T009 — Unit tests for extractor

**Files**: `tests/charter/test_extractor_selection.py`, `tests/charter/test_extractor_activations.py`

Fixtures and assertions:

- `selected_styleguides: [caveman-comments]` in a fenced YAML block → after extraction, `governance.doctrine.selected_styleguides == ["caveman-comments"]`. Round-trip through `governance.yaml` preserves the field.
- Mixed fixture with all 8 `selected_<kind>` fields populated round-trips losslessly.
- `activations:` block with one entry produces a `GovernanceConfig.activations` list of length 1 with the right `activation_context`, `doctrine_pack_id`, `artifact_id`.
- Invalid entry (e.g. `mission_type: dev` typo) raises `ValueError` during extraction.
- Empty charter (no `selected_<kind>` and no `activations:`) round-trips byte-identical to today.

---

## Definition of Done

- ✅ `tests/integration/test_user_doctrine_artifact_lifecycle.py::test_case_1_selected_styleguides_field_round_trips` turns GREEN
- ✅ New unit tests cover all 5 new selection fields round-tripping
- ✅ `governance.yaml` byte-stability for empty fixtures (NFR-005 regression check)
- ✅ `tests/specify_cli/next/test_wp_prompt_governance_contract.py` — 23/23 stays green
- ✅ `tests/architectural/test_layer_rules.py` — 8/8 stays green

---

## Risks

| Risk | Mitigation |
|------|------------|
| Charter has `selected_styleguides` AND aliased `styleguides` — which wins? | Precedence matches existing pattern: the prefixed key wins via `_get_list_value` candidate ordering. Test with both-set fixture. |
| Activations block at unexpected nesting depth (e.g. nested under `doctrine:`) | This WP supports top-level only. Document in the contract; reject nested with a clear ValueError. |
| Extractor changes break existing charter fixtures | The 23-test ATDD suite is the gate. Run before commit. |

---

## Reviewer Guidance

- Verify the alias tuple for each new field — `selected_<kind>` MUST be the canonical first entry.
- Verify the activations applier is called from the same code path that applies the doctrine row (so a single fenced YAML block can carry both).
- Verify `_OPTIONAL_EMPTY_OMIT_KEYS` covers `activations` so empty fixtures stay byte-identical.

## Activity Log

- 2026-05-17T16:38:10Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1645548 – Started implementation via action command
- 2026-05-17T16:47:25Z – claude:opus-4-7:python-pedro:implementer – shell_pid=1645548 – Sync extensions: 5 selected_<kind> fields + activations block round-trip; case-1 lifecycle test green; layer rule intact
- 2026-05-17T16:48:00Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1666985 – Started review via action command
- 2026-05-17T16:52:03Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1666985 – Review passed: 5 selected_<kind> parity + activations block round-trip + validation. case_1_selected_styleguides_field_round_trips ATDD green. extractor.py confirmed as correct source location (no separate sync.py). 18 new unit tests, all green.
