---
work_package_id: WP06
title: Activation identifier normalization
dependencies: []
requirement_refs:
- C-006
- C-009
- FR-017
- NFR-002
- NFR-005
planning_base_branch: feat/doctrine-delivery-reachability
merge_target_branch: feat/doctrine-delivery-reachability
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-reachability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-reachability unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-doctrine-delivery-reachability-01KYMXD6
base_commit: 6e5d3ee65958fbcd6dc74dbc4b9be524567f580d
created_at: '2026-07-28T21:55:20.753274+00:00'
subtasks:
- T031
- T032
- T033
- T034
phase: Phase 3 - Activation
history:
- at: '2026-07-28T19:48:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/charter/activation/pack_context.py
create_intent:
- tests/charter/test_activation_identifier_normalization.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/activation/pack_context.py
- tests/charter/test_activation_identifier_normalization.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP06 — Activation identifier normalization

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile named in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

Resolve it with **`spec-kitty agent profile show python-pedro`**. **Do not read the raw `*.agent.yaml`**.

---

## Objective

Reconcile the activation store's identifier form with the selector form at a **single boundary**, as a
**separate declared change** that is explicitly **excluded from any reachability-progress claim**
(C-009).

## Context — why this is its own WP, landing before WP08

The activation store holds directives as `025-boy-scout-rule`; DRG nodes are
`directive:DIRECTIVE_025`. Counting unmatched ids as unreachable inflates the "unreachable" set by
roughly 25 artefacts. Normalizing the form moves that count with **zero change in reachability**.

That is a trap, not progress: a reviewer could "reduce the unreachable count by 25" and claim SC-005
without wiring anything. So:
- This normalization lands **before** WP08 pins any named set, or the pin is immediately stale.
- Its effect is **declared and partitioned** so it can never be banked as reachability progress.

Read [`research/squad-findings-and-corrections.md`](../research/squad-findings-and-corrections.md)
finding on SC-005 fakeability, and C-009.

## Subtasks

### T031 — Normalize the identifier form at one boundary
1. Identify where the store form and selector form meet (`pack_context.py` activation read).
2. Normalize at exactly one place — do not scatter `.replace()` calls.
3. An identifier in either form resolves to the same node.

### T032 — Declare the normalization; exclude it from progress (C-009)
1. Document the normalization explicitly where the activation set is computed.
2. Ensure the reachability measure (WP08 will pin it) can subtract this effect — the count delta from
   normalization is reported separately and never counted as "artefacts made reachable".

### T033 — Partition the measured set
1. Partition activated-but-unreachable into `{not-a-node, node-but-unreachable}`.
2. `not-a-node` is the ~25 that normalization addresses; `node-but-unreachable` is the real target of
   FR-015's wiring. The partition is the artefact WP08 pins.

### T034 — Red-first
1. An identifier in the store form that does not resolve today resolves after normalization, OR fails
   naming the accepted form. Write the failing test first.

## Branch Strategy

Planning base and merge target `feat/doctrine-delivery-reachability`. No inbound dependency — starts
immediately. **WP08 depends on this landing first.** `spec-kitty implement WP06` resolves the
workspace.

## Test strategy

```bash
PWHEADLESS=1 pytest tests/charter/test_activation_identifier_normalization.py tests/charter/test_config_sourced_derivation.py -q
```

## Definition of Done

- [ ] Store-form and selector-form identifiers resolve to the same node, at one boundary
- [ ] The normalization is documented and its count effect is separable
- [ ] The measured set is partitioned `{not-a-node, node-but-unreachable}`
- [ ] The change is landable and testable independently, and cannot be banked as SC-005 progress
- [ ] A red commit precedes each green commit (C-006)
- [ ] `ruff` + `mypy --strict` clean

## Risks

| Risk | Mitigation |
|---|---|
| Normalization banked as reachability progress | C-009 — partition and exclude explicitly |
| Landing after WP08 pins the set | Ordering: this lands first |
| Scattered `.replace()` calls | One boundary only |

## Reviewer guidance

1. Confirm the normalization is at one site.
2. Confirm the partition exists and that `not-a-node` is excluded from any SC-005 claim.
3. Confirm no reachability count is claimed as improved by this WP.
