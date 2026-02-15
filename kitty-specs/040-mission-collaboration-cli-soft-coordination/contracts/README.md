# API Contracts: Mission Collaboration CLI

**Feature**: 040-mission-collaboration-cli-soft-coordination
**Version**: S1/M1 Step 1
**Date**: 2026-02-15

## Overview

This directory contains API contracts for the mission collaboration CLI, including:
1. CLI command signatures
2. SaaS API integration endpoints
3. Adapter protocol definitions
4. Event schema references (feature 006 ownership)

---

## CLI Commands

See [cli-commands.md](cli-commands.md) for detailed command signatures, arguments, options, and output formats.

**Commands (6 total):**
- `mission join` - Join mission with role-based capabilities
- `mission focus set` - Declare focus target (work package or prompt step)
- `mission drive set` - Set drive intent (active|inactive)
- `mission status` - Display mission participants and collision summary
- `mission comment` - Post comment with focus context
- `mission decide` - Capture decision with focus context

---

## SaaS API Integration

See [saas-api.md](saas-api.md) for SaaS endpoint specifications, request/response formats, and error handling.

**Endpoints (2 total):**
- `POST /api/v1/missions/{mission_id}/participants` - Join mission (mints participant_id)
- `POST /api/v1/events/batch/` - Replay queued events (batch upload)

---

## Adapter Protocol

See [adapter-protocol.md](adapter-protocol.md) for ObserveDecideAdapter interface definition, operation signatures, and contract tests.

**Operations (5 total):**
- `normalize_actor_identity` - Extract agent identity from runtime context
- `parse_observation` - Parse agent output into structured signals
- `detect_decision_request` - Identify decision requests in observations
- `format_decision_answer` - Format decision answer for agent input
- `healthcheck` - Check adapter prerequisites

---

## Event Schemas

See [event-schemas.md](event-schemas.md) for canonical event type reference and payload structures.

**Event Types (14 total, feature 006 ownership):**
- ParticipantInvited, ParticipantJoined, ParticipantLeft, PresenceHeartbeat
- DriveIntentSet, FocusChanged
- PromptStepExecutionStarted, PromptStepExecutionCompleted
- ConcurrentDriverWarning, PotentialStepCollisionDetected, WarningAcknowledged
- CommentPosted, DecisionCaptured, SessionLinked

**Note:** Event schemas are owned by feature 006 (spec-kitty-events). This reference documents the contract for feature 040 integration only. For canonical schema definitions, see spec-kitty-events repository.

---

## Contract Ownership

| Contract Type | Owner | Responsibility |
|---------------|-------|----------------|
| CLI Commands | Feature 040 | Command signatures, argument validation, output format |
| SaaS API | SaaS Team | Endpoint paths, request/response schemas, authentication |
| Adapter Protocol | Feature 040 | Protocol interface, operation signatures, contract tests |
| Event Schemas | Feature 006 | Event types, payload structures, schema versioning |

---

## Integration Testing

Contracts are validated through integration tests:
- **CLI commands**: `tests/specify_cli/cli/commands/mission/`
- **SaaS API**: `tests/specify_cli/integration/test_saas_*_mock.py`
- **Adapter protocol**: `tests/specify_cli/adapters/test_*.py`
- **Event schemas**: `tests/specify_cli/integration/test_006_event_schemas.py`

---

## Versioning

**S1/M1 Scope:**
- CLI commands: v1.0 (initial release)
- SaaS API: v1 endpoints (stable)
- Adapter protocol: v1.0 (Protocol-based, extensible)
- Event schemas: Pinned to feature 006 prerelease (semver TBD)

**Breaking Changes:**
- CLI commands: Major version bump (e.g., v1 → v2)
- SaaS API: New version path (e.g., /api/v1 → /api/v2)
- Adapter protocol: Protocol extension (backward compatible via default methods)
- Event schemas: Feature 006 semver (e.g., 1.0.0 → 2.0.0)

---

## Questions?

Contact the feature 040 team lead or open a GitHub issue.
