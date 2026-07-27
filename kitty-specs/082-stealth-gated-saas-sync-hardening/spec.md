# Feature Specification: Stealth-Gated SaaS Sync Hardening

**Feature Branch**: `082-stealth-gated-saas-sync-hardening`  
**Created**: 2026-04-11  
**Status**: Draft  
**Input**: User description: "Keep the CLI SaaS/tracker surface hidden for customers by default. Only explicitly opted-in internal test machines should enable it through `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. Within that gated surface, harden readiness, background behavior, and testing so the internal flow is production-grade without removing the rollout gate."

## Planning Decisions Locked

- The CLI rollout posture remains stealth-gated. `SPEC_KITTY_ENABLE_SAAS_SYNC=1` stays as the explicit internal opt-in gate for hosted SaaS, tracker, and sync behavior.
- The env var continues to control visibility and permission of the hosted surface. It is not removed in this mission.
- Inside the enabled surface, the CLI should use a shared readiness abstraction rather than ad hoc checks.
- Background sync auto-start is intent-gated, not machine-state-gated, and controlled by config `sync.background_daemon: auto | manual` with default `auto`.
- Unit tests may stub a canonical readiness resolver; a smaller integration layer should exercise the real evaluator against auth/config/binding fixtures.
- This mission does not introduce rollout logic into `spec-kitty-tracker`; tracker remains ungated and version-pinned by downstream consumers.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Customers Do Not See Hosted Tracker Features By Default (Priority: P1)

A customer installing the CLI without special internal setup should not see the hosted tracker surface or accidentally start talking to the SaaS.

**Why this priority**: The current rollout posture is intentional stealth. The shipped CLI must fail closed for everyone except explicitly opted-in internal testers.

**Independent Test**: In a clean shell with no `SPEC_KITTY_ENABLE_SAAS_SYNC`, run `spec-kitty --help`, `spec-kitty tracker --help`, and representative sync entry points. Verify the hosted tracker surface is absent or blocked.

**Acceptance Scenarios**:

1. **Given** no `SPEC_KITTY_ENABLE_SAAS_SYNC` environment variable, **When** a user runs `spec-kitty --help`, **Then** the hosted `tracker` command group is not visible.
2. **Given** no `SPEC_KITTY_ENABLE_SAAS_SYNC` environment variable, **When** code paths attempt hosted sync behavior, **Then** they fail closed and do not initiate SaaS/network activity.

---

### User Story 2 - Internal Testers Can Opt In Cleanly (Priority: P1)

An internal tester on a designated machine can turn on the hosted surface explicitly and use the CLI against the dev SaaS deployment.

**Why this priority**: The rollout gate exists so one controlled environment can exercise the full flow before public exposure.

**Independent Test**: Set `SPEC_KITTY_ENABLE_SAAS_SYNC=1` on an internal machine, run hosted tracker and sync commands, and verify the full command surface is visible and operable.

**Acceptance Scenarios**:

1. **Given** `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, **When** an internal tester runs `spec-kitty --help`, **Then** the hosted tracker command group is available.
2. **Given** `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, **When** the internal tester uses hosted tracker flows, **Then** the CLI follows the current SaaS/dev testing path instead of remaining hidden.

---

### User Story 3 - Enabled Mode Fails At Readiness Boundaries (Priority: P1)

When the hosted surface is enabled, commands should fail at the real missing prerequisite with clear guidance instead of relying on one global gate for every case.

**Why this priority**: Stealth gating and internal quality are separate concerns. Once the gate is opened, the internal experience still needs proper readiness behavior.

**Independent Test**: With `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, exercise commands across missing auth, missing host config, unreachable host, missing mission binding, and ready states. Verify each state produces the correct message and behavior.

**Acceptance Scenarios**:

1. **Given** the hosted surface is enabled but no auth exists, **When** a hosted command runs, **Then** it reports the missing auth prerequisite rather than a generic gate error.
2. **Given** the hosted surface is enabled and auth exists but the mission is not bound, **When** a mission-origin tracker command runs, **Then** it reports the missing binding prerequisite specifically.

---

### User Story 4 - Background Sync Starts Only On Remote Intent (Priority: P2)

When enabled, the CLI should only start the background sync daemon from commands that actually require hosted sync behavior, and operators should be able to override that behavior in config.

**Why this priority**: Internal testers need realistic automation, but passive or local-only commands should not silently turn into background network activity.

**Independent Test**: With `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, compare local-only commands, remote tracker/sync commands, and `sync.background_daemon=manual` vs `auto`.

**Acceptance Scenarios**:

1. **Given** the hosted surface is enabled, **When** a user runs help or local-only commands, **Then** no background sync daemon auto-start occurs.
2. **Given** the hosted surface is enabled and `sync.background_daemon=manual`, **When** a remote tracker/sync command would otherwise auto-start background sync, **Then** the CLI honors manual mode and explains the next step.

### Edge Cases

- What happens when the env var is enabled on an internal machine but `SPEC_KITTY_SAAS_URL` is unset?
- What happens when cached auth exists but the env var is absent?
- How does CI behave when auth fixtures exist but the rollout env var is intentionally off?
- What happens when the background daemon is in `manual` mode and a hosted command expects background connectivity?

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Keep explicit CLI rollout gate | As a product owner, I want the hosted CLI surface gated by `SPEC_KITTY_ENABLE_SAAS_SYNC` so that customers do not see unfinished SaaS/tracker features. | High | Open |
| FR-002 | Hide tracker surface by default | As a customer, I want the CLI to hide hosted tracker features unless explicitly enabled so that unfinished functionality is not exposed. | High | Open |
| FR-003 | Enable internal hosted testing | As an internal tester, I want the hosted surface to become available when the env var is set so that I can test against the dev SaaS deployment. | High | Open |
| FR-004 | Centralize readiness in enabled mode | As a maintainer, I want a shared readiness evaluator for hosted commands so that enabled-mode failures are consistent and actionable. | High | Open |
| FR-005 | Intent-gated daemon startup | As an operator, I want background sync to auto-start only from commands that truly require hosted sync so that passive CLI use stays local. | Medium | Open |
| FR-006 | Configurable daemon policy | As an operator, I want `sync.background_daemon: auto | manual` so that I can override auto-start behavior without touching rollout gating. | Medium | Open |
| FR-007 | Update tests for dual-mode behavior | As a maintainer, I want tests to cover both rollout-disabled and rollout-enabled paths so that stealth gating and internal readiness both remain correct. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Fail closed by default | In the absence of `SPEC_KITTY_ENABLE_SAAS_SYNC`, 100% of hosted tracker visibility and execution paths must remain hidden or blocked. | Safety | High | Open |
| NFR-002 | Actionable enabled-mode failures | In enabled mode, 100% of readiness failures must name the missing prerequisite and the next corrective action. | Usability | High | Open |
| NFR-003 | No passive network side effects | Help and local-only commands must not start hosted background networking even on enabled internal machines. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Stealth rollout remains in force | This mission must preserve the hidden-by-default rollout posture for all customer machines. | Product | High | Open |
| C-002 | Tracker remains ungated | This mission must not add rollout logic to `spec-kitty-tracker`; only the CLI and SaaS own rollout posture. | Architecture | High | Open |
| C-003 | Internal machine workflow remains valid | Internal test machines that explicitly set `SPEC_KITTY_ENABLE_SAAS_SYNC=1` must continue to exercise the hosted surface during the rollout window. | Operational | High | Open |

### Key Entities *(include if feature involves data)*

- **Hosted Tracker Rollout Gate**: The CLI-level env-var boundary controlling whether hosted tracker/sync surfaces are visible and usable.
- **Hosted Tracker Readiness**: The per-invocation state describing whether enabled-mode hosted commands have the prerequisites they require.
- **Background Sync Policy**: The operator-facing config that decides whether hosted commands auto-start the background sync daemon.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a machine without `SPEC_KITTY_ENABLE_SAAS_SYNC`, the hosted tracker command surface remains hidden and hosted sync paths fail closed.
- **SC-002**: On an internal machine with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, hosted tracker and sync commands are available and use readiness-based failures rather than one generic gate error.
- **SC-003**: Background sync only auto-starts from hosted commands that require remote behavior, and `sync.background_daemon=manual` prevents auto-start even when the rollout gate is enabled.
- **SC-004**: The automated test suite covers both rollout-disabled customer behavior and rollout-enabled internal-testing behavior.
