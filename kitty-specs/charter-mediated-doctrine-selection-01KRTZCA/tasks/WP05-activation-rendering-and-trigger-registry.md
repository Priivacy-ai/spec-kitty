---
work_package_id: WP05
title: Activation Registry Rendering + Trigger Registry Population
dependencies:
- WP04
requirement_refs:
- FR-007
- FR-009
- NFR-001
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T024
- T024a
- T025
agent: claude
agent_profile: python-pedro
authoritative_surface: src/charter/_activation_render.py
execution_mode: code_change
owned_files:
- src/charter/_activation_render.py
- src/charter/activations.py
- tests/architectural/test_trigger_registry_coverage.py
- tests/charter/test_context_activation_render.py
role: implementer
history: []
tags: []
---

## Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Add the context-scoped activation renderer: when the resolver builds the implement-prompt governance payload, it filters the merged activation registry by current `(mission_type, action)` and emits one when-doing stanza per match. Populate `_REGISTERED_TRIGGERS` with the 15-token frozenset resolved at plan time.

After this WP, Case 1 step 5 — *"when writing a code comment, fetch caveman"* — works for software-dev missions.

---

## Context

WP01 introduced `ActivationEntry` + `resolve_for_context`. WP02 made the extractor populate `GovernanceConfig.activations`. This WP wires that data into the prompt builder.

The Trigger Registry (FR-009 + C-005) is populated at this WP per plan §2.10. The 15-token set is the architectural gate that prevents dead triggers in shipped artifacts.

See:
- [plan.md §2.4, §2.10](../plan.md)
- [data-model.md §7](../data-model.md)
- [contracts/activation-registry.md](../contracts/activation-registry.md)

---

## Branch Strategy

- **Planning/base**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Implement command**: `spec-kitty agent action implement WP05 --agent claude`

---

## Subtasks

### T022 — Add `_render_activation_stanza` helper

**File**: `src/charter/context.py`

Helper signature:

```python
def _render_activation_stanza(
    entry: ActivationEntry,
    *,
    mission_type: str,
    action: str,
    service: DoctrineService,
) -> str:
    """Render one activation entry as a 'when you <action> in a <mission_type> ...' line.

    Wildcard handling: when activation_context.mission_type / .action is absent
    or 'generic'/'any', the rendered line omits that qualifier (reads as
    "When you <action>, ...").
    """
    declared_mt = entry.activation_context.get("mission_type")
    declared_action = entry.activation_context.get("action")

    qualifier = ""
    if declared_mt not in (None, "generic", "any"):
        qualifier = f" in a {declared_mt} mission"

    action_label = declared_action if declared_action not in (None, "generic", "any") else action

    kind = entry.artifact_kind or _infer_kind(entry.artifact_id, service)
    return (
        f"When you {action_label}{qualifier}, run "
        f"`spec-kitty charter context --include {kind}:{entry.artifact_id}` "
        f"and apply the returned rule."
    )
```

`_infer_kind` is a helper that inspects `DoctrineService` repositories to find which kind owns the given artifact_id; raises `ValueError` if none match.

### T023 — Wire activation resolver into `build_charter_context`

After the global-selection renderers (WP04 land), add:

```python
from charter.activations import resolve_for_context

# Merged activations come from: governance.activations (project) +
# OrgCharterPolicy.activations (org) + MissionTypeProfile.activations (WP08).
# WP05 covers project + org sources; WP08 adds the profile source.
all_activations = list(governance.activations) + list(org_policy_activations)
matched = resolve_for_context(
    all_activations,
    mission_type=mission_type or "any",
    action=action,
)
activation_lines = [
    _render_activation_stanza(e, mission_type=mission_type, action=action, service=service)
    for e in matched
]
```

Concatenate `activation_lines` into the assembled context text under an `Activations:` header.

### T024 — Populate canonical frozensets and **MANDATORY** runtime re-export

**Files**:
- `tests/architectural/test_trigger_registry_coverage.py` (canonical home — see data-model.md §7)
- `src/charter/activations.py` (mandatory runtime re-export)

Per the canonical definition in [data-model.md §7](../data-model.md#7-trigger-registry-fr-009--canonical-definition), populate both canonical frozensets in the test file:

```python
# tests/architectural/test_trigger_registry_coverage.py
_ALLOWED_ACTIONS: frozenset[str] = frozenset({
    "specify", "plan", "tasks", "implement", "review", "merge", "accept",
    "charter.interview", "charter.generate", "charter.context",
})
_REGISTERED_TRIGGERS: frozenset[str] = _ALLOWED_ACTIONS | frozenset({
    "write_comment", "write_docstring", "rename_identifier", "add_dependency",
})
```

**MANDATORY** (not optional) — re-export both canonical frozensets from `src/charter/activations.py` as `ALLOWED_ACTIONS` and `REGISTERED_TRIGGERS` so the runtime resolver, prompt builder, and charter sync validator all consume one source. This replaces the prior "re-export if needed" wording and removes the copy/paste-drift attack surface:

```python
# src/charter/activations.py
# Re-export the canonical frozensets defined in
# tests/architectural/test_trigger_registry_coverage.py per data-model.md §7.
# DO NOT redefine the literals here.
from tests.architectural.test_trigger_registry_coverage import (
    _ALLOWED_ACTIONS as ALLOWED_ACTIONS,
    _REGISTERED_TRIGGERS as REGISTERED_TRIGGERS,
)
```

(If importing test-tree code into runtime is undesirable, instead relocate the canonical literals to a dedicated `src/charter/_trigger_vocabulary.py` module and import them back into the test file — the byte-identity contract is what matters, and the cross-check test in T024a enforces it either way.)

### T024a — Cross-check architectural test (MANDATORY deliverable)

**File**: `tests/architectural/test_trigger_registry_coverage.py`

Add the cross-check test `test_trigger_registry_runtime_export_in_sync` to the same file. It MUST assert byte-identical equality between the canonical frozensets and the `src/charter/activations.py` re-exports:

```python
def test_trigger_registry_runtime_export_in_sync() -> None:
    """Cross-check: the runtime re-export in charter.activations MUST be
    byte-identical to the canonical frozensets in this file. Pinning this
    eliminates the copy/paste-drift risk identified in analysis-report.md
    finding A1.
    """
    from charter.activations import ALLOWED_ACTIONS, REGISTERED_TRIGGERS

    assert ALLOWED_ACTIONS == _ALLOWED_ACTIONS, (
        "charter.activations.ALLOWED_ACTIONS drifted from the canonical "
        "_ALLOWED_ACTIONS in test_trigger_registry_coverage.py. See data-model.md §7."
    )
    assert REGISTERED_TRIGGERS == _REGISTERED_TRIGGERS, (
        "charter.activations.REGISTERED_TRIGGERS drifted from the canonical "
        "_REGISTERED_TRIGGERS in test_trigger_registry_coverage.py. See data-model.md §7."
    )
    assert isinstance(ALLOWED_ACTIONS, frozenset)
    assert isinstance(REGISTERED_TRIGGERS, frozenset)
```

This test is the architectural gate that makes the runtime re-export non-optional.

### T025 — Unit tests

**File**: `tests/charter/test_context_activation_render.py`

Coverage:

- One entry matching `(software-dev, implement)` renders one stanza with both qualifiers.
- One entry with only `action: write_comment` renders without mission_type qualifier.
- One entry with `mission_type: generic` renders without mission_type qualifier.
- Two entries matching the same context render two stanzas in declaration order (concatenation policy).
- Zero matches → no `Activations:` header emitted.
- Wildcard-only entry (`activation_context: {}`) matches every context.

---

## Definition of Done

- ✅ `tests/integration/test_user_doctrine_artifact_lifecycle.py::test_case_1_styleguide_render_includes_trigger_stanza` turns GREEN
- ✅ `tests/architectural/test_trigger_registry_coverage.py::test_every_declared_trigger_is_in_the_registered_set` stays GREEN with the populated set (still vacuous since no artifacts declare triggers yet — WP08 may add a first declaration)
- ✅ `tests/architectural/test_trigger_registry_coverage.py::test_registered_triggers_constant_is_a_frozenset_for_immutability` stays GREEN
- ✅ **NEW** `tests/architectural/test_trigger_registry_coverage.py::test_trigger_registry_runtime_export_in_sync` GREEN — pins the byte-identical equality between the canonical frozensets and the `src/charter/activations.py` re-exports (resolves analysis-report finding A1)
- ✅ `src/charter/activations.py` exposes `ALLOWED_ACTIONS` and `REGISTERED_TRIGGERS` as `frozenset[str]`, sourced from the canonical definition per data-model.md §7
- ✅ New unit tests cover stanza rendering with wildcards, multiple matches, and zero matches
- ✅ `tests/specify_cli/next/test_wp_prompt_governance_contract.py` — 23/23 stays green

---

## Risks

| Risk | Mitigation |
|------|------------|
| Trigger registry token set drifts between `_REGISTERED_TRIGGERS` and `charter.activations.ALLOWED_ACTIONS` | Optional cross-check test asserting `ALLOWED_ACTIONS ⊆ _REGISTERED_TRIGGERS`. |
| `_infer_kind` returns a wrong kind when an ID exists in two repositories | Operator must specify `artifact_kind` explicitly when ambiguity exists; helper raises `ValueError` on ambiguity. |
| Multiple matches stomp the prompt (verbosity creep) | Concatenation policy is in the contract; operator-tightenable. Document in WP09 user docs. |

---

## Reviewer Guidance

- Verify the rendered stanza phrasing matches the ATDD test's regex (`when you write (a )?(code )?comment`).
- Verify wildcard handling produces clean prose (no "When you implement in a generic mission" — drop the qualifier).
- Run the ATDD test for Case 1 step 5 explicitly — its assertion is layered (phrase + ID + fetch command).
