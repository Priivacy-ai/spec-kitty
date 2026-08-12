# Contract: Schema-diagram drift guard (FR-004, NFR-001, C-003) — hardened per post-plan squad

## Both sides of the comparison (architecture HIGH — diagram side was missing)
- **Model side**: introspect via an explicit `file:class` binding table (1:N). Pydantic `model_fields` with `FieldInfo.alias or name` + transitive nested recursion; frozen-dataclass `fields()`; StrEnum via `list()`. Never a hand-copied count.
- **Diagram side**: the `@startyaml` field-declaration shape is PINNED — top-level YAML keys (recursing into nested-model sub-maps) = the declared field set; scalar example values are excluded. The guard extracts this set and diffs it against the model side.

## Non-fakeable tests (reviewer HIGH/MEDIUM)
1. **Completeness over ALL kinds**: add a synthetic `ArtifactKind` member → the guard FAILS until it carries an explicit disposition (`diagrammed` | `consciously-omitted`) in the binding table. (Not just the 4 priority kinds.)
2. **Omit-a-field**: a diagram MISSING a model field FAILS (not only "add a field to the model").
3. **Nested depth-2**: add a field to a genuinely nested value-object — `AgentProfileSchema → AgentSpecialization`, or `MissionStepContract → MissionStepContractStep → inputs` (DRG is FLAT — do not use it for the depth test) — and assert FAIL.
4. Binds `styleguides/models.py:AntiPattern` vs the DRG `anti_pattern` NodeKind (no class) correctly.
