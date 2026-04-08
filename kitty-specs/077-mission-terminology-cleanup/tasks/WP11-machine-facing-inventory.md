---
work_package_id: WP11
title: Machine-Facing Inventory (Scope B Start)
dependencies:
- WP10
requirement_refs:
- FR-014
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T047
- T048
- T049
- T050
history:
- actor: system
  at: '2026-04-08T12:45:50Z'
  event: created
authoritative_surface: kitty-specs/077-mission-terminology-cleanup/research/
execution_mode: planning_artifact
mission_slug: 077-mission-terminology-cleanup
owned_files:
- kitty-specs/077-mission-terminology-cleanup/research/scope-b-inventory.md
priority: P1
tags: []
---

# WP11 — Machine-Facing Inventory (Scope B Start)

> ⚠️ **GATED**: This WP cannot start until WP10 is merged on `main`. Per spec §2 + C-004, Scope B is hard-gated on Scope A acceptance.

## Objective

Inventory every first-party machine-facing surface that emits or accepts tracked-mission identity. Identify residual `feature_*` payload fields. Cross-reference findings with `src/specify_cli/core/upstream_contract.json`. Produce a Scope B alignment plan that informs WP12 and WP13.

This is a **planning artifact** WP — no source code changes.

## Context

Scope A (`#241`, WP01-WP10) cleaned up the operator-facing CLI. Scope B (`#543`, WP11-WP13) cleans up the machine-facing contracts. The two are sequenced because:
1. Scope A gives Scope B a stable canonical operator vocabulary to reason against.
2. The machine-facing contract changes have downstream consumer impact (orchestrator, SaaS, hub, tracker, runtime, events projections, dashboards) and need a stable starting state.

The verified upstream contract facts from spec §8.4:
- `mission_slug`, `mission_number`, and `mission_type` are canonical in `spec-kitty-events 3.0.0`
- `MissionCreated` and `MissionClosed` are canonical event names
- Scan at validation time: `mission_slug` in 110 files in `spec-kitty-events`, `mission_run_slug` in 0, `MissionCreated` in 15, `MissionRunCreated` in 0

Scope B's job is to bring `spec-kitty`'s first-party machine-facing surfaces into alignment with this canonical state.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution worktree**: created by `spec-kitty implement WP11` from the lane assigned by `lanes.json`.

## Detailed Subtasks

### T047 — Inventory first-party machine-facing surfaces emitting tracked-mission identity

**Purpose**: Find every first-party Python module that emits a JSON/dict payload identifying a tracked mission.

**Steps**:
1. Search for surfaces that produce JSON containing tracked-mission identity:
   ```bash
   grep -rn '"feature_slug"\|"feature_number"\|"feature_type"' src/specify_cli/
   grep -rn '"mission_slug"\|"mission_number"\|"mission_type"' src/specify_cli/
   ```
2. For each match, classify by surface:
   - Orchestrator-api commands (`src/specify_cli/orchestrator_api/**`)
   - Status events (`src/specify_cli/status/**`)
   - Agent CLI emitters (`src/specify_cli/agent/**`, `src/specify_cli/cli/commands/agent/**`)
   - Runtime bridge (`src/specify_cli/next/runtime_bridge.py` if present)
   - Other first-party JSON producers
3. Record each surface with: file path, function name, payload field names, classification.

### T048 — Identify residual `feature_*` fields in payloads

**Purpose**: Find every payload field that still uses the legacy `feature_*` naming.

**Steps**:
1. From the T047 inventory, isolate any surface that emits `feature_slug`, `feature_number`, `feature_type`, or any other `feature_*` field.
2. For each, capture:
   - The exact field name
   - Which surface emits it
   - Whether `mission_slug`/`mission_number`/`mission_type` are also present (dual-write) or absent
   - Whether `upstream_contract.json` lists this field as forbidden
3. Decide for each field: **remove**, **dual-write** (gate behind a compatibility alias), or **mark deprecated** (with a documented removal date).

### T049 — Cross-reference findings with `upstream_contract.json`

**Purpose**: Confirm the canonical state defined by the upstream contract.

**Steps**:
1. Read `src/specify_cli/core/upstream_contract.json` and note the forbidden field lists per surface:
   - `envelope.forbidden_fields`: `["feature_slug", "feature_number"]`
   - `payload.mission_scoped.forbidden_fields`: `["feature_slug", "feature_number", "feature_type"]`
   - `body_sync.forbidden_fields`: `["feature_slug", "mission_key"]`
   - `orchestrator_api.forbidden_payload_fields`: `["feature_slug"]`
2. For each surface in the T047/T048 inventory, look up the matching contract section and confirm the field is forbidden upstream.
3. Any surface emitting a forbidden field is a **drift** that Scope B must resolve.
4. Any surface emitting a field that the upstream contract requires (e.g., `mission_slug`) but currently does NOT is also a **drift**.

### T050 — Produce Scope B alignment plan

**Purpose**: Write the inventory + decisions as a research artifact that WP12 and WP13 consume.

**Steps**:
1. Create `kitty-specs/077-mission-terminology-cleanup/research/scope-b-inventory.md`:

   ```markdown
   # Scope B: Machine-Facing Inventory and Alignment Plan

   **Mission**: 077-mission-terminology-cleanup
   **Scope**: Scope B (issue #543)
   **Date**: <DATE>
   **HEAD commit**: <git rev-parse HEAD>

   ## Surfaces Inventory

   | Surface | File | Function | Current fields | Required fields (per upstream) | Drift? |
   |---|---|---|---|---|---|
   | ... | ... | ... | ... | ... | ... |

   ## Residual `feature_*` Fields

   | Field | Surface | Decision | Rationale |
   |---|---|---|---|
   | feature_slug | <file>:<function> | remove | <reason> |
   | feature_number | <file>:<function> | dual-write | <reason> |
   | ... | ... | ... | ... |

   ## Upstream Contract Mapping

   | upstream_contract.json section | Forbidden fields | Required fields | First-party surfaces |
   |---|---|---|---|
   | envelope | feature_slug, feature_number | schema_version, ... | <list> |
   | ... | ... | ... | ... |

   ## Alignment Plan (input to WP12)

   ### Field changes
   ...

   ### Compat gating
   ...

   ### Removal-date assignments
   ...

   ## Constraints (locked)

   - C-008: no abstraction that makes a future Mission → MissionRun rename easier
   - C-009: no `mission_run_slug` field
   - C-010: no widening of orchestrator-api envelope
   - All §3.3 non-goals stay locked
   ```

2. Fill in every section with actual data from T047/T048/T049.

3. Commit to `kitty-specs/077-mission-terminology-cleanup/research/scope-b-inventory.md`.

## Files Touched

| File | Action | Notes |
|---|---|---|
| `kitty-specs/077-mission-terminology-cleanup/research/scope-b-inventory.md` | CREATE | Inventory + alignment plan |

No source code changes in this WP.

## Definition of Done

- [ ] All first-party machine-facing surfaces emitting tracked-mission identity are inventoried
- [ ] Every residual `feature_*` field is identified with a remove/dual-write/deprecate decision
- [ ] Cross-reference with `upstream_contract.json` is complete
- [ ] `scope-b-inventory.md` exists and documents the alignment plan
- [ ] WP12 and WP13 can start from this plan without re-discovering the inventory

## Risks and Reviewer Guidance

**Risks**:
- The inventory could miss a surface if its payload field is generated dynamically (e.g., from a dict comprehension). Use both grep and code-reading to find them.
- A surface might use `feature_*` internally but expose `mission_*` externally. That's fine — only externally exposed fields matter for Scope B.

**Reviewer checklist**:
- [ ] Inventory covers `orchestrator_api/**`, `status/**`, `agent/**`, `next/**`, and any other first-party JSON producer
- [ ] Decisions for each `feature_*` field have rationale
- [ ] Cross-reference table is accurate against the current `upstream_contract.json`
- [ ] No source code is modified

## Implementation Command

```bash
spec-kitty implement WP11
```

This WP depends on WP10. **Do not start until WP10 is merged on `main`.** Per spec §2 + C-004, Scope B is hard-gated.

## References

- Spec §2 — Sequencing rule
- Spec §8.4 — Verified upstream contract facts
- Spec §13.2 — Scope B work package outline
- `src/specify_cli/core/upstream_contract.json` — authoritative contract
- WP10 — Scope A acceptance gate (must be green)

## Activity Log

- 2026-04-08T15:01:36Z – unknown – Done override: Mission completed in main checkout
