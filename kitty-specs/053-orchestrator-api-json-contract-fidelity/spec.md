# Feature Specification: Orchestrator-API JSON Contract Fidelity

**Feature Branch**: `053-orchestrator-api-json-contract-fidelity`
**Created**: 2026-03-20
**Status**: Draft
**References**: [GitHub Issue #3](https://github.com/Priivacy-ai/spec-kitty/issues/3), Issue #304

## Problem Statement

The orchestrator-api claims to be a "JSON-first machine contract" but breaks that promise in two ways:

1. **Stale `--json` flag in docs**: The documentation (`docs/reference/orchestrator-api.md`) tells external callers to pass `--json` to `contract-version`, but the 2.x code defines no such flag. External orchestrators follow the documented contract and fail on first handshake.

2. **Root CLI path emits prose, not JSON**: The `_JSONErrorGroup` handler only intercepts errors when the sub-app is invoked directly. When invoked through the real entry path (`spec-kitty orchestrator-api ...`), the root CLI's `BannerGroup` handles errors first, emitting Typer's human-readable stderr with no stdout. This is why `spec-kitty-orchestrator` reports "returned no output."

3. **Tests don't exercise the real path**: Tests invoke the sub-app directly (`runner.invoke(app, ...)`), which hits `_JSONErrorGroup` and passes. They never test the actual `spec-kitty orchestrator-api ...` command path that real callers use.

## User Scenarios & Testing

### User Story 1 - External Orchestrator Handshake (Priority: P1)

An external orchestrator (e.g., `spec-kitty-orchestrator`) calls `spec-kitty orchestrator-api contract-version` to verify compatibility before proceeding. The orchestrator parses stdout as JSON. If the command produces anything other than a valid JSON envelope on stdout, the handshake fails.

**Why this priority**: This is the entry point for all orchestrator interactions. If the handshake fails, no orchestrator workflow can proceed.

**Independent Test**: Run `spec-kitty orchestrator-api contract-version` from a shell and verify stdout is a valid JSON envelope with `success: true`.

**Acceptance Scenarios**:

1. **Given** a clean install of spec-kitty 2.x, **When** an orchestrator runs `spec-kitty orchestrator-api contract-version`, **Then** stdout contains a valid JSON envelope with `success: true` and the contract version.
2. **Given** a clean install of spec-kitty 2.x, **When** an orchestrator runs `spec-kitty orchestrator-api contract-version --unknown-flag`, **Then** stdout contains a JSON envelope with `success: false` and `error_code: "USAGE_ERROR"` (not prose stderr).

---

### User Story 2 - Parse/Usage Errors Return JSON (Priority: P1)

When any orchestrator-api subcommand is invoked with bad arguments through the root CLI path, the error must be a JSON envelope on stdout, not Typer's prose on stderr.

**Why this priority**: Without this, every error case breaks the machine contract. Callers cannot programmatically distinguish error types.

**Independent Test**: Run `spec-kitty orchestrator-api contract-version --bogus` and verify stdout is a JSON envelope with `error_code: "USAGE_ERROR"`.

**Acceptance Scenarios**:

1. **Given** the root CLI entry path, **When** a user runs `spec-kitty orchestrator-api nonexistent-command`, **Then** stdout contains a JSON envelope with `error_code: "USAGE_ERROR"`.
2. **Given** the root CLI entry path, **When** a user runs `spec-kitty orchestrator-api move-task` (missing required args), **Then** stdout contains a JSON envelope with `error_code: "USAGE_ERROR"` and a descriptive message.

---

### User Story 3 - Documentation Matches Reality (Priority: P2)

A developer reading `docs/reference/orchestrator-api.md` can trust that the documented command signatures, flags, and error contracts match the actual CLI behavior.

**Why this priority**: Stale docs are the root cause of issue #304. Without accurate docs, external integrators build against a phantom API.

**Independent Test**: Compare every command signature in `orchestrator-api.md` against the actual CLI `--help` output and verify they match.

**Acceptance Scenarios**:

1. **Given** the orchestrator-api docs, **When** a developer reads the `contract-version` section, **Then** no `--json` flag is mentioned (the API is always-JSON by design).
2. **Given** the orchestrator-api docs, **When** a developer reads the error handling section, **Then** it states that all errors produce JSON envelopes on stdout with documented `error_code` values.

---

### Edge Cases

- What happens when `spec-kitty orchestrator-api` is invoked with no subcommand? Must produce JSON help or JSON error, not prose.
- What happens when the root CLI itself fails before reaching the orchestrator-api sub-app (e.g., broken plugin)? Must not break JSON contract for orchestrator-api paths.
- What happens when stderr is redirected but stdout is not? Callers parse stdout only; stderr content is irrelevant to the contract.

## Requirements

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | JSON errors through root CLI | As an orchestrator, I want parse/usage errors to return JSON envelopes when I invoke commands through `spec-kitty orchestrator-api ...` so that I can programmatically handle all error cases. | High | Open |
| FR-002 | Remove `--json` flag references | As a developer, I want the docs and tests to not reference a `--json` flag so that I don't build against a nonexistent API surface. | High | Open |
| FR-003 | Tests exercise real entry path | As a maintainer, I want integration tests that invoke `spec-kitty orchestrator-api ...` through the root CLI so that the tested path matches what callers actually use. | High | Open |
| FR-004 | No-subcommand JSON response | As an orchestrator, I want `spec-kitty orchestrator-api` (no subcommand) to return a JSON envelope so that even discovery/help requests are machine-parseable. | Medium | Open |
| FR-005 | Clean up backward-compat shims | As a maintainer, I want any `--json` no-op shims or legacy compatibility code removed so that the contract surface is minimal and honest. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Zero prose on stdout | 100% of orchestrator-api command invocations (success or failure) must produce valid JSON on stdout, with zero bytes of non-JSON prose. | Correctness | High | Open |
| NFR-002 | Code documentation | All error-handling paths must have inline comments explaining the JSON contract guarantee. | Maintainability | Medium | Open |
| NFR-003 | Test coverage | Every orchestrator-api subcommand must have at least one test exercising the root CLI entry path, not just the sub-app. | Quality | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No backward compatibility | No `--json` flag or shim. The API is always-JSON. Callers that pass `--json` will get a clean USAGE_ERROR envelope. | Technical | High | Open |
| C-002 | 2.x branch target | All changes target the 2.x branch. | Technical | High | Open |
| C-003 | Minimal code | Prefer deleting code over adding it. The fix should reduce the codebase, not grow it. | Technical | Medium | Open |

## Success Criteria

### Measurable Outcomes

- **SC-001**: Running `spec-kitty orchestrator-api contract-version` from a shell produces valid JSON on stdout with exit code 0.
- **SC-002**: Running `spec-kitty orchestrator-api contract-version --bogus` from a shell produces a JSON envelope on stdout with `error_code: "USAGE_ERROR"` and a nonzero exit code.
- **SC-003**: Every command signature in `docs/reference/orchestrator-api.md` matches the actual `--help` output with no stale flags.
- **SC-004**: Integration tests invoke through the root CLI app, not just the sub-app, and all pass.
