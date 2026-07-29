---
work_package_id: WP02
title: Graph document strictness and the org-tier bridge
dependencies:
- WP01
requirement_refs:
- C-006
- FR-001
- NFR-002
- NFR-005
- NFR-006
planning_base_branch: feat/doctrine-delivery-reachability
merge_target_branch: feat/doctrine-delivery-reachability
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-reachability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-reachability unless the human explicitly redirects the landing branch.
created_at: '2026-07-28T19:48:12Z'
subtasks:
- T008
- T009
- T010
- T011
phase: Phase 1 - Foundation
history:
- at: '2026-07-28T19:48:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/
create_intent:
- tests/doctrine/drg/test_org_pack_merge.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/models.py
- src/doctrine/drg/merge.py
- tests/doctrine/drg/test_model_strictness_roundtrip.py
- tests/doctrine/drg/test_org_pack_merge.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP02 — Graph document strictness and the org-tier bridge

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile named in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

Resolve it with **`spec-kitty agent profile show python-pedro`** — the *resolved* definition, with
lineage and `enhances`/`overrides` applied. **Do not read the raw `*.agent.yaml`**: it is the
unresolved base and drops exactly the doctrine this mission delivers.

---

## Objective

Close the two field-loss surfaces WP01 does not: unknown top-level graph-document keys accepted and
silently discarded, and the org-tier bridge that drops edge fields **before any writer runs**.

**This is a consumer-facing read-path break, and that is why it is a separate work package.** It must
NOT ride WP01's lane, which lands first and alone to unblock B1.

## Context

- `DRGGraph` (`src/doctrine/drg/models.py:390`) declares **no `model_config`**, so unknown top-level
  keys are accepted and dropped. `DRGNode` and `DRGEdge` both carry `extra="forbid"`; the container
  does not.
- `_bridge_org_edge_to_drg_edge` (`src/doctrine/drg/merge.py:848`) constructs
  `DRGEdge(source=…, target=…, relation=…)` from an org-fragment edge — a three-field restatement. Any
  additional edge field an org pack declares is lost on merge. WP01 registered it as a `ModelBridge`;
  this WP makes its field coverage an assertion.
- **Blast radius**: `src/charter/packs/default.yaml` ships to every consumer. An org-pack graph
  document with a stray top-level key goes from silently-accepted to a hard load failure on upgrade.
  This is intended, but it needs a typed error, not a bare `ValidationError`.

Read [`contracts/writer-registry.md`](../contracts/writer-registry.md) W-2 through W-4.

## Subtasks

### T008 — Add `extra="forbid"` to `DRGGraph`
1. Red-first: a graph document with an unknown top-level key currently loads; write the test that
   expects rejection.
2. Add `model_config = ConfigDict(extra="forbid")` to `DRGGraph`.
3. Verify all 14 shipped `src/doctrine/*.graph.yaml` fragments still load — they carry only declared
   keys, so built-ins are safe.

### T009 — Typed error and named diagnostic
1. Wrap the raised `ValidationError` at the load boundary into a typed, named error identifying the
   offending file and key (NFR-006 — fail-closed, named).
2. The diagnostic must name the document and the stray key, so a consumer can act on it.

### T010 — Join the org-tier bridge with a field-coverage assertion [P]
1. The bridge maps a foreign fragment shape to `DRGEdge`. Assert that **every `DRGEdge` field the
   fragment schema can express** is set on the minted edge (contract W-3).
2. Red-first: add a fragment field the bridge currently ignores; the assertion fails.
3. Extend the bridge to carry it.

### T011 — Consumer-facing regression tests
1. A fixture org-pack graph document with an unknown top-level key fails to load with the typed error.
2. A fixture org-pack edge with an extra declared field round-trips through the bridge without loss.
3. Confirm the error message is actionable (names file + key).

## Branch Strategy

Planning base and merge target: `feat/doctrine-delivery-reachability`. Depends on WP01 — branch from
WP01's landed state (the registry and derived helper must exist). `spec-kitty implement WP02` resolves
the workspace from `lanes.json`.

## Test strategy

```bash
PWHEADLESS=1 pytest tests/doctrine/drg/test_model_strictness_roundtrip.py tests/doctrine/drg/test_org_pack_merge.py -q
```

## Definition of Done

- [ ] `DRGGraph` rejects unknown top-level keys with a typed, named error
- [ ] All 14 shipped fragments still load
- [ ] The org bridge carries every fragment-expressible edge field, asserted by test
- [ ] A red commit precedes each green commit (C-006)
- [ ] The consumer-facing break is documented in the PR body for later merge review
- [ ] `ruff` + `mypy --strict` clean, zero new suppressions

## Risks

| Risk | Mitigation |
|---|---|
| Consumer org packs break on upgrade | Intended; typed error + named diagnostic + PR-body callout |
| Riding WP01's first-and-alone lane | This is a separate WP for exactly that reason — do not fold it back |

## Reviewer guidance

1. Craft an org-pack fragment with a stray top-level key; confirm the typed error names it.
2. Add a declared field to a bridge fragment; confirm it survives to the minted edge.
3. Confirm the 14 built-in fragments are untouched.
