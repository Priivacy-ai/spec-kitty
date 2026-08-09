# Tasks: Supply Chain Security Checks Layer

**Input**: Design documents from `kitty-specs/supply-chain-security-checks-layer-01KZBFBS/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Author `051-supply-chain-install-safety` directive with policy rules and references | WP01 | |
| T002 | Extend `dependency-hygiene` for JavaScript/TypeScript supply-chain checks | WP01 | [P] |
| T003 | Add `supply-chain-install-safety` tactic with operational checklist | WP01 | [P] |
| T004 | Wire security artifacts into software-dev action indexes (`plan`, `implement`, `review`) | WP02 | |
| T005 | Add action-level scope edges for security artifacts in `packs/built-in/action.graph.yaml` | WP02 | [P] |
| T006 | Add security step to `plan.step-contract.yaml` | WP02 | |
| T007 | Add security step to `implement.step-contract.yaml` before quality gate | WP02 | |
| T008 | Add security step to `review.step-contract.yaml` with advisory compatibility | WP02 | |
| T009 | Bind `reviewer-renata` to directive/tactic and security-audit evidence expectations | WP03 | |
| T010 | Bind implementation-focused profiles (`implementer-ivan`, `node-norris`, `frontend-freddy`) | WP03 | [P] |
| T011 | Bind supporting profiles (`python-pedro`, `java-jenny`, `architect-alphonso`) | WP03 | [P] |
| T012 | Update `agent_profile.graph.yaml` with requires/suggests edges for new security layer | WP03 | |
| T013 | Update SOURCE `plan` mission-step guidance for security and adversarial cadence | WP04 | |
| T014 | Update SOURCE `implement` mission-step guidance for script discipline and Node LTS checks | WP04 | [P] |
| T015 | Update SOURCE `review` mission-step guidance for adversarial evidence disposition | WP04 | [P] |
| T016 | Add tests validating action-context security layer resolution | WP05 | |
| T017 | Add tests validating step-contract security-stage wiring and no new fail-closed gate | WP05 | |
| T018 | Add tests validating profile binding and adversarial evidence expectations | WP05 | |
| T019 | Run targeted suites and fix regressions (`tests/doctrine`, `tests/charter`, `tests/architectural`) | WP05 | |
| T020 | Run terminology guard and confirm mission-language compliance | WP05 | [P] |

## Work Packages

### WP01 — Author the security doctrine artifacts

- **Priority**: P1 (High) · **Requirements**: FR-001, FR-002, FR-003, FR-009
- **Goal**: Create the new directive/tactic layer and extend dependency hygiene so the policy is explicit before any workflow/profile wiring.
- **Independent Test**: Directive and tactic files parse, references resolve, and policy content includes registry authenticity, package freshness, lifecycle-script discipline, and Node LTS awareness.
- **Included subtasks**: T001, T002, T003
- **Dependencies**: none
- **Estimated prompt size**: ~300 lines

### WP02 — Wire software-dev workflow surfaces

- **Priority**: P1 (High) · **Requirements**: FR-004, FR-005, FR-009
- **Goal**: Integrate the layer into action indexes, step contracts, and action graph scope edges while keeping v1 advisory compatibility.
- **Independent Test**: Resolved context for `plan`/`implement`/`review` includes the new layer, and no new fail-closed transition handler is introduced.
- **Included subtasks**: T004–T008
- **Dependencies**: WP01
- **Estimated prompt size**: ~350 lines

### WP03 — Bind targeted agent profiles and graph edges

- **Priority**: P1 (High) · **Requirements**: FR-006, FR-009
- **Goal**: Update targeted built-in profiles and profile graph edges so behavior is consistent with workflow wiring.
- **Independent Test**: Profile payloads expose supply-chain checks and script/LTS posture for all targeted profiles.
- **Included subtasks**: T009–T012
- **Dependencies**: WP01
- **Estimated prompt size**: ~320 lines

### WP04 — Update SOURCE mission-step guidance and adversarial cadence coverage

- **Priority**: P2 (Medium) · **Requirements**: FR-007, FR-010, NFR-005
- **Goal**: Update SOURCE mission-step prompts/guidelines for `plan`/`implement`/`review` to encode security checks and adversarial evidence disposition expectations.
- **Independent Test**: SOURCE mission-step files include explicit adversarial cadence guidance for plan/research plus review-facing artifacts, with no generated-copy edits.
- **Included subtasks**: T013–T015
- **Dependencies**: WP01, WP02
- **Estimated prompt size**: ~260 lines

### WP05 — Regression validation and readiness verification

- **Priority**: P1 (High) · **Requirements**: FR-008, NFR-001, NFR-002, NFR-003, NFR-004
- **Goal**: Add and run targeted tests to prove action wiring, step-contract wiring, profile binding, and advisory compatibility.
- **Independent Test**: New/updated targeted suites are green; red-to-green path shown for each binding class.
- **Included subtasks**: T016–T020
- **Dependencies**: WP02, WP03, WP04
- **Estimated prompt size**: ~300 lines

## Dependency Graph

```text
WP01 ─┬─> WP02 ─┐
      ├─> WP03 ─┼─> WP05
      └─> WP04 ─┘
```

## Parallelization

- **After WP01**: WP02 and WP03 can run in parallel.
- **WP04**: can start after WP01+WP02.
- **WP05**: starts after WP02, WP03, and WP04 are complete.

## MVP Scope

WP01 + WP02 is the smallest coherent vertical slice (policy + workflow wiring). Full mission acceptance requires WP03–WP05 for profile alignment and validation evidence.
