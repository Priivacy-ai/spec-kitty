# Glossary Seed File Schema Validation

## Purpose

Glossary seed files (`.kittify/glossaries/*.yaml`) are the authoritative source of domain terminology for Spec Kitty projects. Today these files are loaded as loose YAML with minimal structural checks. A single malformed term — such as a non-normalized `surface` value — causes the entire scope to fail at load time. Dashboard handlers silently catch the error and report zero glossary terms, hiding the root cause from operators.

This mission adds schema-backed validation with DDD aggregate modeling so that invalid glossary state is rejected with actionable errors at every boundary where seed files are created, edited, loaded, or checked in CI.

## Source

- GitHub Issue: [#1322](https://github.com/Priivacy-ai/spec-kitty/issues/1322)
- Observed failure: `ValueError: TermSurface must be normalized: Sonar quality gate` (PR #1321)

## Actors

| Actor | Role |
|-------|------|
| **Mission author** | Creates and edits glossary seed files during specify/plan phases |
| **Spec Kitty CLI** | Loads seed files at runtime for glossary resolution and dashboard rendering |
| **CI pipeline** | Validates committed glossary seed files on every push |
| **Dashboard consumer** | Reads glossary data via `/api/glossary-health` and `/api/glossary-terms` endpoints |

## User Scenarios & Testing

### Scenario 1: Author introduces invalid term

A mission author adds a term with a non-normalized surface (`Sonar quality gate`) to `spec_kitty_core.yaml`. When they run `spec-kitty glossary validate`, the CLI reports the exact file, term index, field, and the normalization rule violated. The author fixes the surface to `sonar quality gate` and re-validates successfully.

### Scenario 2: CI catches invalid seed file

A contributor pushes a commit that modifies `.kittify/glossaries/team_domain.yaml` with a missing `definition` field. CI runs glossary validation and fails with an actionable error message naming the file, the offending term surface, and the missing field. The contributor fixes the file before merging.

### Scenario 3: Dashboard surfaces validation failure

An operator starts the dashboard with an invalid seed file present. Instead of silently showing zero terms, the glossary health endpoint reports a validation error with the specific file and failure reason. The operator sees what needs fixing rather than a misleading empty state.

### Scenario 4: Runtime load rejects invalid state

`load_seed_file()` validates the entire seed file against the schema before constructing domain objects. If any term violates an invariant, the entire scope is rejected with a structured validation error that names the file, term, field, and rule. No partial loads occur.

### Scenario 5: Save path enforces invariants

When code writes a glossary seed file via `save_seed_file()`, the same validation runs before persisting. Invalid state cannot be written to disk through the programmatic API.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | The system validates that the root document of a glossary seed file is a YAML mapping containing a `terms` key | Proposed |
| FR-002 | The system validates that each term has a `surface` field whose value equals `surface.lower().strip()` (normalized) | Proposed |
| FR-003 | The system validates that each term has a non-empty `definition` field | Proposed |
| FR-004 | The system validates that each term's `confidence` field, when present, is a number in the range 0.0 to 1.0 inclusive | Proposed |
| FR-005 | The system validates that each term's `status` field, when present, is one of: `active`, `draft`, `deprecated` | Proposed |
| FR-006 | The system validates that scope seed filenames map to known `GlossaryScope` values: `mission_local`, `team_domain`, `audience_domain`, `spec_kitty_core` | Proposed |
| FR-007 | Validation errors include the file path, term index or surface, field name, and a human-readable message describing the violated rule | Proposed |
| FR-008 | When any term in a seed file fails validation, the entire scope is rejected — no partial loads | Proposed |
| FR-009 | A CLI command `spec-kitty glossary validate <path>` validates a single seed file when given a file path | Proposed |
| FR-010 | A CLI command `spec-kitty glossary validate <path>` validates all `*.yaml` files under a directory when given a directory path | Proposed |
| FR-011 | The CLI validate command exits with a non-zero status code when validation fails | Proposed |
| FR-012 | `load_seed_file()` validates the seed file before constructing `TermSurface` objects and raises structured validation errors instead of raw `ValueError` | Proposed |
| FR-013 | `save_seed_file()` validates the seed data before writing to disk | Proposed |
| FR-014 | Dashboard glossary endpoints surface validation failure details instead of silently returning empty terms | Proposed |
| FR-015 | The system enforces an explicit unknown-fields policy for glossary seed files (fail-closed on unrecognized fields unless an allowlist is defined) | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Validation of a seed file with 100 terms completes in under 500ms | < 500ms for 100 terms | Proposed |
| NFR-002 | Validation error messages are actionable without consulting documentation — they name the file, term, field, and rule | 100% of error messages include file + term + field + rule | Proposed |
| NFR-003 | New validation code has 90%+ test coverage | ≥ 90% line coverage | Proposed |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | Validation models must follow the existing doctrine schema pattern (schemas under source, models as source of truth) | Proposed |
| C-002 | The `GlossarySeedFile` aggregate root and `GlossaryTerm` child entity must be expressed as domain models with explicit invariants, not ad-hoc dictionary checks | Proposed |
| C-003 | CI validation must cover all files matching `.kittify/glossaries/**/*.yaml` | Proposed |
| C-004 | Changes must not break existing valid seed files — the new validation must accept all currently valid glossary YAML structures | Proposed |

## Domain Language

| Canonical Term | Definition | Avoid |
|----------------|------------|-------|
| glossary seed file | A YAML file under `.kittify/glossaries/` that defines canonical terms for a scope | "glossary file", "term file", "seed data" |
| surface | The normalized lowercase string form of a term | "term name", "label" |
| scope | One of the four glossary resolution levels (mission_local, team_domain, audience_domain, spec_kitty_core) | "context", "namespace" |
| aggregate root | `GlossarySeedFile` — the consistency boundary for a seed file | "document", "container" |

## Assumptions

1. The existing `validate_seed_file()` function in `scope.py` can be replaced or extended rather than preserved as a separate code path.
2. The unknown-fields policy will be fail-closed (reject unknown fields) unless existing seed files in the wild contain metadata fields that must be allowed.
3. The `confidence` and `status` fields remain optional in seed files (defaulting to draft/0.5 when absent), but when present must pass validation.
4. The immediate bad data (`surface: Sonar quality gate`) will be fixed as part of this mission's first work package or as a prerequisite commit.

## Success Criteria

1. `surface: Sonar quality gate` fails validation with an actionable error naming the file, term, field, and normalization rule.
2. `surface: sonar quality gate` passes validation for `spec_kitty_core.yaml`.
3. `spec-kitty glossary validate .kittify/glossaries/spec_kitty_core.yaml` exits non-zero on invalid YAML and zero on valid YAML.
4. `spec-kitty glossary validate .kittify/glossaries/` validates all scope seed files in the directory.
5. Dashboard glossary endpoints no longer silently report zero terms when a seed file contains validation errors.
6. CI fails when committed glossary seed files contain invalid data.
7. All validation errors include file path, term identifier, field name, and human-readable rule description.

## Dependencies

- Existing glossary subsystem: `src/specify_cli/glossary/` (scope.py, models.py)
- Existing doctrine schema pattern: `src/doctrine/schemas/` (for architectural alignment)
- Dashboard handlers: `src/specify_cli/dashboard/handlers/glossary.py`
- CLI glossary commands: `src/specify_cli/cli/`

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Existing valid seed files in user projects contain fields not covered by the schema | Medium | High — false validation failures on upgrade | Audit existing seed file structures before finalizing the unknown-fields policy; consider an allowlist for known metadata fields |
| Dashboard error surfacing changes the API contract for consumers | Low | Medium — downstream tools may parse the response differently | Ensure error responses use a distinct field or status code so existing consumers degrade gracefully |
| Replacing `validate_seed_file()` breaks callers that catch the current `ValueError` shape | Low | Low — internal API, few callers | Grep all callers before changing the exception type; maintain backward-compatible error message format if needed |
