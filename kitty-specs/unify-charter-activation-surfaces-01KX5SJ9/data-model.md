# Phase 1 Data Model: Unify charter activation surfaces

No persistent DB. Four YAML surfaces + their relationships.

## Surface: Activation ledger (AUTHORITY)

- **File**: `.kittify/config.yaml` → `activated_directives` / `activated_tactics` / `activated_procedures` / `activated_paradigms` / `activated_styleguides` / `activated_toolguides` (per-kind lists of config-stems).
- **Role**: THE single activation authority (FR-001). Written only via `charter.activation_engine.commit_plan`.
- **Read by**: `PackContext.from_config` (runtime, today) AND — after this mission — the derivation (`compiler`/`synthesizer`).

## Surface: Interview record

- **File**: `.kittify/charter/interview/answers.yaml` → `selected_directives` etc.
- **Role after this mission**: captured interview selections only (FR-003). NOT an activation source. Its selections are promoted into the activation ledger (FR-007).

## Surface: Compiled reference set (DERIVED)

- **File**: `.kittify/charter/references.yaml`.
- **Role**: derived from the activation ledger (was: from the interview record). The resolution surface the dangler test checks.

## Surface: DRG graph (DERIVED)

- **File**: `src/doctrine/graph.yaml` (built-in) + induced charter graph.
- **Role**: derived; must stay byte-fresh (deterministic `generate_graph`).

## Invariants

- **I-1 (parity)**: every entry in the activation ledger resolves in the compiled reference set, and nothing resolves that is absent from the ledger. Enforced fail-closed by `consistency_check` (FR-005).
- **I-2 (answers inert)**: editing the interview record without an activation-ledger change has no effect on the compiled reference set (SC-004).
- **I-3 (migration lossless)**: the ledger is the migration seed; 0 previously-active artefacts dropped (FR-006); answers-only artefacts are promoted, not dropped.

## Derivation flow (target)

```
interview -> answers.yaml (record)
          -> promote selections -> config.activated_*  (AUTHORITY, FR-007)
charter activate/deactivate     -> config.activated_*  (commit_plan)
config.activated_* --derive-->  references.yaml + graph.yaml
consistency_check: config == references == graph  (fail-closed, FR-005)
```
