# Specification: Local Custom Mission Loader

**Mission ID:** `01KQ2VNJFYFT4371K45VMR8GPD`
**Mission Slug:** `local-custom-mission-loader-01KQ2VNJ`
**Tracker:** Implements [#505](https://github.com/Priivacy-ai/spec-kitty/issues/505) (Phase 6 / WP6.5). Parent epic: [#468](https://github.com/Priivacy-ai/spec-kitty/issues/468). Umbrella: [#461](https://github.com/Priivacy-ai/spec-kitty/issues/461). Distribution ADR ([#516](https://github.com/Priivacy-ai/spec-kitty/issues/516)) stays open.
**Status:** Draft (Specify phase)

## Purpose

### TL;DR

Let teams author and run their own local mission definitions as first-class peers to built-in missions through the existing runtime and composition pipeline.

### Stakeholder Context

Spec Kitty currently ships only built-in missions (`software-dev`, `research`, `documentation`, `plan`). Teams whose workflows do not match those built-ins have no first-class extension point — they cannot keep their own per-project mission YAML alongside `kitty-specs/` and run it through `spec-kitty next`. Issue [#505](https://github.com/Priivacy-ai/spec-kitty/issues/505) closes that gap with a v1 local loader: project-authored mission definitions discovered from `.kittify/missions/` and existing override paths, validated structurally, and dispatched through the same internal runtime + StepContractExecutor + ProfileInvocationExecutor pipeline that built-ins already use. Distribution remains local — SaaS registry, `mission install`, and cross-team sharing stay deferred under [#516](https://github.com/Priivacy-ai/spec-kitty/issues/516). Retrospective *execution* (alongside `retrospective.yaml`, synthesizer handoff, HiC/autonomous gating, and summary UI) is out of scope; this tranche only requires a structural retrospective marker so future tranches (#506–#511) can attach behavior to it without breaking compatibility.

## Background and Current State

The runtime is already CLI-internal under `src/specify_cli/next/_internal_runtime/` (PR #796) and the `software-dev` mission is rewritten onto profile-invocation composition (PR #795, stabilized by PR #797). The retired `spec-kitty-runtime` PyPI package is no longer a production dependency, and the preflight fix for [#798](https://github.com/Priivacy-ai/spec-kitty/issues/798) (commit `cedb77ff` in this workspace) removed the last function-scoped imports of it from `runtime_bridge.py`. Discovery already supports an established precedence chain (explicit / env / project override / project legacy / project config / user global / built-in) along with hooks like `SPEC_KITTY_MISSION_PATHS`, `.kittify/config.yaml mission_packs`, and `mission-pack.yaml`. This mission consumes those existing surfaces; it does not introduce a parallel loader.

## User Scenarios and Testing

### Primary Actor

A project lead or platform engineer ("operator") who maintains a Spec Kitty-using project and wants their team to follow a custom workflow that is not one of the four built-in missions.

### Primary Scenario — Author and Run a Local Custom Mission

1. The operator authors `.kittify/missions/erp-integration/mission.yaml` describing seven steps: `query-erp`, `lookup-provider`, `ask-user`, `create-js`, `refactor-function`, `write-report`, `retrospective`. Each agent-executed step declares a profile (or an explicit action / contract binding); the `ask-user` step is marked as a human/input gate; the final step has the recognized retrospective marker.
2. The operator runs `spec-kitty mission run erp-integration --mission erp-q3-rollout` from the project root. The CLI resolves the `erp-integration` mission key through the existing discovery precedence, validates the YAML, scaffolds (or attaches to) the tracked mission `erp-q3-rollout` under `kitty-specs/`, and starts the runtime against the discovered template.
3. As the runtime advances, agent-executed steps dispatch through `StepContractExecutor` / `ProfileInvocationExecutor` and produce paired `started` / `completed|failed` invocation records that record the contract action.
4. The `ask-user` step pauses the runtime via the existing `decision_required` path; the operator answers, and the runtime resumes.
5. After the last step before the retrospective marker, the runtime treats the marker as a structural step (no execution side effect this tranche).

### Exception Path — Missing Retrospective Marker

The operator publishes `.kittify/missions/legacy-flow/mission.yaml` without a recognizable retrospective marker. The first command that loads the definition (`spec-kitty mission run legacy-flow --mission whatever`) exits non-zero with a clear, structured error naming the mission key, the missing marker, and the file path. No tracked mission is started.

### Exception Path — Ambiguous Mission Definition

Two layers of the discovery precedence (e.g., a project-override and a built-in) both declare the same mission key. The loader rejects the run with a structured `MISSION_KEY_AMBIGUOUS` error listing every source path, so the operator can decide which copy is canonical.

### Edge Cases

- Malformed YAML, unknown top-level keys, missing required runtime fields (`mission.key`, `mission.name`, `steps[]`).
- A composed step missing both an `agent_profile` field and an explicit action / contract binding.
- A mission key resolved through `SPEC_KITTY_MISSION_PATHS` whose definition shadows a built-in name (must be flagged, not silently overridden).
- A mission-pack manifest that exposes a custom mission via the existing pack discovery hook.
- Backward compatibility: starting a built-in mission (`software-dev`, `research`, `documentation`, `plan`) must behave identically to current behavior with no new validation rejections.

## Domain Language

| Term | Canonical meaning in this spec |
| --- | --- |
| **Mission key** | The reusable identifier of a custom mission *definition* (e.g., `erp-integration`). Resolved through discovery precedence. |
| **Mission slug** | The identifier of a *tracked* mission run under `kitty-specs/<slug>/` (e.g., `erp-q3-rollout-01KQ…`). |
| **Custom mission** | A non-built-in mission definition discovered through the local loader. |
| **Built-in mission** | One of the four currently bundled missions: `software-dev`, `research`, `documentation`, `plan`. |
| **Composed step** | An agent-executed step routed through `StepContractExecutor` and `ProfileInvocationExecutor`. |
| **Decision-required step** | A human/input gate routed through the internal runtime's existing `decision_required` path. |
| **Retrospective marker** | A structural marker (e.g., `id: retrospective`) on a final step that this tranche only validates; no execution semantics yet. |

Avoid the synonym "mission name" for either of `mission key` or `mission slug` — the terms are not interchangeable.

## Functional Requirements

| ID | Requirement | Status |
| --- | --- | --- |
| FR-001 | Provide an operator-facing CLI surface to start and run a custom mission definition. The v1 contract is `spec-kitty mission run <mission-key> --mission <mission-slug> [--json]`, where `<mission-key>` selects the reusable definition and `<mission-slug>` identifies the tracked mission under `kitty-specs/`. | Locked |
| FR-002 | Resolve `<mission-key>` through the existing internal runtime discovery precedence: explicit / environment / project override / project legacy / project config / user global / built-in. No new precedence introduced. | Locked |
| FR-003 | Load custom mission definitions from `.kittify/missions/<key>/`, `.kittify/overrides/missions/<key>/`, and any existing mission-pack discovery hooks (e.g., `mission-pack.yaml`, `.kittify/config.yaml mission_packs`, `SPEC_KITTY_MISSION_PATHS`) without adding a parallel loader. | Locked |
| FR-004 | Reject invalid custom mission definitions at load time with structured, actionable errors covering: malformed YAML, missing required runtime fields (`mission.key`, `mission.name`, `mission.version`, `steps[]`), unresolved mission key, ambiguous / shadowed definitions, and missing retrospective marker. Each error includes the file path(s), the mission key (when known), and a stable error code suitable for tooling. | Locked |
| FR-005 | A custom mission definition that does not declare a structural retrospective step or marker MUST be rejected before the runtime starts. The retrospective step is *not* executed in this tranche. | Locked |
| FR-006 | Agent-executed custom steps MUST dispatch through `StepContractExecutor` and `ProfileInvocationExecutor`, preserving invocation trail records (paired started + completed/failed), `action_hint`, mode-of-work, DRG context resolution, and glossary chokepoint behavior. | Locked |
| FR-007 | Human/input decision steps MUST use the existing internal runtime `decision_required` path (snapshot `pending_decisions`, `DecisionInputRequested` event), not a synthetic profile invocation. | Locked |
| FR-008 | Each composed custom step MUST resolve a profile through an explicit per-step `agent_profile` (alias accepted: `agent-profile`) field on the runtime step, or through an explicit action / contract binding. The software-dev-specific `_ACTION_PROFILE_DEFAULTS` table MUST NOT be expanded as a generic fallback for arbitrary custom missions. | Locked |
| FR-009 | A reference custom mission representing the operator's "ERP" example (`query-erp` → `lookup-provider` → `ask-user` → `create-js` → `refactor-function` → `write-report` → `retrospective`) MUST be authorable as local YAML and exercisable end-to-end through the runtime in tests, including a `decision_required` step and composed profile-invocation steps. | Locked |
| FR-010 | Existing built-in missions (`software-dev`, `research`, `documentation`, `plan`) MUST keep their current end-to-end behavior. The new loader must not alter validation, dispatch, or invocation semantics for built-ins. | Locked |
| FR-011 | When a custom mission key shadows a built-in mission key, the loader MUST surface a structured warning or error (per FR-004 ambiguity rules) rather than silently overriding the built-in. The exact severity (warn vs. reject) is a planning-phase decision but the behavior MUST be deterministic and documented. | Open (planning resolves warn-vs-reject) |
| FR-012 | The loader MUST be reachable from the existing `spec-kitty next` advancement path for a tracked mission whose definition resolves to a custom mission, so the runtime advances composed and decision-required steps identically to the `mission run` entry point. | Locked |
| FR-013 | Validation errors MUST be representable in `--json` output (where applicable) so external tooling can consume them, while still printing a human-readable summary on the default text channel. | Locked |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
| --- | --- | --- | --- |
| NFR-001 | Loading and validating a single custom mission definition (≤ 50 steps) plus discovering all built-ins MUST complete fast enough to be invisible to operators on local hardware. | < 250 ms p95 on a Mac/Linux dev machine; benchmarked in tests against the ERP fixture. | Locked |
| NFR-002 | Every error path defined under FR-004 MUST emit an error code from a closed enumeration (e.g., `MISSION_KEY_AMBIGUOUS`, `MISSION_RETROSPECTIVE_MISSING`, `MISSION_YAML_MALFORMED`) and a stable JSON shape. | 100% of FR-004 cases covered by named error codes; new codes documented in `docs/reference/missions.md`. | Locked |
| NFR-003 | Test coverage of the new loader, validation, and runtime dispatch surface MUST meet the project's "90%+ test coverage for new code" charter standard. | ≥ 90% line coverage on new modules under `src/specify_cli/next/_internal_runtime/discovery.py` *additions*, the loader, and validators; reported via `pytest --cov` in CI. | Locked |
| NFR-004 | The reference ERP fixture suite MUST run in under 10 seconds locally so it is a practical inner-loop test. | < 10 s wall clock on the same hardware as NFR-001. | Locked |
| NFR-005 | All new code MUST type-check clean under `mypy --strict` per the charter. | Zero `mypy --strict` errors on new / changed modules. | Locked |

## Constraints

| ID | Constraint | Status |
| --- | --- | --- |
| C-001 | No SaaS mission registry, `spec-kitty mission install`, or cross-team distribution work in this tranche. Distribution stays under [#516](https://github.com/Priivacy-ai/spec-kitty/issues/516). | Locked |
| C-002 | No production import or runtime dependency on the retired `spec-kitty-runtime` PyPI package. The architectural boundary test in `tests/architectural/test_shared_package_boundary.py` MUST stay green. | Locked |
| C-003 | No legacy DAG fall-through reintroduction for composition-backed actions. PR #797's invariants stay in force. | Locked |
| C-004 | Invocation JSONL MUST NOT be written outside `ProfileInvocationExecutor` / `InvocationWriter`. The loader / runtime path is a consumer, not a writer. | Locked |
| C-005 | Retrospective execution, `retrospective.yaml` writing, synthesizer handoff, HiC / autonomous gating, and summary UI are out of scope. Marker validation only. | Locked |
| C-006 | Architecture boundary preserved: host LLM / harness owns reading and generation; Spec Kitty owns routing, governance context assembly, validation, trail writing, provenance, DRG checks, staging / promotion, and additive propagation. | Locked |
| C-007 | No new top-level CLI command groups beyond what the v1 contract requires. `spec-kitty mission run` may be a new subcommand on the existing `mission` group; no other new groups. | Locked |
| C-008 | Tests use real filesystem fixtures under `tmp_path`; no monkey-patching of the loader past well-defined seams. (Charter: "Integration tests for CLI commands.") | Locked |

## Success Criteria

1. Operators can run a project-authored custom mission end-to-end (`spec-kitty mission run` → `spec-kitty next`) with the same observable behavior as a built-in mission. Verifiable via the ERP fixture's full runtime walk in tests.
2. Operators authoring a custom mission without a retrospective marker see a single clear, structured error within one second of running the load command, naming the missing marker and the file path. Verifiable via a focused unit test against the validator.
3. Two layers exposing the same mission key produce a deterministic, named ambiguity error (or warning, per FR-011) listing every source path. No silent override. Verifiable via discovery-precedence tests.
4. All existing built-in missions continue passing their current test suites unchanged. Verifiable via `tests/specify_cli/next/test_runtime_bridge_composition.py` and the parity / coverage suites.
5. The `spec_kitty_runtime` import boundary remains clean: zero production imports under `src/`. Verifiable via `tests/architectural/test_shared_package_boundary.py`.
6. Validation errors are consumable by external tooling via `--json` output with stable error codes. Verifiable via JSON-schema-pinned tests.

## Key Entities

- **Custom mission definition file** — a YAML document under `.kittify/missions/<key>/mission.yaml` (or override path / pack manifest entry) whose top-level shape mirrors the existing internal runtime template (`mission.key`, `mission.name`, `mission.version`, `steps[]`, optional `audit_steps[]`).
- **Runtime step record** (per-step within `steps[]`) — at minimum `id`, `kind` (composed / decision_required), and either `agent_profile` (alias `agent-profile`) or an explicit action / contract binding. The retrospective step is recognized structurally (e.g., `id: retrospective`).
- **Discovery context** — the existing internal runtime `DiscoveryContext` (chain of explicit / env / project override / legacy / config / user global / built-in sources), unchanged in shape.
- **Mission step contract** — existing `MissionStepContract` records (`mission: <mission-key>`, `action: <step-id>` or explicit binding) loaded through `src/doctrine/mission_step_contracts/repository.py`. Each composed custom step expects a matching contract.
- **Tracked mission record** — the `kitty-specs/<mission-slug>/` directory created (or attached to) when `spec-kitty mission run` is invoked. Identity (mission_id ULID, mid8, slug, branch contract) follows the existing identity model documented in CLAUDE.md.

## Assumptions

- Discovery precedence (explicit / env / project override / project legacy / project config / user global / built-in) is already implemented in `_internal_runtime/discovery.py`; the loader extends it without reordering.
- Mission-pack discovery (`mission-pack.yaml`, `.kittify/config.yaml mission_packs`) is already wired through the same module. If any of these are not actually wired, the planning phase will scope a minimal addition rather than design a parallel mechanism.
- The runtime template shape (`mission.key`, `mission.name`, `mission.version`, `steps[]`, optional `audit_steps[]`) is the right authoring surface for v1. Any divergence is a planning-phase decision.
- "Structural retrospective marker" means `id: retrospective` on the last step (or a `retrospective: true` flag on a step). Exact spelling is locked in plan; the validator only requires recognizability.

## Out of Scope (defer-only)

- Any execution semantics for the retrospective step (deferred to #506 / #507 / #508 / #509 / #510 / #511).
- SaaS mission registry, `spec-kitty mission install`, cross-team distribution (deferred to #516).
- Cross-mission summary UI or HiC/autonomous lifecycle gating.
- Phase 7 work (#469).
- Adding new mission types beyond the loader's discovery; no new built-ins ship in this tranche.
- Changes to the retired `spec-kitty-runtime` PyPI package; that package stays retired.

## Dependencies

- Internal: `_internal_runtime/discovery.py`, `_internal_runtime/engine.py`, `_internal_runtime/planner.py`, `_internal_runtime/schema.py`, `mission_step_contracts/executor.py` (`StepContractExecutor`), `ProfileInvocationExecutor`, `runtime_bridge.py`, `cli/commands/mission.py`, `cli/commands/mission_type.py`, `doctrine/mission_step_contracts/repository.py`.
- External: `spec_kitty_events` (PyPI; payload models), `spec_kitty_tracker` (PyPI; per existing usage). No new external deps anticipated; planning will confirm.
- Preflight: [#798](https://github.com/Priivacy-ai/spec-kitty/issues/798) fix (`cedb77ff` locally on `main`) must remain in place. Architectural boundary test must stay green.
