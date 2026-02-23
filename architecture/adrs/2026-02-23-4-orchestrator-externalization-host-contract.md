# Externalize Orchestration Behind a Host Contract

**Filename:** `2026-02-23-4-orchestrator-externalization-host-contract.md`

**Status:** Accepted

**Date:** 2026-02-23

**Deciders:** CLI Team, Platform Team

**Technical Story:** Remove bundled `spec-kitty orchestrate` runtime from core CLI and define a stable host contract for external orchestrators.

---

## Context and Problem Statement

`spec-kitty` historically bundled an autonomous orchestrator runtime (`spec-kitty orchestrate`) inside the core CLI package. That model created two structural problems:

* Security posture concerns: many organizations do not want autonomous orchestration logic bundled into the same trusted CLI used for core developer workflows.
* Product architecture rigidity: bundling one orchestrator implementation in core makes alternative orchestration strategies harder to build and evolve.

At the same time, we now have a dedicated external orchestrator implementation (`spec-kitty-orchestrator`) that can drive workflow transitions via CLI calls.

## Decision Drivers

* **Security boundary clarity:** keep core CLI free of autonomous orchestration runtime and related execution behaviors.
* **Extensibility:** support multiple orchestrator implementations through a versioned contract, not through in-core strategy branching.
* **Deterministic ownership:** core CLI remains the sole authority for mutating workflow state.
* **Operational simplicity:** avoid maintaining a compatibility shim for legacy `orchestrate` behavior.

## Considered Options

* **Option 1:** Keep bundled `spec-kitty orchestrate` and add external API as secondary path.
* **Option 2:** Externalize orchestration and expose a host command contract (`spec-kitty orchestrator-api`).
* **Option 3:** Move all orchestration logic to a separate service and remove local host command support.

## Decision Outcome

**Chosen option:** **Option 2**.

Core CLI will:

* Hard-remove bundled `spec-kitty orchestrate` runtime.
* Expose orchestration state operations only through `spec-kitty orchestrator-api` subcommands.
* Maintain a stable JSON envelope contract (`contract_version`, `command`, `timestamp`, `correlation_id`, `success`, `error_code`, `data`).
* Require policy metadata validation/sanitization for run-affecting operations.

External orchestrators (including `spec-kitty-orchestrator`) integrate only through this host contract.

### Explicit No-Shim Decision

There is **no compatibility shim** for `spec-kitty orchestrate`.

Rationale:

* A shim preserves ambiguous ownership and prolongs security concerns.
* Clean contract boundaries are easier to reason about for both users and integrators.
* Keeping two orchestration entrypoints in core creates drift and support burden.

## Host Mutation Authority

Workflow state mutations remain host-authoritative:

* External orchestrators may request transitions.
* `spec-kitty orchestrator-api` validates transition semantics and policy metadata.
* State changes are applied by core CLI code only.

This prevents external orchestrators from directly writing workflow state files outside the contract.

## Consequences

### Positive

* Clear security boundary for organizations that disallow bundled autonomous orchestrators.
* Enables multiple orchestration strategies without changing core runtime behavior.
* Simplifies core CLI surface: orchestration is now a contract, not an embedded runtime.

### Negative

* Breaking change for users invoking `spec-kitty orchestrate` directly.
* Requires users and docs to migrate to external orchestrator tooling.

### Neutral

* Core workflow commands (`specify`, `plan`, `tasks`, `implement`, `review`, `merge`) remain unchanged.

## Confirmation

This decision is successful when:

1. Core CLI has no bundled orchestrator runtime (`src/specify_cli/orchestrator/` removed).
2. `spec-kitty orchestrate` command is absent from CLI.
3. `spec-kitty orchestrator-api` provides the versioned contract used by external orchestrators.
4. CI guardrails fail builds if bundled orchestrator runtime is reintroduced.

## More Information

Related implementation artifacts:

* `src/specify_cli/orchestrator_api/`
* `.github/workflows/orchestrator-boundary.yml`
* `spec-kitty-orchestrator` host client integration
