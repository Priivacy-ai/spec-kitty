# Tasks: Doctrine Enrichment — Frontend, Brownfield, BDD, and Tactic Normalization

**Mission**: `doctrine-enrichment-frontend-brownfield-normalization-01KQ48XA`
**Branch**: `feature/doctrine-enrichment-bdd-profiles` → `main`
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Research**: [research.md](research.md)

---

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|-----|---------|
| T001 | Move 15 testing-discipline tactics from root to `shipped/testing/` | WP04 | N | [D] |
| T002 | Move 13 analysis tactics from root to `shipped/analysis/` | WP02 | N | [D] |
| T003 | Move 7 communication tactics from root to `shipped/communication/` | WP01 | N | [D] |
| T004 | Move 12 architecture tactics from root to `shipped/architecture/` | WP03 | N | [D] |
| T005 | Run `pytest -m doctrine`; assert tactic count unchanged | WP01 | N | [D] |
| T006 | Create `analysis/code-documentation-analysis.tactic.yaml` (adapted) | WP02 | N | [D] |
| T007 | Create `analysis/terminology-extraction-mapping.tactic.yaml` (adapted) | WP02 | [D] |
| T008 | Create provenance import files in `_reference/` for both tactics | WP02 | [D] |
| T009 | Verify both tactics load and pass schema validation | WP02 | N | [D] |
| T010 | Create `architecture/reference-architectural-patterns.tactic.yaml` (new) | WP03 | N | [D] |
| T011 | Create `architecture/development-bdd.tactic.yaml` + provenance import | WP03 | [D] |
| T012 | Extend `behavior-driven-development.tactic.yaml` notes (toolchain landscape, failure modes) | WP03 | [D] |
| T013 | Add `bdd-scenario-lifecycle` + `behaviour-driven-development` refs to BDD tactic | WP03 | N | [D] |
| T014 | Verify all WP03 YAML artifacts pass schema validation | WP03 | N | [D] |
| T015 | Create `testing/bug-fixing-checklist.tactic.yaml` (language-agnostic, test-first) | WP04 | N | [D] |
| T016 | Create `testing/test-readability-clarity-check.tactic.yaml` (dual-perspective) | WP04 | [D] |
| T017 | Verify both testing tactics pass schema validation | WP04 | N | [D] |
| T018 | Create `paradigms/shipped/behaviour-driven-development.paradigm.yaml` | WP05 | N | [D] |
| T019 | Create `procedures/shipped/bdd-scenario-lifecycle.procedure.yaml` | WP05 | [D] |
| T020 | Verify paradigm and procedure pass schema validation | WP05 | N | [D] |
| T021 | Create `agent_profiles/shipped/frontend-freddy.agent.yaml` (full profile + BDD enrichment) | WP06 | N | [D] |
| T022 | Verify Freddy passes schema validation and is resolvable by the profile repo | WP06 | N | [D] |
| T023 | Verify Freddy `avoidance-boundary` explicitly names Node Norris's domain | WP06 | N | [D] |
| T024 | Create `agent_profiles/shipped/node-norris.agent.yaml` (full profile + BDD enrichment) | WP07 | N | [D] |
| T025 | Verify Norris passes schema validation and is resolvable by the profile repo | WP07 | N | [D] |
| T026 | Verify Norris `avoidance-boundary` explicitly names Frontend Freddy's domain | WP07 | N | [D] |
| T027 | Add `bug-fixing-checklist` tactic ref to `implementer-ivan.agent.yaml` | WP08 | N | [D] |
| T028 | Add BDD tactic refs + paradigm ref to `reviewer-renata.agent.yaml` | WP08 | [D] |
| T029 | Add BDD paradigm ref + procedure context to `architect-alphonso.agent.yaml` | WP08 | [D] |
| T030 | Add BDD paradigm + tactic refs + self-review step to `java-jenny.agent.yaml` | WP08 | [D] |
| T031 | Verify all 4 updated profiles pass schema validation | WP08 | N | [D] |
| T032 | Write generic profile specialization tactic inheritance test | WP09 | N | [D] |
| T033 | Verify test passes with zero specialization pairs (empty fixture) | WP09 | N | [D] |
| T034 | Verify test catches missing inherited tactic refs in specialist profiles | WP09 | N | [D] |

**Requirement References:**
FR-001→WP06 | FR-002→WP07 | FR-003→WP02 | FR-004→WP01 | FR-005→WP03 | FR-006→WP04,WP08 | FR-007→WP04,WP08 | FR-008→WP09 | FR-009→WP05 | FR-010→WP05 | FR-011→WP06,WP07,WP08 | FR-012→WP03

---

## Phase 1 — Foundation (WP01–WP05, parallelizable)

### WP01 — Tactic Directory Normalization

**Priority**: P1 (foundation)
**Estimated prompt size**: ~200 lines
**Dependencies**: none
**Owned surface**: `src/doctrine/tactics/shipped/`

**Goal**: Move 7 communication-discipline tactics from `shipped/` root into `shipped/communication/`. Captures the canonical pre-move tactic count baseline for NFR-003. WP02/03/04 handle the analysis/, architecture/, and testing/ moves respectively alongside their new-file creation work.

**Included subtasks:**
- [x] T003 Move 7 communication tactics from root to `shipped/communication/` (WP01)
- [x] T005 Capture pre-move baseline count; run `pytest -m doctrine`; assert count unchanged (WP01)

**Risk**: Classification ambiguity for communication tactics. Mitigation: follow research.md guide.

**Prompt file**: [WP01-tactic-directory-normalization.md](tasks/WP01-tactic-directory-normalization.md)

---

### WP02 — Brownfield Analysis Tactics

**Priority**: P1
**Estimated prompt size**: ~280 lines
**Dependencies**: none (creates new files in `analysis/`; directory will exist after WP01 merges, or can be created by this WP if running in parallel)
**Owned surface**: `src/doctrine/tactics/shipped/analysis/` (moved + new files), `src/doctrine/_reference/quickstart-agent-augmented-development/candidates/`

**Goal**: Move 13 existing analysis tactics from root into `shipped/analysis/`, then create 2 new brownfield analysis tactics and record provenance.

**Included subtasks:**
- [x] T002 Move 13 analysis tactics from root to `shipped/analysis/` (WP02)
- [x] T006 Create `analysis/code-documentation-analysis.tactic.yaml` (WP02)
- [x] T007 Create `analysis/terminology-extraction-mapping.tactic.yaml` (WP02)
- [x] T008 Create provenance import files in `_reference/` for both tactics (WP02)
- [x] T009 Verify all analysis tactics load and pass schema validation (WP02)

**Prompt file**: [WP02-brownfield-analysis-tactics.md](tasks/WP02-brownfield-analysis-tactics.md)

---

### WP03 — Architecture Tactics + BDD Tactic Enrichment

**Priority**: P1
**Estimated prompt size**: ~420 lines
**Dependencies**: none
**Owned surface**: `src/doctrine/tactics/shipped/architecture/` (moved + new files), `src/doctrine/tactics/shipped/behavior-driven-development.tactic.yaml` (modified), `src/doctrine/_reference/` (new import)

**Goal**: Move 12 existing architecture tactics from root into `shipped/architecture/`, create 2 new architecture tactics, and enrich the existing BDD tactic.

**Included subtasks:**
- [x] T004 Move 12 architecture tactics from root to `shipped/architecture/` (WP03)
- [x] T010 Create `architecture/reference-architectural-patterns.tactic.yaml` (WP03)
- [x] T011 Create `architecture/development-bdd.tactic.yaml` + provenance import (WP03)
- [x] T012 Extend `behavior-driven-development.tactic.yaml` notes (WP03)
- [x] T013 Add procedure/paradigm refs to BDD tactic (WP03)
- [x] T014 Verify all WP03 YAML artifacts pass schema validation (WP03)

**Prompt file**: [WP03-architecture-tactics-and-bdd-enrichment.md](tasks/WP03-architecture-tactics-and-bdd-enrichment.md)

---

### WP04 — New Testing Tactics

**Priority**: P1
**Estimated prompt size**: ~260 lines
**Dependencies**: none
**Owned surface**: `src/doctrine/tactics/shipped/testing/` (moved + new files)

**Goal**: Move 15 existing testing tactics from root into `shipped/testing/`, then create 2 new testing tactics (bug-fixing checklist, test readability check).

**Included subtasks:**
- [x] T001 Move 15 testing tactics from root to `shipped/testing/` (WP04)
- [x] T015 Create `testing/bug-fixing-checklist.tactic.yaml` (WP04)
- [x] T016 Create `testing/test-readability-clarity-check.tactic.yaml` (WP04)
- [x] T017 Verify all testing tactics pass schema validation (WP04)

**Prompt file**: [WP04-new-testing-tactics.md](tasks/WP04-new-testing-tactics.md)

---

### WP05 — BDD Paradigm and Procedure

**Priority**: P1
**Estimated prompt size**: ~300 lines
**Dependencies**: none
**Owned surface**: `src/doctrine/paradigms/shipped/`, `src/doctrine/procedures/shipped/`

**Goal**: Create the `behaviour-driven-development` paradigm (encoding BDD as a collaboration practice with Discovery/Formulation/Automation) and the `bdd-scenario-lifecycle` procedure (covering Formulation → Automation → Maintenance).

**Included subtasks:**
- [x] T018 Create `paradigms/shipped/behaviour-driven-development.paradigm.yaml` (WP05)
- [x] T019 Create `procedures/shipped/bdd-scenario-lifecycle.procedure.yaml` (WP05)
- [x] T020 Verify paradigm and procedure pass schema validation (WP05)

**Prompt file**: [WP05-bdd-paradigm-and-procedure.md](tasks/WP05-bdd-paradigm-and-procedure.md)

---

## Phase 2 — Profiles (WP06–WP08, WP06/WP07 parallel)

### WP06 — Frontend Freddy Profile

**Priority**: P2
**Estimated prompt size**: ~320 lines
**Dependencies**: WP04 (bug-fixing-checklist tactic), WP05 (BDD paradigm/procedure)
**Owned surface**: `src/doctrine/agent_profiles/shipped/frontend-freddy.agent.yaml`

**Goal**: Create the complete Frontend Freddy agent profile — browser-side implementer specializing from `implementer-ivan`, with full specialization context, self-review protocol, and BDD references.

**Included subtasks:**
- [x] T021 Create `agent_profiles/shipped/frontend-freddy.agent.yaml` (WP06)
- [x] T022 Verify Freddy passes schema validation and resolves via profile repo (WP06)
- [x] T023 Verify Freddy `avoidance-boundary` explicitly names Node Norris domain (WP06)

**Prompt file**: [WP06-frontend-freddy-profile.md](tasks/WP06-frontend-freddy-profile.md)

---

### WP07 — Node Norris Profile

**Priority**: P2
**Estimated prompt size**: ~320 lines
**Dependencies**: WP04 (bug-fixing-checklist tactic), WP05 (BDD paradigm/procedure)
**Owned surface**: `src/doctrine/agent_profiles/shipped/node-norris.agent.yaml`

**Goal**: Create the complete Node Norris agent profile — server-side Node.js implementer specializing from `implementer-ivan`, with full specialization context, self-review protocol, and BDD references.

**Included subtasks:**
- [x] T024 Create `agent_profiles/shipped/node-norris.agent.yaml` (WP07)
- [x] T025 Verify Norris passes schema validation and resolves via profile repo (WP07)
- [x] T026 Verify Norris `avoidance-boundary` explicitly names Frontend Freddy domain (WP07)

**Prompt file**: [WP07-node-norris-profile.md](tasks/WP07-node-norris-profile.md)

---

### WP08 — Enrich Existing Profiles

**Priority**: P2
**Estimated prompt size**: ~380 lines
**Dependencies**: WP03 (development-bdd tactic), WP04 (bug-fixing, test-readability tactics), WP05 (BDD paradigm/procedure)
**Owned surface**: `src/doctrine/agent_profiles/shipped/implementer-ivan.agent.yaml`, `reviewer-renata.agent.yaml`, `architect-alphonso.agent.yaml`, `java-jenny.agent.yaml`

**Goal**: Add bug-fixing and BDD-related tactic/paradigm references to four existing profiles.

**Included subtasks:**
- [x] T027 Add `bug-fixing-checklist` ref to `implementer-ivan.agent.yaml` (WP08)
- [x] T028 Add BDD tactic refs + paradigm ref to `reviewer-renata.agent.yaml` (WP08)
- [x] T029 Add BDD paradigm + procedure context to `architect-alphonso.agent.yaml` (WP08)
- [x] T030 Add BDD paradigm + tactic refs + self-review step to `java-jenny.agent.yaml` (WP08)
- [x] T031 Verify all 4 updated profiles pass schema validation (WP08)

**Prompt file**: [WP08-enrich-existing-profiles.md](tasks/WP08-enrich-existing-profiles.md)

---

## Phase 3 — Tests (WP09)

### WP09 — Profile Specialization Tactic Inheritance Test

**Priority**: P3
**Estimated prompt size**: ~280 lines
**Dependencies**: WP06, WP07, WP08 (all profiles with tactic refs complete)
**Owned surface**: `tests/doctrine/test_profile_inheritance.py` (modified or new sibling)

**Goal**: Add a generic acceptance test asserting that any profile P specializing from base profile B must declare all tactic references that B declares. The test must pass with zero specialization pairs and must not hardcode any specific profile or tactic names.

**Included subtasks:**
- [x] T032 Write generic tactic inheritance test in `tests/doctrine/` (WP09)
- [x] T033 Verify test passes with zero specialization pairs (empty fixture) (WP09)
- [x] T034 Verify test catches missing inherited tactic refs in specialist profiles (WP09)

**Prompt file**: [WP09-profile-specialization-inheritance-test.md](tasks/WP09-profile-specialization-inheritance-test.md)
