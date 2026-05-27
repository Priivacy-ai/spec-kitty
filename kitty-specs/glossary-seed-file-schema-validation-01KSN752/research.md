# Research: Glossary Seed File Schema Validation

## R1: Existing Validation Gap Analysis

**Decision**: Current `validate_seed_file()` is insufficient — checks only `terms` key presence and `surface`/`definition` field existence. Does not check normalization, confidence range, status enum, or unknown fields.

**Rationale**: The function at `src/specify_cli/glossary/scope.py:64` performs structural checks only. Domain invariants (surface normalization, confidence bounds, status values) are enforced later during `TermSurface`/`TermSense` construction, causing fail-at-construction errors that are hard to diagnose.

**Alternatives considered**:
- Extend existing `validate_seed_file()` with manual checks → rejected: would duplicate Pydantic's validation capabilities and not produce structured errors
- Replace dataclass validation entirely with Pydantic → rejected: existing `TermSurface`/`TermSense` are the runtime domain model used throughout 20+ modules; replacing them is out of scope

## R2: Doctrine Schema Pattern Analysis

**Decision**: Follow the doctrine Pydantic pattern — `ConfigDict(frozen=True, extra="forbid")`, field-level validators, `model_validator` for cross-field rules.

**Rationale**: `src/doctrine/directives/models.py` demonstrates the established pattern:
- `Directive(BaseModel)` with `ConfigDict(frozen=True, extra="forbid", populate_by_name=True)`
- Required fields with `Field(pattern=...)` constraints
- Optional fields with `Field(default_factory=list)`
- `@model_validator(mode="after")` for cross-field invariants
- Separate `validation.py` module for YAML-level schema validation via jsonschema

For glossary seed files, Pydantic validation alone is sufficient (no separate JSON Schema needed initially) because the invariants are simple field-level checks, not complex cross-document references.

**Alternatives considered**:
- Add JSON Schema + jsonschema validation (like doctrine `validate_directive()`) → deferred: can be added later if CI or external tools need standalone schema files; Pydantic models are the source of truth and can generate JSON Schema on demand via `model_json_schema()`

## R3: Unknown Fields Policy

**Decision**: Fail-closed (`extra="forbid"`) — unknown fields in seed files are rejected.

**Rationale**: Glossary seed files have a well-defined structure (`surface`, `definition`, `confidence`, `status`). Unknown fields are likely typos or unsupported extensions. Fail-closed prevents silent data loss and aligns with the DDD aggregate boundary principle.

**Alternatives considered**:
- `extra="allow"` with warning → rejected: silently tolerating unknown data undermines the aggregate integrity the spec requires
- `extra="ignore"` → rejected: same problem as allow, plus data loss on round-trip through `save_seed_file()`

**Risk**: If existing seed files in the wild contain metadata fields beyond the four known ones, this will be a breaking change. Mitigation: audit `.kittify/glossaries/` files in this repo and document any additional fields found.

## R4: Error Aggregation Strategy

**Decision**: Collect all validation errors per file before raising, rather than failing on the first error.

**Rationale**: When a seed file has multiple issues (e.g., three terms with non-normalized surfaces), the operator needs to see all problems at once to fix them in one pass. Pydantic v2 natively collects all `ValidationError` entries.

**Alternatives considered**:
- Fail-fast on first error → rejected: poor developer experience when multiple terms need fixing
- Warning-only mode → rejected: conflicts with the fail-fast aggregate boundary decision (FR-008)

## R5: `save_seed_file()` Validation Scope

**Decision**: Validate the term data that will be written by constructing a `GlossarySeedFile` model from the serialized form before writing to disk.

**Rationale**: `save_seed_file()` receives `list[TermSense]` — already-validated domain objects. The risk is low (data is valid by construction), but validating the serialized output catches edge cases like rounding errors in confidence serialization or encoding issues.

**Alternatives considered**:
- Skip validation in `save_seed_file()` since input is already validated domain objects → rejected: defense-in-depth; the spec requires validation at all write boundaries (FR-013)
- Validate the `TermSense` objects directly → insufficient: we need to validate the YAML-serialized form, not the in-memory objects

## R6: Dashboard API Backward Compatibility

**Decision**: Add optional `validation_errors` field to `GlossaryHealthResponse`. For `/api/glossary-terms`, return the existing array format when valid; include errors in a wrapper object only when validation fails.

**Rationale**: Existing dashboard JS consumers expect `GlossaryHealthResponse` shape for health and a bare array for terms. Adding an optional field to health is backward-compatible. For terms, the error case currently returns `[]`, so changing it to `{"terms": [], "validation_errors": [...]}` is a semantic improvement but a structural change. Consumers already handle the empty-array case; the wrapper object is only returned on error.

**Alternatives considered**:
- Always return wrapper object for terms → rejected: breaks existing consumers that expect bare array
- Return errors via HTTP status code (4xx) → rejected: validation errors are about the data state, not the request; 200 with error details is more appropriate for a health-check pattern
