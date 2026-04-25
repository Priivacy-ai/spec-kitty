# Data Model: Runtime Mission Execution Extraction

**Mission**: `runtime-mission-execution-extraction-01KPDYGW`
**Phase**: 1 — Design & Contracts
**Status**: Authoritative type reference for WP02–WP05 implementers

---

## Overview

This document describes the type shapes introduced by this mission. It covers:
- The three seam Protocols (`PresentationSink`, `ProfileInvocationExecutor`, `StepContractExecutor`)
- Type aliases used across the extraction surface
- What is NOT introduced by this mission (deferred to Phase 6)

---

## Seam Protocols

### PresentationSink

**Location**: `src/runtime/seams/presentation_sink.py`
**Purpose**: Decouples runtime output from Rich; CLI adapters inject a Rich implementation.

| Method | Signature | Notes |
|---|---|---|
| `write_line` | `(text: str) -> None` | Plain text output |
| `write_status` | `(message: str) -> None` | Transient/progress message |
| `write_json` | `(data: object) -> None` | Structured JSON output |

Full IDL: [`contracts/presentation_sink.md`](contracts/presentation_sink.md)

### StepContractExecutor

**Location**: `src/runtime/seams/step_contract_executor.py`
**Purpose**: Execution-layer entry point; Phase 6 of #461 provides the concrete implementation.

| Method | Signature | Notes |
|---|---|---|
| `execute` | `(step_contract: Any, context: Any) -> Any` | `Any` narrows in Phase 6 |

Full IDL: [`contracts/step_contract_executor.md`](contracts/step_contract_executor.md)

### ProfileInvocationExecutor (boundary reference)

**Location**: `src/specify_cli/invocation/executor.py` (already implemented; accessible via `src/runtime/seams/profile_invocation_executor.py` alias)
**Purpose**: Executes profile-governed invocations; this mission documents the call boundary, not the implementation.

Full boundary spec: [`contracts/profile_invocation_executor.md`](contracts/profile_invocation_executor.md)

---

## Type Aliases (stdlib only — no new dependencies)

These are type aliases used within `src/runtime/` code. All are expressible with stdlib `typing`.

| Alias | Type | Used in | Notes |
|---|---|---|---|
| `AgentName` | `str` | `decisioning`, `bridge` | CLI-provided agent identifier (e.g. `"claude"`) |
| `MissionHandle` | `str` | `discovery` | ULID, mid8, or slug — resolved by `discovery.resolver` |
| `LaneId` | `str` | `bridge`, `decisioning` | Lane identifier (e.g. `"lane-a"`) |
| `WorkPackageId` | `str` | `bridge`, `decisioning` | WP identifier (e.g. `"WP01"`) |

These are defined as simple `TypeAlias` in the relevant subpackages; no new Pydantic models are introduced by this mission.

---

## Deferred Types (Phase 6)

The following types are intentionally deferred to #461 Phase 6. They appear as `Any` in the `StepContractExecutor` Protocol:

| Type | Phase | Notes |
|---|---|---|
| `StepContract` | Phase 6 | Step definition from mission artefacts |
| `ExecutionContext` | Phase 6 | Runtime state at execution time |
| `StepResult` | Phase 6 | Structured execution result |
| `InvocationContext` | Phase 4 (shipped) | In `invocation/executor.py` |
| `InvocationResult` | Phase 4 (shipped) | In `invocation/record.py` |

---

## What This Mission Does NOT Introduce

- No new Pydantic models
- No new database schema
- No new YAML/JSON configuration schema
- No new CLI commands or argument shapes
- No new `spec-kitty-events` or `spec-kitty-tracker` events

The extraction is a pure code-move. The data contracts are only the three Protocol definitions above.
