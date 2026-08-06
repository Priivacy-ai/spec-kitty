# Implementation Plan: Supply Chain Security Checks Layer

**Branch**: `feat/supply-chain-security-checks-layer` | **Date**: 2026-08-06 | **Spec**: `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/spec.md`
**Input**: Feature specification from `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/spec.md`

## Summary

Add a built-in, advisory-by-default supply-chain security layer to the software-dev mission flow and core review/implementation profiles. The change is doctrine-first: author a new directive for install-time and dependency safety (registry authenticity, package freshness, lifecycle-script discipline, Node Active LTS awareness, and IoC posture), add/extend tactics, wire them into software-dev action indexes and step contracts, bind them into targeted agent profiles, and update SOURCE mission-step guidance. Keep v1 non-blocking at runtime (no new fail-closed transition handler), while requiring explicit evidence capture and adversarial-squad disposition at planning/review point-cuts.

## Technical Context

**Language/Version**: Python 3.11+ (repository baseline), YAML, Markdown
**Primary Dependencies**: Existing Spec Kitty stack only (`typer`, `rich`, `pytest`, `mypy`, `ruff`); no new third-party package required
**Storage**: Filesystem artifacts only (`packs/built-in/**`, `src/doctrine/**`, `kitty-specs/**`)
**Testing**: Targeted pytest suites for doctrine/action/profile wiring + architectural terminology/governance checks; red-to-green tests for new bindings
**Target Platform**: Cross-platform CLI (Linux/macOS/Windows)
**Project Type**: Single-project Python CLI monorepo
**Performance Goals**: No user-visible slowdown in charter/action-context resolution; planning/review command behavior remains functionally unchanged
**Constraints**:
- SOURCE-only edits for mission-step prompts (no generated agent-copy edits)
- No new built-in AppSec persona in v1
- No new fail-closed transition gate handler in v1
- No live external denylist synchronization in core
- Adversarial squad remains advisory cadence, but evidence/disposition is explicit
**Scale/Scope**:
- `packs/built-in/directives/` (new directive)
- `packs/built-in/tactics/` (new tactic + extension)
- `src/doctrine/missions/software-dev/actions/*/index.yaml`
- `src/doctrine/missions/built_in_step_contracts/*`
- `packs/built-in/agent_profiles/*.agent.yaml` + `packs/built-in/agent_profile.graph.yaml`
- `packs/built-in/action.graph.yaml`
- `src/doctrine/missions/mission-steps/software-dev/{plan,implement,review}/`
- Targeted tests under `tests/`

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority / canonical source unification** — PASS: doctrine updates land in canonical SOURCE surfaces only; no alternate authority introduced.
- **Architectural alignment** — PASS: changes stay inside existing doctrine + mission/action/profile seams; no cross-boundary runtime/package split added.
- **ATDD-first / test remediation discipline** — PASS (planned): every new binding path gets explicit test coverage and red-to-green validation.
- **Terminology canon** — PASS with watch: mission artifacts must preserve canonical terminology (`Mission`, not legacy synonyms).
- **Adversarial squad cadence** — PASS with explicit integration: cadence remains advisory per charter, but this mission requires explicit evidence/disposition capture in plan/review-facing artifacts.
- **Git/workflow discipline** — PASS: PR-bound branch already in use (`feat/supply-chain-security-checks-layer`), no direct protected-branch publish.

No charter violations require complexity exemptions at planning time.

## Project Structure

### Documentation (this mission)

```
kitty-specs/supply-chain-security-checks-layer-01KZBFBS/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── security-checks-layer-contract.md
│   └── adversarial-evidence-contract.md
└── tasks.md                 # created later by /spec-kitty.tasks
```

### Source Code (repository root)

```
packs/built-in/
├── directives/
│   └── 047-supply-chain-install-safety.directive.yaml          # new
├── tactics/
│   ├── architecture/dependency-hygiene.tactic.yaml             # extended (JS/TS + checks)
│   └── security/supply-chain-install-safety.tactic.yaml        # new
├── action.graph.yaml                                            # action scope edges
├── agent_profiles/
│   ├── reviewer-renata.agent.yaml
│   ├── implementer-ivan.agent.yaml
│   ├── node-norris.agent.yaml
│   ├── frontend-freddy.agent.yaml
│   ├── python-pedro.agent.yaml
│   ├── java-jenny.agent.yaml
│   └── architect-alphonso.agent.yaml
└── agent_profile.graph.yaml                                     # profile requires/suggests edges

src/doctrine/missions/
├── software-dev/actions/
│   ├── plan/index.yaml
│   ├── implement/index.yaml
│   └── review/index.yaml
├── built_in_step_contracts/
│   ├── plan.step-contract.yaml
│   ├── implement.step-contract.yaml
│   └── review.step-contract.yaml
└── mission-steps/software-dev/
    ├── plan/{prompt.md,guidelines.md}
    ├── implement/{prompt.md,guidelines.md}
    └── review/{prompt.md,guidelines.md}

tests/
└── ... targeted doctrine/context/architectural suites for new bindings
```

**Structure Decision**: Single-project doctrine-centric update. No new runtime subsystem or package boundary is introduced; all changes are additive wiring inside existing mission/action/profile artifacts.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Implementation Concern Map

> Implementation concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Directive and tactic authoring for supply-chain safety

- **Purpose**: Create the new supply-chain directive and operational tactic, and extend dependency hygiene for JS/TS to encode package authenticity, freshness, script discipline, Node LTS awareness, and incident/IoC posture.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-009.
- **Affected surfaces**: `packs/built-in/directives/`, `packs/built-in/tactics/architecture/dependency-hygiene.tactic.yaml`, `packs/built-in/tactics/security/`.
- **Sequencing/depends-on**: none.
- **Risks**: Over-specifying incident-specific details; must keep the directive threat-class based and point to CAS/vendor lists as external authority.

### IC-02 — Software-dev action and step-contract wiring

- **Purpose**: Bind the security layer into `plan`, `implement`, and `review` via action indexes and step contracts, while preserving existing transition gate semantics.
- **Relevant requirements**: FR-004, FR-005, FR-009.
- **Affected surfaces**: `src/doctrine/missions/software-dev/actions/*/index.yaml`, `src/doctrine/missions/built_in_step_contracts/*`, `packs/built-in/action.graph.yaml`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: Accidental hard-gating in v1; must avoid introducing new fail-closed handler behavior.

### IC-03 — Agent profile and DRG bindings

- **Purpose**: Add security references and self-review expectations to targeted existing profiles and connect them through profile graph edges.
- **Relevant requirements**: FR-006, FR-009.
- **Affected surfaces**: `packs/built-in/agent_profiles/*.agent.yaml`, `packs/built-in/agent_profile.graph.yaml`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: Inconsistent profile coverage; must ensure review + implementation profiles align on script approval and Node LTS posture.

### IC-04 — SOURCE mission-step guidance update

- **Purpose**: Update software-dev SOURCE prompts/guidelines so generated agent surfaces inherit the security-check behavior through canonical upgrade flow.
- **Relevant requirements**: FR-007, FR-010.
- **Affected surfaces**: `src/doctrine/missions/mission-steps/software-dev/{plan,implement,review}/`.
- **Sequencing/depends-on**: IC-01, IC-02.
- **Risks**: Editing generated copies by mistake; strict SOURCE-only path discipline required.

### IC-05 — Adversarial squad evidence integration

- **Purpose**: Ensure guidance contracts include explicit adversarial-squad cadence instructions and disposition rules for contested findings, with the chosen scope: plan/research plus review-facing artifacts.
- **Relevant requirements**: FR-010, NFR-005.
- **Affected surfaces**: directive/tactic text, review guidance sections, mission planning artifacts contract docs.
- **Sequencing/depends-on**: IC-01, IC-04.
- **Risks**: Ambiguous evidence expectations; must define a minimal, repeatable evidence contract.

### IC-06 — Regression validation and plan-phase readiness

- **Purpose**: Add/adjust tests that prove action wiring, step-contract wiring, profile bindings, and advisory compatibility; ensure plan outputs are substantive and committed for downstream phases.
- **Relevant requirements**: FR-008, NFR-001, NFR-002, NFR-003, NFR-004.
- **Affected surfaces**: targeted `tests/**`, mission planning artifacts under `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/`.
- **Sequencing/depends-on**: IC-02, IC-03, IC-04, IC-05.
- **Risks**: False confidence from incomplete test surface; test set must explicitly cover at least one path per binding category.
