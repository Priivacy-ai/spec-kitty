# Missions (mission-type resolution)

This package holds the mission-type models: **mission-step contracts**
(`MissionStepContract` → `MissionStepContractStep`) that turn a mission type's
action sequence into executable steps, the frozen **action index** (`ActionIndex`)
projected per workflow action, and the `MissionStep` model.

This README is a **pointer** to the canonical docs — it does not restate the
schema (the code models here + the drift-guarded diagrams are the source of truth).

## Canonical documentation

- **Schema diagrams + resolution seam** — [Mission-type resolution](../../../docs/architecture/mission-type-resolution.md)
  (the `@startyaml` `MissionStepContract`/`ActionIndex` diagrams are generated from these models and drift-guarded;
  `action-index` and `mission-type` are documented here as *mission concepts*, not artefact kinds).
- **Artifact-kind vocabulary** — [Doctrine artifact kinds](../../../docs/architecture/doctrine-kinds.md)
  (`mission_step_contract` is one of the twelve `ArtifactKind` members).
- **Owning domain plan** — the doctrine-charter domain (merged on `main`).
