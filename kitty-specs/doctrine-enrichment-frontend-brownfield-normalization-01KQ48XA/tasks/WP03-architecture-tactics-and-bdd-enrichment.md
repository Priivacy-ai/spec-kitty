---
work_package_id: WP03
title: Architecture Tactics and BDD Tactic Enrichment
dependencies: []
requirement_refs:
- FR-005
- FR-012
planning_base_branch: feature/doctrine-enrichment-bdd-profiles
merge_target_branch: feature/doctrine-enrichment-bdd-profiles
branch_strategy: Planning artifacts for this feature were generated on feature/doctrine-enrichment-bdd-profiles. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/doctrine-enrichment-bdd-profiles unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-doctrine-enrichment-frontend-brownfield-normalization-01KQ48XA
base_commit: 6bcf2d94a7fee98c225cf7a3988c6240f380863a
created_at: '2026-04-26T11:44:00.238706+00:00'
subtasks:
- T010
- T011
- T012
- T013
- T014
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "81134"
history:
- timestamp: '2026-04-26T08:49:24Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: src/doctrine/tactics/shipped/architecture/
execution_mode: code_change
owned_files:
- src/doctrine/tactics/shipped/architecture/aggregate-boundary-design.tactic.yaml
- src/doctrine/tactics/shipped/architecture/anti-corruption-layer.tactic.yaml
- src/doctrine/tactics/shipped/architecture/architecture-diagram-review-checklist.tactic.yaml
- src/doctrine/tactics/shipped/architecture/atomic-design-review-checklist.tactic.yaml
- src/doctrine/tactics/shipped/architecture/atomic-state-ownership.tactic.yaml
- src/doctrine/tactics/shipped/architecture/c4-zoom-in-architecture-documentation.tactic.yaml
- src/doctrine/tactics/shipped/architecture/compositional-stream-boundaries.tactic.yaml
- src/doctrine/tactics/shipped/architecture/cross-cutting-state-via-store.tactic.yaml
- src/doctrine/tactics/shipped/architecture/dependency-hygiene.tactic.yaml
- src/doctrine/tactics/shipped/architecture/domain-event-capture.tactic.yaml
- src/doctrine/tactics/shipped/architecture/language-driven-design.tactic.yaml
- src/doctrine/tactics/shipped/architecture/problem-decomposition.tactic.yaml
- src/doctrine/tactics/shipped/architecture/reference-architectural-patterns.tactic.yaml
- src/doctrine/tactics/shipped/architecture/development-bdd.tactic.yaml
- src/doctrine/tactics/shipped/behavior-driven-development.tactic.yaml
- src/doctrine/_reference/quickstart-agent-augmented-development/candidates/tactic-development-bdd.import.yaml
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load curator-carla
```

---

## Objective

This WP owns `src/doctrine/tactics/shipped/architecture/` end-to-end and also modifies `behavior-driven-development.tactic.yaml` in the `shipped/` root.

**Step 1 — Move 12 existing architecture tactics** from `shipped/` root to `shipped/architecture/` (see list below). Do NOT modify YAML content.

**Step 2 — Create 2 new architecture tactics**: `reference-architectural-patterns` (from scratch) and `development-bdd` (adapted from quickstart).

**Step 3 — Enrich existing `behavior-driven-development.tactic.yaml`** with toolchain notes, failure modes, and new references.

**Key distinction**: `development-bdd` (architecture-level, shapes system behavioral contracts) is purposely separate from `behavior-driven-development` (technique-level, describes how to write BDD scenarios). Their `purpose` fields must make this distinction clear.

**NFR-003 baseline**: After this WP, `len(repo.load_all())` must equal WP01 baseline + 2 (from WP02) + 2 (from this WP) = baseline + 4.

Create `architecture/` if WP01 has not merged: `mkdir -p src/doctrine/tactics/shipped/architecture/`

**Tactics to move from root → `architecture/`** (12 files):
```
aggregate-boundary-design.tactic.yaml
anti-corruption-layer.tactic.yaml
architecture-diagram-review-checklist.tactic.yaml
atomic-design-review-checklist.tactic.yaml
atomic-state-ownership.tactic.yaml
c4-zoom-in-architecture-documentation.tactic.yaml
compositional-stream-boundaries.tactic.yaml
cross-cutting-state-via-store.tactic.yaml
dependency-hygiene.tactic.yaml
domain-event-capture.tactic.yaml
language-driven-design.tactic.yaml
problem-decomposition.tactic.yaml
```

---

## Subtask T010 — Create `reference-architectural-patterns.tactic.yaml`

**File**: `src/doctrine/tactics/shipped/architecture/reference-architectural-patterns.tactic.yaml`

**Purpose**: Help architects identify and apply named reference architecture patterns to a problem context.

```yaml
schema_version: "1.0"
id: reference-architectural-patterns
name: Reference Architectural Patterns Selection
purpose: >
  Identify and apply established reference architecture patterns to a given problem context.
  Use when designing a new system or major subsystem, when an existing architecture is
  struggling with scaling, coupling, or maintainability, or when evaluating strategic
  options before committing to an implementation approach.
steps:
  - title: Characterize the problem domain
    description: >
      Describe the system's primary quality attribute requirements (scalability, consistency,
      latency, availability, deployability, modifiability) and the primary domain type
      (data-intensive, event-driven, user-facing, integration hub, batch processing).
      Be concrete: "needs 10k concurrent users" rather than "must scale".
  - title: Enumerate candidate patterns
    description: >
      List reference patterns relevant to the characterized domain. Common patterns to
      consider: Layered/N-Tier (predictable, testable, well-understood), Hexagonal/Ports
      and Adapters (domain isolation, testability), Event-Driven (decoupling, async),
      CQRS (separate read/write paths for high-traffic reads), Microservices (independent
      deployability at team scale), Modular Monolith (monolith with enforced module
      boundaries — often the right starting point), Pipe-and-Filter (data transformation
      pipelines), Space-Based (extreme horizontal scale).
  - title: Score each candidate against constraints
    description: >
      For each candidate pattern, score along three dimensions: coupling (how much does
      this pattern introduce distributed coupling?), scalability (does it address the
      characterized scale requirements?), operational complexity (what does this pattern
      demand from deployment, monitoring, and failure recovery?). Use H/M/L for each
      dimension. Eliminate patterns that score H on a constraint the system cannot afford.
  - title: Select and document rationale
    description: >
      Choose the pattern (or combination) with the best fit. Write an ADR capturing:
      the selected pattern, the constraints that drove the selection, the alternatives
      considered, and the trade-offs accepted. The ADR is the exit artifact of this tactic.
failure_modes:
  - "Pattern cargo-culting — adopting microservices or event-driven because they are fashionable, not because the constraints demand them."
  - "Skipping the scoring step — 'we'll use hexagonal' without checking whether the team can actually build and operate it."
  - "Missing the operational dimension — patterns that look good on paper (microservices) often have severe operational complexity costs."
  - "Starting with a complex pattern when a Modular Monolith would suffice — YAGNI applies to architecture."
notes: >
  The Modular Monolith is frequently underrated: it provides enforced module boundaries
  without distributed-system operational complexity. Prefer it as the default for new
  systems of moderate scale, and evolve toward microservices only when team or scale
  constraints make autonomous deployability necessary.
references:
  - name: Architecture Diagram Review Checklist
    type: tactic
    id: architecture-diagram-review-checklist
    when: After selecting a pattern, use this tactic to validate the design diagram
  - name: ADR Drafting Workflow
    type: tactic
    id: adr-drafting-workflow
    when: Document the selected pattern and its rationale in an ADR
  - name: AMMERSE Impact Analysis
    type: tactic
    id: ammerse-impact-analysis
    when: Use for high-stakes decisions to quantify trade-offs across the seven AMMERSE dimensions
```

---

## Subtask T011 — Create `development-bdd.tactic.yaml` + provenance import

**File**: `src/doctrine/tactics/shipped/architecture/development-bdd.tactic.yaml`

**Key point**: This is the architecture-level BDD tactic — it governs using BDD to define behavioral contracts that shape system boundaries. It is distinct from `behavior-driven-development` (the testing technique tactic). Make the `purpose` field clearly distinguishable.

```yaml
schema_version: "1.0"
id: development-bdd
name: BDD as Behavioral Contract Design
purpose: >
  Use Behaviour-Driven Development principles to define observable behavioral contracts
  before implementation begins, ensuring system boundaries are expressed in terms
  stakeholders can validate. Apply during design to establish what the system must do
  at its public interfaces — not how to write test scenarios (see the
  behavior-driven-development tactic for that). Outputs of this tactic serve as
  the behavioral contract that step definitions later implement.
steps:
  - title: Identify the observable behaviors
    description: >
      For the system or component being designed, list all externally observable outcomes.
      Each outcome is a candidate behavioral contract. Focus on what the system does at
      its boundary — not internal implementation. Ask: "What would a consumer observe
      when interacting with this system?"
  - title: Express each behavior as a Given/When/Then statement
    description: >
      Write a plain-language behavioral statement for each identified outcome:
      Given (the preconditions), When (the triggering event or action), Then (the
      observable outcome). These statements define the behavioral contract. Domain
      experts must be able to read and validate them without technical background.
  - title: Validate with domain experts
    description: >
      Review behavioral statements with stakeholders, product owners, or domain experts.
      A statement that surprises or confuses a domain expert is wrong — revise it.
      Validated statements become the authoritative design artifact.
  - title: Identify boundary conflicts and ambiguities
    description: >
      Review statements across components: where two components describe the same
      behavior, a boundary conflict exists. Where a statement is ambiguous about
      which component is responsible, a design gap exists. Resolve both before
      proceeding to implementation.
failure_modes:
  - "Writing behavioral contracts that encode implementation detail (database schemas, API internals) rather than observable outcomes."
  - "Skipping stakeholder validation — contracts written by engineers alone often specify the wrong behavior."
  - "Conflating this architectural tactic with test-writing — behavioral contracts defined here become the acceptance criteria for BDD scenarios, not the scenarios themselves."
notes: >
  Adapted from patterns.sddevelopment.be.
  This tactic produces the behavioral contract specification that feeds into the
  bdd-scenario-lifecycle procedure (Formulation phase). The output of this tactic
  is the input to the example-mapping-workshop procedure.
references:
  - name: Behavior-Driven Development
    type: tactic
    id: behavior-driven-development
    when: Use this tactic to translate the behavioral contracts into executable Given/When/Then scenarios
  - name: Example Mapping Workshop
    type: procedure
    id: example-mapping-workshop
    when: Use to collaboratively validate and refine the behavioral contracts with stakeholders
```

Also create `src/doctrine/_reference/quickstart-agent-augmented-development/candidates/tactic-development-bdd.import.yaml`:

```yaml
id: "imp-quickstart-development-bdd"
source:
  title: "Tactic: Development.BDD"
  type: "tactic"
  publisher: "quickstart_agent-augmented-development"
  accessed_on: "2026-04-26"
classification:
  target_concepts:
    - "tactic"
  rationale: >
    BDD as an architectural design practice — defining behavioral contracts at system
    boundaries before implementation. Placed under architecture/ because behavioral
    contracts shape system boundaries.
adaptation:
  summary: >
    Reframed from "how to do BDD" to "how to use BDD thinking during architectural
    design". Steps focus on identifying observable behaviors and establishing contracts,
    not on writing Gherkin scenarios. Distinguishes clearly from the existing
    behavior-driven-development tactic.
  notes:
    - "Source references patterns.sddevelopment.be — preserved as attribution in notes field."
    - "Failure modes added to prevent conflation with test-writing."
external_references:
  - title: "BDD Primer (patterns.sddevelopment.be)"
    url: "https://patterns.sddevelopment.be/primers/toolchain-and-automation/bdd"
    extraction_action: none
status: "adopted"
resulting_artifacts:
  - "src/doctrine/tactics/shipped/architecture/development-bdd.tactic.yaml"
```

---

## Subtask T012 — Extend `behavior-driven-development.tactic.yaml` notes

**File**: `src/doctrine/tactics/shipped/behavior-driven-development.tactic.yaml` (existing — modify in-place)

**What to add to the `notes` field** (append to existing content):

```
Toolchain landscape (informational — steps above are toolchain-agnostic):
- Specification language: Gherkin (.feature files) with Given/When/Then
- Runners: Cucumber-JVM (Java/Kotlin), Cucumber-JS (JavaScript/TypeScript),
  Behave (Python), SpecFlow (.NET/C#), Godog (Go)
- Browser automation: Playwright (modern, multi-language, built-in auto-wait),
  Selenium WebDriver (mature, W3C standard, Java/.NET ecosystem)
- Narrative reports: Serenity BDD (JVM) — Screenplay pattern + living documentation HTML
- Custom DSLs: when the domain vocabulary is highly specialised and stakeholders do not
  read Gherkin, a fluent internal DSL in the project language may replace Gherkin;
  trade-off: better domain expression, worse non-technical readability and no
  built-in living documentation
Source: patterns.sddevelopment.be/primers/toolchain-and-automation/bdd
```

---

## Subtask T013 — Add references to BDD paradigm and procedure

**File**: `src/doctrine/tactics/shipped/behavior-driven-development.tactic.yaml`

Add two entries to the `references` array (append, do not replace existing references):

```yaml
  - name: BDD Scenario Lifecycle
    type: procedure
    id: bdd-scenario-lifecycle
    when: After scenarios are written in Given/When/Then, use this procedure to wire them to executable tests and maintain them as living documentation
  - name: Behaviour-Driven Development Paradigm
    type: paradigm
    id: behaviour-driven-development
    when: For the philosophical and collaborative framing of BDD — Discovery/Formulation/Automation cycle, Three Amigos practice
```

Also extend `failure_modes` with these additions (append):
```yaml
  - "Rubber-stamp scenarios — writing Given/When/Then scenarios after the code is done to satisfy a process requirement, rather than letting them drive development."
  - "Shared mutable state between scenarios — Scenario B relying on state created by Scenario A breaks test isolation and makes the suite order-dependent."
  - "Orphaned step definitions — step definitions with no matching .feature step accumulate silently; run `cucumber --dry-run` (or equivalent) regularly to detect them."
```

---

## Subtask T014 — Verify all artifacts pass schema validation

```bash
python3 -c "
import sys; sys.path.insert(0, 'src')
from doctrine.tactics.repository import TacticRepository
r = TacticRepository()
all_tactics = r.load_all()
for id_ in ['reference-architectural-patterns', 'development-bdd', 'behavior-driven-development']:
    assert id_ in all_tactics, f'{id_} not found'
    print(f'OK: {id_}')
"
pytest -m doctrine -q
```

**Validation checklist**:
- [ ] `reference-architectural-patterns.tactic.yaml` exists in `architecture/`
- [ ] `development-bdd.tactic.yaml` exists in `architecture/` with `notes` attribution
- [ ] `behavior-driven-development.tactic.yaml` has toolchain landscape in `notes`
- [ ] `behavior-driven-development.tactic.yaml` has 3 new `failure_modes` entries
- [ ] `behavior-driven-development.tactic.yaml` has 2 new `references` entries
- [ ] Provenance import file created for `development-bdd`
- [ ] `pytest -m doctrine -q` is green

---

## Branch Strategy

No dependencies. Merges into `feature/doctrine-enrichment-bdd-profiles`.

```bash
spec-kitty agent action implement WP03 --agent claude
```

---

## Definition of Done

- 2 new YAML files in `shipped/architecture/`
- `behavior-driven-development.tactic.yaml` has toolchain notes, 3 new failure modes, 2 new references
- All 3 tactics load via the tactic repository
- `pytest -m doctrine -q` is green

## Reviewer Guidance

- Verify `development-bdd` and `behavior-driven-development` have clearly differentiated `purpose` fields
- Verify `notes` attribution line in `development-bdd`
- Verify toolchain section in `behavior-driven-development.notes` references `patterns.sddevelopment.be`
- Check that new `references` entries in BDD tactic reference IDs that will exist after WP05 merges

## Activity Log

- 2026-04-26T12:09:16Z – claude – shell_pid=76324 – 12 architecture tactics moved; reference-architectural-patterns + development-bdd created; BDD tactic enriched with toolchain notes + 3 new failure modes; doctrine tests green (1125 pass)
- 2026-04-26T12:12:23Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=81134 – Started review via action command
- 2026-04-26T12:13:27Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=81134 – Review passed: 12 architecture tactics renamed (100% similarity). reference-architectural-patterns and development-bdd created with clear purpose distinction. BDD tactic enriched with toolchain notes + 3 new failure modes (rubber-stamp, shared state, orphaned steps). Forward references to WP05 artifacts deferred correctly. Doctrine tests green.
- 2026-04-26T13:10:20Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=81134 – Done override: Feature merged to feature/doctrine-enrichment-bdd-profiles (squash merge commit 7383936b2)
