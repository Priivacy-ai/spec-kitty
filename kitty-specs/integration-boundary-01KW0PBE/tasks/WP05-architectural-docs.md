---
work_package_id: WP05
title: Architectural documentation
dependencies:
- WP04
requirement_refs:
- FR-009
tracker_refs: []
planning_base_branch: feat/integration-boundary
merge_target_branch: feat/integration-boundary
branch_strategy: Planning artifacts for this mission were generated on feat/integration-boundary. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/integration-boundary unless the human explicitly redirects the landing branch.
subtasks:
- T020
phase: Phase 5 - documentation
assignee: ''
agent: ''
shell_pid: ''
authoritative_surface: architecture/
owned_files:
- architecture/
execution_mode: code_change
history:
- at: '2026-06-26T00:00:00Z'
  actor: system
  action: Prompt generated via spec-kitty.tasks
---

# Work Package Prompt: WP05 – Architectural documentation

## Objective

Add or update an architectural document under `architecture/` that records the
CORE and INTEGRATION set definitions, the one-directional rule, all allowlist
exemptions, and deferred scope items. A contributor must be able to read this
document once and understand the boundary model without reading the enforcement test.

---

## Prerequisites

WP04 must be merged first so the allowlist is finalised (exactly one entry) before
it is documented here.

---

## Subtasks

### T020 — Add/update architectural doc under `architecture/`

Follow the `architecture/README.md` template. Create (or update if an appropriate
file already exists):

```
architecture/<version>/integration-core-boundary.md
```

The document MUST cover all four items required by FR-009:

**a) CORE and INTEGRATION set definitions**

List every package in each set with its root path (`src/specify_cli/<pkg>/`) and a
one-sentence description of its responsibility. Match the definitions in
`kitty-specs/integration-boundary-01KW0PBE/data-model.md` exactly:

| Set | Package | Description |
|-----|---------|-------------|
| CORE | `core/` | Mission creation, contract gate, dependency graph |
| CORE | `status/` | State machine, event log, adapter registry |
| CORE | `readiness/` | Readiness checks and coordinator |
| CORE | `invocation/` | Op lifecycle propagation and registry |
| INTEGRATION | `orchestrator_api/` | Orchestrator HTTP client |
| INTEGRATION | `sync/` | Real-time SaaS sync, WebSocket, OfflineQueue |
| INTEGRATION | `tracker/` | Issue-tracker origin binding |
| INTEGRATION | `saas/` | SaaS-specific feature flags and rollout |
| INTEGRATION | `saas_client/` | SaaS REST client |

Also note out-of-scope modules (not in either set): `coordination/`, `lanes/`,
`runtime/`.

**b) The one-directional rule and its rationale**

```
CORE must NOT import INTEGRATION.
INTEGRATION may import CORE facades.
```

Rationale: CORE modules implement the canonical mission lifecycle and governance
logic; coupling them to outbound adapters would make the governance engine depend
on the availability and startup ordering of external connectors. Inversion (CORE
fires events; INTEGRATION registers handlers) keeps the governance path fast,
testable, and independent of connectivity.

**c) Allowlist exemptions with justifications and planned follow-up actions**

Exactly one entry at the time of this mission's merge:

| Source | Imported | Rationale | Planned resolution |
|--------|----------|-----------|-------------------|
| `readiness/coordinator.py` | `specify_cli.saas.rollout` | `is_saas_sync_enabled` is a pure feature-flag read (shared-config v1) with no side effects. Not a structural SaaS dependency. Exempted until `is_saas_sync_enabled` is relocated to a core/kernel config module. | Follow-up mission — no issue number assigned yet; tracked in `architecture/` docs. |

**d) Deferred scope items**

Include a Deferred section with:
- **Physical extraction** (`src/orchestrator/`): deferred per ADR
  `architecture/adrs/2026-05-11-1-defer-391-structural-extraction-from-3-2-x.md`
  and the ownership manifest `architecture/2.x/05_ownership_manifest.yaml`.
- **Bidirectional enforcement** (preventing INTEGRATION from importing CORE): out of
  scope for this mission (C-003); deferred.
- **`coordination/`, `lanes/`, `runtime/`**: not classified in either set; their
  import patterns are not checked by `test_integration_boundary.py` (C-004).

**Document standards**

- Follow the ADR template in `architecture/README.md` if this is a new ADR. If
  updating an existing doc, follow the existing section structure.
- The document must be committed on `feat/integration-boundary` alongside the code
  changes (FR-009).
- Do NOT break the architecture/README.md index if it lists docs in a table.

---

## Acceptance Criteria

1. The architectural document exists under `architecture/` and covers all four
   FR-009 items.
2. The CORE/INTEGRATION set table matches `data-model.md` exactly.
3. The allowlist table contains exactly one entry with a written rationale and
   follow-up reference.
4. Deferred items (physical extraction, bidirectional enforcement,
   `coordination/`/`lanes/`/`runtime/`) are listed with rationale references.
5. The document is committed on `feat/integration-boundary`.
6. `pytest tests/architectural/test_no_legacy_terminology.py` passes (terminology
   guard — run before pushing doctrine/prose changes).
