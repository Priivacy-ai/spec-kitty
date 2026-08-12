# Contract: Schema-diagram drift guard

**Requirement**: FR-010, NFR-001

## Interface

- **Form**: a pytest test (in `tests/docs/` or `tests/architectural/`).
- **Binding**: each schema diagram declares the code model it depicts (e.g. a comment marker
  `<!-- model: src/doctrine/agent_profiles/schema_models.py:AgentProfileSchema -->` or a registry entry).
- **Check**: parse the `@startyaml` field set from the diagram; introspect the model's field set
  (Pydantic `model_fields` / dataclass `fields()` / StrEnum members); assert they are equal.

## Guarantees (testable)

1. Adding a field to a bound model without updating its diagram → guard FAILS.
2. Renaming/removing a model field the diagram still shows → guard FAILS.
3. A diagram whose fields match its model exactly → guard PASSES.
4. Every priority artefact kind (agent-profile, mission-type/step, action-index, DRG, artefact-kind vocab) has a bound diagram covered by the guard.

## Notes

- The guard operates on the **field set** (names + presence), not prose; type-annotation text in the
  typed-placeholder is informational and not drift-checked (kept human-authored).
- Distinguishes `styleguides/models.py:AntiPattern` from the DRG `anti_pattern` node (must not bind a
  diagram of one to the other).
