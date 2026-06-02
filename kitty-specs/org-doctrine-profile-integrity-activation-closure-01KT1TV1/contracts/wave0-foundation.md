# Contract: Wave 0 — Foundation

## C0.1 Canonical kind/ID resolver (FR-027, R-009)

- **Given** the operator token `agent-profile`
  **When** `ArtifactKind.from_operator_token("agent-profile")` is called
  **Then** it returns `ArtifactKind.AGENT_PROFILE`; likewise `mission-step-contract` → `MISSION_STEP_CONTRACT`, `mission-type` → the mission-type sentinel.
- **Given** an unknown token `frobnicate`
  **When** `from_operator_token` is called
  **Then** it raises a structured error listing valid tokens (no silent drop).
- **Given** the charter surfaces `activate`/`deactivate`/`list`/`context --include`
  **Then** none re-declare the kind set; each resolves kind via `from_operator_token` (grep proof: no second kind enumeration).
- **Given** a config/file-stem ID `001-architectural-integrity-standard` of kind `directive`
  **When** the ID resolver runs
  **Then** it returns the DRG URN `directive:DIRECTIVE_001` using the artifact's `id:` field; an unknown ID raises.

## C0.2 `SPECIALIZES_FROM` relation + no-leak (FR-001, FR-002)

- **Given** the `Relation` enum
  **Then** it contains `SPECIALIZES_FROM = "specializes_from"`, distinct from `DELEGATES_TO`.
- **Given** a merged DRG with a `specializes_from` edge A→B and no delegation edges
  **When** a consumer queries `edges_from(A, Relation.DELEGATES_TO)` (or `walk_edges({A}, {DELEGATES_TO})`)
  **Then** the lineage edge is **not** returned (I-R1). A regression test guards this.

## C0.3 Org-fragment unknown-relation handling (FR-003)

- **Given** an org or project DRG fragment with `relation: specializes_from`
  **When** the fragment is bridged into the DRG
  **Then** the edge is accepted (the enum member exists) — it is **not** silently dropped.
- **Given** a fragment with a genuinely unknown relation `relation: bogus`
  **When** bridged
  **Then** a structured error is raised (parity with the project-fragment Pydantic path; no silent `None` drop). Shipped/org/project fragments behave identically for a valid lineage edge.

## C0.4 Merge relocation + layer rule (C-009, OQ-2-ii)

- **Given** the relocated `doctrine.drg.merge.merge_three_layers(built_in, org_fragments, project_fragments)`
  **When** called with graph data
  **Then** it returns a merged `DRGGraph` and imports nothing from `charter`/`specify_cli`.
- **Given** `tests/architectural/test_layer_rules.py`
  **Then** it passes with `doctrine` not importing `charter`; `charter/drg.py` calls the doctrine merge and only adds activation-aware filtering.
- **Given** the pre-relocation merge behavior captured by existing tests
  **When** the relocated merge runs on the same inputs
  **Then** the merged node/edge set is identical (strangler-fig behavior-preservation, `refactoring-strangler-fig`).
- **Given** `DRGGraph`
  **Then** `edges_to(urn, relation=None)` returns the reverse adjacency (incoming edges), used by Wave 3.
