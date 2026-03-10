# Research: Tracker Publish Resource Routing

**Feature**: 048-tracker-publish-resource-routing
**Date**: 2026-03-10
**Status**: Complete — no unknowns required external research

## Findings

### 1. Credential Key Availability

**Decision**: Use `credentials["project_key"]` for Jira and `credentials["team_id"]` for Linear.

**Rationale**: Both keys are already required by `factory.py:build_connector()` via `_require()` calls (lines 81 and 88). Any successfully bound tracker already has these keys in `~/.spec-kitty/credentials`. The derivation function does not need to validate connector readiness — it only reads the credential dict that `_load_runtime()` already resolves.

**Alternatives considered**:
- Deriving from `TrackerProjectConfig.workspace` — rejected because `workspace` is the provider workspace name (e.g., Jira site), not the resource identifier (e.g., Jira project key)
- Adding a new config field to `.kittify/config.yaml` — rejected because the data already exists in credentials and adding config fields increases migration burden

### 2. Payload Forward Compatibility

**Decision**: Add `external_resource_type` and `external_resource_id` as top-level fields in the snapshot payload alongside existing `provider` and `workspace`.

**Rationale**: The SaaS snapshot endpoint (`/api/v1/connectors/trackers/snapshots/`) accepts JSON payloads with standard forward-compatible handling — unknown fields are ignored by older SaaS versions. No endpoint version bump needed.

**Alternatives considered**:
- Nesting under a `routing` sub-object — rejected for simplicity; top-level fields match the flat structure of `provider` and `workspace`
- Adding to the event envelope instead — rejected per spec constraint C-002 (Git event envelope must remain unchanged)

### 3. Null Semantics

**Decision**: Both fields are `null` when routing cannot be derived. The publish still succeeds.

**Rationale**: This matches the existing pattern where `project_uuid` and `project_slug` can be `null` in the event envelope. The SaaS falls back to its current `(provider, workspace)` resolution path when routing fields are absent.

**Alternatives considered**:
- Raising an error when routing keys are missing — rejected because it would break existing bindings that lack the credential key (e.g., legacy credentials without `project_key`)
- Omitting the fields entirely instead of null — rejected because explicit null signals "resolved but unavailable" per the event envelope convention (Section "Field absence vs null" in `docs/reference/event-envelope.md`)
